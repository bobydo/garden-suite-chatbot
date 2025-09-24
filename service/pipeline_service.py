from prompts.answer_prompt import ANSWER_PROMPT
from service.retriever_service import RetrieverService
from langchain_ollama import ChatOllama
from service.log_helper import LogHelper
from config import OLLAMA_MODEL

class PipelineService:
    def __init__(self, model: str = OLLAMA_MODEL, temperature: float = 0):
        self.llm = ChatOllama(model=model, temperature=temperature)
        self.retriever = RetrieverService()
        self.logger = LogHelper.get_logger("PipelineService")

    def run_chat(self, user_question: str, history: list | None = None) -> str:
        history = history or []

        # 1) Retrieve
        hits = self.retriever.get_relevant_chunks(user_question, k=4)
        if not hits:
            retrieved_chunks = "(no context retrieved)"
        else:
            retrieved_chunks = "\n".join(
                f"• {h.metadata.get('title', h.metadata.get('source', h.metadata.get('url','(no-url)')))} "
                f"({h.metadata.get('url', h.metadata.get('source',''))}) — {h.page_content[:240]}..."
                for h in hits
            )

        # 2) Build messages
        messages = ANSWER_PROMPT.format_messages(
            chat_history=history,
            question=user_question,
            retrieved_chunks=retrieved_chunks,
            top_k=4
        )

        # 3) Call Ollama
        resp = self.llm.invoke(messages)
        self.logger.info(f"Answered: {user_question}")
        return getattr(resp, "content", str(resp))
