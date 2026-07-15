# 💰 Where Is My Money Going (WIMM)

> AI-powered personal finance analytics — upload your bank statements, let AI auto-classify every transaction, and visualize exactly where your money goes.

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-14-000000?logo=next.js&logoColor=white)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql&logoColor=white)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Repository:** https://github.com/TanishqChamoli/WhereIsMyMoney.git
**Live demo:** http://54.146.129.1 *(EC2 + Docker Compose)*

---

## 📖 Overview

**Where Is My Money Going (WIMM)** is a self-hostable personal finance analytics web app. You upload bank
statements (CSV, Excel, or PDF) from virtually any bank in the world, and a multi-tier AI pipeline
automatically classifies each transaction into meaningful categories. From there, WIMM builds rich,
interactive dashboards that reveal your spending habits, recurring subscriptions, income trends, budget
health, and personalized financial insights.

No manual tagging. No spreadsheets. Just upload and understand.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📤 **Multi-format Upload** | CSV, Excel (`.xls` / `.xlsx`, incl. TSV-disguised), and PDF bank statements |
| 🏦 **41+ Bank Formats** | HDFC, ICICI, SBI, Axis, Kotak, IDFC, Revolut, Chase, Barclays, N26, Lidl, Aldi, Tesco, and more — India, Europe, US & global fintech |
| 💱 **Multi-currency** | INR (₹), EUR (€), USD ($), GBP (£) + 22 more — **auto-detected** from your transactions |
| 🤖 **4-Tier AI Classification** | Learned rules → rule engine → ML zero-shot → optional LLM fallback |
| 📊 **Interactive Dashboard** | Summary cards, category pie chart, spending timeline, income vs expenses, budget status, income trend |
| 🧾 **Transactions Page** | Full CRUD, rich filters, bulk actions, cross-page select-all, mobile card layout |
| 📈 **Deep Analytics** | Category drill-down, income analysis, recurring detection, top merchants, velocity, outliers, day patterns |
| 💰 **Smart AI Budgets** | Data-driven budget suggestions with methodology badges, trend indicators & confidence meters |
| 🔄 **Subscription Detector** | Active vs possibly-cancelled subscriptions, annual cost & savings opportunities |
| 🧠 **AI Summary** | A rich, personality-filled monthly review with fun stats, achievements & predictions — plus a 🔄 Regenerate button |
| ➕ **Add Cash Transaction** | Manual entry for non-bank / cash spending |
| 🔒 **JWT Auth** | Email + password registration, access/refresh tokens, with legacy session fallback |
| 📱 **Responsive UI** | Mobile-friendly card layouts, dark/light theme toggle with system preference detection |

---

## 🤖 AI Classification Pipeline

WIMM classifies every transaction through a **4-tier cascade**, stopping at the first confident result.
This keeps the vast majority of transactions blazingly fast while reserving heavy ML/LLM work for the
genuinely ambiguous ones.

| Tier | Engine | What it does | Speed |
|------|--------|--------------|-------|
| **1** | **Learned Rules** | Applies patterns learned from *your* past corrections | <1ms |
| **2** | **Rule Engine** | 465+ merchant regex / keyword / transaction-code patterns (handles 70–80% of transactions) | <1ms |
| **3** | **ML Classifier** | `valhalla/distilbart-mnli-12-3` zero-shot (DistilBART-MNLI, ~300MB) with **true NLI batching** — ~10–20s for 401 transactions | seconds |
| **4** | **LLM Fallback** | Optional Ollama LLM for the hardest cases | optional |

The ML model is loaded **once as a process-wide singleton at startup** (no per-request reload), and the
zero-shot inference path bypasses the slow HuggingFace `pipeline` to batch NLI pairs directly — a ~200×
speedup over the naive per-transaction loop.

