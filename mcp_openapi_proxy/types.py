from pydantic import BaseModel
from typing import List, Any

class TextContent(BaseModel):
    type: str
    text: str
    uri: str

class ReadResourceResult(BaseModel):
    contents: List[Any]

class ServerResult(BaseModel):
    root: ReadResourceResult