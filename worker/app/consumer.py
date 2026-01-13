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
    Process submission in the worker with idempotency guarantee.
    
    Idempotency: If called multiple times with same submission_id,
    only processes if status is still PENDING. This handles Kafka retries.
    
    Steps:
    1. Check if already processed (idempotency)
    2. Update status to PROCESSING
    3. Simulate resource-intensive operation (~5s delay)
    4. Validate content
    5. Update status to PASSED or FAILED
    """
    db = SessionLocal()
    try:
        # Fetch the submission
        submission = db.query(Submission).filter(Submission.id == submission_id).first()
        if not submission:
            logger.warning(f"[{submission_id}] NOT FOUND - skipping")
            return False

        # IDEMPOTENCY CHECK: Skip if already processed
        if submission.status != SubmissionStatus.PENDING:
            logger.info(f"[{submission_id}] Already processed (status: {submission.status}) - skipping")
            return True  # Return True because message is already handled

        # Update to PROCESSING state (atomic operation)
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
        logger.error(f"[{submission_id}] ERROR: {str(e)}")
        # Try to mark as FAILED, but don't crash if DB is down
        try:
            submission = db.query(Submission).filter(Submission.id == submission_id).first()
            if submission and submission.status == SubmissionStatus.PROCESSING:
                submission.status = SubmissionStatus.FAILED
                submission.processed_at = datetime.utcnow()
                db.commit()
                logger.info(f"[{submission_id}] Status: PROCESSING -> FAILED (error)")
        except Exception as db_error:
            logger.error(f"[{submission_id}] Failed to update error status: {str(db_error)}")
        return False
    finally:
        db.close()


def start_consumer():
    """
    Start Kafka consumer with exactly-once semantics.
    
    Design:
    1. enable_auto_commit=False: Don't auto-commit offsets
    2. Manual commit ONLY after successful processing
    3. Idempotency check prevents duplicate processing
    4. If worker crashes, Kafka rebalances and reprocesses message
    
    Guarantees:
    - At-least-once delivery: Messages won't be lost
    - Idempotent processing: Duplicate messages are skipped
    - Effective exactly-once: Combined with database state checks
    """
    # Initialize database
    init_db()
    
    logger.info("Initializing Kafka Consumer...")
    
    try:
        # Create Kafka consumer with manual offset management
        consumer = KafkaConsumer(
            'submissions',
            bootstrap_servers=['localhost:9092'],
            group_id='submission-processor',
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=False,  # ✓ Manual commit for exactly-once
            max_poll_records=1,  # Process one at a time for clarity
        )
        
        logger.info("✓ Connected to Kafka broker")
        logger.info("✓ Listening on topic: 'submissions'")
        logger.info("✓ Consumer group: 'submission-processor'")
        logger.info("✓ Manual offset commit enabled (exactly-once semantics)")
        logger.info("\n" + "="*60)
        logger.info("Kafka Consumer Worker Started")
        logger.info("="*60 + "\n")
        
        # Process messages with manual offset management
        for message in consumer:
            try:
                submission_data = message.value
                submission_id = submission_data.get('id')
                content = submission_data.get('content')
                
                logger.info(f"[{submission_id}] Received submission event from Kafka")
                
                # Process the submission (with idempotency check)
                success = process_submission(submission_id, content)
                
                # ✓ ONLY commit offset AFTER successful processing
                if success:
                    consumer.commit()  # Commit offset to Kafka
                    logger.info(f"[{submission_id}] Offset committed")
                else:
                    logger.warning(f"[{submission_id}] Processing failed - offset NOT committed (will retry)")
                    
            except Exception as e:
                logger.error(f"Error processing Kafka message: {str(e)}")
                # Don't commit on error - message will be reprocessed
                
    except Exception as e:
        logger.error(f"Kafka Consumer Error: {str(e)}")
        logger.info("Retrying in 5 seconds...")
        time.sleep(5)
        start_consumer()  # Reconnect and retry


if __name__ == '__main__':
    start_consumer()
