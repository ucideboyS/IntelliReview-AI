# PROJECT_CONTEXT.md — IntelliReview AI

> **Purpose:** This document provides complete context about the IntelliReview-AI project for any developer or AI model working on the codebase. Read this before making any changes.

---

## 1. Project Overview

**IntelliReview AI** is an AI-powered code intelligence and review platform. Users submit source code (either by pasting directly or providing a GitHub repository/file URL), and the system returns a structured quality analysis powered by GPT-4.1-nano via GitHub Models.

The platform is designed to evolve into a full **Code Health Intelligence Platform** — providing multi-dimensional scoring, security analysis, historical tracking, analytics dashboards, and automated refactor suggestions.

**Core User Flow:**
1. User pastes code or enters a GitHub URL
2. Frontend sends code to the FastAPI backend
3. Backend calls GPT-4.1-nano via GitHub Models API
4. AI returns structured JSON with score, issues, explanation, and fixed code
5. Result is persisted to SQLite and returned to the frontend
6. Frontend renders the analysis with animated score ring, issue cards, and fixed code

---

## 2. Current Architecture

```
IntelliReview-AI/
├── main.py                         # FastAPI app entry point, lifespan, middleware, routes
├── requirements.txt                # Python dependencies
├── test_api.py                     # API test suite
├── env_Version2.example            # Example environment variables
├── reviews.db                      # SQLite database (auto-created at runtime)
└── app/
    ├── __init__.py
    ├── database.py                 # SQLAlchemy engine, session, ReviewRecord model, init_db
    ├── models/
    │   └── code_request.py         # Pydantic input model: CodeRequest
    ├── routes/
    │   └── review.py               # POST /review-code, GET /reviews
    ├── services/
    │   └── github_service.py       # AI integration: analyze_code_with_fix()
    ├── static/
    │   └── style.css               # Global stylesheet (dark/light theme, all UI components)
    └── templates/
        └── index.html              # Single-page frontend (HTML + CSS + vanilla JS)
```

### Backend Flow

```
Request → POST /review-code
        → CodeRequest (Pydantic validation)
        → analyze_code_with_fix(code, language)  [github_service.py]
        → AsyncOpenAI → GPT-4.1-nano (GitHub Models)
        → JSON parsed + validated
        → ReviewRecord saved to SQLite via SQLAlchemy
        → JSON response returned to frontend
```

### Frontend Flow

```
index.html (vanilla JS, no framework)
  ├── Paste Mode   → textarea input → POST /review-code
  ├── GitHub Mode  → fetch GitHub API → fetch raw files → POST /review-code (per file)
  ├── Score Ring   → SVG circle animation based on quality_score
  ├── Metrics Bars → 5 animated dimension bars (derived from quality_score)
  ├── History Drawer → GET /reviews → render history cards
  └── Theme Toggle → localStorage dark/light mode
```

---

## 3. Tech Stack

| Layer | Technology | Version |
|---|---|---|
| **Web Framework** | FastAPI | 0.129.0 |
| **ASGI Server** | Uvicorn | 0.41.0 |
| **AI Client** | OpenAI Python SDK (AsyncOpenAI) | 1.82.0 |
| **AI Model** | GPT-4.1-nano via GitHub Models | — |
| **AI Endpoint** | `https://models.inference.ai.azure.com` | — |
| **ORM** | SQLAlchemy | 2.0.46 |
| **Database** | SQLite (default) / PostgreSQL (via `DATABASE_URL`) | — |
| **Validation** | Pydantic v2 | 2.12.5 |
| **Templating** | Jinja2 | 3.1.6 |
| **HTTP Client** | HTTPX | 0.28.1 |
| **Env Config** | python-dotenv | 1.2.1 |
| **Linting** | Pylint | 4.0.4 |
| **Frontend** | Vanilla HTML + CSS + JavaScript | — |
| **Fonts** | JetBrains Mono, Inter (Google Fonts) | — |

### Environment Variables

