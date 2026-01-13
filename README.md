# Content Processor

A full-stack microservice application that allows users to submit content and track its processing status in real-time. The application uses Kafka as a message broker to decouple the API from the processing workers, enabling true scalability and fault tolerance.

## Overview

This application implements a three-state processing pipeline:
- **PENDING**: Submission received, awaiting processing
- **PROCESSING**: Content is being validated (simulated 5s delay)
- **PASSED/FAILED**: Processing complete (based on validation rules)

### Validation Rules
- ✅ **PASSED**: Content length ≥ 10 AND contains at least one number
- ❌ **FAILED**: Any other condition

## Project Structure

```
content-processor/
├── backend/                 # FastAPI API Server (Kafka Producer)
│   ├── app/
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── schemas/        # Pydantic request/response models
│   │   ├── routes/         # API endpoints
│   │   ├── database.py     # Database configuration
│   │   └── __init__.py     # FastAPI app initialization
│   ├── main.py             # Entry point
│   └── requirements.txt
│
├── worker/                  # Kafka Consumer Worker Service
│   ├── app/
│   │   ├── models/         # Shared database models
│   │   ├── consumer.py     # Kafka consumer logic
│   │   ├── database.py     # Database configuration
│   │   └── __init__.py
│   ├── main.py             # Worker entry point
│   └── requirements.txt
│
├── frontend/                # React Application
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── services/        # API client
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
│
├── docker-compose.yml       # Kafka + Zookeeper setup
└── README.md
```

## Architecture

### Microservice Design with Kafka

The application follows a **producer-consumer pattern** using Kafka as the message broker:

```
┌─────────────┐
│  Frontend   │ (React)
└──────┬──────┘
       │ HTTP
┌──────▼──────────────────┐
│  FastAPI API Server     │ (Kafka Producer)
│  ├── POST /submissions  │ ✓ Creates DB record
│  ├── Publishes to Kafka │ ✓ Returns immediately
│  └── GET /submissions   │ ✓ Queries DB status
└──────┬──────────────────┘
       │
       │ Publish: submission event
       ▼
┌──────────────────────────┐
│   Kafka Topic: "submissions"   │
│   (Message Queue)        │
└──────┬──────────────────┘
       │
       │ Consume: subscription event
       ▼
┌──────────────────────────┐
│  Kafka Consumer Worker   │ (Process 1)
│  ├── Consume events      │ 
│  ├── Validate content    │
│  └── Update DB status    │
└──────────────────────────┘

[Additional workers can be added]
  Worker 2, Worker 3, ... etc.
  (all consume from same topic)
```

#### 1. **API Server (Producer)**
- Receives HTTP submission requests
- Creates submission record in database (status: PENDING)
- Publishes event to Kafka topic immediately
- Returns submission ID to user (non-blocking)
- Never processes content directly

```python
@router.post("/api/submissions/")
async def create_submission(content):
    # 1. Create DB record
    submission = Submission(id=uuid, content=content, status=PENDING)
    db.add(submission)
    db.commit()
    
    # 2. Publish to Kafka (non-blocking)
    kafka_producer.send('submissions', {
        'id': submission.id,
        'content': content
    })
    
    # 3. Return immediately
    return submission  # status: PENDING
```

#### 2. **Kafka Worker (Consumer)**
- Listens to Kafka topic "submissions"
- Consumes submission events one at a time
- Updates database status: PENDING → PROCESSING
- Simulates resource-intensive processing (5s sleep)
- Validates content and updates final status: PROCESSING → PASSED/FAILED

```python
def start_consumer():
    consumer = KafkaConsumer('submissions', group_id='submission-processor')
    
    for event in consumer:
        submission_id = event['id']
        content = event['content']
        
        # Update to PROCESSING
        db.update_status(submission_id, PROCESSING)
        
        # Simulate work
        time.sleep(5)
        
        # Validate & finalize
        is_valid = validate(content)
        final_status = PASSED if is_valid else FAILED
        db.update_status(submission_id, final_status)
```

#### 3. **Key Advantages**

| Aspect | Benefit |
|--------|---------|
| **Decoupling** | API and workers are completely independent |
| **Scaling** | Add workers without modifying API |
| **Fault Tolerance** | Kafka stores messages; workers can restart safely |
| **Load Balancing** | Multiple workers share consumer group automatically |
| **Non-blocking** | API returns immediately; no waiting for processing |
| **Persistence** | Kafka retains messages; no lost submissions |
| **Monitoring** | Kafka UI available at `http://localhost:8080` |

#### 4. **State Management**
All state transitions via database (single source of truth):
- **PENDING** → **PROCESSING**: Worker updates upon consuming event
- **PROCESSING** → **PASSED/FAILED**: Worker updates after validation
- Frontend polls `/api/submissions/{id}` to check current status

## Scalability Design

### Current Architecture (Kafka + Multiple Workers)

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  Load Balancer / API Gateway                           │
│                                                         │
└──────────────┬──────────────────────────────────────────┘
               │
    ┌──────────┼──────────┐
    │          │          │
