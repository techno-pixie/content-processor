## Architecture

**Current: Single Application with Logical Layers**

Application runs as one process with two main components:

1. **API Layer (FastAPI)** - Handles HTTP requests, accepts submissions, stores them
2. **Worker Layer** - Processes jobs asynchronously in the background
3. **Shared Database** - API and Worker communicate only through database

Both layers run in the same Python process, but are logically separated. The Worker picks up jobs created by the API.

```
Single Process (main.py)
├── FastAPI API Routes
│   └── Creates PENDING submissions
│
├── Background Worker (FastAPI Poll or Kafka Consumer)
│   └── Processes submissions
│   └── Updates status (PENDING → PROCESSING → PASSED/FAILED)
│
└── Shared Database
```

This approach is practical for development and moderate volume. When we need massive scale, we can split these into separate services (true 3-tier), but the logic stays the same.

## How It Works

```
User submits content
     ↓
API creates record (PENDING) and queues job
     ↓
API returns immediately (user doesn't wait)
     ↓
Background worker picks up job
     ↓
Worker validates and updates status
(PENDING → PROCESSING → PASSED/FAILED)
     ↓
Frontend polls for updates
```

**Key insight:** API and Worker communicate only through the database. They're completely independent. If a worker crashes, another picks up the job. No data loss.

## Scaling to High Volume

The beauty of this design: You can evolve from single process to distributed services.

### Current (Single Process)
- 1 process runs API + Worker
- Handles ~100 submissions/day
- No external services needed
- Fast for development and testing

### Production (Separate Services)
```
API Server         Worker Service 1
    ↓                      ↓
Kafka Topic ← messages flow through
    ↓                      ↓
        Shared Database
```

To scale:
1. Extract Worker into separate `worker.py` service
2. Run multiple Worker instances consuming from Kafka
3. Run multiple API instances
4. Each scales independently

**The code is already ready for this** - `SubmissionProcessor` works with any queue system (Kafka or polling). Just deploy as separate services.

## Development vs Production

### Right Now (Single Process)
- API and Worker in same process
- Use FastAPI polling for simple jobs or Kafka for more throughput
- No external dependencies (except Kafka if chosen)
- Perfect for development, testing, and moderate load

**How to run:**
```bash
# Development: FastAPI producer/consumer
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production-ready: Kafka producer/consumer
USE_KAFKA=true uvicorn main:app --host 0.0.0.0 --port 8000
```

The submission processing logic is shared in `SubmissionProcessor` - same validation, same status updates, same timeout handling. Only the queue implementation changes.

**Limitation:** If the process crashes, jobs being processed are lost (mitigated by 5-minute timeout that resets stuck jobs).

### When You Scale (Separate Services)
Split into separate API and Worker services when you need independent scaling:

```bash
# Terminal 1: API only
uvicorn api:app --port 8000

# Terminal 2+: Workers only
USE_KAFKA=true python worker.py
```

Multiple workers consume from same Kafka topic, process independently, scale horizontally. No job loss - Kafka persists messages.

## Crash Safety & Idempotency

The system handles worker crashes:

1. **Crash before processing:** Job stays PENDING, another worker retries
2. **Crash during processing:** Job has 5-minute timeout, resets to PENDING automatically
3. **Crash during final update:** Job already marked PASSED/FAILED, idempotency prevents duplicate processing



