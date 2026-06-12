
from pydantic import BaseModel

class QueryRequest(BaseModel):
    query: str
    document_id: str = None  # Optional filter to search a specific document
