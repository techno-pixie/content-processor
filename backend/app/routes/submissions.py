import uuid
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from kafka import KafkaProducer
from app.database import get_db
from app.models import Submission, SubmissionStatus
from app.schemas import SubmissionCreate, SubmissionResponse

router = APIRouter(prefix="/api/submissions", tags=["submissions"])

# Kafka producer (shared connection)
try:
    kafka_producer = KafkaProducer(
        bootstrap_servers=['localhost:9092'],
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    )
except Exception as e:
    print(f"Warning: Could not connect to Kafka: {e}")
    kafka_producer = None


@router.post("/", response_model=SubmissionResponse)
async def create_submission(
    submission_data: SubmissionCreate,
    db: Session = Depends(get_db)
):
    """
    Submit content for processing.
    
    Returns immediately with submission ID and PENDING status.
    Processing happens asynchronously in Kafka worker.
    """
    # Generate unique ID
    submission_id = str(uuid.uuid4())

    # Create new submission record
    submission = Submission(
        id=submission_id,
        content=submission_data.content,
        status=SubmissionStatus.PENDING
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    # Publish to Kafka topic for worker to process
    # This is non-blocking - the request returns immediately
    if kafka_producer:
        try:
            kafka_producer.send('submissions', {
                'id': submission_id,
                'content': submission_data.content
            })
            kafka_producer.flush()
        except Exception as e:
            print(f"Warning: Could not send to Kafka: {e}")

    return submission


@router.get("/{submission_id}", response_model=SubmissionResponse)
def get_submission(
    submission_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieve submission status and details by ID.
    """
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    return submission


@router.get("/", response_model=list[SubmissionResponse])
def list_submissions(db: Session = Depends(get_db)):
    """
    List all submissions (useful for admin/monitoring).
    """
    submissions = db.query(Submission).order_by(Submission.created_at.desc()).all()
    return submissions
