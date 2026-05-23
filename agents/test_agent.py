"""agents/test_agent.py — Test suite generation agent."""
import re
from agents.base_agent import BaseAgent


class TestAgent(BaseAgent):
    AGENT_NAME    = "Tests"
    AGENT_ICON    = "🧪"
    OUTPUT_SUBDIR = "tests"

    @property
    def system_prompt(self) -> str:
        return """You are a senior QA engineer and testing expert for React + TypeScript + Vite projects.

Generate a comprehensive test suite using Vitest + React Testing Library + MSW (Mock Service Worker).

Structure your response as FILE BLOCKS using this format:
### FILE: <path>
```
<complete test file content>
```

Generate ALL of the following:
- vitest.config.ts
- src/test/setup.ts (test setup file)
- src/test/mocks/handlers.ts (MSW request handlers)
- src/test/mocks/server.ts (MSW server setup)
- src/test/utils/render.tsx (custom render with providers)
- Unit tests for every component (src/components/__tests__/<Component>.test.tsx)
- Integration tests for every page (src/pages/__tests__/<Page>.test.tsx)
- Hook tests (src/hooks/__tests__/<hook>.test.ts)
- API service tests (src/services/__tests__/api.test.ts)
- E2E test plan (docs/e2e_test_plan.md) — describe Playwright scenarios
- Test coverage configuration

Each test file must:
- Use describe/it/expect blocks
- Test happy path, edge cases, and error states
- Include snapshot tests where relevant
- Test user interactions (click, type, submit)
- Mock external dependencies
- Include accessibility checks with @testing-library/jest-dom
"""

    def user_prompt(self) -> str:
        components = ", ".join(self.plan.get("components", []))
        return f"""Requirements:
---
{self.requirements}
---

Plan:
{self.plan_summary()}

Components to test: {components}
Test framework: {self.plan.get('test_framework', 'Vitest + React Testing Library')}

Specific test task: {self.plan.get('agent_tasks', {}).get('tests', 'Write comprehensive tests.')}

Generate ALL test files now using the ### FILE: format."""

    async def process_output(self, raw: str):
        pattern = re.compile(
            r"###\s*FILE:\s*(.+?)\n```[^\n]*\n([\s\S]+?)```",
            re.MULTILINE,
        )
        matches = pattern.findall(raw)
        if not matches:
            self.write_file("test_suite.md", raw)
            return
        for rel_path, content in matches:
            self.write_file(rel_path.strip(), content)
        self.write_file("_test_generation_log.md", raw)
