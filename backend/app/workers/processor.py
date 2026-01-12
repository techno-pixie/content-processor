import asyncio
import re
from datetime import datetime
from app.models import Submission, SubmissionStatus
from app.database import SessionLocal


def validate_content(content: str) -> bool:
    """
    Validation Logic:
    - PASSED: content length >= 10 AND contains a number
    - FAILED: otherwise
    """
    if len(content) < 10:
        return False
    if not re.search(r'\d', content):
        return False
    return True


async def process_submission(submission_id: str) -> None:
    """
    Asynchronous worker that processes a submission.
    This simulates a resource-intensive operation with a ~5s delay.
    
    Process:
    1. Retrieve submission from database
    2. Update status to PROCESSING
    3. Simulate processing delay
    4. Validate content
    5. Update status to PASSED or FAILED
    """
    db = SessionLocal()
    try:
        # Fetch the submission
        submission = db.query(Submission).filter(Submission.id == submission_id).first()
        if not submission:
            return

        # Update to PROCESSING state
        submission.status = SubmissionStatus.PROCESSING
        db.commit()

        # Simulate resource-intensive processing with ~5s delay
        await asyncio.sleep(5)

        # Validate the content
        is_valid = validate_content(submission.content)

        # Update status based on validation result
        submission.status = SubmissionStatus.PASSED if is_valid else SubmissionStatus.FAILED
        submission.processed_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        # Mark as failed if processing encounters an error
        submission = db.query(Submission).filter(Submission.id == submission_id).first()
        if submission:
            submission.status = SubmissionStatus.FAILED
            submission.processed_at = datetime.utcnow()
            db.commit()
        print(f"Error processing submission {submission_id}: {str(e)}")
    finally:
        db.close()
