from pydantic import BaseModel
from typing import List, Optional

class TextContent(BaseModel):
    type: str
    text: str
    uri: Optional[str] = None

class ReadResourceResult(BaseModel):
    contents: List[TextContent]

class CallToolResult(BaseModel):
    content: List[TextContent]

class ServerResult(BaseModel):
    root: CallToolResult

class Tool(BaseModel):
    name: str
    description: str
    inputSchema: dict