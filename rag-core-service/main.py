import os
import uuid
import psycopg2
import fitz  # PyMuPDF
import asyncio
import httpx

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from langchain_text_splitters import RecursiveCharacterTextSplitter
from vector_store import embedding_model, get_or_create_collection
from config import POSTGRES_DB_PARAMS
from query_engine import retrieve_and_generate
from model import QueryRequest

load_dotenv()
app = FastAPI(title="DocuMind RAG Core", version="1.0.0")

GATEWAY_CALLBACK_URL = f"{os.getenv('GATEWAY_BASE_URL','http://localhost:8081')}/api/gateway/status-callback"

# Database Connection Helper Configuration
def get_db_connection():
    """Returns a fresh connection to the PostgreSQL instance."""
    return psycopg2.connect(**POSTGRES_DB_PARAMS)

# Background Task for parsing to prevent blocking the HTTP response thread
async def process_pdf_background(file_name: str, document_id: str, file_bytes: bytes):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Open the raw file bytes directly from memory using PyMuPDF
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        await push_status_to_gateway(file_name, 35, "Reading", "Reading rawPDF text modules...")

        # Temporary storage for layout strings
        full_text_accumulator = []
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            # "blocks" layout mode preserves multi-column ordering and structural paths
            blocks = page.get_text("blocks")
            
            for b in blocks:
                text_block = b[4].strip()
                if text_block:
                    full_text_accumulator.append(text_block)

        full_text = "\n\n".join(full_text_accumulator)

        # 1. Define Character Splitters for Hierarchy
        # Parent chunk: Large window to capture whole paragraphs/topics
        parent_splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=200)
        # Child chunk: Small window optimized for semantic vector lookup
        child_splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)

        parent_docs = parent_splitter.split_text(full_text)

        # Initialize or grab our ChromaDB collection
        collection = get_or_create_collection()

        # Arrays to batch-insert data into ChromaDB efficiently
        chroma_ids = []
        chroma_embeddings = []
        chroma_documents = []
        chroma_metadatas = []
        
        # 2. Loop through Parent Chunks and write them to PostgreSQL
        for index, parent_content in enumerate(parent_docs):
            parent_id = str(uuid.uuid4())
            
            cursor.execute(
                """
                INSERT INTO document_parents (id, document_id, parent_index, raw_content)
                VALUES (%s, %s, %s, %s);
                """,
                (parent_id, document_id, index, parent_content)
            )

            # 3. Sub-split this specific Parent into smaller Child Chunks
            child_docs = child_splitter.split_text(parent_content)
            
            # --- CRUCIAL STEP PREPARATION ---
            # In the next step, these child_docs will be vectorized and sent to ChromaDB.
            # For now, we will print out the structural relationship to verify our loops work.
            await push_status_to_gateway(file_name, 70, "Embedding", "Embedding Child Chunks...")
            for child_idx, child_content in enumerate(child_docs):
                print(f"🔄️Embedding is generating for Child-{child_idx} of Parent-{index}")
                # generate embedding for this child chunk
                embedding = embedding_model.embed_query(child_content)
                
                #append to batch arrays for ChromaDB insertion
                chroma_ids.append(str(f"{parent_id}_c_{child_idx}"))
                chroma_embeddings.append(embedding)
                chroma_documents.append(child_content)
                chroma_metadatas.append({
                    "parent_id": parent_id,
                    "document_id": document_id,
                })


        await push_status_to_gateway(file_name, 90, "Vector Storage", "Storing vector representations...")
        # 4. Batch insert all child chunks into ChromaDB with their embeddings and metadata
        if chroma_ids:
            collection.add(
                ids=chroma_ids,
                embeddings=chroma_embeddings,
                documents=chroma_documents,
                metadatas=chroma_metadatas
            )
            print(f"✅ Inserted {len(chroma_ids)} child chunks into ChromaDB for document {document_id}.")
        else:            
            print(f"⚠️ No child chunks generated for document {document_id}. Check the text splitting logic.") 
        
        # Update tracking state to completed
        cursor.execute("UPDATE documents SET status = 'COMPLETED' WHERE id = %s;", (document_id,))
        conn.commit()
        print(f"✅ Hierarchical parsing complete for document {document_id}. Generated {len(parent_docs)} Parent blocks.")
        await push_status_to_gateway(file_name, 100, "completed", "Processing complete.")
    except Exception as e:
        conn.rollback()
        cursor.execute("UPDATE documents SET status = 'FAILED', error_message = %s WHERE id = %s;", (str(e), document_id))
        conn.commit()
        print(f"❌ Error in background processing: {str(e)}")
    finally:
        cursor.close()
        conn.close()

async def push_status_to_gateway(file_name: str, progress: int, stage: str, status_text: str):
    """Pushes a state event up to the Spring Boot Gateway callback lane."""
    payload = {
        "fileName": file_name,
        "progress": progress,
        "stage": stage,
        "statusText": status_text
    }
    try:
        async with httpx.AsyncClient() as client:
            await client.post(GATEWAY_CALLBACK_URL, json=payload)
    except Exception as e:
        print(f"❌ Failed to deliver SSE status callback update: {str(e)}")

# async def background_pdf_processor(file_name: str, file_bytes: bytes):
#     try:
#         # Phase 1: Landed on Disk -> Extracting text
#         await push_status_to_gateway(file_name, 35, "extracting", "Parsing PDF text modules...")
#         await asyncio.sleep(1.5) # Simulating processing workload
        
#         # Phase 2: Building Vectors -> Embedding via Gemini
#         await push_status_to_gateway(file_name, 70, "embedding", "Generating vector matrices via Gemini...")
#         await asyncio.sleep(2.0) # Simulating Gemini API processing latency
        
#         # Phase 3: Final Integration Completed Successfully
#         await push_status_to_gateway(file_name, 100, "completed", "Processed")
        
#     except Exception as e:
#         await push_status_to_gateway(file_name, 100, "failed", f"Processing error: {str(e)}")

@app.get("/api/v1/health")
def health_check():
    return {
        "status": "healthy", 
        "message": "✅ DocuMind RAG Core is operational."
    }

@app.post("/api/v1/ingest/upload")
async def upload_document(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Accepts a raw PDF file, creates a unique registry token in PostgreSQL, 
    and offloads the heavy layout extraction work to a background worker thread.
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF extractions are supported in this pipeline.")

    # Read binary stream
    file_bytes = await file.read()
    file_size = len(file_bytes)
    document_id = str(uuid.uuid4())

    # Insert initial transaction log as 'PROCESSING'
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO documents (id, file_name, file_size_bytes, content_type, status)
            VALUES (%s, %s, %s, %s, 'PROCESSING');
            """,
            (document_id, file.filename, file_size, file.content_type)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database Registry Failure: {str(e)}")
    finally:
        cursor.close()
        conn.close()

    # Offload extraction to a background thread so the client gets an instant response
    background_tasks.add_task(process_pdf_background, file.filename, document_id, file_bytes)

    return {
        "document_id": document_id,
        "status": "PROCESSING",
        "message": "File accepted successfully. Parsing has started asynchronously."
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
        answer = retrieve_and_generate(payload.query, payload.documentId)
        return {
            "query": payload.query,
            "answer": answer
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query Execution Error: {str(e)}")