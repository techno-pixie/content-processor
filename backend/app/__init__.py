from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.routes.submissions import router as submissions_router

# Initialize database
init_db()

app = FastAPI(
    title="Content Processor API",
    description="API for submitting and tracking content processing",
    version="2.0.0 (Kafka-based)"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(submissions_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
