# IntelliReview — AI Code Reviewer

## Project Structure

```
intellireview/
├── main.py                        # FastAPI entry point
├── .env                           # Environment variables
├── requirements.txt
├── test_api.py                    # Manual API test script
├── reviews.db                     # SQLite database (auto-created)
└── app/
    ├── __init__.py
    ├── database.py                # DB engine, session, ReviewRecord model
    ├── models/
    │   ├── __init__.py
    │   └── code_request.py        # Pydantic request model
    ├── routes/
    │   ├── __init__.py
    │   └── review.py              # /review-code and /reviews endpoints
    ├── services/
    │   ├── __init__.py
    │   ├── ollama_service.py      # Async Ollama AI integration
    │   ├── code_analyzer.py       # Pylint static analysis
    │   └── score_generator.py     # Pylint score parser
    ├── templates/
    │   └── index.html             # Main UI
    └── static/
        └── style.css
```

## Setup & Run

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Start Ollama (required for AI analysis)
```bash
ollama serve
ollama pull phi3:latest
```

### 3. Run the app
```bash
uvicorn main:app --reload
```

### 4. Open in browser
```
http://localhost:8000
```

### 5. Test the API directly
```bash
python test_api.py
```

## API Endpoints

| Method | Path           | Description                          |
|--------|----------------|--------------------------------------|
| GET    | `/`            | Web UI                               |
| POST   | `/review-code` | Analyze code (body: `code`, `language`) |
| GET    | `/reviews`     | Last 20 stored reviews               |
| GET    | `/health`      | Health check                         |

## Bugs Fixed

| File                  | Bug                                                              |
|-----------------------|------------------------------------------------------------------|
| `main.py`             | `global_exception_handler` missing `Request` param + `JSONResponse` import |
| `ollama_service.py`   | `def` instead of `async def` (called with `await` in router)    |
| `ollama_service.py`   | Used `requests` (sync) — replaced with `httpx` async client     |
| `review.py`           | Wrong import paths for models and services                       |
| `code_request.py`     | Missing `language` field used by `test_api.py`                  |
| `database.py`         | No ORM model defined — tables never created properly             |
| `_env`                | Malformed — value was a file path instead of an API key          |
| Project structure     | Flat files with `app.*` imports — reorganized into proper package |
