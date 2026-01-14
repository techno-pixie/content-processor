import logging
from typing import Optional

from processor_app.config import (
    USE_KAFKA,
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_TOPIC,
    KAFKA_GROUP_ID
)
from processor_app.repositories.repository import Repository
from processor_app.repositories.processor_repository import ProcessorRepository
from processor_app.producers.kafka_producer import KafkaProducerImpl
from processor_app.producers.fastapi_trigger import FastAPITrigger
from processor_app.consumers.kafka_consumer import KafkaConsumer
from processor_app.consumers.fastapi_poll import FastAPIPoll

logger = logging.getLogger(__name__)


class Factory:
    _repository: Optional[Repository] = None

    @staticmethod
    def _get_kafka_settings():
        return KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC, KAFKA_GROUP_ID
    
    @staticmethod
    def _is_kafka_enabled() -> bool:
        return USE_KAFKA
    
    @staticmethod
    def get_repository() -> Repository:
        if Factory._repository is None:
            Factory._repository = ProcessorRepository()
        return Factory._repository
    
    @staticmethod
    def get_producer():
        if Factory._is_kafka_enabled():
            logger.info("3. Using Kafka producer")
            kafka_servers, kafka_topic, _ = Factory._get_kafka_settings()
            return KafkaProducerImpl(kafka_servers, kafka_topic)
        else:
            logger.info("3. Using FastAPI poll")
            return FastAPITrigger()
    
    @staticmethod
    def get_consumer(repository, validator):
        if Factory._is_kafka_enabled():
            logger.info("4. Using Kafka consumer")
            kafka_servers, kafka_topic, kafka_group_id = Factory._get_kafka_settings()
            return KafkaConsumer(repository, validator, kafka_servers, kafka_topic, kafka_group_id)
        else:
            logger.info("4. Using FastAPI poll")
            return FastAPIPoll(repository, validator)