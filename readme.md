# Cloud Provider AI Assistant



## 1. Project Overview
The assistant:

## 2. Folder Structure
```
src/
  main.py

```

## 3. Requirements
- Python 3.10+
- Optional: Docker
- Install dependencies with:
```
pip install -r requirements.txt
```

## 4. Running Locally (venv)
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m src.main
uvicorn server:app --host 0.0.0.0
```

## 5. Running with Docker
```

```

## 6. Technical Decisions


![Architecture Diagram](./app/graph_diagrams/orchestratorflow.png)