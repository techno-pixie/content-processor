import logging

from processor_app.interfaces.producer import IProducer

logger = logging.getLogger(__name__)


class FastAPITrigger(IProducer):
    def __init__(self):
        pass

    def produce(self, submission_id: str, content: str) -> None:
        logger.debug(f"[{submission_id}] FastAPI processor will auto-discover this submission via polling")

    def is_available(self) -> bool:
        return True
