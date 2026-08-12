import fitz

from app.vector_store import get_chroma_collection, embedding_model


chroma_client = get_chroma_collection()

# Define parent and child splitters for hierarchical text chunking
parent_splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=200)
child_splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)

def process_and_embed_document(document_path: str, document_id: str):
    """Processes a PDF document, extracts text, generates embeddings, and stores them in ChromaDB."""
    print(f"[RAG Engine] Starting to process document: {document_path} with ID: {document_id}")
    
    try:
        # Open the PDF document
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

        full_text = "\n\n".join(full_text_accumulator)

        if not full_text.strip():
            raise ValueError("PDF content is empty or unreadable.")


        parent_docs = parent_splitter.split_text(full_text)

        if full_text.strip():  # Only process non-empty pages
                # Generate embedding for the extracted text
                embedding_vector = embedding_model.embed_query(text)

                # Store the embedding in ChromaDB with metadata
                chroma_client.add(
                    collection_name="documind_child_chunks",
                    documents=[text],
                    metadatas=[{"document_id": document_id, "page_number": page_number}],
                    ids=[f"{document_id}_page_{page_number}"],
                    embeddings=[embedding_vector]
                )
                print(f"[RAG] Stored embedding for page {page_number} of document {document_id}")    

        print(f"[RAG] Completed processing document: {document_path}")
    except Exception as e:
        print(f"[RAG] Error processing document {document_path}: {e}")