import os
import uuid
import fitz
import httpx

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.vector_store import get_chroma_collection, embedding_model
from app.db import update_document_status, get_db_connection
from app.kafka_producer import send_to_dlq

chroma_client = get_chroma_collection()
httpx_client = httpx.Client()

GATEWAY_CALLBACK_URL = f"{os.getenv('GATEWAY_BASE_URL','http://localhost:8080')}/api/gateway/status-callback"
# Define parent and child splitters for hierarchical text chunking
parent_splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=200)
child_splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)

# Define a function to push status updates to the Gateway service vis SSE
def push_status_to_gateway(document_id: str, file_name: str, path:str, progress: int, stage: str, message: str):
    """Sends a status update to the Gateway service."""
    payload = {
        "documentId": document_id,
        "fileName": file_name,
        "path": path,
        "progress": progress,
        "stage": stage,
        "message": message
    }
    try:
        response = httpx_client.post(f"{GATEWAY_CALLBACK_URL}", json=payload)
        response.raise_for_status()
        print(f"[Gateway Callback] Status pushed successfully for document {document_id} , progress {progress}% at stage '{stage}' with message: {message}")
    except Exception as e:
        print(f"[Gateway Callback] ❌ Failed to deliver SSE status callback: {e}")

# Define the main function to process and embed document
def process_and_embed_document(document_path: str, document_id: str, file_name: str, raw_event:str):
    """Processes a PDF document, extracts text, generates embeddings, and stores them in ChromaDB."""
    print(f"[RAG Engine] Starting to process document: {document_path} with ID: {document_id}")
    
    update_document_status(document_id, "PROCESSING")
    push_status_to_gateway(document_id, file_name, document_path, 5, "processing", "Started processing the document.")

    try:
        # 1. PDF Text Extraction using PyMuPDF (fitz)
        doc = fitz.open(document_path)
        full_text = ""

        # Temporary storage for layout strings
        full_text_accumulator = []
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            # "blocks" layout mode preserves multi-column ordering and structural paths
            blocks = page.get_text("blocks")
            
            full_text_accumulator.append(f"\n--- Page {page_num + 1} ---\n")
            for b in blocks:
                text_block = b[4].strip()
                if text_block:
                    full_text_accumulator.append(text_block)
            progress = min(20,int(5 + int((page_num + 1) / len(doc) * 10)))
            push_status_to_gateway(document_id, file_name, document_path, progress, "processing", f"Extracted text from page {page_num + 1}/{len(doc)}")

        doc.close()
        full_text = "\n\n".join(full_text_accumulator)

        if not full_text.strip():
            raise ValueError("PDF content is empty or unreadable.")

        # 2. Hierarchical(parent-child) Text Chunking & Embedding
        parent_docs = parent_splitter.split_text(full_text)

        # Arrays to batch-insert data into ChromaDB efficiently
        chroma_ids, chroma_embeddings, chroma_documents, chroma_metadatas = [], [], [], []
        
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                for idx, parent_chunk in enumerate(parent_docs):
                    parent_id = str(uuid.uuid4())
                    print(f"[RAG] Generated Parent Chunk ID: {parent_id} for chunk {idx + 1}/{len(parent_docs)}")

                    cursor.execute(
                        """
                        INSERT INTO document_parents (id, document_id, parent_index, raw_content, page_start, page_end)
                        VALUES (%s, %s, %s, %s, %s, %s);
                        """,
                        (parent_id, document_id, idx, parent_chunk, None, None)
                    )
                    progress = min(98,int(30 + int((idx + 1) / len(parent_docs) * 65)))
                    push_status_to_gateway(document_id, file_name, document_path, progress, "embedding", f"Embedded Parent Chunk {idx + 1}/{len(parent_docs)}")

                    #Generate child chunks for each parent chunk
                    child_chunks = child_splitter.split_text(parent_chunk)

                    for child_idx, child_chunk in enumerate(child_chunks):
                        child_id = f"{parent_id}_c_{child_idx}"
                        child_embedding = embedding_model.embed_query(child_chunk)
                        chroma_ids.append(child_id)
                        chroma_embeddings.append(child_embedding)
                        chroma_documents.append(child_chunk)
                        chroma_metadatas.append({
                            "parent_id": parent_id,
                            "document_id": document_id,
                            "parent_index": idx,
                            "child_index": child_idx
                        })
                    
                    progress = min(98,int(30 + int((idx + 1) / len(parent_docs) * 65)))
                    push_status_to_gateway(document_id, file_name, document_path, progress, "embedding", f"Embedded Parent Chunk {idx + 1}/{len(parent_docs)}")

        if chroma_ids:
            chroma_client.add(
                ids=chroma_ids,
                embeddings=chroma_embeddings,
                documents=chroma_documents,
                metadatas=chroma_metadatas
            )
        update_document_status(document_id, "EMBEDDED")
        push_status_to_gateway(document_id, file_name, document_path, 100, "completed", "Document processing and embedding completed successfully.")            
        print(f"✅ [RAG] Hierarchical parsing complete for document {document_id}")

    except Exception as e:
        print(f"[RAG] Error processing document {document_path}: {e}")
        # update_document_status(document_id, "FAILED", str(e)[:200])
        send_to_dlq(original_payload=raw_event, exception=e, document_id=document_id)
        push_status_to_gateway(document_id, file_name, document_path, 100, "failed", f"Error processing document {document_path}: {str(e)[:50]}")
