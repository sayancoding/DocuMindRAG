import uuid
import os
from dotenv import load_dotenv
import psycopg2
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from pydantic import BaseModel
import fitz  # This is PyMuPDF

from langchain_text_splitters import RecursiveCharacterTextSplitter
from vector_store import embedding_model, get_or_create_collection

load_dotenv()
app = FastAPI(title="DocuMind RAG Core", version="1.0.0")

# Database Connection Helper Configuration
DB_PARAMS = {
    "dbname": "documind_metadata",
    "user": "documind_user",
    "password": "documind_password",
    "host": "localhost",  # Change to "postgres" when dockerized together later
    "port": "5432"
}

def get_db_connection():
    """Returns a fresh connection to the PostgreSQL instance."""
    return psycopg2.connect(**DB_PARAMS)

# Background Task for parsing to prevent blocking the HTTP response thread
def process_pdf_background(document_id: str, file_bytes: bytes):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Open the raw file bytes directly from memory using PyMuPDF
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        
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
            for child_idx, child_content in enumerate(child_docs):
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

    except Exception as e:
        conn.rollback()
        cursor.execute("UPDATE documents SET status = 'FAILED', error_message = %s WHERE id = %s;", (str(e), document_id))
        conn.commit()
        print(f"❌ Error in background processing: {str(e)}")
    finally:
        cursor.close()
        conn.close()

@app.get("/api/v1/health")
def health_check():
    print(f"🔍 Health check endpoint hit.")
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
    background_tasks.add_task(process_pdf_background, document_id, file_bytes)

    return {
        "document_id": document_id,
        "status": "PROCESSING",
        "message": "File accepted successfully. Parsing has started asynchronously."
    }
