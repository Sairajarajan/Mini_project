# Aegis — Intelligent Child Chat Guardian

**U23CS704 Mini Project — First Review**
Sona College of Technology | Department of CSE

**Team:**
- SAI RAJA RAJAN J K — CSE C, 4th Year (6178192102)
- SHALINI — CSE C, 4th Year (61782323102)

**Supervisor:** Dr. A.C. Kaladevi, ME, MCA, PhD

**Repo:** https://github.com/Sairajarajan/Mini_project

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
  - **Both parents alerted** on warn/block: e.g. Alice sends "I want to meet you alone" to Bob →
    Alice's parent gets `sent_improper` AND Bob's parent gets `received_toxic`
    ("Your child Bob received an inappropriate message from Alice...")
  - App **uninstalled/stopped** (no heartbeat for 48h) → warning email to parent
- **Privacy-preserving** — only alerts are sent, not full chat logs

## Architecture

```mermaid
flowchart LR
    subgraph Clients
        UI1[React Web UI :5173]
        UI2[Flutter App]
    end
    UI1 -- "WebSocket /ws/chat" --> API
    UI2 -- "WebSocket /ws/chat" --> API

    subgraph Backend[FastAPI Relay :8000]
        API[chat router] --> BUF{Intercept Buffer<br/>holds message}
        BUF --> C1[toxic-bert<br/>fast check ~0.05s]
        C1 -- "suspicious? (tox ≥ 0.35<br/>or risk keyword)" --> C2[Qwen2.5-1.5B<br/>context scoring ~13s]
        C1 -- "clean" --> DEC
        C2 --> DEC{Decision Engine<br/>risk 0-100}
        DEC -- "<45" --> DEL[deliver]
        DEC -- "45-74" --> WARN[deliver + alert]
        DEC -- "≥75 / grooming<br/>exploitation" --> BLOCK[reject + alert]
        DEL --> UI1
        WARN --> UI1
    end

    WARN --> ALERT[Guardian Alerts<br/>sent_improper -> sender's parent<br/>received_toxic -> recipient's parent]
    BLOCK --> ALERT
    ALERT --> EMAIL[Email mock / Gmail SMTP]
    API --> DB[(MongoDB Atlas<br/>users, chat_log,<br/>alert_records, heartbeats)]
    HB[heartbeat monitor<br/>48h inactive] --> ALERT
```

Text equivalent:

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
| Backend | Python 3.14, FastAPI, Uvicorn, WebSockets |
| AI/ML | PyTorch (CPU), Transformers, toxic-bert (BERT-6-label), Qwen2.5-1.5B-Instruct (LoRA fine-tune supported) |
| Database | MongoDB Atlas (Motor async driver) |
| Frontend (web) | React 18 + Vite (Sprint 3 ✅) |
| Frontend (mobile) | Flutter (code written, SDK install pending) |
| Auth | Google OAuth (planned, Sprint 3) |
| Email | Gmail SMTP (mock in dev) |

## Project Structure

```
backend/
├── app/
│   ├── main.py            # FastAPI entry point + lifespan (Mongo connect, heartbeat task)
│   ├── config.py          # env-based settings (.env) incl. model paths
│   ├── database.py        # Motor async MongoDB client
│   ├── models.py          # Pydantic schemas (User, Alert, Decision...)
│   ├── routers/
│   │   ├── users.py       # user upsert/get/list, heartbeat
│   │   ├── chat.py        # WebSocket relay + intercept buffer + history
│   │   └── alerts.py      # alert records listing (parent dashboard)
│   └── services/
│       ├── classifier.py  # toxic-bert fast check + Qwen2.5 context scoring (LoRA-ready)
│       ├── decision.py    # risk thresholds → deliver/warn/block
│       ├── email_service.py   # Mock/SMTP parent alert emails
│       └── heartbeat.py   # background 48h-inactivity monitor task
├── scripts/
│   ├── test_db.py             # MongoDB connectivity check
│   ├── test_classifier.py     # classify sample messages
│   ├── test_ws.py             # WebSocket end-to-end test (2 fake users)
│   ├── download_models.py     # fetch Qwen2.5 + toxic-bert from HF Hub
│   ├── download_data.py       # cyberbullying dataset + PAN12 (manual step)
│   └── train_lora.py          # LoRA fine-tune of Qwen (CPU-friendly)
├── data/                  # datasets (gitignored)
├── models/                # LLM weights — gitignored, see "Models" section
├── requirements.txt       # web deps
├── requirements-ml.txt    # ML deps (torch CPU, transformers, detoxify)
├── .env                   # secrets (gitignored) — copy from .env.example
└── .env.example
web/                       # React chat UI (Vite) — Sprint 3 ✅
├── src/App.jsx            # login + chat + parent alerts panel
├── vite.config.js         # proxies / and /ws to backend :8000
└── package.json
app/                       # Flutter mobile app — Sprint 3 (SDK install pending)
├── pubspec.yaml
└── lib/ (main.dart, api.dart, login_page.dart, chat_page.dart)
```

