
from typing import List, Optional

from pydantic import BaseModel, Field


class Document(BaseModel):
    id: str
    file_name: str
    file_size_bytes: int
    content_type: str
    status: str

class QueryRequest(BaseModel):
    documentId: str = Field(..., description="Target document UUID to query against")
    query: str = Field(..., min_length=1, description="User's natural language question")

class SourceContext(BaseModel):
    parentId: str
    content: str
    relevanceScore: Optional[float] = None

class QueryResponse(BaseModel):
    documentId: str
    query: str
    answer: str
    sources: List[SourceContext]