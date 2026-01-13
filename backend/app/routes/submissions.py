import uuid
import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from kafka import KafkaProducer
from app.database import get_db
from app.models import Submission, SubmissionStatus
from app.schemas import SubmissionCreate, SubmissionResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/submissions", tags=["submissions"])

# Kafka producer with delivery guarantees
try:
    kafka_producer = KafkaProducer(
        bootstrap_servers=['localhost:9092'],
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        acks='all',  # ✓ Wait for all replicas to acknowledge (strongest guarantee)
        retries=3,   # ✓ Retry up to 3 times on failure
        max_in_flight_requests_per_connection=1,  # ✓ Maintain order
    )
except Exception as e:
    logger.warning(f"Could not connect to Kafka: {e}")
    kafka_producer = None


@router.post("/", response_model=SubmissionResponse)
async def create_submission(
    submission_data: SubmissionCreate,
    db: Session = Depends(get_db)
):
    """
    Submit content for processing.
    
    Flow:
    1. Create submission record in DB (status: PENDING)
    2. Publish to Kafka topic (with delivery guarantees)
    3. Return submission ID immediately (non-blocking)
    
    Delivery Guarantee: acks='all' ensures message reaches all replicas
    """
    # Generate unique ID
    submission_id = str(uuid.uuid4())

    # 1. Create submission record in database
    submission = Submission(
        id=submission_id,
        content=submission_data.content,
        status=SubmissionStatus.PENDING
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    logger.info(f"[{submission_id}] Created submission in database")

    # 2. Publish to Kafka with delivery guarantee
    if kafka_producer:
        try:
            future = kafka_producer.send('submissions', {
                'id': submission_id,
                'content': submission_data.content
            })
            # Wait for confirmation (blocking, but fast ~10-50ms)
            future.get(timeout=5)
            kafka_producer.flush()
            logger.info(f"[{submission_id}] Published to Kafka successfully")
        except Exception as e:
            logger.error(f"[{submission_id}] Failed to publish to Kafka: {e}")
            # DB record exists, but Kafka message failed
            # Worker will never see this - submission stuck in PENDING
            # In production: alert/retry logic needed here

    # 3. Return immediately
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
