from utils.agents.research_agent.nodes import (
    research_flow,
    make_aws_expert_node,
    make_azure_expert_node,
    make_researcher_leader_node,
)

from utils.agents.research_agent.tools import (
    retrieve_aws_information,
    retrieve_azure_information,
)

from utils.agents.research_agent.schemas import AgentState

from langgraph.graph import START, END
from langgraph.graph import StateGraph
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode
# from langgraph.prebuilt import tools_condition

from langchain_core.messages import AnyMessage
from typing import Any, Literal
from pydantic import BaseModel


def tools_condition_aws(
    state: list[AnyMessage] | dict[str, Any] | BaseModel,
    messages_key: str = "aws_messages",
) -> Literal["tools", "__end__"]:

    if isinstance(state, list):
        ai_message = state[-1]
    elif (isinstance(state, dict) and (messages := state.get(messages_key, []))) or (
        messages := getattr(state, messages_key, [])
    ):
        ai_message = messages[-1]
    else:
        msg = f"No messages found in input state to tool_edge: {state}"
        raise ValueError(msg)
    if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
        return "tools"
    return "__end__"


def tools_condition_azure(
    state: list[AnyMessage] | dict[str, Any] | BaseModel,
    messages_key: str = "azure_messages",
) -> Literal["tools", "__end__"]:

    if isinstance(state, list):
        ai_message = state[-1]
    elif (isinstance(state, dict) and (messages := state.get(messages_key, []))) or (
        messages := getattr(state, messages_key, [])
    ):
        ai_message = messages[-1]
    else:
        msg = f"No messages found in input state to tool_edge: {state}"
        raise ValueError(msg)
    if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
        return "tools"
    return "__end__"


class ResearchAgent():
    @staticmethod
    def build_graph():
        # --------------- Model ---------------
        llm = ChatOpenAI(
            model="gpt-4o", 
            temperature=0.0, 
            max_tokens=1000
        )

        # Define researchers under lead
        researchers = ["aws_expert", "azure_expert"]
        azure_retriever_tool = retrieve_azure_information
        aws_retriever_tool = retrieve_aws_information

        # Nodes
        builder = StateGraph(AgentState)
        builder.add_node("lead_researcher", make_researcher_leader_node(llm, researchers))
        builder.add_node("aws_expert", make_aws_expert_node(llm))
        builder.add_node("aws_retrieve", ToolNode(tools=[aws_retriever_tool], messages_key='aws_messages'))
        builder.add_node("azure_expert", make_azure_expert_node(llm))
        builder.add_node("azure_retrieve", ToolNode(tools=[azure_retriever_tool], messages_key='azure_messages'))

        # Connections
        builder.add_edge(START, "lead_researcher")

        builder.add_conditional_edges(
            "lead_researcher",
            research_flow
        )

        builder.add_conditional_edges(
            "azure_expert",
            tools_condition_azure,
            {
                "tools": "azure_retrieve",
                END: "lead_researcher",
            }
        )

        builder.add_conditional_edges(
            "aws_expert",
            tools_condition_aws,
            {
                "tools": "aws_retrieve",
                END: "lead_researcher",
            }
        )

        builder.add_edge("azure_retrieve", "azure_expert")
        builder.add_edge("aws_retrieve", "aws_expert")

        # builder.add_edge("aws_expert", "lead_researcher")
        # builder.add_edge("azure_expert", "lead_researcher")

        return builder.compile()
