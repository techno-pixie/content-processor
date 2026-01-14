import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from processor_app.consumers.fastapi_poll import FastAPIPoll
from processor_app.content_processor_service.schema import SubmissionStatus
from processor_app.content_processor_service.schema import Submission

@pytest.fixture
def mock_repository():
    return AsyncMock()


@pytest.fixture
def mock_validator():
    validator = Mock()
    validator.validate = Mock(return_value=True)
    return validator


@pytest.fixture
def fastapi_consumer(mock_repository, mock_validator):
    return FastAPIPoll(mock_repository, mock_validator, poll_interval=1)


class TestFastAPIPollConsumer:
    
    def test_initialization(self, mock_repository, mock_validator):
        consumer = FastAPIPoll(mock_repository, mock_validator, poll_interval=2)
        
        assert consumer.repository == mock_repository
        assert consumer.validator == mock_validator
        assert consumer.poll_interval == 2
        assert consumer.running == False
        assert consumer._poll_task is None
    
    @pytest.mark.asyncio
    async def test_start_consumer(self, fastapi_consumer):
        await fastapi_consumer.start()
        
        assert fastapi_consumer.running == True
        assert fastapi_consumer._poll_task is not None
        
        await fastapi_consumer.shutdown()
    
    @pytest.mark.asyncio
    async def test_shutdown_consumer(self, fastapi_consumer):
        await fastapi_consumer.start()
        await fastapi_consumer.shutdown()
        
        assert fastapi_consumer.running == False
    
    @pytest.mark.asyncio
    async def test_is_running_when_started(self, fastapi_consumer):
        await fastapi_consumer.start()
        
        is_running = await fastapi_consumer.is_running()
        assert is_running == True
        
        await fastapi_consumer.shutdown()
    
    @pytest.mark.asyncio
    async def test_is_running_when_stopped(self, fastapi_consumer):
        is_running = await fastapi_consumer.is_running()
        assert is_running == False
    
    @pytest.mark.asyncio
    async def test_process_async_with_valid_content(self, fastapi_consumer, mock_repository, mock_validator):
        
        mock_submission = Mock(spec=Submission)
        mock_submission.id = "test-id"
        mock_submission.content = "Test content 123"
        mock_submission.status = SubmissionStatus.PENDING
        mock_submission.processing_started_at = None
        mock_submission.processing_started_at = None
        
        mock_repository.get_by_id = AsyncMock(return_value=mock_submission)
        mock_repository.update_status = AsyncMock(return_value=mock_submission)
        mock_validator.validate.return_value = True
        
        await fastapi_consumer.processor.process_submission("test-id", "Test content 123")
        
        assert mock_validator.validate.called
        mock_validator.validate.assert_called_with("Test content 123")
        
        assert mock_repository.update_status.called
        calls = mock_repository.update_status.call_args_list
        assert calls[-1][0][1] == SubmissionStatus.PASSED
    
    @pytest.mark.asyncio
    async def test_process_async_with_invalid_content(self, fastapi_consumer, mock_repository, mock_validator):
        
        mock_submission = Mock(spec=Submission)
        mock_submission.id = "test-id"
        mock_submission.content = "short"
        mock_submission.status = SubmissionStatus.PENDING
        mock_submission.processing_started_at = None
        
        mock_repository.get_by_id = AsyncMock(return_value=mock_submission)
        mock_repository.update_status = AsyncMock(return_value=mock_submission)
        mock_validator.validate.return_value = False
        
        await fastapi_consumer.processor.process_submission("test-id", "short")
        
        assert mock_validator.validate.called
        
        assert mock_repository.update_status.called
        calls = mock_repository.update_status.call_args_list
        assert calls[-1][0][1] == SubmissionStatus.FAILED
    
    @pytest.mark.asyncio
    async def test_process_async_submission_not_found(self, fastapi_consumer, mock_repository, mock_validator):
        mock_repository.get_by_id = AsyncMock(return_value=None)
        
        await fastapi_consumer.processor.process_submission("nonexistent-id", "content")
        
        assert mock_repository.get_by_id.called
        mock_repository.get_by_id.assert_called_with("nonexistent-id")
    
    @pytest.mark.asyncio
    async def test_process_async_updates_final_status(self, fastapi_consumer, mock_repository, mock_validator):
        mock_submission = Mock(spec=Submission)
        mock_submission.id = "test-id"
        mock_submission.content = "Test content 123"
        mock_submission.status = SubmissionStatus.PENDING
        mock_submission.processing_started_at = None
        
        mock_repository.get_by_id = AsyncMock(return_value=mock_submission)
        mock_repository.update_status = AsyncMock(return_value=mock_submission)
        mock_validator.validate.return_value = True
        
        await fastapi_consumer.processor.process_submission("test-id", "Test content 123")
        
        assert mock_repository.update_status.called
        calls = mock_repository.update_status.call_args_list
        assert calls[0][0][1] == SubmissionStatus.PROCESSING
        assert calls[1][0][1] == SubmissionStatus.PASSED
    
    @pytest.mark.asyncio
    async def test_process_async_handles_exceptions(self, fastapi_consumer, mock_repository, mock_validator):
        mock_submission = Mock(spec=Submission)
        mock_submission.id = "test-id"
        mock_submission.content = "Test content"
        mock_submission.status = SubmissionStatus.PENDING
        mock_submission.processing_started_at = None
        
        mock_repository.get_by_id = AsyncMock(return_value=mock_submission)
        mock_repository.update_status = AsyncMock(side_effect=Exception("DB Error"))
        mock_validator.validate.return_value = True
        
        await fastapi_consumer.processor.process_submission("test-id", "Test content")
        assert mock_repository.get_by_id.called


