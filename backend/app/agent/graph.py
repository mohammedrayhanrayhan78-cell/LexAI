from __future__ import annotations

import logging
from langgraph.graph import StateGraph, END
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.state import AgentState
from app.agent.tools import AgentTools
from app.services.retrieval import retrieval_service
from app.core.llm.router import llm_router

logger = logging.getLogger(__name__)


class LegalAgentGraph:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.workflow = StateGraph(AgentState)
        self._build_graph()

    def _build_graph(self) -> None:
        # Add nodes
        self.workflow.add_node("classify_intent", self.classify_intent_node)
        self.workflow.add_node("rag_retrieval", self.rag_retrieval_node)
        self.workflow.add_node("tool_node", self.tool_execution_node)
        self.workflow.add_node("direct_answer", self.direct_answer_node)

        # Set entry point
        self.workflow.set_entry_point("classify_intent")

        # Add conditional edges based on intent
        self.workflow.add_conditional_edges(
            "classify_intent",
            self.route_intent,
            {
                "rag": "rag_retrieval",
                "summarize": "tool_node",
                "compare": "tool_node",
                "direct": "direct_answer",
            },
        )

        # Connect processing nodes to completion
        self.workflow.add_edge("rag_retrieval", "direct_answer")
        self.workflow.add_edge("tool_node", END)
        self.workflow.add_edge("direct_answer", END)

        self.compiled_graph = self.workflow.compile()

    async def classify_intent_node(self, state: AgentState) -> AgentState:
        query = state["query"]
        try:
            classification_prompt = [
                {
                    "role": "system",
                    "content": (
                        "Classify the user query into exactly one of these categories: "
                        "'rag' (general question requiring law/statute context search), "
                        "'summarize' (request to summarize documents), "
                        "'compare' (request to compare clauses or documents), "
                        "'direct' (conversational or general inquiry not needing document lookup). "
                        "Return only the category name in lowercase."
                    ),
                },
                {"role": "user", "content": query},
            ]
            intent_resp = await llm_router.generate_response(classification_prompt)
            cleaned_intent = intent_resp.strip().lower()

            if cleaned_intent in {"rag", "summarize", "compare", "direct"}:
                state["intent"] = cleaned_intent
            else:
                state["intent"] = "rag"  # Safe default for legal queries
        except Exception as e:
            logger.warning(f"Intent classification failed: {e}. Defaulting to 'rag'.")
            state["intent"] = "rag"
        return state

    def route_intent(self, state: AgentState) -> str:
        intent = state.get("intent", "rag")
        if intent in {"summarize", "compare"}:
            return intent
        elif intent == "rag":
            return "rag"
        return "direct"

    async def rag_retrieval_node(self, state: AgentState) -> AgentState:
        chunks = await retrieval_service.search_relevant_chunks(
            self.db, query=state["query"], user_id=state["user_id"]
        )
        state["retrieved_context"] = chunks
        return state

    async def tool_execution_node(self, state: AgentState) -> AgentState:
        intent = state["intent"]
        if intent == "summarize":
            output = await AgentTools.summarize_document(self.db, state["user_id"], state["query"])
        elif intent == "compare":
            output = await AgentTools.compare_documents(self.db, state["user_id"], state["query"])
        else:
            output = "Tool execution not recognized."
        
        state["tool_output"] = output
        state["final_response"] = output
        return state

    async def direct_answer_node(self, state: AgentState) -> AgentState:
        messages = state["messages"]
        image_bytes = state.get("image_bytes")
        retrieved_context = state.get("retrieved_context", [])

        formatted_history = list(messages)
        if retrieved_context:
            context_block = "Relevant legal document excerpts:\n" + "\n---\n".join(retrieved_context)
            formatted_history.insert(0, {"role": "system", "content": context_block})

        if image_bytes is not None:
            response = await llm_router.generate_response_with_image(formatted_history, image_bytes)
        else:
            response = await llm_router.generate_response(formatted_history)

        state["final_response"] = response
        return state

    async def run(self, messages: list[dict], user_id: uuid.UUID, query: str, image_bytes: bytes | None = None) -> str:
        initial_state: AgentState = {
            "messages": messages,
            "user_id": user_id,
            "query": query,
            "intent": "rag",
            "retrieved_context": [],
            "tool_output": None,
            "final_response": "",
            "image_bytes": image_bytes,
        }
        result_state = await self.compiled_graph.ainvoke(initial_state)
        return result_state["final_response"]