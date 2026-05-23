"""
agents/code_builder_agent.py — Iterative npm install + build fixer agent.

Runs AFTER all code-generation agents complete:
  1. Locates the generated package.json inside the workspace.
  2. Pre-sanitises package.json (removes banned packages like shadcn-ui).
  3. Runs `npm install --legacy-peer-deps` to install dependencies.
     On ETARGET / E404 failures, deterministically patches package.json
     (strips bad version to "*", removes non-existent packages) and retries.
     No LLM is used for install failures — version resolution is a registry
     lookup problem, not an LLM problem.
  4. Runs `npm run build` (tsc + vite build) to verify the project compiles.
     On failure, asks the LLM to read the error log and fix source files.
  5. Repeats steps 3-4 until the build passes or MAX_BUILD_ATTEMPTS is hit.

NOTE: `npm run build` is used (not `npm run dev`) because it runs the TypeScript
compiler + bundler and exits with a proper success/failure code.
"""

import asyncio
import json
import re
import time
from pathlib import Path

import config
from agents.base_agent import AgentState, Status
from llm_client import LLMClient


MAX_BUILD_ATTEMPTS    = 5
MAX_INSTALL_ROUNDS    = 8   # max rounds of deterministic version-patching

# Packages that must never appear as npm dependencies (they are CLI tools,
# not installable libraries, or they simply do not exist on npm).
_BANNED_PACKAGES = {
    "shadcn-ui",
    "@shadcn/ui",
    "shadcn",
}

# ── Reference version table ───────────────────────────────────────────────────
# Loaded once from the proto-agent's own package.json so generated projects
# always use the same known-good, tested versions rather than LLM guesses.
def _load_reference_versions() -> dict[str, str]:
    """Return a flat {package: version} map from the repo-root package.json."""
    ref = Path(__file__).parent.parent / "package.json"
    if not ref.exists():
        return {}
    try:
        data = json.loads(ref.read_text(encoding="utf-8"))
        versions: dict[str, str] = {}
        for section in ("dependencies", "devDependencies"):
            versions.update(data.get(section, {}))
        return versions
    except Exception:
        return {}

_REFERENCE_VERSIONS: dict[str, str] = _load_reference_versions()

def _is_subpath_export(name: str) -> bool:
    """
    Return True when *name* looks like a module sub-path export rather than a
    real npm package name, e.g. "zustand/middleware", "react/jsx-runtime".

    Rules:
      - Scoped packages  (@scope/name)          → valid, return False
      - Unscoped with /  (zustand/middleware)    → sub-path, return True
    """
    if name.startswith("@"):
        # @scope/name is a valid package; @scope/name/sub would be a sub-path
        parts = name.lstrip("@").split("/")
        return len(parts) > 2          # e.g. @scope/pkg/sub
    return "/" in name                 # e.g. zustand/middleware


def _extract_pkg_name(pkg_at_ver: str) -> str:
    """
    Extract the package name from a '<name>@<version>' string.
    Handles both plain names ('react@^18.3.0') and scoped packages
    ('@radix-ui/react-dialog@^1.1.0').
    """
    pkg_at_ver = pkg_at_ver.rstrip(".")
    if pkg_at_ver.startswith("@"):
        # @scope/name@version  → split on '@', parts = ['', 'scope/name', 'version']
        parts = pkg_at_ver[1:].split("@", 1)
        return "@" + parts[0]
    else:
        return pkg_at_ver.split("@", 1)[0]


_BUILD_FIX_PROMPT = """You are a senior React + Vite + TypeScript developer performing automated error fixing.

You are given a build error log and the current contents of the files mentioned in the errors.
Fix ALL errors so the project builds successfully.

Return ONLY the fixed files using this exact format:

### FILE: <relative/path/from/project-root>
```
<complete corrected file contents — never truncate>
```

Rules:
- Output the COMPLETE file content for every changed file — no placeholders.
- Fix every error shown in the log.
- Do NOT touch files that are not related to the errors.
- Do NOT add "shadcn-ui", "@shadcn/ui", or "shadcn" as npm dependencies.
- If a package is missing or has an invalid version, fix it in package.json
  using only real, published npm packages with accurate semver ranges.
"""


