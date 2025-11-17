# from utils.agents.orchestrator_agent.schemas import Router
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage

from utils.agents.orchestrator_agent.schemas import AgentState
from utils.agents.orchestrator_agent.prompts import system_prompt_supervisor
from utils.agents.orchestrator_agent.prompts import system_prompt_writter

from typing import Literal
from typing_extensions import TypedDict

def make_supervisor_node(llm: ChatOpenAI, members: list[str]) -> str:
	options = ["FINISH"] + members
	system_prompt = system_prompt_supervisor.format(members=members)

	class Router(TypedDict):
		"""Worker to route to next. If no workers needed, route to FINISH."""
		next: Literal[*options]

	def supervisor_node(state: AgentState):
		"""An LLM-based router."""
		messages = [SystemMessage(content=system_prompt)] + state["messages"]
		response = llm.with_structured_output(Router).invoke(messages)
		next_node = response["next"]

		return {"messages":[], "next_node": next_node}

	return supervisor_node


def make_writter_node(llm: ChatOpenAI) -> str:
	def writter_node(state: AgentState):
		missing_providers = state.get("missing_researchers", [])
		azure_response = state.get("azure_messages", [])
		aws_response = state.get("aws_messages", [])

		if azure_response:
			# Take the last message as the most recent one
			azure_content = f"Azure Cloud Information:\n{azure_response[-1].content}"
		else:
			azure_content = "Azure Cloud Information: Missing data."

		if aws_response:
			aws_content = f"AWS Cloud Information:\n{aws_response[-1].content}"
		else:
			aws_content = "AWS Cloud Information: Missing data."

		context = f"{azure_content}\n\n{aws_content}"

		system_prompt = system_prompt_writter.format(
			missing_providers=missing_providers,
			context=context,
		)

		messages = [SystemMessage(content=system_prompt)] + [state["messages"][0]]
		response = llm.invoke(messages)

		return {"messages":[response]}
	
	return writter_node