---

## Models (LLM weights — NOT in GitHub)

**Why not in the repo:** GitHub rejects files > 100 MB and flags repos > 1 GB.
The combined models are ~4.4 GB, so they are **gitignored** and must be downloaded once.

| # | Model | Size | Purpose |
|---|---|---|---|
| 1 | `Qwen/Qwen2.5-1.5B-Instruct` | ~3.2 GB | LLM context classifier (intent + risk score) |
| 2 | `unitary/toxic-bert` | ~1.3 GB | Fast toxicity check (BERT, 6-label) |

### Download (one of these)

**Option A — automated script (recommended):**

```powershell
cd backend
.\.venv\Scripts\python scripts\download_models.py
```

**Option B — HuggingFace CLI:**

```powershell
cd backend
.\.venv\Scripts\python -m pip install -U huggingface_hub

hf download Qwen/Qwen2.5-1.5B-Instruct --local-dir models\Qwen2.5-1.5B-Instruct
hf download unitary/toxic-bert          --local-dir models\toxic-bert
```

**Option C — manual browser download:**
- https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct → `models/Qwen2.5-1.5B-Instruct`
- https://huggingface.co/unitary/toxic-bert → `models/toxic-bert`

No auth token required — both are open models. Files must land in `backend/models/`
(the path is configurable via `QWEN_MODEL_PATH` / `TOXIC_BERT_PATH` in `.env`).

---

## Quick Start (all commands in order)

> Windows PowerShell. Python 3.13+, Node 20+, MongoDB Atlas URI required.

```powershell
# 1) Clone
git clone https://github.com/Sairajarajan/Mini_project.git
cd Mini_project

# 2) Backend environment
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m pip install -r requirements-ml.txt
.\.venv\Scripts\python -m pip install email-validator

# 3) Secrets  (edit .env -> put your MONGODB_URI, keep EMAIL_MODE=mock for demo)
copy .env.example .env

# 4) Models (~4.4 GB, one-time download)
.\.venv\Scripts\python scripts\download_models.py

# 5) Verify DB
.\.venv\Scripts\python scripts\test_db.py        # expect: MongoDB ping: True

# 6) Start backend  (terminal 1)
.\.venv\Scripts\python -m uvicorn app.main:app --port 8000
#    Swagger docs: http://localhost:8000/docs

# 7) Start web chat UI  (terminal 2)
cd ..\web
npm install
npm run dev                                     # http://localhost:5173

# 8) Use it: open http://localhost:5173 in TWO browser tabs
#    tab 1 -> create "Alice" (parent.alice@test.com)
#    tab 2 -> create "Bob"   (parent.bob@test.com)
#    Alice -> Bob: "hi"                 -> badge "deliver · risk 0.1" (instant)
#    Alice -> Bob: "wanna meet at the park after school alone?"
#                                      -> badge "block · risk 95" + parent alerts on both sides

# 9) Optional tests
cd ..\backend
.\.venv\Scripts\python -m pip install pytest pytest-asyncio
.\.venv\Scripts\python -m pytest scripts\tests\test_core.py -q       # 14 unit tests
.\.venv\Scripts\python scripts\tests\test_e2e_ws.py                  # E2E (server running)
.\.venv\Scripts\python scripts\metrics.py                            # accuracy + latency report
```

