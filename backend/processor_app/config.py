import os
from typing import List

USE_KAFKA = os.getenv('USE_KAFKA', '').lower() in ('true', '1', 'yes')

KAFKA_BOOTSTRAP_SERVERS: List[str] = os.getenv(
    'KAFKA_BOOTSTRAP_SERVERS',
    'localhost:9092'
).split(',')

KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'submissions')
KAFKA_GROUP_ID = os.getenv('KAFKA_GROUP_ID', 'submission-processor')

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite+aiosqlite:///./submissions.db')

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

__all__ = [
    'USE_KAFKA',
    'KAFKA_BOOTSTRAP_SERVERS',
    'KAFKA_TOPIC',
    'KAFKA_GROUP_ID',
    'DATABASE_URL',
    'LOG_LEVEL',
]
