**Run Backend API & Frontend (local)**

- **Prerequisites**:
  - Python 3.10+ (project uses 3.14 in venv but 3.10+ is fine)
  - Virtual environment (recommended)
  - Node/npm not required — frontend is static files served by FastAPI

- **Install dependencies**:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

- **Run the backend (API + static frontend)**:

```bash
# Option A: use helper runner
python3 run_api.py

# Option B: uvicorn directly (use this port if you prefer 8001):
uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8001
```

- **Open the frontend UI**:

