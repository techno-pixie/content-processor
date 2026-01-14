import json
import logging
import asyncio
from typing import Callable, Optional

from kafka import KafkaConsumer as KafkaConsumerClient

from processor_app.interfaces.consumer import IConsumer
from processor_app.content_processor_service.content_processor_repository import ContentProcessorRepository
from processor_app.interfaces.validator import IContentValidator
from processor_app.consumers.submission_processor import SubmissionProcessor

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
        self._task = None
        self.on_complete_callback: Optional[Callable] = None
        self.processor = SubmissionProcessor(repository, validator)

    async def start(self) -> None:
        try:
            self.consumer = KafkaConsumerClient(
                self.topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                auto_offset_reset='earliest',
                enable_auto_commit=False,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')) if m else None,
            )
            logger.info(f"Kafka consumer initialized on topic '{self.topic}'")
            
            self.running = True
            self._task = asyncio.create_task(self._consume_messages())
            logger.info("Kafka consumer started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Kafka consumer: {e}")
            self.running = False
            raise

    async def shutdown(self) -> None:
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self.consumer:
            self.consumer.close()
        logger.info("Kafka consumer shut down")

    async def is_running(self) -> bool:
        return self.running and self._task is not None and not self._task.done()

    def set_on_complete_callback(self, callback: Callable[[str, bool], None]) -> None:
        self.on_complete_callback = callback

    async def _consume_messages(self) -> None:
        while self.running:
            try:
                # Poll messages with timeout
                messages = self.consumer.poll(timeout_ms=1000, max_records=1)
                
                for topic_partition, records in messages.items():
                    for message in records:
                        if not self.running:
                            break

                        try:
                            submission_data = message.value
                            submission_id = submission_data.get('id')
                            content = submission_data.get('content')

                            logger.info(f"[{submission_id}] Received submission from Kafka")

                            success = await self.processor.process_submission(submission_id, content)

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
                
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Kafka consumer error: {e}")
                await asyncio.sleep(1)
