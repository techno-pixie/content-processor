from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from processor_app.content_processor_service.content_processor_route import router as content_processor_router
from processor_app.content_processor_service.content_processor_repository import ContentProcessorRepository
from processor_app.infra.factory import Factory
from processor_app.consumers.fastapi_poll import FastAPIPoll
from processor_app.consumers.kafka_consumer import KafkaConsumer
from processor_app.producers.fastapi_trigger import FastAPITrigger
from processor_app.producers.kafka_producer import KafkaProducerImpl
from processor_app.validators import ContentValidator
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Content Processor API",
    description="API for submitting and tracking content processing"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(content_processor_router)


@app.on_event("startup")
async def startup_event():
    logger.info("=" * 60)
    logger.info("Starting up application")
    logger.info("=" * 60)
    
    try:
        # Initialize repository
        logger.info("1. Initializing repository...")
        repo = Factory.get_repository()
        content_repo = ContentProcessorRepository(repo)
        await repo.init_db()
        logger.info("2. Repository initialized")
        
        # Detect if using Kafka
        use_kafka = os.getenv('USE_KAFKA', '').lower() in ('true', '1', 'yes')
        validator = ContentValidator()
        
        if use_kafka:
            logger.info("3. Using Kafka producer/consumer")
            kafka_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092').split(',')
            kafka_topic = os.getenv('KAFKA_TOPIC', 'submissions')
            kafka_group_id = os.getenv('KAFKA_GROUP_ID', 'submission-processor')
            
            # Create Kafka producer and consumer
            producer = KafkaProducerImpl(kafka_servers, kafka_topic)
            consumer = KafkaConsumer(content_repo, validator, kafka_servers, kafka_topic, kafka_group_id)
            logger.info("4. Kafka producer and consumer created")
        else:
            logger.info("3. Using FastAPI poll/trigger")
            # Create FastAPI producer and consumer
            producer = FastAPITrigger()
            consumer = FastAPIPoll(content_repo, validator)
            logger.info("4. FastAPI producer and consumer created")
        
        # Store producer in app state for repository to use
        app.state.producer = producer
        content_repo.producer = producer
        
        # Start consumer
        logger.info("5. Starting consumer...")
        await consumer.start()
        logger.info("6. Consumer started")
        
        # Store consumer for shutdown
        app.state.consumer = consumer
        
        logger.info("=" * 60)
        logger.info("Application startup complete")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"STARTUP ERROR: {str(e)}", exc_info=True)


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down application")
    
    if hasattr(app.state, 'consumer'):
        await app.state.consumer.shutdown()
        logger.info("Consumer shut down successfully")


@app.get("/health")
def health_check():
    return {"status": "ok"}