```env
GITHUB_TOKEN=ghp_xxxx        # Required: GitHub token for GitHub Models API access
DATABASE_URL=sqlite:///./reviews.db   # Optional: override with PostgreSQL URL
```

---

## 4. Current Implemented Features

### Backend

- [x] **FastAPI application** with lifespan context manager for DB initialization
- [x] **CORS middleware** configured to allow all origins (development mode)
- [x] **POST `/review-code`** — accepts `CodeRequest`, calls AI, saves result, returns JSON
- [x] **GET `/reviews`** — returns the 20 most recent `ReviewRecord` entries from DB
- [x] **GET `/health`** — health check endpoint returning version and status
- [x] **GET `/`** — serves the Jinja2 HTML frontend
- [x] **Global exception handler** — catches all unhandled exceptions, returns 500 JSON
- [x] **Structured logging** — Python `logging` module throughout all layers
- [x] **Async AI calls** — `AsyncOpenAI` client with `async def` route handlers
- [x] **JSON output enforcement** — AI prompt explicitly requests strict JSON output
- [x] **Regex fallback parsing** — strips markdown fences and extracts JSON block from AI response
- [x] **SQLite persistence** — every review saved with timestamp to `ReviewRecord`
- [x] **Pydantic input validation** — `CodeRequest` with `min_length=1` on code field
- [x] **Multi-language support** — Python, JavaScript, TypeScript, Java, C++, Go, Rust, SQL, PHP, C#, Kotlin, Swift

### Frontend

- [x] **Dark / Light theme toggle** — manual toggle, persisted in `localStorage`
- [x] **Sticky frosted-glass navbar** — logo, nav links, status badge, theme button
- [x] **Hero section** — shown before first analysis, auto-hides after first result
- [x] **Paste mode** — code textarea with line numbers and scroll sync
- [x] **GitHub mode** — accepts full repo URL or single file blob URL
  - Fetches repo tree via GitHub API
  - Filters code files by extension (max 10 files, max 50KB each)
  - Analyzes files sequentially with 3s delay between calls
  - Shows per-file score breakdown
- [x] **Animated score ring** — SVG circle that fills based on `quality_score`
- [x] **Score grade label** — Excellent / Good / Average / Needs Work / Poor
- [x] **5-dimension metric bars** — Readability, Performance, Maintainability, Security, Best Practices (currently derived/estimated from `quality_score`)
- [x] **Stats bar** — shows Overall Score, Language, Grade after analysis completes
- [x] **AI Explanation box** — displays `ai_explanation` from response
- [x] **Issues box** — displays `issues` with color-coded warning styling
- [x] **Fixed Code panel** — displays `fixed_code` with monospace formatting
- [x] **Copy button** — copies fixed code to clipboard with visual confirmation
- [x] **Language badge** — shown in output panel header after analysis
- [x] **Review History drawer** — slides in from right, fetches `/reviews`, shows score/language/date/issues
- [x] **Per-file repo breakdown** — file-by-file score table for GitHub repo mode
- [x] **Loading shimmer** — skeleton animation while AI is processing
- [x] **Keyboard shortcut** — `Ctrl + Enter` triggers analysis
- [x] **About section** — describes the tech stack at page footer
- [x] **Responsive layout** — single-column on screens ≤ 768px

---

## 5. AI Prompt & Output Schema

### Prompt Template (`github_service.py`)

```python
f"""You are an expert {language} code reviewer.

Analyze the following {language} code carefully.

Respond ONLY in valid JSON (no markdown, no backticks, no extra text).

Format EXACTLY like this:
{{
  "quality_score": "<number from 1-10>",
  "issues": "clear description of issues or 'No issues found.'",
  "ai_explanation": "short explanation of the code quality",
  "fixed_code": "corrected code or 'No fix needed.'"
}}

Code:
{code}"""
```

### AI Model Configuration

```python
model       = "gpt-4.1-nano"
temperature = 0          # Deterministic output for consistent scoring
```

