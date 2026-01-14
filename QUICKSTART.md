### Prerequisites
- Python 3.9+
- Node 16+
- npm

### Quick Start (2 steps)


**Step 1: Start Backend API**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Step 2: Start Frontend (new terminal)**
```bash
cd frontend
npm install
npm run dev
```