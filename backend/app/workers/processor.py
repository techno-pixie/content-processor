import asyncio
import re
from datetime import datetime
from app.models import Submission, SubmissionStatus
from app.database import SessionLocal

WHITESPACE_RE = re.compile(r"\s")
DIGIT_RE = re.compile(r"\d")

def validate_content(content: str) -> bool:
    return (
        len(content) >= 10
        and not WHITESPACE_RE.search(content)
        and DIGIT_RE.search(content)
    )


async def process_submission(submission_id: str) -> None:
    db = SessionLocal()
    try:
        submission = db.query(Submission).filter(Submission.id == submission_id).first()
        if not submission:
            return
        submission.status = SubmissionStatus.PROCESSING
        db.commit()

        await asyncio.sleep(5)

        is_valid = validate_content(submission.content)

        submission.status = SubmissionStatus.PASSED if is_valid else SubmissionStatus.FAILED
        submission.processed_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        submission = db.query(Submission).filter(Submission.id == submission_id).first()
        if submission:
            submission.status = SubmissionStatus.FAILED
            submission.processed_at = datetime.utcnow()
            db.commit()
        print(f"Error processing submission {submission_id}: {str(e)}")
    finally:
        db.close()
