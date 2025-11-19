from enum import Enum

from langgraph.graph import MessagesState
from langgraph.graph.message import add_messages

from pydantic import BaseModel, Field
from langchain.messages import AnyMessage

from typing_extensions import Annotated, List


class AgentState(MessagesState):
	messages: Annotated[list[AnyMessage], add_messages]
	missing_researchers: List[str]
	next_node: str = None
	team_activated: bool = False
	ai_intent: str = None
	team_lead_response: List[dict]

class IntentOutput(BaseModel):
	intent: str = Field(..., description="One of: 'INTENT.SEARCH', 'INTENT.REPORT', 'INTENT.UNKNOWN'")
	  
class Intent(str, Enum):
	SEARCH = "INTENT.SEARCH"
	REPORT = "INTENT.REPORT"
	UNKNOWN = "INTENT.UNKNOWN"