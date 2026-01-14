import logging
import asyncio

from processor_app.interfaces.consumer import IConsumer
from processor_app.content_processor_service.content_processor_repository import ContentProcessorRepository
from processor_app.interfaces.validator import IContentValidator
from processor_app.consumers.submission_processor import SubmissionProcessor

logger = logging.getLogger(__name__)


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
        self.processor = SubmissionProcessor(repository, validator)

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
                    logger.info(f"[{submission.id}] Found pending submission, processing...")
                    await asyncio.sleep(5)
                    await self.processor.process_submission(submission.id, submission.content)
                
                await asyncio.sleep(self.poll_interval)
                
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                await asyncio.sleep(self.poll_interval)
         
