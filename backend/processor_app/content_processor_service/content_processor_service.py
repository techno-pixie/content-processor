import logging
from processor_app.content_processor_service.response.create_response import ContentSubmissionResponse
from processor_app.content_processor_service.content_processor_repository import ContentProcessorRepository
from processor_app.content_processor_service.request.content_request import ContentSubmissionRequest

logger = logging.getLogger(__name__)


class ContentProcessorService:
    def __init__(self, repo: ContentProcessorRepository) -> None:
        self._repository = repo

    async def create_submission(self, submission_data: ContentSubmissionRequest):
        submission = await self._repository.create(submission_data)
        return ContentSubmissionResponse(**submission.__dict__)
    
    async def get_submission(self, submission_id: str):
        return await self._repository.get_by_id(submission_id)
    
    async def list_submissions(self):
        return await self._repository.list_all()