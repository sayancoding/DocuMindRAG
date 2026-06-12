import psycopg2

import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from config import POSTGRES_DB_PARAMS
from vector_store import get_or_create_collection,embedding_model

load_dotenv()

gemini_client = genai.Client()

def get_db_connection():
    return psycopg2.connect(**POSTGRES_DB_PARAMS)

def retrieve_and_generate(user_query: str, document_id: str = None):
    """
    Executes Hierarchical Retrieval: Finds matching child vectors,
    swaps them for complete parent contexts from Postgres, and generates an answer.
    """
    # Step A: Generate Embedding Vector for the User's Question
    query_vector = embedding_model.embed_query(user_query)

    # Step B: Query ChromaDB for the Top 4 closest semantic Child Chunks
    collection = get_or_create_collection()

    # Construct metadata filter if a specific document_id is passed
    metadata_filter = {"document_id": document_id} if document_id else None

    chroma_results = collection.query(
        query_embeddings=[query_vector],
        n_results=4,
        where=metadata_filter
    )

    if not chroma_results["metadatas"] or not chroma_results["metadatas"][0]:
        return "No relevant reference contexts could be located for this query."
    
    # Extract the parent_ids linked to the winning child vectors
    parent_ids = [meta["parent_id"] for meta in chroma_results["metadatas"][0]]

    # Step C: Hydrate Parent Contexts from PostgreSQL
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Use tuple parsing to fetch all matched parent texts in a single batch query
        cursor.execute(
            """
            SELECT raw_content 
            FROM document_parents 
            WHERE id IN %s 
            ORDER BY parent_index ASC;
            """,
            (tuple(parent_ids),)
        )
        parent_records = cursor.fetchall()
        # Combine the rich parent sections into a unified context window
        context_window = "\n\n---\n\n".join([row[0] for row in parent_records])
        
    except Exception as e:
        print(f"❌ Database Retrieval Failure: {str(e)}")
        context_window = ""
    finally:
        cursor.close()
        conn.close()
        
    if not context_window:
        return "Failed to resolve ground-truth context boundaries."

    # Step D: Construct System Prompt and Generate Answer via Gemini 2.5 Flash
    system_instruction = (
        "You are DocuMind AI, an expert technical assistant. Answer the user's question "
        "using ONLY the provided reference context sections. If the answer cannot be found "
        "in the context, state clearly that you do not possess that information. Maintain "
        "strict factual accuracy and do not hallucinate."
    )

    user_prompt = f"Context:\n{context_window}\n\nQuestion: {user_query}\n\nAnswer:"

    response = gemini_client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.2,  # Low temperature makes the output deterministic and factual
        ),
    )
    
    return response.text