### Expected JSON Output Schema

```json
{
  "quality_score": "7",
  "issues": "Missing input validation on line 12. No error handling in fetch call.",
  "ai_explanation": "The code is functional but lacks defensive programming practices.",
  "fixed_code": "def process(data):\n    if not data:\n        raise ValueError('data cannot be empty')\n    ..."
}
```

### Fallback Parsing Logic

```python
# 1. Strip markdown code fences: ```json ... ```
raw_output = re.sub(r"```json|```", "", raw_output).strip()

# 2. Extract JSON block with greedy regex
json_match = re.search(r"\{.*\}", raw_output, re.DOTALL)

# 3. Attempt json.loads() on extracted block

# 4. On failure, return fallback dict with raw output in ai_explanation
```

---

## 6. Database Schema

### Table: `reviews`

```python
class ReviewRecord(Base):
    __tablename__ = "reviews"

    id            = Column(Integer, primary_key=True, index=True)
    code          = Column(Text, nullable=False)          # Raw submitted code
    language      = Column(String(50), default="Python")  # Programming language
    quality_score = Column(String(10))                    # e.g. "7" or "N/A"
    issues        = Column(Text)                          # Issue description string
    ai_explanation= Column(Text)                          # AI explanation string
    fixed_code    = Column(Text)                          # Fixed code string
    created_at    = Column(DateTime, default=utc_now)     # UTC timestamp
```

### Notes
- `quality_score` is stored as **String**, not Integer — must be cast with `parseFloat()` in frontend and `float()` in Python
- `DATABASE_URL` defaults to `sqlite:///./reviews.db`; can be overridden with a PostgreSQL connection string
- SQLite `check_same_thread=False` is set for FastAPI's async/threaded access pattern

---

## 7. Current Limitations

| Limitation | Details |
|---|---|
| **Single score field** | Only `quality_score` (1–10) stored in DB; no individual dimension scores |
| **No Pydantic output model** | AI response validated via regex + `json.loads`, not a strict Pydantic schema |
| **No authentication** | All endpoints are public; no user accounts, JWT, or sessions |
| **No rate limiting** | Any client can spam `/review-code` with large payloads |
| **No input size guard** | `CodeRequest.code` has `min_length=1` but no `max_length` — risk of token explosion |
| **SQLite in production** | Not suitable for concurrent multi-user load; no connection pooling |
| **Sequential repo analysis** | GitHub repo files are analyzed one-by-one with 3s delays, not parallel |
| **No caching** | Identical code submitted twice triggers two full AI calls |
| **No background jobs** | Long repo analyses block the HTTP response |
| **Estimated dimension scores** | 5-metric bars on frontend are derived/randomized from `quality_score`, not real AI scores |
| **No token tracking** | Token usage per request is not logged or limited |
| **No test coverage for AI layer** | `test_api.py` tests the API surface but not AI response parsing edge cases |
| **CORS open** | `allow_origins=["*"]` — must be restricted before production deployment |

---

## 8. Pending Features / Roadmap

### 🧠 Stage 1 — Core Intelligence (Next Priority)

- [ ] **Multi-dimensional scoring** — expand AI prompt to return 5 real scores: `readability`, `performance`, `maintainability`, `security`, `best_practices`
- [ ] **Pydantic output model** — define `ReviewResponse` schema to validate AI JSON strictly
- [ ] **Store dimension scores in DB** — add 5 new columns to `ReviewRecord`
- [ ] **Repository-level summary** — architecture overview, risk hotspots, refactor roadmap
- [ ] **Historical trend tracking** — score delta between analyses of same repo

### 🚀 Stage 2 — Dashboard & Analytics

- [ ] **Analytics dashboard page** — total analyses, avg score, avg security score, language breakdown
- [ ] **Radar chart** — visual pentagon chart for 5 dimension scores
- [ ] **Score-over-time graph** — using Chart.js or similar
- [ ] **Technical debt estimation** — Low/Medium/High label from AI
- [ ] **Most common issue category** — classify and aggregate issue types

