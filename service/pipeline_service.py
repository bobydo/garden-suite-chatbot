import os
from datetime import datetime
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_core.prompts import ChatPromptTemplate
from prompts.answer_prompt import ANSWER_PROMPT
from service.retriever_service import RetrieverService
from tools.bylaw_lookup import BylawLookup
from tools.fee_lookup import FeeLookup
from langchain_ollama import ChatOllama
from service.log_helper import LogHelper
from config import OLLAMA_MODEL


class ChatState(TypedDict):
    question: str
    history: list
    intent: str
    retrieved_context: str
    answer: str


class PipelineService:
    def __init__(self, model: str = OLLAMA_MODEL, temperature: float = 0, _use_agents: bool = True):
        self.llm = ChatOllama(model=model, temperature=temperature)
        self.retriever = RetrieverService()
        self.bylaw_lookup = BylawLookup()
        self.fee_lookup = FeeLookup()
        self.logger = LogHelper.get_logger("PipelineService")
        self.graph = self._build_graph()

    def _build_graph(self):
        """Build the LangGraph StateGraph: classify → retrieve → generate."""
        graph = StateGraph(ChatState)

        graph.add_node("classify", self._classify_node)
        graph.add_node("retrieve_bylaw", self._retrieve_bylaw_node)
        graph.add_node("retrieve_fee", self._retrieve_fee_node)
        graph.add_node("retrieve_general", self._retrieve_general_node)
        graph.add_node("generate", self._generate_node)

        graph.set_entry_point("classify")

        graph.add_conditional_edges(
            "classify",
            lambda state: state["intent"],
            {
                "bylaw":   "retrieve_bylaw",
                "fee":     "retrieve_fee",
                "general": "retrieve_general",
            }
        )

        graph.add_edge("retrieve_bylaw",   "generate")
        graph.add_edge("retrieve_fee",     "generate")
        graph.add_edge("retrieve_general", "generate")
        graph.add_edge("generate", END)

        return graph.compile()

    # ── Node 1: classify (LLM call #1) ────────────────────────────────────────

    def _classify_node(self, state: ChatState) -> ChatState:
        """Classify question intent: bylaw / fee / general."""
        classify_prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are classifying questions about Edmonton garden suite development.\n"
             "Reply with exactly one word — the category that best fits:\n"
             "  bylaw   — regulations, zoning rules, setbacks, permitted uses, bylaw sections\n"
             "  fee     — costs, permit fees, prices, charges, application fees\n"
             "  general — anything else: processes, timelines, general info, how-to\n"
             "Reply with only the single word. No punctuation, no explanation."),
            ("human", "{question}")
        ])
        try:
            response = self.llm.invoke(classify_prompt.format_messages(question=state["question"]))
            intent = str(response.content).strip().lower().split()[0]
            if intent not in ("bylaw", "fee", "general"):
                intent = "general"
        except Exception as e:
            self.logger.warning(f"Classification failed, defaulting to general: {e}")
            intent = "general"

        self.logger.info(f"Classified '{state['question']}' → {intent}")
        return {**state, "intent": intent}

    # ── Node 2a: retrieve bylaw (no LLM call) ─────────────────────────────────

    def _retrieve_bylaw_node(self, state: ChatState) -> ChatState:
        """Search PDF collection via BylawLookup."""
        try:
            result = self.bylaw_lookup.find(state["question"])
            context = (
                f"Bylaw source: {result.get('section', '')} | {result.get('url', '')}\n"
                f"Content: {result.get('text', '')}"
            )
        except Exception as e:
            self.logger.error(f"Bylaw retrieval failed: {e}")
            context = self._general_context(state["question"])
        return {**state, "retrieved_context": context}

    # ── Node 2b: retrieve fee (no LLM call) ───────────────────────────────────

    def _retrieve_fee_node(self, state: ChatState) -> ChatState:
        """Search website collection via FeeLookup."""
        try:
            result = self.fee_lookup.find(state["question"])
            context = (
                f"Fee source: {result.get('url', '')}\n"
                f"Content: {result.get('text', '')}"
            )
        except Exception as e:
            self.logger.error(f"Fee retrieval failed: {e}")
            context = self._general_context(state["question"])
        return {**state, "retrieved_context": context}

    # ── Node 2c: retrieve general (no LLM call) ───────────────────────────────

    def _retrieve_general_node(self, state: ChatState) -> ChatState:
        """Hybrid search across all 3 collections."""
        context = self._general_context(state["question"])
        return {**state, "retrieved_context": context}

    def _general_context(self, question: str) -> str:
        """Shared helper: hybrid retrieval across all collections."""
        try:
            hits = self.retriever.get_relevant_chunks(question, k=4)
            if not hits:
                return "(no context retrieved)"
            return "\n".join(
                f"• {h.metadata.get('title', h.metadata.get('source', h.metadata.get('url', '(no-url)')))} "
                f"({h.metadata.get('url', h.metadata.get('source', ''))}) — {h.page_content[:240]}..."
                for h in hits
            )
        except Exception as e:
            self.logger.error(f"General retrieval failed: {e}")
            return "(retrieval failed: Qdrant may be unavailable)"

    # ── Node 3: generate (LLM call #2) ────────────────────────────────────────

    def _generate_node(self, state: ChatState) -> ChatState:
        """Generate final answer using retrieved context."""
        messages = ANSWER_PROMPT.format_messages(
            chat_history=state["history"],
            question=state["question"],
            retrieved_chunks=state["retrieved_context"],
            top_k=4
        )
        try:
            resp = self.llm.invoke(messages)
            answer = getattr(resp, "content", str(resp))
        except Exception as e:
            self.logger.error(f"LLM generation failed: {e}")
            answer = (
                "I couldn't generate an answer because the language model isn't reachable. "
                "Please ensure Ollama is running (ollama serve) and the model is available "
                "(e.g., ollama pull llama3)."
            )
        self._log_gap_if_needed(state["question"], state["retrieved_context"], answer)
        return {**state, "answer": answer}

    def _log_gap_if_needed(self, question: str, context: str, answer: str):
        """Log questions the system couldn't answer so content creators know what to add."""
        no_context = context == "(no context retrieved)"
        uncertain = "uncertain" in answer.lower() or "i don't know" in answer.lower()
        if no_context or uncertain:
            os.makedirs("logs", exist_ok=True)
            with open("logs/content_gaps.log", "a", encoding="utf-8") as f:
                reason = "no_context" if no_context else "uncertain_answer"
                f.write(f"{datetime.now().isoformat()} | {reason} | {question}\n")
            self.logger.info(f"Gap logged [{reason}]: {question}")

    # ── Public entry point ────────────────────────────────────────────────────

    def run_chat(self, user_question: str, history: list | None = None) -> str:
        history = history or []
        try:
            initial_state: ChatState = {
                "question": user_question,
                "history": history[-3:],   # last 3 exchanges for context
                "intent": "",
                "retrieved_context": "",
                "answer": ""
            }
            result = self.graph.invoke(initial_state)
            self.logger.info(f"Graph answered [{result['intent']}]: {user_question}")
            return result["answer"]
        except Exception as e:
            self.logger.error(f"Graph execution failed: {e}")
            return (
                "I'm having trouble right now. Please ensure Ollama and Qdrant are running, "
                "then try again."
            )