**Alerts in demo mode (`EMAIL_MODE=mock`):** emails are printed to the backend terminal
instead of sent. Check the web UI "Parent alerts" panel, or
http://localhost:8000/alerts (and /alerts/{user_id}).

---

## Build & Run

### 1. Prerequisites
- Python 3.13+ (tested on 3.14)
- Node.js 20+ (for React web UI)
- Flutter 3.44+ (for mobile app — see "Flutter app" below)
- MongoDB Atlas free cluster (connection string in `.env`)
- Git

### 2. Backend setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate                    # Windows
# or: source .venv/bin/activate           # Linux/macOS

pip install -r requirements.txt
pip install -r requirements-ml.txt
pip install email-validator               # pydantic EmailStr dependency
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
- `USE_LLM=true` — toggle the Qwen2.5 context classifier on/off
- `USE_LORA=true` — attach trained LoRA adapter at `models/lora-aegis` (after `train_lora.py`)
- `CASCADE=true` — fast path: toxic-bert + risk keywords first; the Qwen LLM runs only for
  suspicious messages. **This is the speed optimization** (normal chat ~0.1-0.2 s vs ~10 s)
- `LLM_TRIGGER_TOXICITY=0.35` — toxicity score that forces the LLM check
- `QWEN_MAX_NEW_TOKENS=56` / `QWEN_MAX_INPUT_TOKENS=256` — LLM generation budget

### 4. Download models (once)

