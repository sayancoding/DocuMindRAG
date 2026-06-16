import os
import chromadb
from google import genai
from dotenv import load_dotenv
from config import CHROMA_HOST, CHROMA_PORT

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("❌ CRITICAL ERROR: GEMINI_API_KEY environment variable is missing!")

# 1. Initialize the official, native Google GenAI Client
ai_client = genai.Client(api_key=api_key)

# 2. Build a lean embedder wrapper matching the exact method signatures main.py expects
class NativeGeminiEmbedder:
    def embed_query(self, text: str) -> list[float]:
        """Generates a 768-dimensional text embedding vector natively."""
        response = ai_client.models.embed_content(
            model="gemini-embedding-001",
            contents=text
        )
        # Handle batch or single vector outputs securely
        if isinstance(response.embeddings, list):
            return response.embeddings[0].values
        return response.embedding.values

# Instantiate the clean wrapper
embedding_model = NativeGeminiEmbedder()

# 3. Establish the internal container-to-container connection channel
chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=int(CHROMA_PORT))

def get_or_create_collection(collection_name: str = "documind_child_chunks"):
    return chroma_client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}
    )