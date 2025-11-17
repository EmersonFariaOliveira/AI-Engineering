import operator

from pydantic import BaseModel, Field
from langchain.messages import AnyMessage

from typing import List
from typing_extensions import TypedDict, Annotated

class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    aws_messages: Annotated[list[AnyMessage], operator.add]
    azure_messages: Annotated[list[AnyMessage], operator.add]
    missing_researchers: List[str]

class context_schema(BaseModel):
    researchers: List[str] = Field(None, description="List of all the researchers that needs to be involved on the search")
    missing_researchers: List[str] = Field(None, description="List of missing researchers to call")