import psycopg

from config import POSTGRES_DB_PARAMS

def get_db_connection():
    """Returns a fresh connection to the PostgreSQL instance."""
    return psycopg.connect(**POSTGRES_DB_PARAMS)

def update_document_status(document_id: str, status: str):
    """Updates the status of a document in the database."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE documents SET status = %s WHERE id = %s",
                    (status, document_id)
                )
                conn.commit()
                print(f"[DB] Successfully updated document [{document_id}] status to {status}")
    except Exception as e:
        print(f"[DB] Error updating document [{document_id}] status: {e}")
            