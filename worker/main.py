"""
Content Processor - Kafka Consumer Worker

To run:
    python main.py
"""
from app.consumer import start_consumer

if __name__ == "__main__":
    start_consumer()
