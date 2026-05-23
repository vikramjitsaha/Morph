"""agents/startup_agent.py — Startup & Deployment Guide agent."""
from agents.base_agent import BaseAgent


class StartupAgent(BaseAgent):
    AGENT_NAME    = "Startup Guide"
    AGENT_ICON    = "🚀"
    OUTPUT_SUBDIR = "docs"

    @property
    def system_prompt(self) -> str:
        return """You are a DevOps engineer and technical writer.
Write a comprehensive startup, development, and deployment guide for a React + Vite project.

Structure your response as a single detailed Markdown document with these sections:

# Startup & Deployment Guide

## Prerequisites
- Exact software versions required (Node.js, npm/yarn/pnpm, Docker, etc.)
- OS compatibility notes
- Required accounts/services

## Local Development Setup
- Step-by-step clone & install instructions
- Environment variable configuration (explain each .env variable)
- Starting dev server
- Running with hot reload

## Project Structure Explanation
- Every directory and its purpose
- Key files explained

## Available Scripts
- Table of all npm scripts with descriptions

## Environment Configuration
- All environment variables documented in a table
- Local vs Production vs CI differences

## Running Tests
- Unit tests
- Integration tests
- Coverage reports
- E2E tests

## Building for Production
- Build command and output
- Bundle analysis
- Optimization tips

## Docker Deployment
- Dockerfile walkthrough
- docker-compose.yml explanation
- Build and run commands

## CI/CD Pipeline
- GitHub Actions workflow explanation
- Deployment stages

## Troubleshooting
- Common errors and fixes (at least 10)
- Debug tips

## Performance Monitoring
- Lighthouse scores
- Core Web Vitals

Be extremely specific with every command. Use code blocks for all commands.

IMPORTANT: Do NOT reference "shadcn-ui" as an npm install target. shadcn/ui components
are added via CLI (npx shadcn@latest add <component>) not via npm install."""

    def user_prompt(self) -> str:
        return f"""Requirements:
---
{self.requirements}
---

Plan:
{self.plan_summary()}

Tech stack: {', '.join(self.plan.get('tech_stack', []))}
Deployment target: {self.plan.get('deployment_target', 'Vercel')}

Specific startup task: {self.plan.get('agent_tasks', {}).get('startup', 'Write complete startup guide.')}

Also generate:
1. A Dockerfile for the app
2. A docker-compose.yml
3. A .github/workflows/ci.yml GitHub Actions pipeline
4. A .nvmrc file with Node version

Use ### FILE: path format for separate files, and write the main startup guide as:
### FILE: docs/STARTUP_GUIDE.md

Generate all files now."""

    async def process_output(self, raw: str):
        import re
        pattern = re.compile(
            r"###\s*FILE:\s*(.+?)\n```[^\n]*\n([\s\S]+?)```",
            re.MULTILINE,
        )
        matches = pattern.findall(raw)
        if not matches:
            self.write_file("STARTUP_GUIDE.md", raw)
            return
        for rel_path, content in matches:
            rel_path = rel_path.strip()
            # Put docker/ci files in project root context
            self.write_file(rel_path, content)
        self.write_file("_startup_generation_log.md", raw)