class TestCrashSafetyAndIdempotency:
    @pytest.mark.asyncio
    async def test_crash_before_db_write_prevents_double_processing(self, mock_repository, mock_validator):
        submission_id = "crash-test-789"
        content = "Valid content 99999"
        consumer = FastAPIPoll(mock_repository, mock_validator, poll_interval=0.1)
        
        submission_pending = Submission(
            id=submission_id,
            content=content,
            status=SubmissionStatus.PENDING,  
            created_at=datetime.utcnow()
        )
        submission_processing = Submission(
            id=submission_id,
            content=content,
            status=SubmissionStatus.PROCESSING,  
            created_at=datetime.utcnow()
        )
      
        mock_repository.get_by_id.side_effect = [
            submission_pending,     
            submission_processing,   
        ]
        mock_repository.update_status.return_value = None
        mock_validator.validate.return_value = True
        
        await consumer.processor.process_submission(submission_id, content)
        
        assert mock_repository.update_status.call_count == 2  # PROCESSING and PASSED
        first_call = mock_repository.update_status.call_args_list[0]
        assert first_call[0][1] == SubmissionStatus.PROCESSING  
        second_call = mock_repository.update_status.call_args_list[1]
        assert second_call[0][1] == SubmissionStatus.PASSED
        
        mock_repository.update_status.reset_mock()
        
        await consumer.processor.process_submission(submission_id, content)
        
        assert not mock_repository.update_status.called


    @pytest.mark.asyncio
    async def test_already_processed_submission_skipped(self, mock_repository, mock_validator):

        submission_id = "already-done-999"
        content = "Some content 12345"
        consumer = FastAPIPoll(mock_repository, mock_validator, poll_interval=0.1)
        
        submission_already_passed = Submission(
            id=submission_id,
            content=content,
            status=SubmissionStatus.PASSED, 
            created_at=datetime.utcnow(),
            processed_at=datetime.utcnow()
        )
        mock_repository.get_by_id.return_value = submission_already_passed
        
        await consumer.processor.process_submission(submission_id, content)
        
        assert not mock_repository.update_status.called


    @pytest.mark.asyncio
    async def test_concurrent_crash_scenario(self, mock_repository, mock_validator):
        
        submission_id = "concurrent-crash-111"
        content = "Concurrent test 12345"
        consumer = FastAPIPoll(mock_repository, mock_validator, poll_interval=0.1)
        
        submission_pending = Submission(
            id=submission_id,
            content=content,
            status=SubmissionStatus.PENDING,
            created_at=datetime.utcnow()
        )
        submission_passed = Submission(
            id=submission_id,
            content=content,
            status=SubmissionStatus.PASSED,
            created_at=datetime.utcnow(),
            processed_at=datetime.utcnow()
        )
    
        mock_repository.get_by_id.side_effect = [
            submission_pending,  
            submission_passed,  
        ]
        mock_repository.update_status.return_value = None
        mock_validator.validate.return_value = True
        
        await consumer.processor.process_submission(submission_id, content)
        assert mock_repository.update_status.call_count == 2  
        
        mock_repository.update_status.reset_mock()
        
        await consumer.processor.process_submission(submission_id, content)
        assert not mock_repository.update_status.called  


    @pytest.mark.asyncio
    async def test_submission_not_found_is_handled_gracefully(self, mock_repository, mock_validator):
        submission_id = "nonexistent-222"
        content = "Some content 12345"
        consumer = FastAPIPoll(mock_repository, mock_validator, poll_interval=0.1)
        mock_repository.get_by_id.return_value = None
        
        await consumer.processor.process_submission(submission_id, content)
        
        assert not mock_repository.update_status.called


    @pytest.mark.asyncio
    async def test_database_error_does_not_mark_as_failed(self, mock_repository, mock_validator):

        submission_id = "db-error-333"
        content = "Content for DB error test 12345"
        consumer = FastAPIPoll(mock_repository, mock_validator, poll_interval=0.1)
        
        submission = Submission(
            id=submission_id,
            content=content,
            status=SubmissionStatus.PENDING,
            created_at=datetime.utcnow()
        )
        mock_repository.get_by_id.return_value = submission
        
        mock_repository.update_status.side_effect = Exception("Database connection lost")
        mock_validator.validate.return_value = True
        
        await consumer.processor.process_submission(submission_id, content)
        
        assert mock_repository.update_status.called


    @pytest.mark.asyncio
    async def test_processing_timeout_resets_job(self, mock_repository, mock_validator):

        submission_id = "timeout-test-111"
        content = "Content that timed out 12345"
        consumer = FastAPIPoll(mock_repository, mock_validator, poll_interval=0.1)
        
        processing_started_time = datetime.utcnow() - timedelta(minutes=6)  
        
        submission_stuck_processing = Submission(
            id=submission_id,
            content=content,
            status=SubmissionStatus.PROCESSING,
            created_at=datetime.utcnow() - timedelta(minutes=10),  
            processing_started_at=processing_started_time  
        )
        
        submission_reset_pending = Submission(
            id=submission_id,
            content=content,
            status=SubmissionStatus.PENDING,
            created_at=datetime.utcnow() - timedelta(minutes=10),
            processing_started_at=processing_started_time  
        )
        
        mock_repository.get_by_id.side_effect = [
            submission_stuck_processing,  
            submission_reset_pending,     
        ]
        mock_repository.update_status.return_value = None
        mock_validator.validate.return_value = True
        
        await consumer.processor.process_submission(submission_id, content)
        
        assert mock_repository.update_status.called
        calls = mock_repository.update_status.call_args_list
        assert calls[0][0][1] == SubmissionStatus.PENDING
        
        mock_repository.update_status.reset_mock()
        
        await consumer.processor.process_submission(submission_id, content)
        
        assert mock_repository.update_status.call_count == 2
        assert mock_repository.update_status.call_args_list[0][0][1] == SubmissionStatus.PROCESSING
        assert mock_repository.update_status.call_args_list[1][0][1] == SubmissionStatus.PASSED


    @pytest.mark.asyncio
    async def test_processing_within_timeout_window_skipped(self, mock_repository, mock_validator):
       
        submission_id = "processing-active-222"
        content = "Content being processed 12345"
        consumer = FastAPIPoll(mock_repository, mock_validator, poll_interval=0.1)
        
        processing_started_time = datetime.utcnow() - timedelta(minutes=2)
        
        submission_active_processing = Submission(
            id=submission_id,
            content=content,
            status=SubmissionStatus.PROCESSING,
            created_at=datetime.utcnow() - timedelta(minutes=5),
            processing_started_at=processing_started_time  
        )
        
        mock_repository.get_by_id.return_value = submission_active_processing
        
        await consumer.processor.process_submission(submission_id, content)
        
        assert not mock_repository.update_status.called


    @pytest.mark.asyncio
    async def test_processing_timeout_threshold_exactly_5_minutes(self, mock_repository, mock_validator):
        
        submission_id = "timeout-boundary-333"
        content = "Boundary test content 12345"
        consumer = FastAPIPoll(mock_repository, mock_validator, poll_interval=0.1)
        
        processing_started_time = datetime.utcnow() - timedelta(minutes=5, seconds=1)
        
        submission_at_boundary = Submission(
            id=submission_id,
            content=content,
            status=SubmissionStatus.PROCESSING,
            created_at=datetime.utcnow() - timedelta(minutes=10),
            processing_started_at=processing_started_time
        )
        
        mock_repository.get_by_id.side_effect = [
            submission_at_boundary,  
            submission_at_boundary,  
        ]
        mock_repository.update_status.return_value = None
        mock_validator.validate.return_value = True
        
        await consumer.processor.process_submission(submission_id, content)
        
        assert mock_repository.update_status.called
        first_call = mock_repository.update_status.call_args_list[0]
        assert first_call[0][1] == SubmissionStatus.PENDING
