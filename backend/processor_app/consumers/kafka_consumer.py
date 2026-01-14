"""Kafka consumer for processing submissions from Kafka topic"""

import json
import logging
import threading
from typing import Callable, Optional
from datetime import datetime

from kafka import KafkaConsumer

from processor_app.interfaces.consumer import IConsumer
from processor_app.content_processor_service.content_processor_repository import ContentProcessorRepository
from processor_app.content_processor_service.schema import SubmissionStatus
from processor_app.interfaces.validator import IContentValidator

logger = logging.getLogger(__name__)


class KafkaConsumer(IConsumer):
    
    def __init__(
        self,
        repository: ContentProcessorRepository,
        validator: IContentValidator,
        bootstrap_servers: list,
        topic: str = "submissions",
        group_id: str = "submission-processor"
    ):
        self.repository = repository
        self.validator = validator
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.group_id = group_id
        self.consumer = None
        self.running = False
        self._thread = None
        self.on_complete_callback: Optional[Callable] = None

    async def start(self) -> None:
        try:
            self.consumer = KafkaConsumer(
                self.topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='earliest',
                enable_auto_commit=False,
                max_poll_records=1,
            )
            logger.info(f"Kafka consumer initialized on topic '{self.topic}'")
            
            self.running = True
            self._thread = threading.Thread(target=self._consume_messages, daemon=True)
            self._thread.start()
            logger.info("Kafka consumer started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Kafka consumer: {e}")
            self.running = False
            raise

    async def shutdown(self) -> None:
        self.running = False
        if self.consumer:
            self.consumer.close()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Kafka consumer shut down")

    async def is_running(self) -> bool:
        return self.running and self.consumer is not None

    def set_on_complete_callback(self, callback: Callable[[str, bool], None]) -> None:
        self.on_complete_callback = callback

    def _consume_messages(self) -> None:
        try:
            for message in self.consumer:
                if not self.running:
                    break

                try:
                    submission_data = message.value
                    submission_id = submission_data.get('id')
                    content = submission_data.get('content')

                    logger.info(f"[{submission_id}] Received submission from Kafka")

                    success = self._process_submission(submission_id, content)

                    if success:
                        self.consumer.commit()
                        logger.info(f"[{submission_id}] Offset committed")
                        if self.on_complete_callback:
                            self.on_complete_callback(submission_id, True)
                    else:
                        logger.warning(f"[{submission_id}] Processing failed - will retry")
                        if self.on_complete_callback:
                            self.on_complete_callback(submission_id, False)

                except Exception as e:
                    logger.error(f"Error processing message: {e}")

        except Exception as e:
            logger.error(f"Kafka consumer error: {e}")

    def _process_submission(self, submission_id: str, content: str) -> bool:
        try:
            submission = self.repository.get_by_id(submission_id)
            if not submission:
                logger.warning(f"[{submission_id}] Submission not found")
                return False

            if submission.status != SubmissionStatus.PENDING:
                logger.info(f"[{submission_id}] Already processed (status: {submission.status})")
                return True

            self.repository.update_status(submission_id, SubmissionStatus.PROCESSING)
            logger.info(f"[{submission_id}] Status: PENDING -> PROCESSING")

            is_valid = self.validator.validate(content)

            final_status = SubmissionStatus.PASSED if is_valid else SubmissionStatus.FAILED
            self.repository.update_status(submission_id, final_status, datetime.utcnow())

            result = "PASSED" if is_valid else "FAILED"
            logger.info(f"[{submission_id}] Status: PROCESSING -> {result}")
            return True

        except Exception as e:
            logger.error(f"[{submission_id}] Error during processing: {e}")
            try:
                submission = self.repository.get_by_id(submission_id)
                if submission and submission.status == SubmissionStatus.PROCESSING:
                    self.repository.update_status(
                        submission_id,
                        SubmissionStatus.FAILED,
                        datetime.utcnow()
                    )
                    logger.info(f"[{submission_id}] Marked as FAILED due to error")
            except Exception as db_error:
                logger.error(f"[{submission_id}] Failed to update error status: {db_error}")
            return False