class CodeBuilderAgent:
    """
    Post-generation build validator and auto-fixer.

    Install failures are fixed deterministically (no LLM).
    TypeScript / source build failures are fixed by the LLM.
    """

    AGENT_NAME = "CodeBuilder"
    AGENT_ICON = "🔨"

    def __init__(self, workspace: Path, global_log: list, plan: dict):
        self.workspace  = workspace
        self.global_log = global_log
        self.plan       = plan
        self.state      = AgentState(name=self.AGENT_NAME, icon=self.AGENT_ICON)
        self.llm        = LLMClient()
        # Log file written to output/ (parent of the workspace folder)
        output_dir = workspace.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = output_dir / "codebuilder_build.log"
        # Start fresh each run
        self.log_path.write_text(
            f"CodeBuilder log — {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Workspace: {workspace}\n"
            + "=" * 72 + "\n",
            encoding="utf-8",
        )

    # ── Public entry point ────────────────────────────────────────────────────

    async def run(self):
        self.state.status     = Status.RUNNING
        self.state.start_time = time.time()
        self.state.progress   = 3
        self.state.activity   = "Locating project…"
        self._glog("🔨 CodeBuilder Agent started")

        # 1. Find package.json
        pkg_json = self._find_package_json()
        if pkg_json is None:
            self._fail("No package.json found in workspace — DevAgent may have failed.")
            return

        project_dir = pkg_json.parent
        self._glog(f"📦 project root: {project_dir.relative_to(self.workspace)}")

        # 2. Pre-sanitise: remove banned packages + resolve real versions from npm registry
        self.state.activity = "Resolving package versions from npm registry…"
        self._glog("📌 Resolving package versions from npm registry…")
        self._sanitise_package_json(pkg_json)
        self._append_log("[SANITISED package.json]\n" + pkg_json.read_text(encoding="utf-8"))
        self.state.progress = 15

        # 2b. Static source-code fixes (patterns the LLM reliably gets wrong)
        self.state.activity = "Patching known bad code patterns…"
        fixed = self._fix_known_source_patterns(project_dir)
        if fixed:
            self._glog(f"🔧 Static source patches applied to {len(fixed)} file(s)")

        # 3. npm install — deterministic patch loop
        self.state.activity = "npm install…"
        ok = await self._install_loop(project_dir, pkg_json)
        if not ok:
            self._fail("npm install failed after all sanitisation attempts.")
            return

        self._glog("✅ npm install succeeded")
        self.state.progress = 38

        # 4. Build loop — LLM fixes TypeScript / source errors
        for attempt in range(1, MAX_BUILD_ATTEMPTS + 1):
            self.state.activity = f"npm run build (attempt {attempt}/{MAX_BUILD_ATTEMPTS})…"
            self._glog(f"🔨 npm run build — attempt {attempt}/{MAX_BUILD_ATTEMPTS}")

            ok, output = await self._npm(["run", "build"], project_dir)
            self._append_log(
                f"[npm run build attempt {attempt} — {'OK' if ok else 'FAILED'}]\n{output}"
            )
            self.state.progress = 38 + int(attempt / MAX_BUILD_ATTEMPTS * 57)

            if ok:
                self.state.status   = Status.COMPLETED
                self.state.progress = 100
                self.state.end_time = time.time()
                self.state.activity = f"Build succeeded on attempt {attempt} ✅"
                self._glog(
                    f"✅ CodeBuilder: build succeeded on attempt {attempt} "
                    f"in {self.state.elapsed}"
                )
                return

            self._glog(
                f"⚠️  Build failed (attempt {attempt}) — "
                f"asking LLM to fix errors…"
            )
            self.state.activity = f"LLM fixing build errors (attempt {attempt})…"
            if not await self._llm_fix_build(output, project_dir):
                self._glog(f"⚠️  LLM produced no fixable files on attempt {attempt}")

        self._fail(f"Build still failing after {MAX_BUILD_ATTEMPTS} LLM fix attempts.")

    # ── npm install — deterministic patch loop ────────────────────────────────

    async def _install_loop(self, project_dir: Path, pkg_json: Path) -> bool:
        """
        Run `npm install --legacy-peer-deps` repeatedly.
        After each failure, parse ETARGET / E404 errors and patch package.json:
          - ETARGET / notarget → version doesn't exist  → set to "*"
          - E404 / 404         → package doesn't exist  → remove it
        Never calls the LLM — this is a pure registry-lookup problem.
        """
        for round_ in range(1, MAX_INSTALL_ROUNDS + 1):
            self.state.activity = f"npm install (round {round_})…"
            self._glog(f"📦 npm install --legacy-peer-deps (round {round_})…")

            ok, output = await self._npm(
                ["install", "--legacy-peer-deps", "--verbose"], project_dir
            )
            self._append_log(
                f"[npm install round {round_} — {'OK' if ok else 'FAILED'}]\n{output}"
            )
            if ok:
                return True

            patched = self._patch_pkg_from_npm_errors(output, pkg_json)
            if not patched:
                self._glog(
                    "⚠️  No ETARGET/E404 patterns found in npm output — "
                    "cannot auto-fix further."
                )
                return False

        self._glog(f"⚠️  npm install still failing after {MAX_INSTALL_ROUNDS} patch rounds.")
        return False

    # ── package.json helpers ──────────────────────────────────────────────────

    def _sanitise_package_json(self, pkg_json: Path):
        """
        Clean up package.json before the first npm install:
          1. Remove banned packages (shadcn-ui, etc.).
          2. For every remaining package, replace the LLM-invented version with:
               a. The version from the repo-root package.json  (preferred — known-good)
               b. The real latest version from the npm registry (fallback for
                  packages not present in the reference)
        This eliminates ETARGET errors at the source.
        """
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
        except Exception:
            return

        changed = False

        # Step 1 — remove banned packages and sub-path pseudo-packages
        for section in ("dependencies", "devDependencies", "peerDependencies"):
            deps: dict = data.get(section, {})
            for pkg in list(deps):
                if pkg in _BANNED_PACKAGES:
                    del deps[pkg]
                    self._glog(f"🗑️  Removed banned package '{pkg}' from {section}")
                    changed = True
                elif _is_subpath_export(pkg):
                    del deps[pkg]
                    self._glog(
                        f"🗑️  Removed sub-path export '{pkg}' from {section} "
                        f"(import path, not an npm package)"
                    )
                    changed = True

        # Step 2 — collect all packages that still need a version resolved
        all_pkgs: list[str] = []
        for section in ("dependencies", "devDependencies"):
            all_pkgs.extend(data.get(section, {}).keys())

        # Step 3 — build resolved version map (reference first, then registry)
        needs_registry: list[str] = []
        resolved: dict[str, str] = {}
        for pkg in all_pkgs:
            if pkg in _REFERENCE_VERSIONS:
                resolved[pkg] = _REFERENCE_VERSIONS[pkg]
            else:
                needs_registry.append(pkg)

        if needs_registry:
            self._glog(
                f"🌐 Fetching versions from npm registry for "
                f"{len(needs_registry)} unlisted package(s)…"
            )
            registry_versions = self._resolve_versions_from_registry(needs_registry)
            resolved.update(registry_versions)

        ref_hits = sum(1 for p in all_pkgs if p in _REFERENCE_VERSIONS)
        self._glog(
            f"📌 Version source: {ref_hits} from reference package.json, "
            f"{len(needs_registry)} from npm registry"
        )

        # Step 4 — apply resolved versions
        for section in ("dependencies", "devDependencies"):
            deps: dict = data.get(section, {})
            for pkg in list(deps):
                if pkg in resolved:
                    old = deps[pkg]
                    new = resolved[pkg]
                    if old != new:
                        deps[pkg] = new
                        self._glog(f"  {pkg}: {old!r} → {new!r}")
                        changed = True

        if changed:
            pkg_json.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _resolve_versions_from_registry(self, packages: list[str]) -> dict[str, str]:
        """
        Fetch real latest versions from registry.npmjs.org concurrently.
        Returns {package: "^<latest>"} for packages that resolve successfully.
        """
        import concurrent.futures
        import urllib.request

        def fetch_latest(pkg: str) -> tuple[str, str | None]:
            encoded = pkg.replace("@", "%40").replace("/", "%2F") if pkg.startswith("@") else pkg
            url = f"https://registry.npmjs.org/{encoded}/latest"
            try:
                with urllib.request.urlopen(url, timeout=10) as resp:
                    meta = json.loads(resp.read())
                    return pkg, meta.get("version")
            except Exception:
                return pkg, None

        result: dict[str, str] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            futures = {pool.submit(fetch_latest, pkg): pkg for pkg in packages}
            for future in concurrent.futures.as_completed(futures, timeout=30):
                try:
                    pkg, version = future.result()
                    if version:
                        result[pkg] = f"^{version}"
                except Exception:
                    pass
        return result

    def _patch_pkg_from_npm_errors(self, error_log: str, pkg_json: Path) -> bool:
        """
        Parse npm error output and update package.json:
          - Packages with a bad version  → version set to "*"
          - Packages that don't exist    → removed
        Returns True if at least one change was made.
        """
        strip_version: set[str] = set()
        remove_pkg:    set[str] = set()

        # "No matching version found for <pkg>@<ver>"  (handles @scope/name too)
        for m in re.finditer(
            r"No matching version found for (\S+)", error_log, re.IGNORECASE
        ):
            strip_version.add(_extract_pkg_name(m.group(1)))

        # "notarget ... for <pkg>@<ver>"
        for m in re.finditer(
            r"notarget\b.*?\bfor\s+(\S+)", error_log, re.IGNORECASE
        ):
            strip_version.add(_extract_pkg_name(m.group(1)))

        # "404  '<pkg>' is not in this registry"
        for m in re.finditer(
            r"404\s+['\"]?(@?[\w\-./]+)['\"]?\s+is not in this registry",
            error_log, re.IGNORECASE,
        ):
            remove_pkg.add(m.group(1))

        if not strip_version and not remove_pkg:
            return False

        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
        except Exception:
            return False

        changed = False
        for section in ("dependencies", "devDependencies", "peerDependencies"):
            deps: dict = data.get(section, {})
            for pkg in list(deps):
                if pkg in remove_pkg:
                    del deps[pkg]
                    self._glog(f"🗑️  Removed non-existent package: {pkg}")
                    changed = True
                elif pkg in strip_version:
                    old = deps[pkg]
                    deps[pkg] = "*"
                    self._glog(f"🔧  Version fixed: {pkg} {old!r} → '*'")
                    changed = True

        if changed:
            pkg_json.write_text(json.dumps(data, indent=2), encoding="utf-8")

        return changed

    # ── LLM build-error fixer ─────────────────────────────────────────────────

    async def _llm_fix_build(self, error_log: str, project_dir: Path) -> bool:
        """Send build errors + relevant file contents to the LLM and apply fixes."""
        file_context = self._gather_error_files(error_log, project_dir)

        user_msg = (
            f"Build error log:\n```\n{error_log[-8000:]}\n```\n\n"
            f"Current file contents:\n{file_context}\n\n"
            "Fix all errors. Return every changed file in ### FILE: format."
        )

        try:
            raw = await self.llm.complete(_BUILD_FIX_PROMPT, user_msg, timeout=180.0)
        except Exception as exc:
            self._glog(f"⚠️  LLM request failed: {exc}")
            return False

        pattern = re.compile(
            r"###\s*FILE:\s*(.+?)\n```[^\n]*\n([\s\S]+?)```",
            re.MULTILINE,
        )
        matches = pattern.findall(raw)
        if not matches:
            return False

        for rel_path, content in matches:
            rel_path = rel_path.strip().lstrip("/")
            target   = project_dir / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            self.state.output_files.append(rel_path)
            self._glog(f"🔧 Fixed: {rel_path}")

        return True

    def _gather_error_files(self, error_log: str, project_dir: Path) -> str:
        """Read the source files referenced in TypeScript / Vite error output."""
        path_re = re.compile(
            r"\b((?:src|tests?)/[\w./\-]+\.(?:tsx?|jsx?|css|json))\b"
        )
        found: set[str] = {"package.json"}
        for m in path_re.finditer(error_log):
            if (project_dir / m.group(1)).exists():
                found.add(m.group(1))

        if len(found) <= 1:
            for fb in ("src/main.tsx", "src/App.tsx", "vite.config.ts"):
                if (project_dir / fb).exists():
                    found.add(fb)

        snippets: list[str] = []
        for rel in sorted(found):
            p = project_dir / rel
            if p.exists():
                content = p.read_text(encoding="utf-8", errors="replace")
                if len(content) > 6000:
                    content = content[:6000] + "\n… (truncated)"
                snippets.append(f"### FILE: {rel}\n```\n{content}\n```")

        return "\n\n".join(snippets) if snippets else "(no matching files found)"

    # ── Subprocess runner ─────────────────────────────────────────────────────

    async def _npm(
        self,
        args: list[str],
        cwd: Path,
        timeout: int = 300,
    ) -> tuple[bool, str]:
        """
        Run `npm <args>` inside *cwd* using shell=True (required on Windows
        where npm is npm.cmd).  Returns (success, combined_stdout+stderr).
        """
        cmd = "npm " + " ".join(args)
        self._glog(f"  $ {cmd}  (cwd={cwd.name})")

        loop = asyncio.get_event_loop()

        def _blocking():
            import subprocess
            result = subprocess.run(
                cmd,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                shell=True,
                timeout=timeout,
            )
            return result.returncode == 0, (result.stdout + result.stderr)

        try:
            ok, output = await asyncio.wait_for(
                loop.run_in_executor(None, _blocking),
                timeout=timeout + 30,
            )
        except asyncio.TimeoutError:
            return False, f"Command '{cmd}' timed out after {timeout}s"
        except Exception as exc:
            return False, f"Command '{cmd}' raised: {exc}"

        # Tail to live log so dashboard feels alive
        for line in output.strip().splitlines()[-15:]:
            if line.strip():
                self.state.log(f"  {line[:120]}")

        return ok, output

    # ── Misc helpers ──────────────────────────────────────────────────────────

    def _find_package_json(self) -> Path | None:
        """Return the shallowest package.json not inside node_modules."""
        candidates = sorted(
            (p for p in self.workspace.rglob("package.json")
             if "node_modules" not in p.parts),
            key=lambda p: len(p.parts),
        )
        return candidates[0] if candidates else None

    def _fix_known_source_patterns(self, project_dir: Path) -> list[str]:
        """
        Apply deterministic regex patches to .ts/.tsx source files for patterns
        the LLM reliably gets wrong.  Returns a list of relative paths that were
        modified.

        Current rules
        ─────────────
        1. Zustand — remove non-existent <ZustandProvider> / <StoreProvider> wrappers
           from main.tsx / App.tsx and their import lines.
        2. Zustand — replace `import { useStore } from 'zustand'` with nothing
           (useStore doesn't exist; each store is its own hook).
        """
        modified: list[str] = []

        tsx_files = [
            f for f in project_dir.rglob("*.tsx")
            if "node_modules" not in f.parts
        ]
        ts_files = [
            f for f in project_dir.rglob("*.ts")
            if "node_modules" not in f.parts
        ]

        for path in tsx_files + ts_files:
            try:
                original = path.read_text(encoding="utf-8")
            except Exception:
                continue

            patched = original

            # ── Rule 1: remove ZustandProvider / StoreProvider JSX wrapper ──
            # Matches patterns like:
            #   <ZustandProvider>...</ZustandProvider>
            #   <StoreProvider store={store}>...</StoreProvider>
            for tag in ("ZustandProvider", "StoreProvider"):
                # Opening tag (with optional attrs)
                patched = re.sub(
                    rf"<{tag}(\s[^>]*)?>",
                    "",
                    patched,
                )
                # Closing tag
                patched = re.sub(rf"</{tag}>", "", patched)

            # ── Rule 2: remove import lines for ZustandProvider / StoreProvider ──
            patched = re.sub(
                r"^.*import[^;]*?(ZustandProvider|StoreProvider)[^;]*;?\s*\n",
                "",
                patched,
                flags=re.MULTILINE,
            )

            # ── Rule 3: remove `import { useStore } from 'zustand'` ──
            patched = re.sub(
                r"^.*import\s*\{[^}]*\buseStore\b[^}]*\}\s*from\s*['\"]zustand['\"];?\s*\n",
                "",
                patched,
                flags=re.MULTILINE,
            )

            if patched != original:
                path.write_text(patched, encoding="utf-8")
                rel = str(path.relative_to(project_dir))
                modified.append(rel)
                self._glog(f"🔧 Static patch applied: {rel}")

        return modified

    def _append_log(self, section: str):
        """Append a labelled section to the build log file."""
        try:
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(f"\n{'─' * 72}\n")
                f.write(f"[{time.strftime('%H:%M:%S')}] {section}\n")
        except Exception:
            pass   # never crash the agent over a logging failure

    def _fail(self, reason: str):
        self.state.status   = Status.FAILED
        self.state.error    = reason
        self.state.activity = f"ERROR: {reason}"
        self.state.end_time = time.time()
        self._glog(f"❌ CodeBuilder: {reason}")

    def _glog(self, msg: str):
        self.state.log(msg)
        ts    = time.strftime("%H:%M:%S")
        entry = f"[{ts}] [{self.AGENT_NAME}] {msg}"
        self.global_log.append(entry)
        if len(self.global_log) > 500:
            del self.global_log[:-500]
