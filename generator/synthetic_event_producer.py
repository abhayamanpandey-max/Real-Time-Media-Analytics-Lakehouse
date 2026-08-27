"""
generator/synthetic_event_producer.py
"""
import argparse
import json
import logging
import random
import signal
import sys
import time
import uuid
from datetime import date, timedelta
from datetime import datetime, timezone

import numpy as np
from kafka import KafkaProducer

from config.loader import load_config
from generator.schemas import ALLOWED_PLATFORMS, ALLOWED_CATEGORIES, AudienceEvent

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

PROPERTY_CATALOG = [{"property_id": f"PROP_{i:03d}", "property_name": name} for i, name in enumerate([
    "Channel Alpha", "Stream Beta", "Media Gamma", "Network Delta",
    "Broadcast Epsilon", "Studio Zeta", "Signal Eta", "Vision Theta",
    "Platform Iota", "Content Kappa", "Channel Lambda", "Stream Mu",
    "Media Nu", "Network Xi", "Broadcast Omicron", "Studio Pi",
    "Signal Rho", "Vision Sigma", "Platform Tau", "Content Upsilon",
], start=1)]

GEO_CATALOG = [{"geography_id": f"GEO_{i:03d}", "geography_name": name} for i, name in enumerate([
    "North Region", "South Region", "East Region", "West Region",
    "Central Region", "Coastal East", "Coastal West", "Mountain Zone",
    "Metro Core", "Rural Belt",
], start=1)]

def produce_event(producer: KafkaProducer, topic: str, config: dict = None) -> dict:
    prop = random.choice(PROPERTY_CATALOG)
    geo = random.choice(GEO_CATALOG)
    platform = random.choice(ALLOWED_PLATFORMS)
    category = random.choice(ALLOWED_CATEGORIES)
    
    event_date = date.today() - timedelta(days=random.randint(0, 30))
    audience_val = int(np.clip(np.random.normal(250_000, 150_000), 1_000, 5_000_000))
    
    event = AudienceEvent(
        event_id=str(uuid.uuid4()),
        property_id=prop["property_id"],
        property_name=prop["property_name"],
        geography_id=geo["geography_id"],
        geography_name=geo["geography_name"],
        platform=platform,
        category=category,
        event_date=event_date.isoformat(),
        audience_value=audience_val,
        ingested_at=datetime.now(timezone.utc).isoformat()
    )
    
    event_dict = event.model_dump()
    if producer:
        producer.send(topic, value=event_dict)
    return event_dict

def main():
    parser = argparse.ArgumentParser(description="Synthetic Audience Event Producer")
    parser.add_argument("--env", type=str, default="dev", help="Environment (dev, prod, etc)")
    parser.add_argument("--interval-seconds", type=float, default=1.0, help="Interval between events")
    parser.add_argument("--once", action="store_true", help="Produce one batch then exit")
    args = parser.parse_args()

    config = load_config(args.env)
    
    bootstrap_servers = config.get("kafka", {}).get("bootstrap_servers", "localhost:9092")
    topic = config.get("kafka", {}).get("topic", "audience_events")

    producer = KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode("utf-8")
    )

    keep_running = True

    def signal_handler(sig, frame):
        nonlocal keep_running
        logger.info("Graceful shutdown initiated...")
        keep_running = False

    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info(f"Starting producer loop. Topic: {topic}, Interval: {args.interval_seconds}s")
    
    try:
        while keep_running:
            event = produce_event(producer, topic, config)
            logger.debug(f"Published event: {event['event_id']}")
            
            if args.once:
                break
                
            time.sleep(args.interval_seconds)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received.")
    finally:
        producer.flush()
        producer.close()
        logger.info("Producer shutdown complete.")

if __name__ == "__main__":
    main()