Every user correction feeds back into Tier 1, so classification gets smarter the more you use it.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 14 (App Router, `standalone` output), React 18, TypeScript, Tailwind CSS, Recharts |
| **Backend** | Python 3.11, FastAPI, SQLAlchemy 2, Pydantic v2 |
| **Database** | PostgreSQL 15 (production) / SQLite (development) |
| **AI / ML** | HuggingFace `transformers` + `torch`, `valhalla/distilbart-mnli-12-3` (zero-shot), optional Ollama LLM |
| **Auth** | JWT (`python-jose`), `bcrypt` 4.0.1 password hashing |
| **Parsing** | `pandas`, `pdfplumber`, `openpyxl`, `xlrd` |
| **Deployment** | Docker Compose, nginx reverse proxy, EC2 (`m6a.large`, 8GB RAM, 512GB Docker volume) |

---

## 📁 Project Structure

```
whereIsMyMoneyGoing/
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI entry point + health checks
│   │   ├── core/                       # Config, database, auth (JWT + session)
│   │   ├── models/                     # SQLAlchemy models
│   │   │   ├── user.py
│   │   │   ├── transaction.py
│   │   │   ├── category.py
│   │   │   ├── budget.py
│   │   │   ├── bank_statement.py
│   │   │   └── classification_rule.py
│   │   ├── routers/                    # API endpoints
│   │   │   ├── auth.py
│   │   │   ├── upload.py
│   │   │   ├── transactions.py
│   │   │   ├── analytics.py
│   │   │   ├── insights.py
│   │   │   ├── budgets.py
│   │   │   ├── categories.py
│   │   │   ├── classification.py
│   │   │   ├── jobs.py                  # Async ML classification jobs + progress
│   │   │   └── ai_summary.py
│   │   ├── schemas/                    # Pydantic request/response schemas
│   │   └── services/                   # Business logic
│   │       ├── bank_parser.py          # 41+ bank format parser (CSV/Excel/PDF)
│   │       ├── analytics_service.py
│   │       ├── insights_service.py
│   │       ├── budget_service.py       # Smart AI budget suggestions
│   │       ├── merchant_extractor.py
│   │       └── classification/         # AI classification pipeline
│   │           ├── pipeline.py
│   │           ├── learned_rules.py    # Tier 1
│   │           ├── rule_engine.py      # Tier 2
│   │           ├── ml_classifier.py    # Tier 3 (DistilBART-MNLI singleton)
│   │           ├── llm_classifier.py   # Tier 4 (Ollama)
│   │           └── rules/              # 465+ merchant / keyword / code patterns
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── app/                            # Next.js App Router pages
│   │   ├── dashboard/
│   │   ├── transactions/
│   │   ├── analytics/
│   │   ├── budgets/
│   │   ├── subscriptions/
│   │   ├── ai-summary/
│   │   ├── add-transaction/
│   │   ├── upload/
│   │   ├── login/  &  register/
│   ├── components/                     # Reusable UI (Sidebar, TransactionTable, charts/, …)
│   ├── lib/                            # api.ts, session.ts, theme.tsx, utils.ts
│   ├── Dockerfile
│   └── package.json
├── Investigations/                     # Design & research docs (see below)
├── docker-compose.yml                  # Full-stack orchestration
├── nginx.conf                          # Reverse proxy config
├── deploy-ec2.sh                       # EC2 bootstrap / deployment script
├── .env.example                        # Environment variable template
└── README.md
```

---

## 🚀 Setup & Run

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose (recommended)

### Option 1 — Docker (recommended)

```bash
docker compose up -d --build
```

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs (Swagger):** http://localhost:8000/docs

### Option 2 — Local development

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend** (in a new terminal):
```bash
cd frontend
npm install
npm run dev        # runs on http://localhost:3000
```

---

## ☁️ Deploy to EC2

The production deployment runs on EC2 (`m6a.large`, 8GB RAM, 512GB Docker volume) behind an nginx
reverse proxy, orchestrated with Docker Compose.

**Automatic:** A cron job auto-deploys the latest `main` branch every 10 minutes.

**Manual:**
```bash
./deploy-ec2.sh
```

The script handles Docker (+ Compose & BuildX plugins) installation, environment setup, and service
orchestration on Amazon Linux 2023 or Ubuntu 22.04.

---

## 🔐 Environment Variables

Copy the template and edit as needed:

