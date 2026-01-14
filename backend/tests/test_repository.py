import pytest
from unittest.mock import Mock, AsyncMock, patch
from processor_app.content_processor_service.content_processor_repository import ContentProcessorRepository
from processor_app.content_processor_service.schema import Submission, SubmissionStatus
from processor_app.content_processor_service.request.content_request import ContentSubmissionRequest


@pytest.fixture
def mock_repository():
    return AsyncMock()


@pytest.fixture
def mock_producer():
    producer = Mock()
    producer.is_available.return_value = True
    return producer


@pytest.fixture
def content_processor_repo(mock_repository, mock_producer):
    return ContentProcessorRepository(mock_repository, mock_producer)


@pytest.mark.asyncio
async def test_create_submission_success(mock_repository, mock_producer):
    mock_session = AsyncMock()
    mock_session.add = Mock()
    mock_session.commit = AsyncMock()
    
    async def async_context_enter():
        return mock_session
    
    mock_session.begin = Mock()
    mock_session.begin.return_value.__aenter__ = AsyncMock(side_effect=async_context_enter)
    mock_session.begin.return_value.__aexit__ = AsyncMock(return_value=None)
    
    async def get_session_impl():
        return mock_session
    
    mock_repository.get_session = Mock()
    mock_repository.get_session.return_value.__aenter__ = AsyncMock(side_effect=get_session_impl)
    mock_repository.get_session.return_value.__aexit__ = AsyncMock(return_value=None)
    
    content_processor_repo = ContentProcessorRepository(mock_repository, mock_producer)
    
    request = ContentSubmissionRequest(content="Test content 123")
    
    result = await content_processor_repo.create(request)
    
    assert result is not None
    assert result.content == "Test content 123"
    
    assert mock_producer.produce.called




@pytest.mark.asyncio
async def test_get_by_id_not_found(mock_repository, mock_producer):
    mock_session = AsyncMock()
    
    # Create a mock result from execute()
    mock_result = Mock()
    mock_result.scalars.return_value.first.return_value = None
    
    # Mock execute to return the result - make it async
    async def async_execute(*args, **kwargs):
        return mock_result
    
    mock_session.execute = async_execute
    
    # Mock session.begin()
    async def async_context_enter():
        return mock_session
    
    mock_session.begin = Mock()
    mock_session.begin.return_value.__aenter__ = AsyncMock(side_effect=async_context_enter)
    mock_session.begin.return_value.__aexit__ = AsyncMock(return_value=None)
    
    async def get_session_impl():
        return mock_session
    
    mock_repository.get_session = Mock()
    mock_repository.get_session.return_value.__aenter__ = AsyncMock(side_effect=get_session_impl)
    mock_repository.get_session.return_value.__aexit__ = AsyncMock(return_value=None)
    
    content_processor_repo = ContentProcessorRepository(mock_repository, mock_producer)
    
    # Call get_by_id with nonexistent ID
    result = await content_processor_repo.get_by_id("nonexistent-id")
    
    # Verify result is None
    assert result is None

@pytest.mark.asyncio
async def test_update_status_success(mock_repository, mock_producer):
    # Setup
    mock_session = AsyncMock()
    mock_submission = Mock(spec=Submission)
    mock_submission.id = "test-id"
    mock_submission.status = SubmissionStatus.PENDING
    
    # Create a mock result from execute()
    mock_result = Mock()
    mock_result.scalars.return_value.first.return_value = mock_submission
    
    # Mock execute to return the result - make it async
    async def async_execute(*args, **kwargs):
        return mock_result
    
    mock_session.execute = async_execute
    mock_session.commit = AsyncMock()
    
    # Mock session.begin()
    async def async_context_enter():
        return mock_session
    
    mock_session.begin = Mock()
    mock_session.begin.return_value.__aenter__ = AsyncMock(side_effect=async_context_enter)
    mock_session.begin.return_value.__aexit__ = AsyncMock(return_value=None)
    
    async def get_session_impl():
        return mock_session
    
    mock_repository.get_session = Mock()
    mock_repository.get_session.return_value.__aenter__ = AsyncMock(side_effect=get_session_impl)
    mock_repository.get_session.return_value.__aexit__ = AsyncMock(return_value=None)
    
    content_processor_repo = ContentProcessorRepository(mock_repository, mock_producer)
    
    # Call update_status
    result = await content_processor_repo.update_status("test-id", SubmissionStatus.PROCESSING)
    
    # Verify result
    assert result is not None
    assert result.id == "test-id"
    
    # Verify commit was called
    assert mock_session.commit.called
    