See the [Models](#models-llm-weights--not-in-github) section above. ~4.4 GB total.

### 5. Verify MongoDB

```bash
.venv\Scripts\python scripts\test_db.py    # expect: MongoDB ping: True
```

### 6. Run the API

```bash
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

- Health check: http://localhost:8000/health
- API docs (Swagger): http://localhost:8000/docs

### 7. Run the React web chat UI

```bash
cd web
npm install
npm run dev        # http://localhost:5173  (proxies / and /ws to :8000)
```

Open two browser tabs, create/pick two profiles, chat — Aegis intercepts each message
and shows `deliver / warn / block` badges with the risk score. The "Parent alerts"
panel lists alert emails for the current profile.

### 8. Tests

```bash
.\.venv\Scripts\python scripts\test_classifier.py   # classifier smoke test
.\.venv\Scripts\python scripts\test_ws.py           # WebSocket E2E (Alice→Bob)
```

---

## API Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | status + DB ping |
| GET | `/config` | current thresholds + model paths |
| POST | `/users/upsert` | create/update child profile (name, parent_email) |
| GET | `/users` | list all profiles (contact picker) |
| GET | `/users/{user_id}` | fetch user |
| POST | `/users/heartbeat?user_id=` | record app heartbeat (anti-uninstall) |
| WS | `/ws/chat?user_id=` | chat relay — send `{"type":"message","recipient_id":"...","text":"..."}` |
| GET | `/chat/history/{user_id}/{other_id}` | last 100 messages between two users |
| GET | `/alerts` | all alert records (parent dashboard) |
| GET | `/alerts/{user_id}` | alerts for one child |

**Decision flow:** every sent message → intercept buffer → toxic-bert (fast) + Qwen2.5
(context) → `risk_score` 0-100 → **deliver** (<45) | **warn** (45-74, delivered + parent
email) | **block** (≥75 or grooming/exploitation intent, rejected + parent email).

---

## Sprint Progress Log

### Sprint 1 ✅ — Backend skeleton
FastAPI + lifespan, Motor MongoDB client, Pydantic models, mock/SMTP email service,
`.env.example`, `test_db.py`, README.

### Sprint 2 ✅ — Context classifier + decision engine + chat relay
- `classifier.py`: toxic-bert fast check **loaded directly via Transformers**
  (Detoxify's `checkpoint=` arg expects its proprietary `.ckpt` format — it rejected the
  downloaded HF directory with `Permission denied`; toxic-bert is a standard
  `BertForSequenceClassification` with 6 toxicity labels, so we load it with
  `AutoModelForSequenceClassification` and take `sigmoid(logits)` — same math, fully offline)
- `classifier.py`: Qwen2.5-1.5B-Instruct scored via chat-template + JSON answer
  (`{"intent","risk_score","reason"}`), lazily loaded in a worker thread, cascade design
  (LLM skipped when `USE_LLM=false`; falls back to `toxicity * 100`)
- `decision.py`: thresholds → deliver/warn/block; `grooming`/`exploitation` always block
- `chat.py`: WebSocket relay with intercept buffer, chat history context (last 8 msgs),
  alert records persisted to Mongo
- `heartbeat.py`: background 48h-inactivity → parent warning email
- Scripts: `download_models.py`, `test_classifier.py`, `test_ws.py`
- Verified E2E: "Hi Bob" → deliver (risk 0.1); "Wanna meet at the park after school,
  just you and me, alone?" → **block** (risk 85, grooming), Bob receives nothing,
  alert record + mock email created.

### Sprint 3 (in progress) — Clients
- ✅ React web chat UI (`web/`): login/profile picker, contacts, WebSocket chat with
  deliver/warn/block badges + risk score, parent alerts panel, 60s heartbeat
- ⏳ Flutter app: code written (`app/lib/`), needs Flutter SDK (see below)
- ⏳ Google OAuth: needs a Google Cloud OAuth client (see "OAuth setup" below)

### Sprint 3.5 ✅ — Inference speed (cascade)
- **Problem:** every message ran Qwen2.5-1.5B on CPU → 9-20 s per message, even "hi".
- **Fix (cascade):** toxic-bert fast check + 40 risk keywords first. The LLM only runs
  when toxicity ≥ 0.35 OR a risk pattern matches. Result:
  - normal chat ("hi", "how are you?", memes): **0.1-0.2 s**
  - suspicious messages ("meet at park alone", "send me photos"): ~8.7 s (LLM, blocked)
- **Truncation fix:** with 40 max_new_tokens the LLM's JSON got cut mid-reason and the
  message fell through as safe. Fixed: token budget → 56, regex fallback parsing
  (`"intent"`, `"risk_score"`, `"reason"` extracted even from truncated JSON), and a
  **fail-safe** — if the LLM was triggered but output is unparseable, risk is raised to
  at least the warn threshold (never silently delivered).
- **Warm-up:** models now preload in the background at server startup (`preload()`),
  so the first message doesn't pay the ~20 s model-load penalty.
- **For even faster LLM checks** (optional): switch to the 0.5B model —
  `hf download Qwen/Qwen2.5-0.5B-Instruct --local-dir models\Qwen2.5-0.5B-Instruct`
  then set `QWEN_MODEL_PATH=models\Qwen2.5-0.5B-Instruct` in `.env` (~2-4 s per LLM check).
- Measured with `scripts/test_speed.py`.

### Sprint 3.6 ✅ — Recipient parent alert
- On warn/block, the **recipient's parent** is now also emailed (`received_toxic`):
  "Your child Bob received an inappropriate message from Alice" + message + reason.
  Sender's parent still gets `sent_improper` as before. Both alerts are stored in
  `alert_records` and visible per-child in the web UI "Parent alerts" panel.
- The email text distinguishes **blocked** ("Aegis blocked this message before delivery")
  from **warn** ("flagged and delivered") via the `blocked` context flag.

### Sprint 4 ✅ — Tests + metrics + docs
- **Unit tests** (`scripts/tests/test_core.py`): decision engine thresholds, intent
  gating, cascade fast path, toxic + grooming detection. `14 passed`.
- **E2E WebSocket test** (`scripts/tests/test_e2e_ws.py`, needs running server):
  safe message delivered, grooming blocked, alerts on BOTH parents. `5 passed`.
- **Metrics** (`scripts/metrics.py`) on 16 labeled samples:

  | Metric | Result |
  |---|---|
  | Accuracy | **100%** (16/16) |
  | Unsafe detected (TP) | 10 |
  | Missed (FN) | 0 |
  | False alerts (FP) | 0 |
  | Fast path latency (median) | **0.05 s** |
  | LLM path latency (median) | ~15 s (CPU; ~2-4 s with 0.5B model) |
- **Architecture diagram**: mermaid version added at the top (renders on GitHub).
- Fix: keyword "school" was too broad (flagged "how was your day at school?");
  narrowed to "your school / which school / school name" → FP eliminated.

### Sprint 4 — remaining
Update the PPTX slide deck with live metrics + architecture diagram; final
review checklist. `test_e2e_ws.py` cleanup uses `DELETE /users/{user_id}`.

---

## Complete Development Log (every step, every command)

> Everything below was actually run on the dev machine (Windows 11, PowerShell 5.1,
> Python 3.14.5, Node 24.16.0, Git 2.55.0, 371 GB free disk, CPU-only PyTorch).
> `.env` values are shown without secrets.

### Phase 0 — Environment discovery
```powershell
# checked what was installed
python --version                                     # 3.14.5
pip --version                                        # pip 26.1.1
node --version                                       # v24.16.0
npm --version                                        # 11.13.0
flutter --version                                    # NOT INSTALLED (still pending)
# disk space: 371.7 GB free on C:
# checked PyTorch CPU availability for Python 3.14:
python -m pip index versions torch --index-url https://download.pytorch.org/whl/cpu
#   -> torch 2.13.0+cpu available
# MongoDB on localhost:27017 -> NOT running (so Atlas is used via MONGODB_URI)
```

### Phase 1 — Backend environment (Sprint 1)
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.txt        # fastapi, uvicorn, websockets, python-dotenv, pydantic, pydantic-settings, motor, pymongo, python-multipart, httpx
.\.venv\Scripts\python -m pip install -r requirements-ml.txt     # torch(cpu), transformers, detoxify, datasets, scikit-learn, pandas, numpy, sentencepiece, accelerate, peft
.\.venv\Scripts\python -m pip install email-validator            # needed by pydantic EmailStr (Sprint 2 import fix)
copy .env.example .env                                            # then fill MONGODB_URI with your Atlas string
.\.venv\Scripts\python scripts\test_db.py                        # expect: MongoDB ping: True
.\.venv\Scripts\python -m uvicorn app.main:app --port 8000       # run API
# http://localhost:8000/health  -> {"status":"ok","db":true}
# http://localhost:8000/docs    -> Swagger UI
```

### Phase 2 — Model downloads (Sprint 2)
```powershell
python -m pip install -U huggingface_hub                          # installs `hf` CLI
hf download Qwen/Qwen2.5-1.5B-Instruct --local-dir models\Qwen2.5-1.5B-Instruct   # ~3.1 GB
hf download unitary/toxic-bert          --local-dir models\toxic-bert            # ~1.3 GB
# equivalent one-command: .\.venv\Scripts\python scripts\download_models.py
# models are gitignored (backend/models/) - GitHub rejects files >100 MB
```

### Phase 3 — Sprint 2 code (context classifier + decision engine + chat relay)

**Files written this phase:** `app/services/classifier.py`, `app/services/decision.py`,
`app/services/heartbeat.py`, `app/routers/users.py`, `app/routers/chat.py`,
`app/routers/alerts.py`, `scripts/download_models.py`, `scripts/test_classifier.py`,
`scripts/test_ws.py` + edits to `app/config.py`, `app/main.py`, `.env.example`.

Key characters/values baked in:
- Risk thresholds: `RISK_THRESHOLD_WARN=45`, `RISK_THRESHOLD_BLOCK=75`
- Intent gating: `BLOCKED_INTENTS = {"exploitation", "grooming"}` — always block
- Severe toxicity gate: `HIGH_TOXICITY = 0.9` → always block
- Chat history context: last `HISTORY_LIMIT = 8` messages (chat_key = "|".join(sorted([u1,u2])))
- LLM system prompt: output JSON only `{"intent","risk_score","reason"}`
- Models loaded lazily in a worker thread (`asyncio.to_thread`) — never block the event loop
- Heartbeat monitor: checks every `HEARTBEAT_CHECK_INTERVAL_HOURS=1` h,
  alerts after `HEARTBEAT_INACTIVE_HOURS=48` h, one email per user (`alert_email_sent_for_inactive`)

**Bugs found & fixed this phase:**
```powershell
# 1) Detoxify refused the HF dir:  Detoxify(model_type, checkpoint=dir) -> Permission denied
#    (Detoxify's checkpoint expects its proprietary .ckpt via torch.load, not a HF folder)
#    FIX: load toxic-bert directly with transformers (BertForSequenceClassification,
#    6 labels: toxicity, severe_toxicity, obscene, threat, insult, identity_attack)
#    and take sigmoid(logits). Same math, fully offline. (classifier.py _ToxicBert)

# 2) from ..database import db -> db was None in routers
#    (Python binds the imported name by VALUE at import time; connect_db() rebinding
#     database.db was invisible) -> AttributeError: 'NoneType' object has no attribute 'users'
#    FIX: routers now use `from .. import database` and access `database.db.*` dynamically
#    (applies to users.py, chat.py, alerts.py, services/heartbeat.py)

# 3) Mongo ObjectId not JSON-serializable -> 500 on /alerts and /chat/history
#    FIX: alerts.py converts _id -> str; chat.py drops _id from history docs
```

**Verification:**
```powershell
.\.venv\Scripts\python -c "from app.main import app; print('APP IMPORTS OK')"
.\.venv\Scripts\python scripts\test_classifier.py     # 8 samples: greeting=0.0, grooming=85, exploitation=85
.\.venv\Scripts\python scripts\test_ws.py             # Alice->Bob: "Hi Bob" deliver 0.1 / "meet at park alone" BLOCK 85
```

### Phase 4 — Git setup + first push (Sprint 2)
```powershell
# Git was NOT installed -> installed via winget:
winget install --id Git.Git -e --accept-source-agreements --accept-package-agreements --silent
$env:Path += ";C:\Program Files\Git\bin"   # each new shell needs this
git init
git add .
git commit -m "Sprint 2: ..."
git branch -M main
git remote add origin https://github.com/Sairajarajan/Mini_project.git
git push -u origin main
# remote already had Sprint 1 -> rejected push -> resolved:
git pull --rebase origin main               # add/add conflicts on 5 files
git checkout --ours <5 files>               # CAREFUL: in rebase --ours = ORIGIN version!
git add <files>; git -c core.editor=true rebase --continue
git push
# NOTE: this rebase silently REVERTED main.py/config.py/.gitignore/README/.env.example
# to the origin versions (lost Sprint 2 edits). Re-applied all edits, committed again.
```

### Phase 5 — Speed optimization (cascade) — "checking takes 15s" complaint
```powershell
# Symptom: every message ran Qwen2.5-1.5B on CPU -> 9-20 s even for "hi"
# FIX (cascade) in classifier.py:
#   - toxic-bert fast check FIRST (~0.05 s)
#   - 40 risk keywords: meet, alone, secret, "don't tell", photos, naked, money,
#     "where do you live", "your school", snapchat, webcam, "you and me", ...
#   - LLM only if toxicity >= LLM_TRIGGER_TOXICITY (0.35) OR keyword hit
#   - config: CASCADE=true, LLM_TRIGGER_TOXICITY=0.35,
#     QWEN_MAX_NEW_TOKENS=56, QWEN_MAX_INPUT_TOKENS=256
#   - models preload at startup (preload() task in lifespan) -> no 20 s first message
# Result: normal chat 0.1-0.2 s; suspicious ~9 s
# BUG found: with 40 tokens the LLM JSON got TRUNCATED (no closing }) -> dangerous
# messages fell through as risk 0.1. FIX: token budget 56 + regex fallback parsing
# (_INTENT_RE/_SCORE_RE/_REASON_RE) + fail-safe: if LLM triggered but unparseable,
# risk >= warn threshold (never silently deliver).
# Verified with scripts/test_speed.py
```

### Phase 6 — React web chat UI (Sprint 3)
```powershell
# files: web/package.json, vite.config.js, index.html, src/main.jsx, src/App.jsx, src/App.css
cd web
npm install
npm run dev                                    # http://localhost:5173
# vite.config.js proxies ONLY /ws /users /alerts /chat /health /config -> :8000
# (initial "/" catch-all proxy broke serving the app itself -> 404; fixed)
# UI: profile picker/create, contacts list, chat bubbles with deliver/warn/block badges
# + risk score, "Parent alerts" panel, 60 s heartbeat (POST /users/heartbeat)
# backend addition: GET /users (contact list)
# verified: build compiles -> npm run build
```

### Phase 7 — ML scripts + Flutter code (Sprint 3)
```powershell
# scripts/download_data.py  -> data/cyberbullying_tweets.csv (239,465 rows)
# scripts/train_lora.py     -> LoRA fine-tune Qwen2.5 (CPU: batch 2, grad_accum 4, lr 2e-4,
#                              r=8, alpha=16, target_modules=[q,k,v,o]_proj) -> models/lora-aegis
# classifier auto-attaches adapter when USE_LORA=true
# dataset FIX: Zahra98/cyberbullying_tweets was REMOVED from HF Hub -> DatasetNotFoundError
#   -> searched Hub API, verified karthikarunr/Cyberbullying-Toxicity-Tweets (239k rows)
#   -> train_lora handles oh_label (0/1) mapping: 1->bullying, 0->neutral
# app/ (Flutter): pubspec.yaml + lib/main.dart, api.dart, login_page.dart, chat_page.dart
#   (mirror of the React UI; runs with: cd app; flutter create .; flutter pub get; flutter run)
```

### Phase 8 — New feature: recipient parent alert
```powershell
# Alice sends "I want to meet you alone" -> Bob:
#   Alice's parent gets sent_improper ("your child behaved improperly")
#   Bob's parent   gets received_toxic ("Your child Bob received an inappropriate message
#                    from Alice: '...'")  -> NEW in chat.py _process_message
# email wording: blocked=True -> "Aegis blocked this message before delivery"
#                blocked=False (warn, delivered) -> "flagged ... and delivered to your child"
# verified via /alerts/u_alice + /alerts/u_bob
```

### Phase 9 — Timezone fix (alert times were ~5.5 h early)
```powershell
# root cause: PyMongo returns datetimes as NAIVE UTC (BSON datetime has no tzinfo),
# API sent "09:37" with no offset -> browser treated it as local time
# FIX: routers stamp naive datetimes with timezone.utc before returning:
#   alerts.py _clean(), chat.py history, users.py get_user
# verified: API now returns "2026-08-17T09:37:40+00:00" -> UI shows local time
```

### Phase 10 — Sprint 4 (tests, metrics, diagram)
```powershell
.\.venv\Scripts\python -m pip install pytest pytest-asyncio
# scripts/tests/test_core.py     14 unit tests (decision engine, cascade, toxicity, grooming)
# scripts/tests/test_e2e_ws.py    5 E2E tests (server must be running)
# scripts/metrics.py             16 labeled samples -> 100% accuracy, 0 FN, 0 FP
#                                 fast path median 0.05 s / LLM path ~15 s
# backend addition: DELETE /users/{user_id} (test cleanup)
# keyword fix: "school" too broad -> "your school" / "which school" / "school name"
# README: mermaid architecture diagram added
```

### Phase 11 — DB cleanup (test data removed on request)
```powershell
# deleted all test documents from MongoDB Atlas:
#   chat_log: 25, alert_records: 18, users: 2  (all now 0)
```

### Run everything in one go
```powershell
# terminal 1 (backend):
.\.venv\Scripts\python -m uvicorn app.main:app --port 8000
# terminal 2 (web):
cd web; npm run dev        # http://localhost:5173 -> open TWO tabs, create Alice & Bob
# optional:
.\.venv\Scripts\python -m pytest scripts\tests\test_core.py -q
.\.venv\Scripts\python scripts\tests\test_e2e_ws.py
.\.venv\Scripts\python scripts\metrics.py
```

### Git workflow for this repo
```powershell
$env:Path += ";C:\Program Files\Git\bin"       # after a fresh shell
git status -sb                                  # check sync (main...origin/main)
git add -A
git commit -m "message"
git push
# after remote changes (someone else pushed):
git pull --rebase origin main
git push
```

---

## Known Notes / Decisions

- **`from ..database import db` bug (fixed):** routers imported the `db` global *by value*,
  so `connect_db()` rebinding `database.db` was invisible to them (`NoneType` errors).
  Routers now use `from .. import database` and access `database.db.*` dynamically.
- **ObjectId serialization:** Mongo docs returned by `/alerts` and `/chat/history` were
  not JSON-serializable (`ObjectId`); alert docs now convert `_id` → str, history drops `_id`.
- **Timezone bug (fixed):** PyMongo returns datetimes as *naive UTC* (BSON has no tzinfo),
  so the API sent `09:03` with no offset and browsers treated it as local time — alerts
  appeared ~5.5h early (UTC shown as local). All routers now stamp naive datetimes as
  UTC (`replace(tzinfo=timezone.utc)`) before returning, so the UI converts to local time.
- **Detoxify incompatibility (fixed):** `Detoxify(checkpoint=<hf dir>)` expects its own
  `.ckpt` format (`torch.load` of config+state_dict) and rejected the HF folder with
  `Permission denied`. toxic-bert is loaded directly via `transformers` instead
  (`BertForSequenceClassification`, 6 labels, `sigmoid(logits)`) — identical math, offline.
- **Rebase hazard (learned):** in `git rebase`, `--ours` = the UPSTREAM version, not yours.
  Resolving an add/add conflict with `--ours` reverted Sprint 2 files to the origin
  versions. Always verify with `git diff` after `--ours`/`--theirs`.
- **Vite proxy (fixed):** a `"/": proxy` catch-all also intercepted the app's own
  index.html → 404. Only specific prefixes are proxied now (`/ws /users /alerts /chat /health /config`).
- **LLM truncation (fixed):** with 40 `max_new_tokens` Qwen's JSON got cut mid-reason;
  a message could fall through as safe. Now: 56 tokens + regex fallback parse
  (`"intent"`/`"risk_score"`/`"reason"` extracted from truncated JSON) + fail-safe
  (LLM-triggered-but-unparseable → risk ≥ warn threshold, never silently delivered).
- **Keyword false positive (fixed):** "school" flagged benign "how was your day at school?".
  Narrowed to "your school / which school / school name". Metrics went 93.8% → 100%.
- **LLM fallback:** if Qwen is missing (`USE_LLM=false`), the system still works —
  risk score degrades to `toxicity * 100`.
- **Intent gating:** `grooming` / `exploitation` intents always block, regardless of
  numeric score.
- **Determinism:** greedy decoding (`do_sample=False`) + fixed thresholds → identical
  results across machines (verified: 2 runs → same output). `torch` CPU can still show
  small numeric variance across process runs.
- First Qwen inference takes ~20 s on CPU (model load); subsequent messages ~9-15 s
  (preload at startup removes the first-hit penalty).
- `.env` is gitignored — **never commit** your MongoDB URI / Gmail app password.
- PyMongo deletes: `delete_many({})` clears a collection; used for the test-data wipe.

## Flutter app (mobile)

The Flutter client is written (`app/`) but the SDK is not installed on the dev machine.
To run it:

```powershell
# 1. Install Flutter SDK (https://docs.flutter.dev/get-started/install/windows)
# 2. Scaffold platform folders + build
cd app
flutter create .          # generates android/ ios/ windows/ etc.
flutter pub get
flutter run               # Windows desktop, or an emulator/device
```

Change `AegisApi.base` in `app/lib/api.dart` to `http://10.0.2.2:8000`
for the Android emulator.

## Google OAuth (Sprint 3, pending)

1. Create an OAuth client at https://console.cloud.google.com/apis/credentials
   (redirect URI `http://localhost:8000/auth/callback`)
2. Put `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` in `.env`
3. Backend `/auth/login` + `/auth/callback` endpoints and a "Sign in with Google"
   button in both clients are the remaining work.

## Sprint Roadmap

| Sprint | Deliverable | Status |
|---|---|---|
| 1 | Backend skeleton, MongoDB, email service, dataset, toxic-bert baseline | ✅ done |
| 2 | Qwen2.5 LLM context classifier, decision engine, chat WebSocket relay | ✅ done |
| 3 | React web chat + Flutter app, Google OAuth login | 🔶 in progress (web ✅, Flutter code ✅, OAuth pending) |
| 4 | E2E tests, metrics, architecture diagram, final docs + PPTX | 🔶 in progress (tests ✅ metrics ✅ diagram ✅, PPTX pending) |

## Roadmap Extras

- LoRA fine-tune `Qwen2.5-1.5B-Instruct` on PAN12 grooming data for intent classes:
  neutral / grooming / exploitation / explicit (`scripts/train_lora.py`)
- Guardian alert dashboard for parents
- Chat history analytics (aggregate, privacy-preserving)