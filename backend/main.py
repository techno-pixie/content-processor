from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from processor_app.content_processor_service.content_processor_route import router as content_processor_router
from processor_app.content_processor_service.content_processor_repository import ContentProcessorRepository
from processor_app.infra.factory import Factory
from processor_app.validators import ContentValidator
from processor_app.config import LOG_LEVEL
import logging

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
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
        
        validator = ContentValidator()
        producer = Factory.get_producer()
        consumer = Factory.get_consumer(content_repo, validator)
        
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
