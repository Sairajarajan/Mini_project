# Aegis — Intelligent Child Chat Guardian

**U23CS704 Mini Project — First Review**
Sona College of Technology | Department of CSE

**Team:**
- SAI RAJA RAJAN J K — CSE C, 4th Year (6178192102)
- SHALINI — CSE C, 4th Year (61782323102)

**Supervisor:** Dr. A.C. Kaladevi, ME, MCA, PhD

---

## Problem Statement (PS-14)

Design a system to detect **grooming patterns and child exploitation attempts** on social media
using language modeling, chat monitoring, and behavioral indicators — protecting children in an
increasingly connected world with proactive, **send-time** safety.

## What Aegis Does

- **Send-time interception** — messages are evaluated by AI *before* delivery to the recipient
- **Context-aware classification** — analyzes message intent + recent conversation history,
  not just isolated keywords
- **Guardian Alerts** — parents are notified by email only when a real threat exists:
  - Child **received** an inappropriate message → alert to child's parent (with message + sender)
  - Child **sent** an improper message → alert to sender's parent ("your child behaved improperly")
  - App **uninstalled/stopped** (no heartbeat for 48h) → warning email to parent
- **Privacy-preserving** — only alerts are sent, not full chat logs

## Architecture

```
Child Chat UI (React web / Flutter app)
        │  WebSocket
        ▼
FastAPI Relay ──> Intercept Buffer ──> Context Classifier ──> Decision Engine
        (holds message)    (toxic-bert fast check   (risk score 0-100)
                            + Qwen2.5 LLM context)       ├─ Safe     → deliver
                                                         ├─ Warn     → deliver + guardian alert
                                                         └─ Block    → reject + guardian alert
        │
        ▼
MongoDB Atlas (users, chat log, alert records, heartbeats)
        │
        ▼
Email Service (mock in dev → Gmail SMTP in production)
```

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.13, FastAPI, Uvicorn, WebSockets |
| AI/ML | PyTorch (CPU), Transformers, Detoxify (toxic-bert), Qwen2.5-1.5B-Instruct (LoRA fine-tune planned) |
| Database | MongoDB Atlas (Motor async driver) |
| Frontend (web) | React (planned, Sprint 3) |
| Frontend (mobile) | Flutter (planned, Sprint 3) |
| Auth | Google OAuth (planned, Sprint 3) |
| Email | Gmail SMTP (mock in dev) |

## Project Structure

```
backend/
├── app/
│   ├── main.py            # FastAPI entry point + lifespan (Mongo connect)
│   ├── config.py          # env-based settings (.env)
│   ├── database.py        # Motor async MongoDB client
│   ├── models.py          # Pydantic schemas (User, Alert, Decision...)
│   ├── routers/           # auth, chat (WebSocket relay), alerts
│   └── services/
│       ├── email_service.py   # Mock/SMTP parent alert emails
│       ├── classifier.py      # toxic-bert + Qwen context scoring (Sprint 2)
│       └── decision.py        # risk thresholds → deliver/warn/block
├── scripts/
│   ├── test_db.py         # MongoDB connectivity check
│   ├── download_data.py   # PAN12 / cyberbullying dataset fetch (Sprint 1)
│   └── train_lora.py      # LoRA fine-tune of Qwen (Sprint 2)
├── data/                  # datasets (gitignored)
├── requirements.txt       # web deps
├── requirements-ml.txt    # ML deps (torch CPU, transformers, detoxify)
├── .env                   # secrets (gitignored) — copy from .env.example
└── .env.example
web/                       # React chat UI (Sprint 3)
app/                       # Flutter mobile app (Sprint 3)
```

## Build & Run

### 1. Prerequisites
- Python 3.13+
- Node.js 20+ (for React, Sprint 3)
- Flutter 3.44+ (for mobile app, Sprint 3)
- MongoDB Atlas free cluster (connection string in `.env`)

### 2. Backend setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate                    # Windows
# or: source .venv/bin/activate           # Linux/macOS

pip install -r requirements.txt
pip install -r requirements-ml.txt
```

> Note: `requirements-ml.txt` pins PyTorch to the CPU build
> (`--index-url https://download.pytorch.org/whl/cpu`). For GPU, install torch from
> `https://download.pytorch.org/whl/cu124` instead.

### 3. Configure secrets

```bash
copy .env.example .env    # Windows
# cp .env.example .env    # Linux/macOS
```

Edit `.env`:
- `MONGODB_URI` — your Atlas connection string
- `EMAIL_MODE=mock` for dev (alerts logged to console); switch to `smtp` + set
  `EMAIL_SENDER` / `EMAIL_APP_PASSWORD` (Gmail App Password) for real emails
- Risk thresholds: `RISK_THRESHOLD_WARN=45`, `RISK_THRESHOLD_BLOCK=75`

### 4. Verify MongoDB

```bash
.venv\Scripts\python scripts\test_db.py    # expect: MongoDB ping: True
```

### 5. Run the API

```bash
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

- Health check: http://localhost:8000/health
- API docs (Swagger): http://localhost:8000/docs

### 6. ML models (first run downloads weights)

```bash
.venv\Scripts\python scripts\download_data.py   # PAN12/cyberbullying dataset
# classifier service loads detoxify/toxic-bert automatically (Sprint 2)
```

## Sprint Roadmap

| Sprint | Deliverable | Status |
|---|---|---|
| 1 | Backend skeleton, MongoDB, email service, dataset, toxic-bert baseline | ✅ done |
| 2 | Qwen2.5 LLM context classifier, decision engine, chat WebSocket relay | ⏳ next |
| 3 | React web chat + Flutter app, Google OAuth login | pending |
| 4 | E2E tests, metrics, architecture diagram, final docs + PPTX | pending |

## Security Notes

- `.env` is gitignored — **never commit** your MongoDB URI / Gmail app password
- Gmail requires an **App Password** (2-Step Verification enabled); regular passwords are rejected
- True uninstall detection is impossible on mobile OSes; Aegis uses **heartbeat-based**
  detection (48h inactivity → parent warning email)

## Roadmap Extras

- LoRA fine-tune `Qwen2.5-1.5B-Instruct` on PAN12 grooming data for intent classes:
  neutral / grooming / exploitation / explicit
- Guardian alert dashboard for parents
- Chat history analytics (aggregate, privacy-preserving)