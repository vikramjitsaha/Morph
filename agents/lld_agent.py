"""agents/lld_agent.py — Low-Level Design (backend architecture) agent."""
import re
from agents.base_agent import BaseAgent


class LLDAgent(BaseAgent):
    AGENT_NAME    = "LLD"
    AGENT_ICON    = "🏗️"
    OUTPUT_SUBDIR = "docs/design"

    @property
    def system_prompt(self) -> str:
        return """You are a senior software architect specialising in backend system design.
Produce a thorough Low-Level Design (LLD) document for the backend of a web application.

Structure your response as FILE BLOCKS:
### FILE: <path>
```
<content>
```

Generate ALL of the following:

1. docs/design/low_level_design.md — Master LLD document covering:
   - System Overview & Architecture Diagram (ASCII/text-based)
   - Module Breakdown (each service/module with responsibilities)
   - Database Schema (table definitions, indexes, relationships, ERD in text)
   - Class Diagrams (UML-style in text)
   - Sequence Diagrams for all key flows (user auth, CRUD operations, etc.)
   - API Contract Definitions (request/response shapes)
   - Error Handling Strategy
   - Caching Strategy (Redis patterns if applicable)
   - Message Queue patterns (if applicable)
   - Security Design (JWT, RBAC, input validation)
   - Performance Considerations
   - Scalability Notes

2. docs/design/database_schema.sql — Complete SQL DDL with:
   - CREATE TABLE statements for all models
   - Indexes, constraints, foreign keys
   - Seed data INSERT statements
   - Migration strategy notes

3. docs/design/architecture_decisions.md — ADRs (Architecture Decision Records):
   - Why specific technologies were chosen
   - Trade-offs considered
   - Alternative approaches rejected

4. docs/design/data_flow.md — Data flow diagrams (text-based) showing how data
   moves through the system end-to-end

Use ASCII art diagrams, tables, and code blocks liberally. Be extremely specific.
"""

    def user_prompt(self) -> str:
        models_detail = "\n".join(
            "  - {}: {}".format(
                m["name"],
                ", ".join(
                    f"{f['name']}: {f['type']}{'(required)' if f.get('required') else ''}"
                    for f in m.get("fields", [])
                ),
            )
            for m in self.plan.get("data_models", [])
        )
        return f"""Requirements:
---
{self.requirements}
---

Plan:
{self.plan_summary()}

Data Models:
{models_detail}

Backend type: {self.plan.get('backend_type', 'express')}
Deployment target: {self.plan.get('deployment_target', 'Docker')}

Specific LLD task: {self.plan.get('agent_tasks', {}).get('lld', 'Produce full LLD.')}

Generate all design documents now using ### FILE: format."""

    async def process_output(self, raw: str):
        pattern = re.compile(
            r"###\s*FILE:\s*(.+?)\n```[^\n]*\n([\s\S]+?)```",
            re.MULTILINE,
        )
        matches = pattern.findall(raw)
        if not matches:
            self.write_file("low_level_design.md", raw)
            return
        for rel_path, content in matches:
            self.write_file(rel_path.strip(), content)
        self.write_file("_lld_generation_log.md", raw)
