from __future__ import annotations

import uuid
from typing import List, Dict, Any, TypedDict, Optional


class AgentState(TypedDict):
    messages: List[Dict[str, str]]
    user_id: uuid.UUID
    query: str
    intent: str  # "direct" | "rag" | "summarize" | "compare"
    retrieved_context: List[str]
    tool_output: Optional[str]
    final_response: str
    image_bytes: Optional[bytes]