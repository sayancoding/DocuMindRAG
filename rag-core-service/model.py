
from pydantic import BaseModel

class QueryRequest(BaseModel):
    query: str
    documentId: str = None  # Optional filter to search a specific document
