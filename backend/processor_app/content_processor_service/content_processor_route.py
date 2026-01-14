import uuid
import logging
from processor_app.content_processor_service.content_processor_repository import ContentProcessorRepository
from processor_app.content_processor_service.request.content_request import ContentSubmissionRequest
from processor_app.content_processor_service.response.create_response import ContentSubmissionResponse
from processor_app.infra.factory import Factory
from fastapi import APIRouter, Depends, Request
from processor_app.content_processor_service.content_processor_service import ContentProcessorService
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/submissions", tags=["content-processor"])

def get_content_processor_service(request: Request, repository = Depends(Factory.get_repository)):
    producer = request.app.state.producer if hasattr(request.app.state, 'producer') else None
    content_repository = ContentProcessorRepository(repository, producer)
    content_processor_service = ContentProcessorService(content_repository)
    return content_processor_service

@router.post("/", response_model=ContentSubmissionResponse)
async def create_submission(
    submission_data: ContentSubmissionRequest,
    content_processor_service: ContentProcessorService = Depends(get_content_processor_service)
):
    return await content_processor_service.create_submission(submission_data)

@router.get("/{submission_id}", response_model=ContentSubmissionResponse)
async def get_submission(
    submission_id: str,
    content_processor_service: ContentProcessorService = Depends(get_content_processor_service)
):
    return await content_processor_service.get_submission(submission_id)


@router.get("/", response_model=list[ContentSubmissionResponse])
async def list_submissions(content_processor_service: ContentProcessorService = Depends(get_content_processor_service)):
    return await content_processor_service.list_submissions()
