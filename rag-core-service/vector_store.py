import os
import chromadb
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

# Explicitly pull the API key from your environment variables
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("❌ CRITICAL ERROR: GEMINI_API_KEY environment variable is missing!")

# Pass the key explicitly into the constructor parameter
embedding_model = GoogleGenerativeAIEmbeddings(
    model="gemini-embedding-001",
    google_api_key=api_key
)

chroma_client = chromadb.HttpClient(host="localhost", port=8000)

def get_or_create_collection(collection_name: str = "documind_child_chunks"):
    return chroma_client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}
    )