# 🤖 Proto-Agent — AI Multi-Agent React/Vite Prototype Generator

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![LLM: OpenRouter](https://img.shields.io/badge/LLM-OpenRouter-orange.svg)](https://openrouter.ai)
[![LLM: Ollama](https://img.shields.io/badge/LLM-Ollama-green.svg)](https://ollama.ai)
[![Rich Dashboard](https://img.shields.io/badge/UI-Rich%20Terminal-purple.svg)](https://rich.readthedocs.io)

> Feed it a requirements markdown file → watch 7 parallel AI agents build your entire React/Vite prototype in real-time → get a ZIP with everything.

---

## ✨ What It Does

Proto-Agent reads your requirements and spins up **8 parallel specialist AI agents**, each tackling a different part of your project simultaneously:

| Agent | Output | Description |
|-------|--------|-------------|
| 🧠 **Planner** | `plan.json` | Reads requirements, creates structured project plan |
| 🎨 **Design** | `design/ui_design_system.md` | Full UI/UX design system, color palette, typography, component specs |
| 💻 **Development** | `src/**` | Complete React + Vite + TypeScript source code |
| 🧪 **Tests** | `tests/**` | Vitest + RTL test suite, MSW mocks, coverage config |
| 📋 **Swagger** | `docs/api/**` | OpenAPI 3.0 spec (YAML + JSON), Swagger UI HTML, Postman collection |
| 🏗️ **LLD** | `docs/design/**` | Low-level design, database schema, sequence diagrams, ADRs |
| 🚀 **Startup Guide** | `docs/STARTUP_GUIDE.md` + `Dockerfile` | Complete setup, deployment, CI/CD pipeline |
| 📖 **README** | `README.md` | Professional README with badges, architecture diagram |

Everything gets packaged into a single timestamped ZIP file.

---

## 📸 Dashboard Preview

```
╔══════════════════════════════════════════════════════════════════════╗
║  🤖  PROTO-AGENT  │  Requirements: requirements.md  │  OpenRouter   ║
╠══════════════════════════════════════════════════════════════════════╣
║  🕐 02:34  ✅ 5/7 done  🔄 2 running  ❌ 0 failed                  ║
╠══════════════════════╦═══════════════════════════════════════════════╣
║ 🧠 Planner  ✅ 100%  ║                                               ║
╠══════════════════════╬═════════════════╦═════════════════════════════╣
║ 🎨 Design   ✅ 100%  ║ 💻 Development  ║ 🔄 Running                 ║
║ [████████████] 100%  ║ [████████░░] 78%║ Writing… «export default…» ║
╠══════════════════════╬═════════════════╬═════════════════════════════╣
║ 🧪 Tests    🔄  62%  ║ 📋 Swagger      ║ ✅ 100%                    ║
║ [████████░░░]  62%   ║ [████████████]  ║ Done — 5 files             ║
╠══════════════════════╩═════════════════╩═════════════════════════════╣
║ 📡 Live Log                                                          ║
║ [14:32:01] 🚀 Development Agent started                              ║
║ [14:32:15] 💻 Development Writing… «const KanbanBoard: React.FC…»   ║
║ [14:32:18] ✅ Swagger Agent completed in 01:22                       ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## ⚡ Quick Start

### 1. Clone & Setup
```bash
git clone <repo>
cd proto-agent
chmod +x setup.sh && ./setup.sh
```

### 2. Configure LLM
```bash
# Edit .env — choose your provider:
nano .env
```

**Option A: OpenRouter** (cloud, any model, needs API key)
```env
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-your-key-here
OPENROUTER_MODEL=anthropic/claude-3-haiku
```

**Option B: Ollama** (local, free, needs Ollama running)
```bash
ollama pull codellama:13b     # or deepseek-coder:6.7b
```
```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=codellama:13b
```

### 3. Write Your Requirements
```bash
nano requirements.md    # or use the sample:
```

### 4. Run!
```bash
source .venv/bin/activate
python main.py requirements.md
```

Or use the sample requirements:
```bash
python main.py sample_requirements.md
```

---

## 📋 Requirements File Format

Write a plain Markdown file describing your prototype. Include:
- **Overview** — what the app does
- **Features** — list of features
- **Pages/Routes** — what screens exist
- **Tech Stack** — preferences (React, Tailwind, etc.)
- **API Endpoints** — if you know them
- **Design Preferences** — colors, style, mood

See `sample_requirements.md` for a complete example (TaskFlow Pro — a Kanban project management app).

---

## 🔧 Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `openrouter` | `openrouter` or `ollama` |
| `OPENROUTER_API_KEY` | — | Your OpenRouter key |
| `OPENROUTER_MODEL` | `anthropic/claude-3-haiku` | Model to use |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `codellama:13b` | Local model name |
| `MAX_TOKENS` | `4096` | Max tokens per LLM call |
| `TEMPERATURE` | `0.3` | Generation temperature |
| `REQUIREMENTS_FILE` | `./requirements.md` | Default input file |
| `OUTPUT_DIR` | `./output` | Where ZIP goes |
| `DASHBOARD_REFRESH_RATE` | `0.25` | Dashboard FPS (seconds) |

---

## 📦 Output ZIP Structure

```
taskflow_pro_20241201_143215.zip
├── README.md                          ← 📖 Readme agent
├── CONTRIBUTING.md
├── LICENSE
├── MANIFEST.md                        ← Auto-generated manifest
├── design/
│   ├── ui_design_system.md            ← 🎨 Design agent
│   └── design_tokens.json
├── src/                               ← 💻 Development agent
│   ├── main.tsx
│   ├── App.tsx
│   ├── components/
│   │   ├── KanbanBoard.tsx
│   │   └── ...
│   ├── pages/
│   ├── hooks/
│   ├── services/
│   └── store/
├── tests/                             ← 🧪 Test agent
│   ├── vitest.config.ts
│   └── src/test/
├── docs/
│   ├── api/                           ← 📋 Swagger agent
│   │   ├── openapi.yaml
│   │   ├── openapi.json
│   │   ├── swagger.html
│   │   └── postman_collection.json
│   ├── design/                        ← 🏗️ LLD agent
│   │   ├── low_level_design.md
│   │   ├── database_schema.sql
│   │   └── architecture_decisions.md
│   └── STARTUP_GUIDE.md              ← 🚀 Startup agent
├── Dockerfile
├── docker-compose.yml
└── .github/workflows/ci.yml
```

---

## 🤖 Recommended Models

### OpenRouter (Cloud)
| Model | Speed | Quality | Cost |
|-------|-------|---------|------|
| `anthropic/claude-3-haiku` | ⚡⚡⚡ | ⭐⭐⭐ | 💰 |
| `anthropic/claude-3.5-sonnet` | ⚡⚡ | ⭐⭐⭐⭐⭐ | 💰💰 |
| `openai/gpt-4o-mini` | ⚡⚡⚡ | ⭐⭐⭐ | 💰 |
| `deepseek/deepseek-coder-v2` | ⚡⚡ | ⭐⭐⭐⭐ | 💰 |

### Ollama (Local)
| Model | RAM | Quality |
|-------|-----|---------|
| `codellama:13b` | 8GB | ⭐⭐⭐ |
| `deepseek-coder:6.7b` | 6GB | ⭐⭐⭐⭐ |
| `qwen2.5-coder:7b` | 6GB | ⭐⭐⭐⭐ |
| `deepseek-coder:33b` | 24GB | ⭐⭐⭐⭐⭐ |

---

## 🏗️ Architecture

```
main.py (orchestrator)
  │
  ├── Phase 1: PlannerAgent (sequential)
  │     └── Reads requirements.md → JSON plan
  │
  ├── Phase 2: 7 parallel agents (asyncio.gather)
  │     ├── DesignAgent    → design/
  │     ├── DevAgent       → src/
  │     ├── TestAgent      → tests/
  │     ├── SwaggerAgent   → docs/api/
  │     ├── LLDAgent       → docs/design/
  │     ├── StartupAgent   → docs/ + Dockerfile
  │     └── ReadmeAgent    → README.md
  │
  ├── Dashboard (Rich Live)
  │     └── Reads AgentState objects (shared memory)
  │         Updates every 250ms
  │
  └── Packager → output/<name>_<timestamp>.zip
```

---

## 📄 License
MIT


## WINDOWS START ##
1) python -m venv .venv    
2) .venv\Scripts\Activate.ps1   
3) pip install -r requirements.txt
4) python main.py requirements.md   


## MAC START ##
1) python3 -m venv .venv    
2) source .venv/bin/activate     
3) pip install -r requirements.txt
4) python3 main.py requirements.md   