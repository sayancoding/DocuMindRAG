
from confluent_kafka import Producer
from app.config import settings
import traceback
import json
from datetime import datetime,timezone
from app.db import get_db_connection

dlq_producer = Producer({
    'bootstrap.servers' : settings.KAFKA_BOOTSTRAP_SERVERS,
    'client.id' : 'rag-core-dlq-producer'
})

DOC_DLQ_TOPIC = settings.KAFKA_TOPIC_DOC_DLQ

def send_to_dlq(original_payload:dict,exception:Exception,document_id:str=None):

    error_type = type(exception).__name__
    error_msg = str(exception)
    stack_trace = traceback.format_exc()
    error_time = datetime.now(timezone.utc).isoformat()

    enrich_payload = {
        "original_message" : original_payload,
        "error_details" : {
            "type" : error_type,
            "message" : error_msg,
            "stacktrace" : stack_trace,
            "occurAt" : error_time
        }
    }

    header = [
        ("dlq.error.type",error_type.encode('utf-8')),
        ("dlq.error.failed.at",error_time.encode('utf-8')),
        ("dlq.source.service", b"rag-core-service")
    ]

    dlq_producer.produce(
        topic=DOC_DLQ_TOPIC,
        key= document_id.encode('utf-8'),
        value= json.dumps(enrich_payload).encode('utf-8'),
        headers=header
    )
    dlq_producer.flush()

    if document_id : 
        mark_document_failed(document_id=document_id,error_msg=error_msg)

    print(f"[DLQ] Successfully routed document {document_id} to {DOC_DLQ_TOPIC}")


def mark_document_failed(document_id:str,error_msg:str):

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE documents 
                    SET status = 'FAILED', 
                        status_message = %s,
                        updated_at = NOW()
                    WHERE id = %s;
                    """,
                    (error_msg[:500], document_id)
                )
    except Exception as db_exp:
        print(f"[DB ERROR : Could not update failed status : {error_msg}]")

