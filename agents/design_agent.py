"""agents/design_agent.py — UI/UX Design System agent."""
from pathlib import Path
from agents.base_agent import BaseAgent


class DesignAgent(BaseAgent):
    AGENT_NAME    = "Design"
    AGENT_ICON    = "🎨"
    OUTPUT_SUBDIR = "design"

    @property
    def system_prompt(self) -> str:
        return """You are a senior UI/UX designer and design system architect.
Create a comprehensive, production-quality design document for a React + Vite prototype.

Your output must be a single well-structured Markdown document covering:
1. Design Philosophy & Aesthetic Direction
2. Color Palette (hex values, CSS variable names, usage rules)
3. Typography System (font families, scale, weights, line heights)
4. Spacing & Layout Grid
5. Component Library Catalogue (for every component: purpose, variants, states, props)
6. Icon System recommendations
7. Animation & Motion guidelines
8. Responsive breakpoints
9. Accessibility guidelines (WCAG 2.1 AA)
10. Design Tokens (as a JSON snippet)
11. Page-by-page wireframe descriptions
12. User Flow diagrams (text-based ASCII art)

Be specific with exact values. Use tables where appropriate. Include CSS variable declarations."""

    def user_prompt(self) -> str:
        return f"""Requirements:
---
{self.requirements}
---

Plan:
{self.plan_summary()}

Specific design task: {self.plan.get('agent_tasks', {}).get('design', 'Create full UI/UX design system.')}

Generate the complete UI/UX Design System document now."""

    async def process_output(self, raw: str):
        self.write_file("ui_design_system.md", raw)
        # Also write a quick design tokens JSON extraction hint file
        tokens_stub = self._extract_tokens_hint(raw)
        if tokens_stub:
            self.write_file("design_tokens.json", tokens_stub)

    @staticmethod
    def _extract_tokens_hint(raw: str) -> str:
        import re, json
        # Try to find JSON block for design tokens
        m = re.search(r"```json\s*(\{[\s\S]+?\})\s*```", raw)
        if m:
            try:
                json.loads(m.group(1))
                return m.group(1)
            except Exception:
                pass
        return ""
