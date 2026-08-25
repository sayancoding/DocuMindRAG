import json
import threading
import asyncio
from confluent_kafka import Consumer, KafkaError
from app.config import settings
from app.rag_engine import process_and_embed_document

def start_kafka_listener():
    print(f"[Kafka Consumer] Listening to topic '{settings.KAFKA_TOPIC_DOCUMENT_INGESTED}'...")
    
    conf = {
        'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
        'group.id': settings.KAFKA_CONSUMER_GROUP,
        'auto.offset.reset': 'earliest',

        # Give the AI up to 15 minutes (900,000 ms) to embed a massive PDF
        'max.poll.interval.ms': 900000, 
        # Increase session timeout to prevent idle drops
        'session.timeout.ms': 45000
    }

    consumer = Consumer(conf)
    consumer.subscribe([settings.KAFKA_TOPIC_DOCUMENT_INGESTED])
    
    print("[Kafka Consumer] Connected, Waiting for messages...")

    try:
        while True:
            # Poll for messages with a 1-second timeout
            msg = consumer.poll(timeout=1.0)
            
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                else:
                    print(f"[Kafka Consumer Error] {msg.error()}")
                    continue

            try:
                # 1. Safely decode and parse
                raw_value = msg.value().decode('utf-8')
                event = json.loads(raw_value)
                
                doc_id = event.get('documentId')
                file_path = event.get('filePath')
                file_name = event.get('fileName')

                print(f"\n[Kafka Consumer] 📥 Consumed event for documentId: {doc_id}")
                
                # 2. Trigger the actual RAG pipeline
                if doc_id and file_path and file_name:
                    process_and_embed_document(file_path, doc_id, file_name)
                    print(f"[Kafka Consumer] 🚀 Triggering RAG pipeline for documentId: {doc_id} path: {file_path} name: {file_name}")
                else:
                    print(f"[Kafka Consumer Warning] Invalid payload: {event}")

            except json.JSONDecodeError as e:
                print(f"[Kafka Consumer Error] Failed to parse JSON: {msg.value()} -> {e}")

    except Exception as fatal_e:
        print(f"[Kafka Consumer FATAL] Thread crashed: {fatal_e}")
    finally:
        consumer.close()

def run_kafka_listener_in_thread():
    listener_thread = threading.Thread(target=start_kafka_listener, daemon=True)
    listener_thread.start()