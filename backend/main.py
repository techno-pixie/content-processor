"""
Content Processor Backend - Main Entry Point

To run:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""
from app import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
