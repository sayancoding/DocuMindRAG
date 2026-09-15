from typing import Dict, List
import psycopg

from dotenv import load_dotenv
from google import genai
from google.genai import types
from rank_bm25 import BM25Okapi
from flashrank import Ranker, RerankRequest

from app.config import POSTGRES_DB_PARAMS
from app.vector_store import embedding_model, get_chroma_collection

load_dotenv()

gemini_client = genai.Client()
ranker = Ranker(model_name="ms-marco-TinyBERT-L-2-v2", cache_dir="/tmp/flashrank")

def get_db_connection():
    return psycopg.connect(**POSTGRES_DB_PARAMS)

def hybrid_search_and_rerank(user_query: str, documentId: str = None):
    """
    Executes Dense Vector Search (Chroma) + Sparse BM25 Search,
    re-ranks top candidates using FlashRank, and fetches corresponding parent chunks.
    """
    # Vector Search: 
    query_vector = embedding_model.embed_query(user_query)

    collection = get_chroma_collection()

    chroma_results = collection.query(
        query_embeddings=[query_vector],
        n_results=15,
        where={"document_id": documentId},
        include=["documents", "metadatas", "distances"]
    )

    if not chroma_results["metadatas"] or not chroma_results["metadatas"][0]:
        return []
    
    child_chunks = []
    if chroma_results and chroma_results.get("documents") and chroma_results["documents"][0]:
        for doc, meta in zip(chroma_results["documents"][0], chroma_results["metadatas"][0]):
            child_chunks.append({
                "content": doc,
                "parent_id": meta.get("parent_id"),
                "document_id": meta.get("document_id")
            })
    if not child_chunks:
        return []

    # Step 2: Adding BM25 Sparse scoring to the retrieved child chunks
    tokenized_corpus = [chunk["content"].lower().split() for chunk in child_chunks]
    bm25 = BM25Okapi(tokenized_corpus)
    tokenized_query = user_query.lower().split()
    bm25_scores = bm25.get_scores(tokenized_query)

    for i, score in enumerate(bm25_scores):
        child_chunks[i]["bm25_score"] = float(score)

    # step 3: reciprocal rank fusion (RRF) to combine dense and sparse scores
    final_ranked_chunks = calculate_rrf_score(child_chunks, k=60)

    selected_parent_ids = execute_flashrank_rerank(user_query, final_ranked_chunks, 3)

    # Step C: Hydrate Parent Contexts from PostgreSQL
    parent_records = fetch_parent_contexts(selected_parent_ids)

    context_window = "\n\n---\n\n".join([row["content"] for row in parent_records])
    
        
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
            temperature=0.2, 
        ),
    )
    
    return response.text

def calculate_rrf_score(chunks:list, k: int = 60) -> list:
    """
    Calculate the Reciprocal Rank Fusion (RRF) score for a given rank.
    RRF score is defined as 1 / (k + rank), where k is a constant to dampen the effect of rank.
    """
    rrf_score_map = {}

    for idx, chunk in enumerate(chunks):
        chunks[idx]["id"] = idx

    vector_rank_list = list(chunks)
    bm25_rank_list = sorted(chunks, key=lambda x: x.get("bm25_score", 0), reverse=True)

    for rank, chunk in enumerate(vector_rank_list):
        chunk_id = chunk["id"]
        rrf_score_map[chunk_id] = 1.0 / (k + rank + 1)

    for rank, chunk in enumerate(bm25_rank_list):
        chunk_id = chunk["id"]
        rrf_score_map[chunk_id] += 1.0 / (k + rank + 1)

    # Pass 3: Attach & Final Sort
    for chunk in chunks:
        chunk["rrf_score"] = rrf_score_map[chunk["id"]]

    final_ranked_chunks = sorted(chunks, key=lambda x: x["rrf_score"], reverse=True)
    return final_ranked_chunks

def execute_flashrank_rerank(user_query: str, fushed_results: list, top_k: int = 3) -> list:
    """
    Execute FlashRank re-ranking on the top candidate chunks.
    This function is a placeholder for the actual FlashRank implementation.
    """
    # logic for FlashRank re-ranking
    passage = []
    for chunk in fushed_results:
        passage.append({
            "id": chunk["id"], 
            "text": chunk["content"], 
            "meta": {
                "parent_id": chunk.get("parent_id")
            }
        })

    rerank_request = RerankRequest(query=user_query,passages=passage)
    rerank_response = ranker.rerank(rerank_request)

    seen_parent_ids = set()
    selected_parent_ids = []

    for res in rerank_response:
        pid = res["meta"]["parent_id"]

        if pid not in seen_parent_ids:
            seen_parent_ids.add(pid)
            selected_parent_ids.append(pid)
        
        if len(seen_parent_ids) >= top_k:
            break

    return selected_parent_ids

def fetch_parent_contexts(parent_ids: List[str]) -> Dict[str, str]:
    """
    Retrieves full parent chunk text from PostgreSQL by parent_ids.
    Returns a dictionary mapping {parent_id: raw_content} for O(1) lookups.
    """
    # 1. Early exit if the list is empty (prevents SQL syntax errors)
    if not parent_ids:
        return {}
        
    parent_map = {}
    
    # 2. Open DB connection and cursor
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                
                # 3. Securely format the SQL 'IN' clause to prevent SQL Injection
                # This creates a string like "%s, %s, %s" based on the list length
                placeholders = ','.join(['%s'] * len(parent_ids))
                
                sql_query = f"""
                    SELECT id, raw_content 
                    FROM document_parents 
                    WHERE id IN ({placeholders})
                """
                
                # 4. Execute query safely by passing the list as a tuple
                cursor.execute(sql_query, tuple(parent_ids))
                rows = cursor.fetchall()
                
                # 5. Populate the dictionary
                for row in rows:
                    pid = str(row[0])      # id
                    content = str(row[1])  # raw_content
                    parent_map[pid] = content
                    
    except psycopg2.Error as e:
        print(f"Database error while fetching parent chunks: {e}")
        
    final_records = []
    for pid in parent_ids:
        if pid in parent_map:
            final_records.append({
                "parent_id": pid,
                "content": parent_map[pid]
            })
            
    return final_records