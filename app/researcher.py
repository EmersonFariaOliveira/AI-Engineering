from langgraph.graph import START, END
from langgraph.graph import MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_classic.tools.retriever import create_retriever_tool

from langchain_chroma import Chroma

from typing_extensions import TypedDict
from typing import List, Optional, Literal

from utils.schemas import AgentState
from utils.func import pretty_print_messages

from pydantic import BaseModel, Field

from utils.prompts import system_prompt_researcher_lead
from utils.prompts import system_prompt_azure_expert

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
    persist_directory="./app/vec_database/chroma_db",
    collection_name="langchain"  # default if you didn't change it before
)

retriever = vectorstore.as_retriever(
    search_type="similarity_score_threshold",
    search_kwargs={
        "k": 5,
        "score_threshold": 0.5,  # 0.0–1.0 (pensa como 0–100%)
    },
)

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
    return {"messages":[AIMessage(content="Hey I'm here to help")]}


def azure_expert(state: AgentState):
    """Call the model to generate a response based on the current state. Given
    the question, it will decide to retrieve using the retriever tool, or simply respond to the user.
    """

    system_prompt = SystemMessage(content=system_prompt_azure_expert)

    llm_with_tools = llm.bind_tools([retriever_tool])
    response = llm_with_tools.invoke([system_prompt] + state["messages"])

    return {"messages": [response]}


# ------------- Conditional edges -------------
def research_flow(state) -> Literal["aws_expert", "azure_expert", END]:
    if len(state["next_node"]) > 0:
        return state["next_node"]
    else:
        return END
    

# ------------- Graph builder -------------

researchers = ["aws_expert", "azure_expert"]
# retriever_tool = create_retriever_tool(
#     retriever,
#     "retrieve_azure_information",
#     "Search and return information about azure cloud.",
# )
retriever_tool = retrieve_azure_information

builder = StateGraph(AgentState)
builder.add_node("lead_researcher", make_researcher_leader_node(llm, researchers))
builder.add_node("aws_expert", aws_expert)
builder.add_node("azure_expert", azure_expert)
builder.add_node("retrieve", ToolNode([retriever_tool]))

builder.add_edge(START, "lead_researcher")
builder.add_conditional_edges(
    "lead_researcher",
    research_flow
)

builder.add_conditional_edges(
    "azure_expert",
    # Assess LLM decision (call `retriever_tool` tool or respond to the user)
    tools_condition,
    {
        # Translate the condition outputs to nodes in our graph
        "tools": "retrieve",
        END: END,
    },
)

# builder.add_edge("retrieve", "azure_expert")
# builder.add_edge("azure_expert", "lead_researcher")

graph = builder.compile()

# dot = graph.get_graph().draw_mermaid()
# with open("./graph_diagrams/flow.mmd", "w", encoding="utf-8") as f:
#     f.write(dot)

# -------------- Call Graph --------------
question = {"messages": [HumanMessage(content="Monte um relatório que mostre o preço médio de GPUs na AWS, Azure, GCP e IBM Cloud, e sugira a opção mais barata por hora de uso")]}

for chunk in graph.stream(question):
    pretty_print_messages(chunk)