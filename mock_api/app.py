"""
mock_api/app.py
"""
import asyncio
import collections
import json
import logging
import threading
import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from kafka import KafkaConsumer

from config.loader import load_config
from mock_api.auth import verify_bearer_token
from generator.schemas import AudienceEventPage, AudienceEvent

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Shared state
BUFFER_MAX_LEN = 50000
event_buffer = collections.deque(maxlen=BUFFER_MAX_LEN)
buffer_lock = threading.Lock()
consumer_thread_running = False

def consume_kafka_events():
    global consumer_thread_running
    config = load_config()
    bootstrap_servers = config.get("kafka", {}).get("bootstrap_servers", "localhost:9092")
    topic = config.get("kafka", {}).get("topic", "audience_events")

    try:
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset='latest',
            enable_auto_commit=True,
            consumer_timeout_ms=1000
        )
        logger.info(f"Kafka consumer started on topic: {topic}")
        while consumer_thread_running:
            try:
                for msg in consumer:
                    if not consumer_thread_running:
                        break
                    with buffer_lock:
                        event_buffer.append(msg.value)
            except Exception as e:
                logger.error(f"Error reading from kafka: {e}")
                time.sleep(1)
    except Exception as e:
        logger.warning(f"Kafka unavailable ({e}). Starting standalone background generator thread...")
        from generator.synthetic_event_producer import produce_event
        # Pre-seed buffer with 500 records
        for _ in range(500):
            evt = produce_event(producer=None, topic="", config=config)
            event_buffer.append(evt)
            
        while consumer_thread_running:
            evt = produce_event(producer=None, topic="", config=config, max_days_back=365)
            with buffer_lock:
                event_buffer.append(evt)
            time.sleep(1.0)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global consumer_thread_running
    consumer_thread_running = True
    thread = threading.Thread(target=consume_kafka_events, daemon=True)
    thread.start()
    yield
    consumer_thread_running = False
    thread.join(timeout=2.0)

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    with buffer_lock:
        return {"status": "ok", "buffered_events": len(event_buffer)}

@app.get("/events", response_model=AudienceEventPage, dependencies=[Depends(verify_bearer_token)])
def get_events(page: int = Query(1, ge=1), page_size: int = Query(100, ge=1)):
    with buffer_lock:
        total = len(event_buffer)
        events = list(event_buffer)
    
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_events = events[start_idx:end_idx]
    has_next = end_idx < total
    
    return AudienceEventPage(
        page=page,
        page_size=page_size,
        total_events=total,
        has_next=has_next,
        events=[AudienceEvent(**e) for e in page_events]
    )

@app.get("/events/count", dependencies=[Depends(verify_bearer_token)])
def get_events_count():
    with buffer_lock:
        return {"total": len(event_buffer)}

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("mock_api.app:app", host="0.0.0.0", port=port)
