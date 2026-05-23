"""agents/readme_agent.py — README.md generation agent."""
from agents.base_agent import BaseAgent


class ReadmeAgent(BaseAgent):
    AGENT_NAME    = "README"
    AGENT_ICON    = "📖"
    OUTPUT_SUBDIR = ""   # goes to workspace root

    @property
    def system_prompt(self) -> str:
        return """You are a technical writer who creates stunning, comprehensive README files for open-source projects.

Generate a single README.md that is:
- Visually impressive with proper badges, emojis, and formatting
- Complete with all essential sections
- Written with developer empathy

Required sections:
1. Project header (logo placeholder, title, tagline)
2. Badges (build status, coverage, version, license, node version)
3. Table of Contents (with anchor links)
4. ✨ Features (detailed feature list with emojis)
5. 🖼️ Screenshots (placeholder image links with descriptions)
6. 🏗️ Architecture Overview (text diagram)
7. 🛠️ Tech Stack (table with icons/descriptions)
8. 📋 Prerequisites
9. ⚡ Quick Start (5-step install)
10. 🔧 Configuration (env vars table)
11. 📁 Project Structure (tree diagram)
12. 🧪 Testing
13. 🚀 Deployment
14. 📚 API Reference (link to Swagger)
15. 🤝 Contributing Guidelines
16. 📄 License
17. 👥 Authors & Acknowledgements
18. 🗺️ Roadmap (future features)

Use GitHub Flavored Markdown (GFM). Use shields.io badge URLs.
Make it look professional and inviting."""

    def user_prompt(self) -> str:
        features = "\n".join(f"- {f}" for f in self.plan.get("key_features", []))
        tech = ", ".join(self.plan.get("tech_stack", []))
        return f"""Requirements:
---
{self.requirements}
---

Plan:
{self.plan_summary()}

Key features:
{features}

Tech stack: {tech}
Deployment target: {self.plan.get('deployment_target', 'Vercel')}

Specific readme task: {self.plan.get('agent_tasks', {}).get('readme', 'Write comprehensive README.')}

Generate the complete README.md now."""

    async def process_output(self, raw: str):
        # Strip any FILE: wrapper if present
        import re
        m = re.search(r"###\s*FILE:.*?\n```[^\n]*\n([\s\S]+?)```", raw)
        content = m.group(1) if m else raw
        self.write_file("README.md", content)
        # Also write a CONTRIBUTING.md
        self.write_file(
            "CONTRIBUTING.md",
            "# Contributing\n\nContributions are welcome! "
            "Please read the README for project context, then open a PR.\n"
        )
        self.write_file(
            "LICENSE",
            "MIT License\n\nCopyright (c) 2024\n\nPermission is hereby granted, "
            "free of charge, to any person obtaining a copy of this software...\n"
        )