```bash
cp .env.example .env
```

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | DB connection string | `sqlite:///./wimm_dev.db` |
| `ENVIRONMENT` | `development` or `production` | `development` |
| `SECRET_KEY` | JWT / session signing key | `change-me-in-production` |
| `CORS_ORIGINS` | Allowed frontend origins (comma-separated) | `http://localhost:3000` |
| `MAX_UPLOAD_SIZE_MB` | Max upload size | `10` |
| `NEXT_PUBLIC_API_URL` | Backend URL for frontend | `http://localhost:8000` |
| `OLLAMA_BASE_URL` | *(optional)* Ollama server for LLM classification | — |
| `OLLAMA_MODEL` | *(optional)* Ollama model name | `llama3.1:8b` |

---

## 📡 API Highlights

All endpoints are served under the `/api/v1` prefix. Full interactive documentation is available at
`/docs` (Swagger UI) when the backend is running.

| Group | Base path | Highlights |
|-------|-----------|------------|
| **Auth** | `/api/v1/auth/*` | `register`, `login`, `refresh`, `session`, `me` |
| **Upload** | `/api/v1/upload` | Upload statement (CSV/Excel/PDF) + `/statements` list |
| **Transactions** | `/api/v1/transactions/*` | CRUD, `bulk-update`, `explain-batch`, `data/clear` |
| **Analytics** | `/api/v1/analytics/*` | `spending-by-category`, `timeline`, `income-vs-expenses`, `summary`, `category/{name}`, `income-timeline` |
| **Insights** | `/api/v1/insights/*` | `recurring`, `subscriptions`, `top-merchants`, `velocity`, `outliers`, `patterns`, `payment-methods`, `summary` |
| **Budgets** | `/api/v1/budgets/*` | CRUD, `summary`, `suggest` (AI suggestions) |
| **Categories** | `/api/v1/categories/*` | CRUD |
| **Classification** | `/api/v1/classify/*` | `classify`, `batch`, `feedback`, `stats` |
| **Jobs** | `/api/v1/jobs/*` | Async ML classification job status + progress |
| **AI Summary** | `/api/v1/ai/summary` | Rich AI-generated financial review |
| **Health** | `/health`, `/health/ml` | Liveness + ML model load status |

---

## 🧪 Running Tests

```bash
cd backend
pytest -v
```

---

## 🆕 Recent Changes

- ⚡ **ML ~200× speedup** — direct NLI pair batching that bypasses the slow HuggingFace pipeline
- 🧠 **Model singleton** — DistilBART-MNLI loaded once at startup, no per-request reload
- ⏳ **Async ML classification** — background jobs with live progress tracking (`/jobs`)
- 💱 **Dynamic currency symbols** — auto-detected per user (no more hardcoded ₹)
- 🔄 **AI Summary** — richer review with personality + stats and a **Regenerate** button
- 💰 **Smart AI budgets** — linear regression, IQR outlier detection, 50/30/20 rule & consistency-based suggestions with methodology badges and confidence meters
- 🐛 **Bulk-update fix** — resolved SQLAlchemy join+update error and added `synchronize_session` handling
- 🏦 **41-bank format support** — including international banks (Revolut, Chase, Barclays, N26, Lidl, Aldi, Tesco, …)
- 🔒 **JWT auth** — email+password login/register/refresh, with legacy session fallback; switched to direct `bcrypt` (fixes 72-byte ValueError)
- 📱 **Mobile-responsive UI** — card layouts on small screens, slide-out drawer menu, dark/light toggle
- 🗑️ **Cascade delete fix** — clear-data no longer hits FK violations (jobs deleted before statements)

---

## 📚 Documentation

Detailed design and research documents live in the [`Investigations/`](Investigations/) directory, including:

- `01-tech-stack-analysis.md` — technology selection rationale
- `02-analytics-specification.md` — analytics feature spec
- `03-ai-classification-pipeline.md` — full classification pipeline design
- `08-bank-format-research.md` — research corpus behind the 41-bank parser
- `12-ml-performance-analysis.md` — ML batching & performance deep-dive
- …and more (feature validation, derived insights, column mapping, etc.)

---

## 📄 License

Released under the **MIT License** — see [LICENSE](LICENSE) for details.

---

<p align="center">
  Built with ❤️ by <a href="https://github.com/TanishqChamoli">Tanishq Chamoli</a>
</p>
