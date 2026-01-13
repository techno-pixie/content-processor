import json
import time
import logging
from kafka import KafkaConsumer
from datetime import datetime
import re
from app.models import Submission, SubmissionStatus
from app.database import SessionLocal, init_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_content(content: str) -> bool:
    """
    Validation Logic:
    - PASSED: content length >= 10 AND contains a number
    - FAILED: otherwise
    """
    if len(content) < 10:
        return False
    if not re.search(r'\d', content):
        return False
    return True


def process_submission(submission_id: str, content: str) -> bool:
    """
    Process submission in the worker.
    
    Steps:
    1. Update status to PROCESSING
    2. Simulate resource-intensive operation (~5s delay)
    3. Validate content
    4. Update status to PASSED or FAILED
    """
    db = SessionLocal()
    try:
        # Fetch the submission
        submission = db.query(Submission).filter(Submission.id == submission_id).first()
        if not submission:
            logger.warning(f"Submission {submission_id} not found in database")
            return False

        # Update to PROCESSING state
        submission.status = SubmissionStatus.PROCESSING
        db.commit()
        logger.info(f"[{submission_id}] Status: PENDING -> PROCESSING")

        # Simulate resource-intensive processing with ~5s delay
        time.sleep(5)

        # Validate the content
        is_valid = validate_content(content)

        # Update status based on validation result
        submission.status = SubmissionStatus.PASSED if is_valid else SubmissionStatus.FAILED
        submission.processed_at = datetime.utcnow()
        db.commit()
        
        result = "PASSED" if is_valid else "FAILED"
        logger.info(f"[{submission_id}] Status: PROCESSING -> {result}")
        return True

    except Exception as e:
        logger.error(f"Error processing submission {submission_id}: {str(e)}")
        submission = db.query(Submission).filter(Submission.id == submission_id).first()
        if submission:
            submission.status = SubmissionStatus.FAILED
            submission.processed_at = datetime.utcnow()
            db.commit()
        return False
    finally:
        db.close()


def start_consumer():
    """
    Start Kafka consumer to process submissions.
    Listens on 'submissions' topic for submission events.
    """
    # Initialize database
    init_db()
    
    logger.info("Initializing Kafka Consumer...")
    
    try:
        # Create Kafka consumer
        consumer = KafkaConsumer(
            'submissions',
            bootstrap_servers=['localhost:9092'],
            group_id='submission-processor',
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True,
        )
        
        logger.info("✓ Connected to Kafka broker")
        logger.info("✓ Listening on topic: 'submissions'")
        logger.info("✓ Consumer group: 'submission-processor'")
        logger.info("\n" + "="*60)
        logger.info("Kafka Consumer Worker Started")
        logger.info("="*60 + "\n")
        
        # Process messages
        for message in consumer:
            try:
                submission_data = message.value
                submission_id = submission_data.get('id')
                content = submission_data.get('content')
                
                logger.info(f"[{submission_id}] Received submission event from Kafka")
                
                # Process the submission
                process_submission(submission_id, content)
                
            except Exception as e:
                logger.error(f"Error processing Kafka message: {str(e)}")
                
    except Exception as e:
        logger.error(f"Kafka Consumer Error: {str(e)}")
        logger.info("Retrying in 5 seconds...")
        time.sleep(5)
        start_consumer()


if __name__ == '__main__':
    start_consumer()
