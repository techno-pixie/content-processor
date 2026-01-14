## Architecture

**Three-tier design:**

1. **API (FastAPI)** - Accepts submissions, stores them, queues jobs, returns immediately
2. **Job Queue** - Holds work to be processed (currently FastAPI, Kafka in production)
3. **Worker** - Processes jobs asynchronously in the background

## Why This Design?

Traditional request-response models make the user wait for validation to complete. This architecture decouples submission from processing:

- User submits → API returns immediately (no waiting)
- Processing happens in background → User polls for status
- Multiple workers can process independently
- If a worker crashes → Another worker picks up the job automatically

This is how production systems at scale handle long-running operations.

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

The beauty of this design: **Each layer scales independently.**

### Current (Development)
- 1 API + 1 Worker
- Handles ~100 submissions/day
- Single process, no external services

### Growing (1K submissions/day)
```
2 API instances (load balanced)
  → Each handles 200 requests/sec
5 Worker instances
  → Processes 5x faster
Same database
```

### High Volume (100K+ submissions/day)
```
10 API instances
50 Worker instances
Kafka (message broker)
Load balancer distributing traffic
```

Each layer scales independently. Add more workers when processing backs up. Add more APIs when submissions increase. No bottlenecks, no coupling.

## Development vs Production

### Right Now (FastAPI Worker)
- Using FastAPI background polling
- No external dependencies
- Single `python main.py` to run everything
- Fast iteration and debugging

**Limitations:** Workers don't persist. If the process crashes, jobs can be lost.

### Production (Kafka)
- Replace queue with **Kafka**
- Multiple workers consume from same topic
- Kafka persists all messages (no job loss)
- Automatic load balancing (Kafka distributes to workers)
- Scales to millions of messages/second

**Code change:** Only the producer/consumer implementation. Validation logic stays the same.

```python
# Development: FastAPI produces jobs
queue.enqueue(job)

# Production: Kafka produces jobs
kafka_producer.send("submissions_topic", job)
```

## Crash Safety & Idempotency

The system handles worker crashes:

1. **Crash before processing:** Job stays PENDING, another worker retries
2. **Crash during processing:** Job has 5-minute timeout, resets to PENDING automatically
3. **Crash during final update:** Job already marked PASSED/FAILED, idempotency prevents duplicate processing



