import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    KAFKA_TOPIC_DOCUMENT_INGESTED: str = os.getenv("KAFKA_TOPIC_DOCUMENT_INGESTED", "document-ingestion-events")
    KAFKA_CONSUMER_GROUP: str = os.getenv("KAFKA_CONSUMER_GROUP", "rag-core-group")

    KAFKA_TOPIC_DOC_DLQ:str = os.getenv("KAFKA_TOPIC_DOC_DLQ",'document-ingestion-dlq')

    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", 5432))
    DB_NAME: str = os.getenv("DB_NAME", "documind_metadata")
    DB_USER: str = os.getenv("DB_USER", "documind_user")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "documind_password")

    CHROMA_HOST: str = os.getenv("CHROMA_HOST", "localhost")
    CHROMA_PORT: int = int(os.getenv("CHROMA_PORT", 8000))

    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

settings = Settings()


POSTGRES_DB_PARAMS = {
    "dbname": settings.DB_NAME,
    "user": settings.DB_USER,
    "password": settings.DB_PASSWORD,
    "host": settings.DB_HOST,
    "port": settings.DB_PORT
}
