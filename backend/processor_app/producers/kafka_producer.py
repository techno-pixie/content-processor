"""Kafka producer for publishing submissions to Kafka topic"""

import json
import logging

from kafka import KafkaProducer

from processor_app.interfaces.producer import IProducer

logger = logging.getLogger(__name__)


class KafkaProducerImpl(IProducer):
    
    def __init__(
        self,
        bootstrap_servers: list,
        topic: str = "submissions"
    ):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.producer = None
        self._initialize()

    def _initialize(self) -> None:
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all',
                retries=3,
                max_in_flight_requests_per_connection=1,
            )
            logger.info("Kafka producer initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            raise

    def produce(self, submission_id: str, content: str) -> None:
        if not self.producer:
            logger.error("Kafka producer not initialized")
            return

        try:
            future = self.producer.send(self.topic, {
                'id': submission_id,
                'content': content
            })
            future.get(timeout=5)
            self.producer.flush()
            logger.info(f"[{submission_id}] Published to Kafka successfully")
        except Exception as e:
            logger.error(f"[{submission_id}] Failed to publish to Kafka: {e}")

    def is_available(self) -> bool:
        return self.producer is not None

    def shutdown(self) -> None:
        if self.producer:
            self.producer.close()
        logger.info("Kafka producer shut down")
