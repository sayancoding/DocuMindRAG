import os
from dotenv import load_dotenv

load_dotenv()

# Natively pull from environment variables (passed by Podman), 
# or gracefully fall back to local settings if running outside a container.
POSTGRES_DB_PARAMS = {
    "dbname": os.getenv("DB_NAME", "documind_metadata"),
    "user": os.getenv("DB_USER", "documind_user"),
    "password": os.getenv("DB_PASSWORD", "documind_password"),
    "host": os.getenv("DB_HOST", "localhost"),  # Defaults to localhost for IDE, overrides to 'postgres' in container
    "port": os.getenv("DB_PORT", "5432")
}

# ChromaDB connection settings, also pulled from environment variables for flexibility
CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")  # Defaults to localhost for IDE, overrides to 'chromadb' in container
CHROMA_PORT = os.getenv("CHROMA_PORT", "8000")