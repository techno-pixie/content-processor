# Content Processor

A full-stack application that allows users to submit content and track its processing status in real-time. The application demonstrates proper separation of concerns between synchronous API requests and asynchronous background processing.

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
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── models/         # SQLAlchemy ORM models
│   │   │   └── submission.py
│   │   ├── schemas/        # Pydantic request/response models
│   │   │   └── submission.py
│   │   ├── routes/         # API endpoints
│   │   │   └── __init__.py
│   │   ├── workers/        # Async processing logic
│   │   │   └── processor.py
│   │   ├── database.py     # Database configuration
│   │   └── __init__.py     # FastAPI app initialization
│   ├── main.py             # Entry point
│   └── requirements.txt
│
└── frontend/                # React application
    ├── src/
    │   ├── components/      # React components
    │   │   ├── App.jsx
    │   │   ├── SubmissionForm.jsx
    │   │   └── SubmissionStatus.jsx
    │   ├── services/        # API client
    │   │   └── api.js
    │   └── main.jsx
    ├── package.json
    └── vite.config.js
```

## Architecture

### Core Design Principles

#### 1. **Separation of Concerns**
- **API Layer**: Handles HTTP requests/responses synchronously
  - Receives submission, stores in database with PENDING status
  - Returns immediately with submission ID
  - Provides endpoint to query status
  
- **Worker Layer**: Handles asynchronous processing
  - Independent from API request/response cycle
  - Runs in background using asyncio
  - Updates database state transitions

#### 2. **Non-Blocking Submission**
```
User Request → API creates record → Return 200 OK immediately
                    ↓
            asyncio.create_task() spawned
                    ↓
        Worker begins processing in background
```

The API does **not** wait for processing. This is critical for scalability:
- Users get instant feedback (submission ID)
- API can handle many concurrent submissions
- Processing doesn't block other requests

#### 3. **State Management**
All state transitions are managed through the database:
- **PENDING** → **PROCESSING**: Worker updates when it starts
- **PROCESSING** → **PASSED/FAILED**: Worker updates when complete
- Frontend polls status endpoint to see updates

### Component Details

#### Backend (FastAPI)

**Database Schema:**
```python
Submission {
  id: UUID (primary key)
  content: String
  status: Enum[PENDING, PROCESSING, PASSED, FAILED]
  created_at: DateTime
  processed_at: DateTime (nullable)
}
```

**API Endpoints:**
- `POST /api/submissions/` - Submit content
  - Request: `{ "content": "string" }`
  - Response: `{ "id": "uuid", "status": "PENDING", ... }`
  - Returns immediately, spawns background task
  
- `GET /api/submissions/{submission_id}` - Check status
  - Returns current submission details
  - Frontend uses this for polling
  
- `GET /api/submissions/` - List all submissions
  - Admin/monitoring endpoint

**Async Worker (`processor.py`):**
```python
async def process_submission(submission_id: str):
    1. Fetch submission from DB
    2. Update status to PROCESSING
    3. await asyncio.sleep(5)  # Simulate processing
    4. Validate content
    5. Update status to PASSED or FAILED
    6. Set processed_at timestamp
```

#### Frontend (React)

**Components:**
- `App.jsx` - Main container, manages submission list
- `SubmissionForm.jsx` - Input form for content
- `SubmissionStatus.jsx` - Status display card

**Real-time Updates:**
```javascript
// After successful submission
const newSubmission = await submitContent(content);
pollStatus(newSubmission.id);

// Poll every 1 second
setInterval(() => {
  const updated = await getSubmissionStatus(submissionId);
  // Update state with new data
}, 1000);

// Stop polling when complete
if (status === 'PASSED' || status === 'FAILED') {
  clearInterval(pollInterval);
}
```

## Scalability Design

### Current Architecture (Single Instance)

```
┌─────────────┐
│  Frontend   │ (React, Static)
└──────┬──────┘
       │ HTTP
┌──────▼──────────────┐
│  FastAPI Server     │
│  ├── API Routes     │
│  ├── asyncio Task   │
│  └── SQLite DB      │
└─────────────────────┘
```

### Scaling Strategy (High Volume)

#### 1. **Separate API and Workers**
For production with high volume, decouple into separate processes:

```
┌──────────────────────────────────────────────────────┐
│                                                      │
│  API Servers (Stateless)                            │
│  ├── POST /submissions → DB insert + Queue task    │
│  ├── GET /submissions/{id} → Query DB              │
│  └── (no processing logic)                         │
│                                                      │
└───────────────┬────────────────────────────────────┘
                │
        ┌───────▼────────┐
        │ Message Queue  │ (Redis/RabbitMQ)
        │ (Task Queue)   │
        └───────┬────────┘
                │
    ┌───────────┼──────────────┐
    │           │              │
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

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API will be available at `http://localhost:8000`

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend will be available at `http://localhost:3000` (or `http://localhost:5173`)

### Testing

1. Open `http://localhost:3000` in browser
2. Submit content in the form
3. Watch status update in real-time (PENDING → PROCESSING → PASSED/FAILED)
4. Try different content:
   - Valid: "This contains number 42" (length ≥ 10, has digit)
   - Invalid: "short" (too short)
   - Invalid: "this has no numbers" (length ≥ 10, but no digit)

### Database

SQLite database is created automatically at `backend/submissions.db`

View submissions:
```bash
sqlite3 submissions.db
> SELECT id, content, status, created_at FROM submissions;
```

## API Documentation

Once running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

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
