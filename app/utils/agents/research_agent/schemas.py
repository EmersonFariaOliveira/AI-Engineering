from langgraph.graph import MessagesState
from langgraph.graph.message import add_messages

from pydantic import BaseModel, Field
from langchain.messages import AnyMessage

from typing_extensions import Annotated, List

class AgentState(MessagesState):
	messages: Annotated[list[AnyMessage], add_messages]
	aws_messages: Annotated[list[AnyMessage], add_messages]
	azure_messages: Annotated[list[AnyMessage], add_messages]
	missing_researchers: List[str]
	team_activated: bool = False
	ai_intent: str = None
	team_lead_response: List[dict]

class context_schema(BaseModel):
	researchers: List[str] = Field(None, description="List of all the researchers that needs to be involved on the search")
	missing_researchers: List[str] = Field(None, description="List of missing researchers to call")