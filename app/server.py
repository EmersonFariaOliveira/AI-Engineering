from dotenv import load_dotenv
load_dotenv("../.env")

from fastapi import FastAPI,WebSocket
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
from utils.agents.orchestrator_agent.graph import OrchestratorAgent
from utils.func import pretty_print_messages
from pydantic import BaseModel
from template import html
import time
import uuid


graph = OrchestratorAgent.build_graph()

app = FastAPI()

class ChatInput(BaseModel):
    messages: list[str]
    thread_id: str

@app.post("/chat")
async def chat(input: ChatInput):
    config = {"configurable": {"thread_id": input.thread_id}}
    result = await graph.ainvoke({"messages": input.messages}, config=config)

    pretty_print_messages(result["messages"])

    last_msg = result["messages"][-1]  # AIMessage
    content = last_msg.content

    reference_data = result.get("team_lead_response", [])

    response_payload = {
        "id": f"chatcmpl-{uuid.uuid4()}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "my-agent-model",  # você pode colocar o nome que quiser
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content
                },
                "finish_reason": "stop"
            }
        ],
        "references": reference_data
    }

    return JSONResponse(content=response_payload)


# Streaming
# Serve the HTML chat interface
@app.get("/")
async def get():
    return HTMLResponse(html)

# WebSocket endpoint for real-time streaming
@app.websocket("/ws/{thread_id}")
async def websocket_endpoint(websocket: WebSocket, thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        async for event in graph.astream({"messages": [data]}, config=config, stream_mode="messages"):
            await websocket.send_text(event[0].content)