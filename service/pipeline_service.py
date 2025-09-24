from prompts.answer_prompt import ANSWER_PROMPT
from service.retriever_service import RetrieverService
from tools.bylaw_lookup import BylawLookup
from tools.fee_lookup import FeeLookup
from langchain_ollama import ChatOllama
from langchain.agents import create_react_agent, AgentExecutor
from langchain.tools import Tool
from langchain.prompts import PromptTemplate
from service.log_helper import LogHelper
from config import OLLAMA_MODEL


class PipelineService:
    def __init__(self, model: str = OLLAMA_MODEL, temperature: float = 0, use_agents: bool = True):
        self.llm = ChatOllama(model=model, temperature=temperature)
        self.retriever = RetrieverService()
        self.logger = LogHelper.get_logger("PipelineService")
        self.use_agents = use_agents
        
        # Initialize tools
        self.bylaw_lookup = BylawLookup()
        self.fee_lookup = FeeLookup()
        
        if self.use_agents:
            self._setup_agent()

    def _setup_agent(self):
        """Setup LangChain agent with tools."""
        # Define tools
        tools = [
            Tool(
                name="bylaw_lookup",
                description="Search for specific bylaw sections related to garden suites. Use this when users ask about specific regulations, zoning requirements, or bylaw sections. Input should be the search term or section number.",
                func=lambda query: str(self.bylaw_lookup.find(query))
            ),
            Tool(
                name="fee_lookup", 
                description="Find current permit fees for garden suite development. Use this when users ask about costs, fees, or permit prices. Input should be the type of permit or fee being asked about.",
                func=lambda query: str(self.fee_lookup.find(query))
            ),
            Tool(
                name="general_search",
                description="Search general garden suite information from documents and websites. Use this for broad questions about garden suites, processes, or general information.",
                func=self._general_search
            )
        ]
        
        # Create agent prompt
        agent_prompt = PromptTemplate.from_template("""
You are an expert assistant for Edmonton garden suite regulations and development. You have access to the following tools:

{tools}

Use the tools when appropriate to provide accurate, specific information. Always cite sources when possible.

When answering:
1. Use bylaw_lookup for specific regulations, zoning, or bylaw sections
2. Use fee_lookup for cost and permit fee questions  
3. Use general_search for broad questions or when other tools don't apply
4. Provide clear, helpful responses with source citations

Previous conversation:
{chat_history}

Question: {input}
{agent_scratchpad}
""")
        
        try:
            # Create ReAct agent
            agent = create_react_agent(self.llm, tools, agent_prompt)
            self.agent_executor = AgentExecutor(
                agent=agent, 
                tools=tools, 
                verbose=True,
                max_iterations=3,
                handle_parsing_errors=True
            )
            self.logger.info("Agent setup completed successfully")
        except Exception as e:
            self.logger.error(f"Failed to setup agent: {e}")
            self.use_agents = False

    def _general_search(self, query: str) -> str:
        """Fallback to original RAG approach for general searches."""
        hits = self.retriever.get_relevant_chunks(query, k=4)
        if not hits:
            return "No relevant information found in the knowledge base."
        
        retrieved_info = "\n".join([
            f"Source: {h.metadata.get('title', h.metadata.get('source', h.metadata.get('url', 'Unknown')))}\n"
            f"Content: {h.page_content[:300]}...\n"
            for h in hits
        ])
        
        return f"Found relevant information:\n{retrieved_info}"

    def run_chat(self, user_question: str, history: list | None = None) -> str:
        history = history or []
        
        try:
            if self.use_agents and hasattr(self, 'agent_executor'):
                # Use agent-based approach
                chat_history_str = "\n".join([
                    f"Human: {h.get('question', '')}\nAssistant: {h.get('answer', '')}" 
                    for h in history[-3:]  # Last 3 exchanges for context
                ]) if history else "No previous conversation."
                
                result = self.agent_executor.invoke({
                    "input": user_question,
                    "chat_history": chat_history_str
                })
                
                answer = result.get("output", "I apologize, but I couldn't generate a proper response.")
                self.logger.info(f"Agent answered: {user_question}")
                return answer
                
            else:
                # Fallback to original RAG approach
                return self._fallback_rag(user_question, history)
                
        except Exception as e:
            self.logger.error(f"Chat processing failed: {e}")
            # Fallback to RAG on any error
            return self._fallback_rag(user_question, history)

    def _fallback_rag(self, user_question: str, history: list) -> str:
        """Original RAG-based approach as fallback."""
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
        self.logger.info(f"RAG fallback answered: {user_question}")
        return getattr(resp, "content", str(resp))
