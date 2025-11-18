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

    results = vectorstore.similarity_search_with_relevance_scores(
        query=query,
        k=5,
    )

    normalized_results = []
    max_score_found = None

    for doc, score in results:
        max_score_found = score if max_score_found is None else max(max_score_found, score)

        if score < SCORE_THRESHOLD:
            print(f"Document ignored due to a low score threshold: {score * 100:.2f}%")
            continue
        
        normalized_results.append({
            "content": doc.page_content,
            "metadata": {
                **(doc.metadata or {}),
                "score": score,
                "score_percent": round(score * 100, 1),
            },
        })
    
    response: dict = {
        "query": query,
        "provider": "Azure",
        "count": len(normalized_results),
        "results": normalized_results,
    }

    if not normalized_results:
        response["message"] = f"No documents matched the threshold ({SCORE_THRESHOLD*100}%)."
        response["max_score_found"] = max_score_found

    return response


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

    provider_lower = provider.lower()
    filtered = [
        item for item in data
        if str(item.get("provider", "")).lower() == provider_lower
    ]

    normalized_results = []

    for item in filtered:
        # Cria uma string “legível” a partir do item
        content_str = ", ".join(f"{k}: {v}" for k, v in item.items())

        normalized_results.append({
            "content": content_str,
            # "metadata": item,   # guarda o JSON completo como metadata
        })

    response: dict = {
        "query": query,
        "provider": provider,
        "count": len(normalized_results),
        "results": normalized_results,
    }

    if not normalized_results:
        response["message"] = f"No data found for provider '{provider}'."

    return response