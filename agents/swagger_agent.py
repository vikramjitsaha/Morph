"""agents/swagger_agent.py — OpenAPI 3.0 / Swagger documentation agent."""
import re
from agents.base_agent import BaseAgent


class SwaggerAgent(BaseAgent):
    AGENT_NAME    = "Swagger"
    AGENT_ICON    = "📋"
    OUTPUT_SUBDIR = "docs/api"

    @property
    def system_prompt(self) -> str:
        return """You are an expert API documentation engineer.
Generate complete, production-quality OpenAPI 3.0 (Swagger) documentation.

Structure your response as FILE BLOCKS:
### FILE: <path>
```
<content>
```

Generate ALL of the following:
1. docs/api/openapi.yaml — Full OpenAPI 3.0 spec (YAML format) with:
   - info, servers, tags sections
   - Every endpoint with operationId, summary, description, parameters, requestBody, responses
   - All schemas/components with full property definitions and examples
   - Authentication schemes (Bearer JWT)
   - Error response schemas (400, 401, 403, 404, 422, 500)
   - Pagination patterns where applicable

2. docs/api/openapi.json — Same spec in JSON format (for tooling)

3. docs/api/swagger.html — Self-contained Swagger UI HTML page that embeds
   swagger-ui from CDN and loads the spec inline (no server needed, works offline)

4. docs/api/api_changelog.md — Version history and breaking changes doc

5. docs/api/postman_collection.json — Postman collection v2.1 with:
   - All endpoints as requests
   - Pre-request scripts for auth token
   - Example request bodies
   - Tests for common assertions

The OpenAPI spec must be 100% valid. Use real-world schemas.
"""

    def user_prompt(self) -> str:
        endpoints = "\n".join(
            f"  - {e['method']} {e['path']}: {e['description']}"
            for e in self.plan.get("api_endpoints", [])
        )
        models = "\n".join(
            f"  - {m['name']}: {', '.join(f['name'] for f in m.get('fields', []))}"
            for m in self.plan.get("data_models", [])
        )
        return f"""Requirements:
---
{self.requirements}
---

Plan:
{self.plan_summary()}

API Endpoints:
{endpoints}

Data Models:
{models}

Specific swagger task: {self.plan.get('agent_tasks', {}).get('swagger', 'Document all API endpoints.')}

Generate all API documentation files now using ### FILE: format."""

    async def process_output(self, raw: str):
        pattern = re.compile(
            r"###\s*FILE:\s*(.+?)\n```[^\n]*\n([\s\S]+?)```",
            re.MULTILINE,
        )
        matches = pattern.findall(raw)
        if not matches:
            self.write_file("api_docs.md", raw)
            return
        for rel_path, content in matches:
            self.write_file(rel_path.strip(), content)
        self.write_file("_swagger_generation_log.md", raw)