### 🔐 Stage 3 — Security Intelligence

- [ ] **Security analysis mode toggle** — focused prompt for SQL injection, XSS, hardcoded secrets
- [ ] **Sensitive data detector** — regex scan for API keys, JWT secrets, AWS credentials, passwords
- [ ] **Risk heatmap** — color-coded file risk levels (High / Medium / Low)

### ⚙️ Stage 4 — Engineering Maturity

- [ ] **Async parallel file processing** — use `asyncio.gather()` for concurrent repo file analysis
- [ ] **Rate limiting** — middleware to limit requests per IP per minute
- [ ] **Input size guard** — `max_length` on `CodeRequest.code` (e.g., 8000 chars)
- [ ] **Token usage tracking** — log `usage.total_tokens` from AI response
- [ ] **Caching layer** — hash code input, return cached result if unchanged
- [ ] **Background job queue** — offload large repo analyses to async task queue

### 👥 Stage 5 — SaaS Features

- [ ] **JWT authentication** — register, login, user-specific review history
- [ ] **Per-user usage dashboard** — total analyses, token consumption, avg score
- [ ] **Role-based access** — Admin / User / Free tier with request limits

### 🧠 Stage 6 — Premium Intelligence

- [ ] **Structured refactor suggestions** — not just fixed code; annotated improvement blocks
- [ ] **Codebase architecture visualization** — folder/module interaction summary
- [ ] **PR Review Mode** — accept GitHub PR URL, analyze diff only

### ⚙️ Infrastructure

- [ ] **Docker + Docker Compose** — containerize app + PostgreSQL
- [ ] **PostgreSQL migration** — replace SQLite for production
- [ ] **Deployment** — Railway / Render / Fly.io
- [ ] **CI/CD pipeline** — GitHub Actions for lint, test, deploy

---

## 9. Current Active Development Task

**Task: UI Redesign (Completed)**

The frontend (`app/templates/index.html` + `app/static/style.css`) was fully redesigned with:
- Sticky frosted-glass navbar with theme toggle
- Hero section with animated gradient heading
- Line-number code editor
- 5-dimension animated metric bars
- Stats bar (score / language / grade)
- Copy button on fixed code panel
- Review history side drawer
- Dark/light theme with `localStorage` persistence
- Responsive mobile layout

**Next Task: Multi-Dimensional Scoring (Stage 1)**

Changes required:
1. Update AI prompt in `github_service.py` to return 5 dimension scores
2. Create `ReviewResponse` Pydantic model in `app/models/`
3. Add 5 score columns to `ReviewRecord` in `app/database.py`
4. Update `app/routes/review.py` to store and return dimension scores
5. Wire real scores to the 5 metric bars in `index.html`

---

## 10. Known Constraints

| Constraint | Impact |
|---|---|
| **GitHub Models rate limit** | GPT-4.1-nano has per-minute request limits; sequential 3s delays used in repo mode as workaround |
| **SQLite single-writer** | Concurrent writes will queue; acceptable for single-user/demo use |
| **No `.env` file in repo** | `GITHUB_TOKEN` must be set manually; see `env_Version2.example` |
| **Frontend is single-file** | All HTML/CSS/JS in `index.html` (CSS now moved to `style.css`); no build tools, no bundler |
| **No migrations system** | SQLAlchemy `create_all()` used; schema changes require manual DB deletion or Alembic setup |
| **Code truncated at 3000 chars** | In GitHub repo mode, files are sliced to 3000 characters before sending to AI to stay within token budget |
| **Max 10 files per repo** | GitHub repo analysis is capped at 10 files to prevent rate limit exhaustion |
| **Python 3.10+ required** | Uses `match`-style type hints and `asynccontextmanager` patterns |

---

*Last updated: 2026-03-03 | Version: 2.0.0 | Maintainer: [@Sahil-Jak](https://github.com/Sahil-Jak)*