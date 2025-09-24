from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from config import SYSTEM_PROMPT_PATH

with open(SYSTEM_PROMPT_PATH, encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

ANSWER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder("chat_history"),
    ("human", """Question: {question}

Context (top {top_k} results):
{retrieved_chunks}

If context is insufficient, respond with what is missing (e.g. lot width, zone)."""),
])
