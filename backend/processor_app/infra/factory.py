
import os
import logging
from typing import Optional

from processor_app.repositories.repository import Repository
from processor_app.repositories.processor_repository import ProcessorRepository

logger = logging.getLogger(__name__)


class Factory:
    _repository: Optional[Repository] = None

    @staticmethod
    def get_repository() -> Repository:
        if Factory._repository is None:
            Factory._repository = ProcessorRepository()
        return Factory._repository