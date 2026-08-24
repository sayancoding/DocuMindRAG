import psycopg

from app.config import POSTGRES_DB_PARAMS

def get_db_connection():
    """Returns a fresh connection to the PostgreSQL instance."""
    return psycopg.connect(**POSTGRES_DB_PARAMS)

def update_document_status(document_id: str, status: str, error_msg: str = None):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                if error_msg:
                    cursor.execute(
                        "UPDATE documents SET status = %s, error_message = %s, updated_at = NOW() WHERE id = %s;",
                        (status, error_msg, document_id)
                    )
                else:
                    cursor.execute(
                        "UPDATE documents SET status = %s, updated_at = NOW() WHERE id = %s;",
                        (status, document_id)
                    )
            conn.commit()
    except Exception as e:
        print(f"[DB Error] Failed to update doc {document_id}: {e}")