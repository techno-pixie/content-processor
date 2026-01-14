"""FastAPI producer for triggering submission processing"""

import logging

from processor_app.interfaces.producer import IProducer

logger = logging.getLogger(__name__)


class FastAPITrigger(IProducer):
    """Triggers submission processing (no-op for FastAPI since it auto-discovers)"""
    
    def __init__(self):
        pass

    def produce(self, submission_id: str, content: str) -> None:
        """
        FastAPI processor auto-discovers work via polling,
        so explicit triggering is not needed.
        This method is here for interface compliance only.
        """
        logger.debug(f"[{submission_id}] FastAPI processor will auto-discover this submission via polling")

    def is_available(self) -> bool:
        """FastAPI trigger is always available"""
        return True
