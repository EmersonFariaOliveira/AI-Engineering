from langgraph.graph import MessagesState, StateGraph
from langchain_core.tools import tool

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from typing import List, Optional, Literal
from typing_extensions import TypedDict
from langgraph.graph import START, END


from dotenv import load_dotenv
load_dotenv()


from utils.func import pretty_print_messages
from utils.schemas import AgentState

from prompts.orchestrator import system_prompt_supervisor

llm = ChatOpenAI(
    model="gpt-4o", 
    temperature=0.0, 
    max_tokens=1000
)

def make_supervisor_node(llm: ChatOpenAI, members: list[str]) -> str:
    options = ["FINISH"] + members
    system_prompt = system_prompt_supervisor.format(members=members)

    class Router(TypedDict):
        """Worker to route to next. If no workers needed, route to FINISH."""
        next: Literal[*options]

    def supervisor_node(state: AgentState):
        """An LLM-based router."""
        messages = [
            {"role": "system", "content": system_prompt},
        ] + state["messages"]
        response = llm.with_structured_output(Router).invoke(messages)
        next_node = response["next"]

        return {"messages":[], "next_node": next_node}

    return supervisor_node

def call_researcher_node(state: AgentState):
    # # Transform the state to the subgraph state
    # subgraph_output = subgraph.invoke({"bar": state["foo"]})  
    # # Transform response back to the parent state
    # return {"foo": subgraph_output["bar"]}
    subgraph_output = "I couldn't find the information" 
    return {"messages": [AIMessage(content=subgraph_output)]}

def call_writter_node(state: AgentState):
    # # Transform the state to the subgraph state
    # subgraph_output = subgraph.invoke({"bar": state["foo"]})  
    # # Transform response back to the parent state
    # return {"foo": subgraph_output["bar"]}
    subgraph_output = "Report analysis: \nThis is the report" 
    return {"messages": [subgraph_output]}

builder = StateGraph(AgentState)
builder.add_node("agent_supervisor", make_supervisor_node(llm, ["researcher_team", "report_writter"]))
builder.add_node("researcher_team", call_researcher_node)
builder.add_node("report_writter", call_writter_node)

builder.add_edge(START, "agent_supervisor")
builder.add_conditional_edges(
    "agent_supervisor",
    lambda state: state["next_node"] if state.get("next_node") in ["researcher_team", "report_writter", END] else END,
    ["researcher_team", "report_writter", END]
)




# def researcher_node(state: AgentState):
#     """An LLM-based router."""
#     messages = [
#         {"role": "system", "content": system_prompt_researcher},
#     ] + state["messages"]

#     response = llm.with_structured_output(Router).invoke(messages)
#     next_node = response["next"]

#     return {"messages":[], "next_node": next_node}











graph = builder.compile()

question = {"messages": [HumanMessage(content="Monte um relatório que mostre o preço médio de GPUs na AWS, Azure e GCP, e sugira a opção mais barata por hora de uso")]}

for chunk in graph.stream(question):
    pretty_print_messages(chunk)