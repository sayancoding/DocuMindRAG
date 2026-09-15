from http.client import HTTPException

from dotenv import load_dotenv
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.model import QueryRequest
from app.kafka_consumer import run_kafka_listener_in_thread
from app.query_engine import hybrid_search_and_rerank

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Launch Kafka consumer thread safely on startup
    run_kafka_listener_in_thread()
    yield
    # Graceful shutdown logic can be added here if needed

load_dotenv()
app = FastAPI(title="DocuMind RAG Core", version="1.0.0", lifespan=lifespan)

@app.get("/api/v1/health")
def health_check():
    return {
        "status": "healthy", 
        "message": "✅ DocuMind RAG Core is operational."
    }

@app.post("/api/v1/query")
async def ask_document(payload: QueryRequest):
    """
    Receives a natural language question, passes it to the hierarchical 
    retrieval engine, and returns Gemini's grounded response.
    """
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query text cannot be empty.")
        
    try:
        answer = hybrid_search_and_rerank(payload.query, payload.documentId)
        return {
            "query": payload.query,
            "answer": answer
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query Execution Error: {str(e)}")
