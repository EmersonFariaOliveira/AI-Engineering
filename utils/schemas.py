from pydantic import BaseModel, Field
from typing import Optional

from langchain.messages import AnyMessage
from typing_extensions import TypedDict, Annotated
import operator

class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int

