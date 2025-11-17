from langgraph.graph import END

from langchain_openai import ChatOpenAI
from langchain_core.messages import  SystemMessage, AIMessage

from typing import Literal

from utils.agents.research_agent.schemas import AgentState

from utils.agents.research_agent.prompts import system_prompt_aws_expert
from utils.agents.research_agent.prompts import system_prompt_azure_expert
from utils.agents.research_agent.prompts import system_prompt_researcher_lead

from utils.agents.research_agent.tools import retrieve_azure_information
from utils.agents.research_agent.tools import retrieve_aws_information

from utils.agents.research_agent.schemas import context_schema

# --------------- Nodes ---------------
def make_researcher_leader_node(llm: ChatOpenAI, members: list[str]) -> str:

    system_prompt = system_prompt_researcher_lead.format(members=members)

    def researcher_leader_node(state: AgentState):
        """An LLM-based router."""

        azure_response = state.get("azure_messages", [])
        aws_response = state.get("aws_messages", [])

        if len(azure_response) > 1 or len(aws_response) > 1:
            return {"messages": azure_response + aws_response + [AIMessage(content="Data collected, foward the data to report_writter worker")], "next_node": []}

        messages = [SystemMessage(content=system_prompt)] + state["messages"]

        response = llm.with_structured_output(context_schema).invoke(messages)
        next_node = response.researchers
        missing_researchers = response.missing_researchers

        if len(next_node):
            team_lead_response = f"Calling providers experts {str(next_node)}"
        else:
            team_lead_response = "No providers experts for this topic"

        return {"messages":[AIMessage(content=team_lead_response)], "next_node": next_node, "missing_researchers": missing_researchers}
    
    return researcher_leader_node
    
def make_aws_expert_node(llm: ChatOpenAI) -> str:
    
    system_prompt = system_prompt_aws_expert

    def aws_expert(state: AgentState):
        """Call the model to generate a response based on the current state. Given
        the question, it will decide to retrieve using the retriever tool, or simply respond to the user.
        """
        aws_response = state.get("aws_messages", [])
        if len(aws_response) > 1:
            return {"messages": []}

        messages = [SystemMessage(content=system_prompt)] + state["messages"]

        llm_with_tools = llm.bind_tools([retrieve_aws_information])
        response = llm_with_tools.invoke(messages)

        return {"messages": [], "aws_messages": [response]}

    return aws_expert

def make_azure_expert_node(llm: ChatOpenAI) -> str:
    
    system_prompt = system_prompt_azure_expert

    def azure_expert(state: AgentState):
        """Call the model to generate a response based on the current state. Given
        the question, it will decide to retrieve using the retriever tool, or simply respond to the user.
        """
        azure_response = state.get("azure_messages", [])
        if len(azure_response) > 1:
            return {"messages": []}
        messages = [SystemMessage(content=system_prompt)] + state["messages"]

        llm_with_tools = llm.bind_tools([retrieve_azure_information])
        response = llm_with_tools.invoke(messages)

        return {"messages": [], "azure_messages": [response]}
    
    return azure_expert

# ------------- Conditional edges -------------
def research_flow(state) -> Literal["aws_expert", "azure_expert", END]:
    if len(state["next_node"]) > 0:
        return state["next_node"]
    else:
        return END
    
