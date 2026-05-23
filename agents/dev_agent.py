"""agents/dev_agent.py — Full React + Vite code generation agent."""
import re
from pathlib import Path
from agents.base_agent import BaseAgent


class DevAgent(BaseAgent):
    AGENT_NAME    = "Development"
    AGENT_ICON    = "💻"
    OUTPUT_SUBDIR = "src"

    @property
    def system_prompt(self) -> str:
        return """You are a senior full-stack React + Vite developer.
Generate a complete, production-ready React + Vite + TypeScript project.

Structure your response as a series of FILE BLOCKS. Each file block uses this exact format:

### FILE: <relative/path/to/file>
```
<complete file contents>
```

You MUST generate ALL of the following files (adapt names to the project):
- package.json
- vite.config.ts
- tsconfig.json
- tsconfig.node.json
- index.html
- tailwind.config.js
- postcss.config.js
- .eslintrc.cjs
- src/main.tsx
- src/App.tsx
- src/index.css
- src/vite-env.d.ts
- src/types/index.ts
- src/hooks/useApi.ts (or relevant custom hooks)
- src/store/ or src/context/ (state management)
- src/services/api.ts (API layer with mock data)
- src/components/ (ALL components listed in the plan)
- src/pages/ (ALL pages listed in the plan)
- src/components/ui/ (Button, Card, Input, Modal, etc.)
- src/utils/helpers.ts
- .env.example

Rules:
- Use TypeScript strictly typed
- Use Tailwind CSS for styling
- Include proper imports/exports
- Make components functional with hooks
- Include meaningful placeholder data
- Every file must be complete and runnable
- Do NOT truncate or use placeholders like "// ... rest of component"

CRITICAL — package.json dependency rules:
- Do NOT add "shadcn-ui", "@shadcn/ui", or "shadcn" as a dependency. shadcn/ui is a CLI
  that copies component source into the project — it is never a runtime npm package.
- Instead, implement all UI primitives directly using Tailwind CSS classes inside src/components/ui/.
- If you need Radix UI primitives use the correct scoped packages:
    "@radix-ui/react-dialog", "@radix-ui/react-dropdown-menu", "@radix-ui/react-tooltip", etc.
- Add "class-variance-authority", "clsx", "tailwind-merge", and "lucide-react" when building
  shadcn-style components.
- Only use real, published npm packages with accurate semver ranges.
  Common safe versions (as of 2024): react@^18.3.0, react-router-dom@^6.23.0,
  @tanstack/react-query@^5.40.0, zustand@^4.5.0, axios@^1.7.0,
  tailwindcss@^3.4.0, vite@^5.3.0, typescript@^5.4.0, @vitejs/plugin-react@^4.3.0.
- Never invent package names or version numbers.
- NEVER add sub-path imports as npm dependencies. Sub-paths are import paths used
  in code, not installable packages. Examples of what NOT to add:
    "zustand/middleware", "react/jsx-runtime", "react-dom/client",
    "@tanstack/react-query/devtools".
  The parent package ("zustand", "react", etc.) is the npm dependency.
  Use sub-paths only inside import statements in .ts/.tsx files.

CRITICAL — Zustand usage rules:
- Zustand does NOT use a Provider. NEVER wrap any component with <ZustandProvider>,
  <StoreProvider>, or any similar Zustand context wrapper — they do not exist.
- NEVER import "useStore" from "zustand". That export does not exist in Zustand v4+.
- The ONLY correct way to use Zustand:
    // Define the store:
    import { create } from 'zustand';
    const useAuthStore = create<AuthState>((set) => ({ ... }));
    // Consume directly in any component — no Provider needed:
    const { user, login } = useAuthStore();
- Middleware is imported from the sub-path, NOT installed as a separate package:
    import { persist } from 'zustand/middleware';
    import { devtools } from 'zustand/middleware';
- The only wrappers allowed in src/main.tsx are: <BrowserRouter>, <QueryClientProvider>,
  and <StrictMode>. Do not add any other Providers unless the library explicitly requires one.

CRITICAL — src/main.tsx MUST follow this exact structure (no deviations):
```tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';
import './index.css';

const queryClient = new QueryClient();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>
);
```
Rules for main.tsx:
- NO ZustandProvider, StoreProvider, or any store-related wrapper.
- NO useStore import.
- NO extra context providers unless a specific library (e.g. Toaster) needs one.
- Zustand stores are imported and called directly inside each component that needs them.
"""

    def user_prompt(self) -> str:
        components = ", ".join(self.plan.get("components", []))
        pages = "\n".join(
            f"  - {p['name']} ({p['route']}): {p['description']}"
            for p in self.plan.get("pages", [])
        )
        endpoints = "\n".join(
            f"  - {e['method']} {e['path']}: {e['description']}"
            for e in self.plan.get("api_endpoints", [])
        )
        return f"""Requirements:
---
{self.requirements}
---

Plan:
{self.plan_summary()}

Pages to build:
{pages}

Components to build: {components}

API endpoints to mock:
{endpoints}

State management: {self.plan.get('state_management', 'React Context')}
Styling: {self.plan.get('styling', 'Tailwind CSS')}

Specific dev task: {self.plan.get('agent_tasks', {}).get('dev', 'Build complete React/Vite app.')}

Generate ALL project files now using the ### FILE: format."""

    async def process_output(self, raw: str):
        """Parse FILE blocks and write each one to disk."""
        # Pattern: ### FILE: path\n```...\n```
        pattern = re.compile(
            r"###\s*FILE:\s*(.+?)\n```[^\n]*\n([\s\S]+?)```",
            re.MULTILINE,
        )
        matches = pattern.findall(raw)

        if not matches:
            # Fallback: save the raw output
            self.write_file("generated_code.md", raw)
            return

        for rel_path, content in matches:
            rel_path = rel_path.strip()
            # Safety: strip leading slashes / src/ prefix duplications
            rel_path = rel_path.lstrip("/")
            self.write_file(rel_path, content)

        # Also write a full dump for reference
        self.write_file("_full_generation_log.md", raw)
