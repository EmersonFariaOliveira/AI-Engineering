from utils.agents.orchestrator_agent.nodes import (
    make_supervisor_node,
    make_writter_node,
    intent_flow
)
from utils.agents.research_agent.graph import ResearchAgent
from utils.agents.orchestrator_agent.schemas import AgentState

from langgraph.graph import START, END, StateGraph
from langchain_openai import ChatOpenAI


class OrchestratorAgent:
    @staticmethod
    def build_graph():
        llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0.0,
            max_tokens=1000,
        )

        builder = StateGraph(AgentState)
        builder.add_node("agent_supervisor", make_supervisor_node(llm))
        builder.add_node("researcher_team", ResearchAgent.build_graph())
        builder.add_node("report_writter", make_writter_node(llm))

        builder.add_edge(START, "agent_supervisor")

        builder.add_conditional_edges(
            "agent_supervisor",
            intent_flow
        )

        builder.add_edge("researcher_team", "agent_supervisor")
        builder.add_edge("report_writter", "agent_supervisor")

        return builder.compile()

