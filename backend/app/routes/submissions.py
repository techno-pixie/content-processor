import uuid
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Submission, SubmissionStatus
from app.schemas import SubmissionCreate, SubmissionResponse
from app.workers import process_submission

router = APIRouter(prefix="/api/submissions", tags=["submissions"])


@router.post("/", response_model=SubmissionResponse)
async def create_submission(
    submission_data: SubmissionCreate,
    db: Session = Depends(get_db)
):
    """
    Submit content for processing.
    
    Returns immediately with submission ID and PENDING status.
    Processing happens asynchronously in the background.
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

    # Start async processing task
    # This is non-blocking - the request returns immediately
    asyncio.create_task(process_submission(submission_id))

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
