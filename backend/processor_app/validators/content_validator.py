"""Content validator implementation"""

import re
import logging
from processor_app.interfaces.validator import IContentValidator

logger = logging.getLogger(__name__)


class ContentValidator(IContentValidator):

    def validate(self, content: str) -> bool:
        if len(content) < 10:
            logger.debug(f"Validation failed: content too short ({len(content)} < 10)")
            return False

        if not re.search(r'\d', content):
            logger.debug("Validation failed: content contains no digits")
            return False

        logger.debug("Content validation passed")
        return True
