import logging
from datetime import datetime, timedelta

from processor_app.content_processor_service.content_processor_repository import ContentProcessorRepository
from processor_app.content_processor_service.schema import SubmissionStatus
from processor_app.interfaces.validator import IContentValidator

logger = logging.getLogger(__name__)

PROCESSING_TIMEOUT_MINUTES = 5


class SubmissionProcessor:
    
    def __init__(
        self,
        repository: ContentProcessorRepository,
        validator: IContentValidator
    ):
        self.repository = repository
        self.validator = validator

    async def process_submission(self, submission_id: str, content: str) -> bool:
        try:
            submission = await self.repository.get_by_id(submission_id)
            if not submission:
                logger.warning(f"[{submission_id}] Submission not found")
                return False

            if submission.status == SubmissionStatus.PROCESSING:
                if submission.processing_started_at:
                    elapsed = datetime.utcnow() - submission.processing_started_at
                    if elapsed > timedelta(minutes=PROCESSING_TIMEOUT_MINUTES):
                        logger.warning(
                            f"[{submission_id}] PROCESSING timeout detected ({elapsed.total_seconds():.0f}s). "
                            f"Resetting to PENDING for retry."
                        )
                        await self.repository.update_status(submission_id, SubmissionStatus.PENDING)
                        submission.status = SubmissionStatus.PENDING
                    else:
                        logger.info(f"[{submission_id}] Already being processed, skipping")
                        return True
                else:
                    logger.info(f"[{submission_id}] Already being processed, skipping")
                    return True
            
            if submission.status != SubmissionStatus.PENDING:
                logger.info(f"[{submission_id}] Already processed (status: {submission.status}), skipping")
                return True

            await self.repository.update_status(
                submission_id,
                SubmissionStatus.PROCESSING,
                processing_started_at=datetime.utcnow()
            )
            logger.info(f"[{submission_id}] Status: PENDING → PROCESSING")

            logger.info(f"[{submission_id}] Processing content...")
            is_valid = self.validator.validate(content)

            final_status = SubmissionStatus.PASSED if is_valid else SubmissionStatus.FAILED
            await self.repository.update_status(submission_id, final_status, datetime.utcnow())

            result = "PASSED" if is_valid else "FAILED"
            logger.info(f"[{submission_id}] Status: PROCESSING → {result}")
            return True

        except Exception as e:
            logger.error(f"[{submission_id}] Error during processing: {e}")
            try:
                submission = await self.repository.get_by_id(submission_id)
                if submission and submission.status == SubmissionStatus.PROCESSING:
                    await self.repository.update_status(
                        submission_id,
                        SubmissionStatus.FAILED,
                        datetime.utcnow()
                    )
                    logger.info(f"[{submission_id}] Marked as FAILED due to error")
            except Exception as db_error:
                logger.error(f"[{submission_id}] Failed to update error status: {db_error}")
            return False
