import logging
import asyncio
from datetime import datetime, timedelta

from processor_app.interfaces.consumer import IConsumer
from processor_app.content_processor_service.content_processor_repository import ContentProcessorRepository
from processor_app.content_processor_service.schema import SubmissionStatus
from processor_app.interfaces.validator import IContentValidator

logger = logging.getLogger(__name__)

# Timeout for PROCESSING state (in minutes)
# If a job stays in PROCESSING for longer than this, reset it to PENDING for retry
PROCESSING_TIMEOUT_MINUTES = 5


class FastAPIPoll(IConsumer):
    def __init__(
        self,
        repository: ContentProcessorRepository,
        validator: IContentValidator,
        poll_interval: int = 1
    ):
        self.repository = repository
        self.validator = validator
        self.poll_interval = poll_interval
        self.running = False
        self._poll_task = None

    async def start(self) -> None:
        self.running = True
        self._poll_task = asyncio.create_task(self._poll())
        logger.info("FastAPI poll consumer started")

    async def shutdown(self) -> None:
        self.running = False
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        logger.info("FastAPI poll consumer shut down")

    async def is_running(self) -> bool:
        return self.running and self._poll_task is not None and not self._poll_task.done()

    async def _poll(self) -> None:
        while self.running:
            try:
                submissions = await self.repository.get_pending()
                
                for submission in submissions:
                    if submission.status == SubmissionStatus.PENDING:
                        logger.info(f"[{submission.id}] Found pending submission, processing...")
                        await self._process_async(submission.id, submission.content)
                
                await asyncio.sleep(self.poll_interval)
                
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                await asyncio.sleep(self.poll_interval)

    async def _process_async(self, submission_id: str, content: str) -> None:
        try:
            submission = await self.repository.get_by_id(submission_id)
            if not submission:
                logger.warning(f"[{submission_id}] Submission not found")
                return
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
                        return
                else:
                    logger.info(f"[{submission_id}] Already being processed, skipping")
                    return
            
            if submission.status != SubmissionStatus.PENDING:
                logger.info(f"[{submission_id}] Already processed (status: {submission.status}), skipping")
                return

           
            await self.repository.update_status(submission_id, SubmissionStatus.PROCESSING, processing_started_at=datetime.utcnow())
            logger.info(f"[{submission_id}] Status: PENDING → PROCESSING")

            logger.info(f"[{submission_id}] Processing content...")
            await asyncio.sleep(5)  
            is_valid = self.validator.validate(content)

            final_status = SubmissionStatus.PASSED if is_valid else SubmissionStatus.FAILED
            await self.repository.update_status(submission_id, final_status, datetime.utcnow())

            result = "PASSED" if is_valid else "FAILED"
            logger.info(f"[{submission_id}] Status: PROCESSING → {result}")

        except Exception as e:
            logger.error(f"[{submission_id}] Error during processing: {e}")
         
