from pathlib import Path
from pydantic import BaseModel, Field

from langgraph.graph import START, END
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from langchain_chroma import Chroma
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from typing import List, Literal, Annotated

from utils.schemas import AgentState
from utils.func import _load_cloud_gpu_data
from utils.func import _pretty_print_messages

from utils.prompts import system_prompt_aws_expert
from utils.prompts import system_prompt_azure_expert
from utils.prompts import system_prompt_researcher_lead

from dotenv import load_dotenv
load_dotenv()

llm = ChatOpenAI(
    model="gpt-4o", 
    temperature=0.0, 
    max_tokens=1000
)

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

vectorstore = Chroma(
    embedding_function=embeddings,
    persist_directory="../app/data/vec_database/chroma_db",
    collection_name="langchain"  # default if you didn't change it before
)

CLOUD_GPU_JSON_PATH = Path("../app/data/cloud_gpu_pricing.json")

# retriever = vectorstore.as_retriever(
#     search_type="similarity_score_threshold",
#     search_kwargs={
#         "k": 5,
#         "score_threshold": 0.5,  # 0.0–1.0 (pensa como 0–100%)
#     },
# )

# --------------- Tools ----------------
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
            print(f"Ignoring doc with low score: {score} (Below threshold of {SCORE_THRESHOLD})")
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

# --------------- Agents (Nodes) ---------------
def make_researcher_leader_node(llm: ChatOpenAI, members: list[str]) -> str:

    system_prompt = system_prompt_researcher_lead.format(members=members)

    class context_schema(BaseModel):
        researchers: List[str] = Field(None, description="List of all the researchers that needs to be involved on the search")
        missing_researchers: List[str] = Field(None, description="List of missing researchers to call")

    def researcher_leader_node(state: AgentState):
        """An LLM-based router."""
        messages = [SystemMessage(content=system_prompt)] + state["messages"]

        response = llm.with_structured_output(context_schema).invoke(messages)
        next_node = response.researchers

        if len(next_node):
            team_lead_response = f"Calling providers experts {str(next_node)}"
        else:
            team_lead_response = "No providers experts for this topic"

        return {"messages":[AIMessage(content=team_lead_response)], "next_node": next_node}
    
    return researcher_leader_node
    

def aws_expert(state: AgentState):
    """Call the model to generate a response based on the current state. Given
    the question, it will decide to retrieve using the retriever tool, or simply respond to the user.
    """
    system_prompt = SystemMessage(content=system_prompt_aws_expert)

    llm_with_tools = llm.bind_tools([aws_retriever_tool])
    response = llm_with_tools.invoke([system_prompt] + state["messages"])

    return {"messages": [response], "aws_messages": [response]}


def azure_expert(state: AgentState):
    """Call the model to generate a response based on the current state. Given
    the question, it will decide to retrieve using the retriever tool, or simply respond to the user.
    """

    system_prompt = SystemMessage(content=system_prompt_azure_expert)

    llm_with_tools = llm.bind_tools([azure_retriever_tool])
    response = llm_with_tools.invoke([system_prompt] + state["messages"])

    return {"messages": [response], "azure_messages": [response]}


# ------------- Conditional edges -------------
def research_flow(state) -> Literal["aws_expert", "azure_expert",  END]:
    if len(state["next_node"]) > 0:
        return state["next_node"]
    else:
        return END
    

# ------------- Graph builder -------------
researchers = ["aws_expert", "azure_expert"]
azure_retriever_tool = retrieve_azure_information
aws_retriever_tool = retrieve_aws_information

builder = StateGraph(AgentState)
builder.add_node("lead_researcher", make_researcher_leader_node(llm, researchers))
builder.add_node("aws_expert", aws_expert)
builder.add_node("aws_retrieve", ToolNode(tools=[aws_retriever_tool], messages_key='aws_messages'))
builder.add_node("azure_expert", azure_expert)
builder.add_node("azure_retrieve", ToolNode(tools=[azure_retriever_tool], messages_key='azure_messages'))
builder.add_edge(START, "lead_researcher")

builder.add_conditional_edges(
    "lead_researcher",
    research_flow
)

builder.add_conditional_edges(
    "aws_expert",
    tools_condition,
    {
        "tools": "aws_retrieve",
        END: END,
    },
)

builder.add_conditional_edges(
    "azure_expert",
    tools_condition,
    {
        "tools": "azure_retrieve",
        END: END,
    },
)

graph = builder.compile()

# Generate the .mmd to render the graph in .png
# Once .mmd is generated use the command below to generate the flow:
#   mmdc -i graph_diagrams/flow.mmd -o graph_diagrams/flow.png

# dot = graph.get_graph().draw_mermaid()
# with open("./graph_diagrams/flow.mmd", "w", encoding="utf-8") as f:
#     f.write(dot)

# -------------- Call Graph --------------
question = {"messages": [HumanMessage(content="Monte um relatório que mostre o preço médio de GPUs na AWS, Azure, GCP e IBM Cloud, e sugira a opção mais barata por hora de uso")]}

for chunk in graph.stream(question):
    _pretty_print_messages(chunk)