┌───▼──┐   ┌───▼──┐   ┌──▼───┐
│ API  │   │ API  │   │ API  │  (Stateless - scale horizontally)
│Srv 1 │   │Srv 2 │   │Srv 3 │
└───┬──┘   └───┬──┘   └──┬───┘
    │          │         │
    └──────────┼─────────┘
               │
        ┌──────▼─────────┐
        │ Kafka Broker   │
        │ Topic: "submissions"  │
        └──────┬─────────┘
               │
    ┌──────────┼──────────┐
    │          │          │
┌───▼──┐   ┌───▼──┐   ┌──▼───┐
│Worker│   │Worker│   │Worker│  (Consumer group - auto-balanced)
│ 1    │   │ 2    │   │ 3    │
└───┬──┘   └───┬──┘   └──┬───┘
    │          │         │
    └──────────┼─────────┘
               │
        ┌──────▼──────────┐
        │  PostgreSQL DB  │
        │ (Shared State)  │
        └─────────────────┘
```

### Scaling Benefits with Kafka

| Dimension | Without Kafka | With Kafka |
|-----------|---------------|-----------|
| **API Instances** | Limited by in-process workers | Unlimited - stateless |
| **Worker Instances** | 1 per server | N per consumer group |
| **Message Loss** | Possible if process crashes | Persisted, replay-able |
| **Throughput** | Single process limited | Scales linearly with workers |
| **Fault Tolerance** | Poor - process death loses tasks | Excellent - Kafka stores events |
| **Max Load** | ~100 req/sec per instance | 10,000+ req/sec with workers |

### Horizontal Scaling Example

**Scale to 10x load:**

```bash
# Terminal 1: Start multiple API servers (behind load balancer)
uvicorn main:app --host 0.0.0.0 --port 8000
uvicorn main:app --host 0.0.0.0 --port 8001
uvicorn main:app --host 0.0.0.0 --port 8002

# Terminal 2-4: Start multiple workers (auto-balanced by Kafka)
python worker/main.py  # Worker 1 - processes 33% of messages
python worker/main.py  # Worker 2 - processes 33% of messages
python worker/main.py  # Worker 3 - processes 33% of messages
```

Kafka automatically distributes messages among workers. Add/remove workers dynamically.

### Future Enhancements for Even Higher Scale

**If you need to handle millions of events/sec:**

1. **Kafka Partitioning**
   - Split topic into multiple partitions
   - Workers distributed across partitions
   - Parallel processing of multiple submissions simultaneously

2. **Database Optimization**
   ```python
   # Switch from SQLite to PostgreSQL
   DATABASE_URL = "postgresql://user:pass@postgres-server/submissions"
   
   # Add connection pooling
   from sqlalchemy.pool import QueuePool
   engine = create_engine(DATABASE_URL, poolclass=QueuePool, pool_size=20)
   ```

3. **Kubernetes Deployment**
   ```yaml
   # Scale API and workers independently
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: api-server
   spec:
     replicas: 10  # 10 API instances
   ---
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: kafka-worker
   spec:
     replicas: 50  # 50 worker instances
   ```

4. **Monitoring & Alerts**
   - Consumer lag monitoring (backlog of unprocessed messages)
   - Kafka metrics (throughput, latency)
   - Alert if consumer lag > 1000 messages

### Current Architecture (Single Instance)
┌───▼──┐   ┌───▼──┐   ┌───▼──┐
│Worker│   │Worker│   │Worker│  (Scale horizontally)
│  1   │   │  2   │   │  N   │
└──────┘   └──────┘   └──────┘
    │           │              │
    └───────────┼──────────────┘
                │
            ┌───▼─────────┐
            │ PostgreSQL  │ (Persistent State)
            │ (Shared DB) │
            └─────────────┘
```

**Implementation Options:**

**Option A: Celery + Redis**
```python
# Install: pip install celery redis

from celery import Celery

celery_app = Celery('content_processor', broker='redis://localhost')

@celery_app.task
def process_submission_task(submission_id: str):
    # Same processing logic
    pass

# In API route:
process_submission_task.delay(submission_id)
```

**Option B: Kubernetes + Native AsyncIO**
```python
# Keep current asyncio design but run in containers
# Deploy multiple FastAPI pods behind load balancer
# Each pod can process tasks independently
# All share same PostgreSQL database
```

#### 2. **Database Optimization**
- **Current**: SQLite (single file, not suitable for concurrent writes)
- **Production**: PostgreSQL
  - Handles concurrent writes
  - ACID transactions ensure state consistency
  - Supports connection pooling
  - Better query performance

```python
# In database.py
DATABASE_URL = "postgresql://user:password@localhost/content_processor"
```

#### 3. **Load Handling**

**Current bottleneck:** 
- Single API server: ~100 req/sec (limited by workers)
- SQLite: No concurrent write locking

**Scaling improvements:**

| Component | Current | Scaled |
|-----------|---------|--------|
| API Servers | 1 | N (load balanced) |
| Message Queue | asyncio | Redis/RabbitMQ |
| Workers | 1 (asyncio tasks) | N (separate processes) |
| Database | SQLite | PostgreSQL |
| **Throughput** | ~100 req/sec | **1000+ req/sec** |

