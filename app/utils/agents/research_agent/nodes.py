import json
from typing import Literal

from langgraph.graph import END

from langchain_openai import ChatOpenAI
from langchain_core.messages import  SystemMessage, AIMessage

from utils.agents.orchestrator_agent.schemas import Intent
from utils.agents.research_agent.schemas import AgentState
from utils.agents.research_agent.schemas import context_schema

from utils.agents.research_agent.prompts import system_prompt_aws_expert
from utils.agents.research_agent.prompts import system_prompt_azure_expert
from utils.agents.research_agent.prompts import system_prompt_researcher_lead

from utils.agents.research_agent.tools import retrieve_aws_information
from utils.agents.research_agent.tools import retrieve_azure_information


import json

def _extract_tool_payload(messages, provider_name: str):
    """
    Extrai conteúdo e metadados de um ToolMessage padronizado.

    Retorna:
      - unified_content (string): 
            "<Provider> Data:\n\nCONTENT...", 
            ou "" (se vazio)
      - metadata_list (list|None)
    """

    # Nenhum resultado de tool ainda
    if len(messages) <= 1:
        return "", None

    last_msg = messages[-1]

    raw_content = getattr(last_msg, "content", "")

    # ToolMessage às vezes vem estruturado como lista de partes [{text: "..."}]
    if isinstance(raw_content, list):
        text_part = next(
            (p.get("text") for p in raw_content if isinstance(p, dict) and "text" in p),
            None,
        )
        raw_content = text_part or ""

    # Tenta JSON
    try:
        payload = json.loads(raw_content)
    except Exception:
        # fallback: não conseguiu parsear → considera vazio
        return "", None

    # Extrai resultados padronizados
    results = payload.get("results", [])
    if not isinstance(results, list):
        results = []

    contents = []
    metadata_list = []

    for r in results:
        if not isinstance(r, dict):
            continue

        c = r.get("content")
        if c:
            contents.append(c)

        m = r.get("metadata")
        if m is not None:
            metadata_list.append(m)

    # -------------------------------
    # 1) Se não tem resultados → retorna string vazia
    # -------------------------------
    if not contents:
        return "", None

    # -------------------------------
    # 2) Junta conteúdo e adiciona prefixo
    # -------------------------------
    unified_content = f"{provider_name} Data:\n\n" + "\n\n".join(contents)

    # Se não tiver metadata
    if not metadata_list:
        metadata_list = None

    return unified_content, metadata_list


# --------------- Nodes ---------------
def make_researcher_leader_node(llm: ChatOpenAI, members: list[str]) -> str:

    system_prompt = system_prompt_researcher_lead.format(members=members)

    def researcher_leader_node(state: AgentState):
        """An LLM-based router / team lead."""

        azure_response = state.get("azure_messages", [])
        aws_response = state.get("aws_messages", [])

        # -----------------------------
        # 1) Já temos retorno das tools?
        # -----------------------------
        if len(azure_response) > 1 or len(aws_response) > 1:
            azure_content, azure_metadata = _extract_tool_payload(azure_response, "Azure")
            aws_content, aws_metadata = _extract_tool_payload(aws_response, "AWS")

            update = {
                "messages": azure_response + aws_response + [
                    AIMessage(
                        content="Data collected, forwarding the results to report writter agent"
                    )
                ],
                "next_node": [],              # você já usava array vazio
                "ai_intent": Intent.REPORT,
                "team_activated": True,
            }

            team_lead_response = []

            # -------- Azure --------
            azure_data = {}
            if azure_content != "":
                azure_data["content"] = azure_content
            if azure_metadata is not None:
                azure_data["metadata"] = azure_metadata
            if azure_data:  # só adiciona se tiver algo
                azure_data["provider"] = "azure"
                team_lead_response.append(azure_data)

            # -------- AWS --------
            aws_data = {}
            if aws_content != "":
                aws_data["content"] = aws_content
            if aws_metadata is not None:
                aws_data["metadata"] = aws_metadata
            if aws_data:
                aws_data["provider"] = "aws"
                team_lead_response.append(aws_data)

            update["team_lead_response"] = team_lead_response

            return update

        # ----------------------------------
        # 2) Ainda não chamou providers: roteamento normal
        # ----------------------------------
        messages = [SystemMessage(content=system_prompt)] + state["messages"]

        response = llm.with_structured_output(context_schema).invoke(messages)
        next_node = response.researchers
        missing_researchers = response.missing_researchers

        if len(next_node):
            team_lead_response = f"Calling providers experts {str(next_node)}"
        else:
            team_lead_response = "No providers experts for this topic"

        return {
            "messages": [AIMessage(content=team_lead_response)],
            "next_node": next_node,
            "missing_researchers": missing_researchers,
        }
    
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


# --------- Conditional edges ---------
def research_flow(state) -> Literal["aws_expert", "azure_expert", END]:
    if len(state["next_node"]) > 0:
        return state["next_node"]
    else:
        return END
    
