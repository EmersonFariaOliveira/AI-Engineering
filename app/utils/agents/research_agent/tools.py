import json
from pathlib import Path
from pydantic import Field
from typing import Annotated

from langchain_chroma import Chroma
from langchain_core.tools import tool
from langchain_openai import OpenAIEmbeddings

# -------------- RAG config --------------
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

vectorstore = Chroma(
    embedding_function=embeddings,
    persist_directory="../app/data/vec_database/chroma_db",
    collection_name="langchain"  # default if you didn't change it before
)

CLOUD_GPU_JSON_PATH = Path("../app/data/cloud_gpu_pricing.json")

def _load_cloud_gpu_data(json_path) -> list[dict]:
    with json_path.open("r", encoding="utf-8") as f:
        return json.load(f)

# ---------------- Tools ------------------
@tool("retrieve_azure_information")
def retrieve_azure_information(query: str) -> dict:
    """
    Search Azure GPU knowledge base and return documents with relevance scores.
    Applies manual score filtering.
    """

    SCORE_THRESHOLD = 0.50

    # Busca com scores
    results = vectorstore.similarity_search_with_relevance_scores(
        query=query,
        k=5,
    )

    filtered = []
    for doc, score in results:
        if score < SCORE_THRESHOLD:   # FILTRO AQUI
            # print(f"Ignoring doc with low score: {score} (Below threshold of {SCORE_THRESHOLD})")
            continue
        
        filtered.append({
            "content": doc.page_content,
            "metadata": doc.metadata,
            "score": score,
            "score_percent": round(score * 100, 1),
        })
    
    # Se nenhum documento passou do threshold, avisa explicitamente
    if not filtered:
        return {
            "results": [],
            "message": f"No documents matched the threshold ({SCORE_THRESHOLD*100}%).",
            "max_score_found": max([s for _, s in results]) if results else None,
        }

    return {"results": filtered}


@tool("retrieve_aws_information")
def retrieve_aws_information(
    query: Annotated[str, Field(description="Query for search information")], 
    provider: Annotated[str, Field(description="Cloud provider name to search")]
) -> dict:
    """
    Search over a local JSON with cloud GPU pricing.
    It just loads the JSON and filters entries by provider name
    (e.g. 'AWS', 'Azure', 'GCP').
    """
    
    data = _load_cloud_gpu_data(CLOUD_GPU_JSON_PATH)

    # filtro simples por provider (case-insensitive)
    provider_lower = provider.lower()
    filtered = [
        item for item in data
        if str(item.get("provider", "")).lower() == provider_lower
    ]

    return {
        "query": query,
        "provider": provider,
        "count": len(filtered),
        "results": filtered,
    }