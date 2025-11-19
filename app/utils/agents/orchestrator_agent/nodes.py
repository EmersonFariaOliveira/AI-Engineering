# from utils.agents.orchestrator_agent.schemas import Router
from langgraph.graph import END
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, AIMessage

from utils.agents.orchestrator_agent.schemas import Intent
from utils.agents.orchestrator_agent.schemas import AgentState
from utils.agents.orchestrator_agent.schemas import IntentOutput

from utils.agents.orchestrator_agent.prompts import system_prompt_writter
from utils.agents.orchestrator_agent.prompts import prompt_intent_system

from typing import Literal


# ----------- Aux Functions -----------
def _map_intent_label(label: str):
	try:
		return Intent(label)
	except Exception:
		return Intent.UNKNOWN


def classify_intent(messages, _llm):
	prompt = [SystemMessage(content=prompt_intent_system)] + messages
	parser = _llm.with_structured_output(IntentOutput)
	result = parser.invoke(prompt)

	return result


# --------------- Nodes ---------------
def make_supervisor_node(llm: ChatOpenAI) -> str:
	def supervisor_node(state: AgentState):
		response_state = {"ai_intent": Intent.UNKNOWN}

		if state['messages'][-1].type == 'human':
			intent = classify_intent(state['messages'], llm)
			user_intent = _map_intent_label(intent.intent)

			if user_intent == Intent.UNKNOWN:
				response_state.update({
					"messages": [
						AIMessage("I'm unable to assist with that. My scope is limited to cloud-provider-related questions. Let me know what you'd like to explore, and I can create a detailed report for you.")
					], 
					"user_intent": user_intent,
					"last_node": "Orchestrator",
					"requester_agent": "Orchestrator"
				})
			else:
				response_state.update({
					"messages": [AIMessage("Calling team members to address the user question!")],
					"team_activated": False,
					"user_intent": user_intent, 
					"last_node": "Orchestrator",
					"requester_agent": "Orchestrator"
				})

		else:

			ai_intent = state.get("ai_intent", Intent.UNKNOWN)
			user_intent = Intent.UNKNOWN

			response_state.update({
				"messages": [],
				"user_intent": user_intent,
				"ai_intent": ai_intent,
				"last_node": "Orchestrator",
				"requester_agent": "Orchestrator"
			})

		return response_state
	return supervisor_node


def make_writter_node(llm: ChatOpenAI) -> str:
	def writter_node(state: AgentState):

		if not state.get("team_activated", False):
			return {
				"messages":[AIMessage(content="I need the information from research team to find information about the topic requested.")],
				"last_node": "report_writter",
				"ai_intent": Intent.SEARCH
			}

		# Check if the research team does not have information of a specific provider
		missing_providers = state.get("missing_researchers", [])
		# Read response from the providers saved on the state
		team_lead_response = state.get("team_lead_response", [])

		contents = [r.get("content", "") for r in team_lead_response]
		# Build context string
		context = "\n\n".join(contents)

		# Insertion of specialists research result and information of missing providers on the system prompt
		system_prompt = system_prompt_writter.format(
			missing_providers=missing_providers,
			context=context,
		)

		# Adding system prompt and user question as a context to AI to answer
		messages = [SystemMessage(content=system_prompt)] + [state["messages"][0]]
		response = llm.invoke(messages)

		return {"messages":[response], "ai_intent": Intent.UNKNOWN}
	
	return writter_node

# --------- Conditional edges ---------
def intent_flow(state) -> Literal["researcher_team", "report_writter", END]:
	intent_to_agent = {
		Intent.SEARCH: "researcher_team",
		Intent.REPORT: "report_writter",
		Intent.UNKNOWN: END,
	}

	ai_intent = state['ai_intent']
	user_intent = state['user_intent']

	if ai_intent is not Intent.UNKNOWN:
		next_node = intent_to_agent.get(ai_intent, END)
	else:		
		next_node = intent_to_agent.get(user_intent, END)

	return next_node