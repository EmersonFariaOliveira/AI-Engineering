import operator
from langchain.messages import AnyMessage
from typing_extensions import TypedDict, Annotated, List

class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    aws_messages: Annotated[list[AnyMessage], operator.add]
    azure_messages: Annotated[list[AnyMessage], operator.add]
    missing_researchers: List[str]
    next_node: str = None