#### 4. **State Consistency Guarantees**

**Problem**: If worker crashes mid-processing, task is lost.

**Solutions:**

1. **Task Persistence**: Store task state in message queue
   ```python
   # Celery automatically retries failed tasks
   @celery_app.task(bind=True, max_retries=3)
   def process_with_retries(self, submission_id):
       try:
           process_submission(submission_id)
       except Exception as e:
           self.retry(exc=e, countdown=60)
   ```

2. **Database Transactions**: Use transactions for atomicity
   ```python
   from sqlalchemy import begin
   
   with db.begin():
       submission.status = PROCESSING
       # If error occurs, automatic rollback
   ```

3. **Monitoring & Alerting**
   - Track stuck submissions (PROCESSING > 30s)
   - Dead letter queue for failed tasks
   - Prometheus metrics for visibility

#### 5. **Performance Benchmarks (Estimated)**

| Scenario | Response Time | Notes |
|----------|---------------|-------|
| Submit | < 50ms | Immediate DB write |
| Poll Status | < 10ms | Simple SELECT query |
| Processing | ~5s | Simulated (tunable) |
| **Peak Load** | No degradation | With proper scaling |

## Running the Application

### Prerequisites

Ensure Docker is installed (for Kafka). If not:
- [Install Docker](https://docs.docker.com/get-docker/)

### Step 1: Start Kafka & Zookeeper

```bash
cd content-processor
docker-compose up -d
```

Wait for Kafka to be ready (~15 seconds):
```bash
docker-compose logs kafka
# Look for "started (kafka.server.KafkaServer)"
```

✓ Kafka will be available at `localhost:9092`  
✓ Kafka UI (optional monitoring) at `http://localhost:8080`

### Step 2: Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

✓ API available at `http://localhost:8000`

### Step 3: Start Kafka Worker (new terminal)

```bash
cd worker
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

You should see:
```
============================================================
Kafka Consumer Worker Started
============================================================

INFO: [submission-id] Received submission event from Kafka
INFO: [submission-id] Status: PENDING -> PROCESSING
INFO: [submission-id] Status: PROCESSING -> PASSED
```

### Step 4: Frontend Setup (new terminal)

```bash
cd frontend
npm install
npm run dev
```

✓ Frontend available at `http://localhost:3000` (or `http://localhost:5173`)

### Testing the Application

1. Open `http://localhost:3000` in browser
2. Submit content in the form
3. Watch status update in real-time (PENDING → PROCESSING → PASSED/FAILED)
4. Try different content:
   - ✅ Valid: "This contains number 42" (length ≥ 10, has digit)
   - ❌ Invalid: "short" (too short)
   - ❌ Invalid: "this has no numbers" (length ≥ 10, but no digit)
5. Check Kafka UI: `http://localhost:8080` to see topic and messages

### Database

SQLite database created automatically at `backend/submissions.db` and `worker/submissions.db`

View submissions (backend):
```bash
sqlite3 backend/submissions.db
> SELECT id, content, status, created_at, processed_at FROM submissions;
```

### Stopping Services

```bash
# Stop Kafka & Zookeeper
docker-compose down

# Deactivate Python virtual environments
deactivate
```

## API Documentation

Once running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **Kafka UI**: `http://localhost:8080` (optional, for monitoring)

## Key Design Decisions

### 1. Why asyncio for workers (current)?
✅ Simple for prototyping  
✅ No external dependencies (Redis, RabbitMQ)  
❌ All workers run in same process  
❌ Not suitable for distributed systems  

**When to upgrade**: High volume (>100 submissions/sec)

### 2. Why polling instead of WebSockets?
✅ Simpler to implement  
✅ Works with any backend  
✅ No persistent connections  
❌ Higher latency (1s poll interval)  

**When to upgrade**: Need real-time updates < 100ms

### 3. Why SQLite for database?
✅ No setup required  
✅ File-based, easy to backup  
❌ No concurrent writes  
❌ Not suitable for production  

**When to upgrade**: Multiple concurrent workers

## Future Enhancements

1. **WebSocket Updates**: Replace polling with WebSocket for real-time updates
2. **Task Retry Logic**: Implement exponential backoff for failed submissions
3. **Batch Processing**: Accept multiple submissions in single request
4. **Admin Dashboard**: Monitor queue, worker status, metrics
5. **Content Caching**: Cache validation results for duplicate submissions
6. **Rate Limiting**: Prevent abuse of submission endpoint
7. **Authentication**: Add user accounts and submission ownership

## Technologies Used

### Backend
- **FastAPI**: Modern async Python web framework
- **SQLAlchemy**: ORM for database operations
- **Uvicorn**: ASGI server
- **Pydantic**: Data validation

### Frontend
- **React 18**: UI library
- **Vite**: Build tool and dev server
- **Axios**: HTTP client
- **CSS**: Custom styling (no external dependencies)

## License

MIT
