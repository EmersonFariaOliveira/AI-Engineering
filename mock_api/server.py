# mock_api/server.py

import json
from pathlib import Path
from typing import Any, Dict, List

from flask import Flask, request, jsonify

app = Flask(__name__)

# Path to the JSON with cloud GPU data (same folder as this server)
CLOUD_GPU_JSON_PATH = Path(__file__).with_name("cloud_gpu_pricing.json")
print(CLOUD_GPU_JSON_PATH)

def _load_cloud_gpu_data(json_path: Path) -> List[Dict[str, Any]]:
    """Load GPU data from a local JSON file."""
    if not json_path.exists():
        raise FileNotFoundError(f"JSON file not found at: {json_path}")

    with json_path.open("r", encoding="utf-8") as f:
        return json.load(f)


@app.route("/search-gpu", methods=["POST"])
def search_cloud_gpus():
    """
    Mock endpoint that filters GPU data by provider and returns
    a normalized structure for the agent.
    """
    if not request.is_json:
        return jsonify({"error": "Request body must be JSON"}), 400

    body = request.get_json(silent=True) or {}

    query = body.get("query", "")
    provider = body.get("provider", "")

    if not provider:
        return jsonify({"error": "Field 'provider' is required"}), 400

    try:
        data = _load_cloud_gpu_data(CLOUD_GPU_JSON_PATH)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 500

    provider_lower = str(provider).lower()
    filtered = [
        item for item in data
        if str(item.get("provider", "")).lower() == provider_lower
    ]

    normalized_results: List[Dict[str, Any]] = []

    for item in filtered:
        # Create a human-readable string from the item
        content_str = ", ".join(f"{k}: {v}" for k, v in item.items())

        normalized_results.append({
            "content": content_str,
            # "metadata": item,  # uncomment if you want the full JSON as metadata
        })

    response: Dict[str, Any] = {
        "query": query,
        "provider": provider,
        "count": len(normalized_results),
        "results": normalized_results,
    }

    if not normalized_results:
        response["message"] = f"No data found for provider '{provider}'."

    return jsonify(response), 200


if __name__ == "__main__":
    # Run with: python mock_api/server.py
    app.run(host="0.0.0.0", port=8001, debug=True)
