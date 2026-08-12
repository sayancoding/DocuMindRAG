
from pydantic import BaseModel

class QueryRequest(BaseModel):
    query: str
    documentId: str = None  # Optional filter to search a specific document

class Document(BaseModel):
    id: str
    file_name: str
    file_size_bytes: int
    content_type: str
    status: str