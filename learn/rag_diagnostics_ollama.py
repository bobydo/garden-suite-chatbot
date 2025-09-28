import logging
import csv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.docstore.document import Document
from langchain_community.llms import Ollama   # Local Ollama integration

# -----------------------------
# Setup logging
# -----------------------------
logging.basicConfig(filename="rag_diagnostics.log", level=logging.INFO)

# -----------------------------
# Example corpus with metadata
# Replace this with your actual PDF/website ingestion pipeline
# -----------------------------
docs = [
    Document(
        page_content="In Edmonton RF3 zoning, the maximum garden suite height is 8.9 meters.",
        metadata={"source": "edmonton_zoning_bylaw.pdf", "page": 42}
    ),
    Document(
        page_content="A development permit is required before building a garden suite.",
        metadata={"source": "city_website", "url": "https://edmonton.ca/garden-suites"}
    )
]

splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)
split_docs = splitter.split_documents(docs)

embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
db = FAISS.from_documents(split_docs, embeddings)

# -----------------------------
# Mixed Prompt Template (Domain + Diagnostics)
# -----------------------------
prompt = PromptTemplate(
    template = """You are an Edmonton Garden Suite compliance assistant. 
Answer questions using ONLY official zoning bylaws, building codes, or city guidelines provided in the context. 

Guidelines:
- If question is about permits, cite Edmonton Zoning Bylaw 12800.
- If question is about costs or utilities, explain clearly with assumptions.
- If question is outside scope (e.g., construction method), politely say: 
  "Please consult a licensed builder or the City of Edmonton help desk."
- If the context contains partial info, summarize it clearly.
- If no relevant information is present at all, reply exactly: "No Answer Found".
- Always include citations at the end of your answer in parentheses (source filename, page number, or URL).
- Always answer in bullet points for clarity.

Context:
{context}

Question: {question}
Answer:""", 
    input_variables=["context", "question"]
)

# -----------------------------
# Ollama LLM (make sure Ollama is running locally)
# -----------------------------
llm = Ollama(model="llama3", temperature=0)

# -----------------------------
# Helper: Keyword coverage scan
# -----------------------------
def keyword_scan(query, docs, keywords):
    hits = [d for d in docs if any(k in d.page_content.lower() for k in keywords)]
    return hits

# -----------------------------
# Diagnostic function
# -----------------------------
def rag_diagnostic(question, expected_answer=None, top_k=3):
    retriever = db.as_retriever(search_kwargs={"k": top_k})
    retrieved = retriever.get_relevant_documents(question)
    context = "\n".join([doc.page_content for doc in retrieved])

    # Run LLM
    chain = LLMChain(llm=llm, prompt=prompt)
    answer = chain.run({"context": context, "question": question})

    # Step 1: Coverage scan
    keywords = [w for w in question.lower().split() if len(w) > 3]
    coverage_hits = keyword_scan(question, split_docs, keywords)

    # Step 2: Diagnosis logic
    if "No Answer Found" in answer:
        if not retrieved:
            diag = "Case 1/2 - No chunks retrieved (data missing or bad chunking)"
        elif not coverage_hits:
            diag = "Case 1 - Data coverage issue (no relevant text in sources)"
        elif coverage_hits and all(ch not in context for ch in [h.page_content for h in coverage_hits]):
            diag = "Case 3 - Embedding/Search issue (relevant text exists but not retrieved)"
        elif coverage_hits and any(h.page_content in context for h in coverage_hits):
            diag = "Case 4 - Prompt issue (info retrieved but model ignored it)"
        else:
            diag = "Unclear - needs manual review"
    else:
        if expected_answer and expected_answer.lower() not in answer.lower():
            diag = "Partial Match - check chunking or grounding"
        else:
            diag = "Answer Found"

    # Collect citation info
    citations = []
    for doc in retrieved:
        src = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", "")
        url = doc.metadata.get("url", "")
        if url:
            citations.append(f"{src} ({url})")
        elif page:
            citations.append(f"{src}, p.{page}")
        else:
            citations.append(src)

    # Debug logging
    logging.info(f"QUESTION: {question}")
    for i, doc in enumerate(retrieved):
        logging.info(f"CHUNK {i+1} (source={doc.metadata}): {doc.page_content[:200]}...")
    logging.info(f"ANSWER: {answer}")
    logging.info(f"DIAGNOSIS: {diag}\n{'-'*50}\n")

    return {
        "q": question,
        "a": answer,
        "diag": diag,
        "sources": citations,
        "coverage_hits": [h.metadata for h in coverage_hits]
    }

# -----------------------------
# Example run
# -----------------------------
if __name__ == "__main__":
    golden_questions = [
        ("What is the maximum garden suite height in RF3?", "8.9"),
        ("Do I need a development permit?", "permit"),
        ("What is the garden suite per sq foot cost?", None)  # realistic "No Answer"
    ]

    results = []
    for q, truth in golden_questions:
        result = rag_diagnostic(q, expected_answer=truth)
        results.append(result)
        print(f"\nQ: {result['q']}")
        print(f"A: {result['a']}")
        print(f"Diagnosis: {result['diag']}")
        print(f"Sources: {result['sources']}")
        print(f"Coverage hits: {result['coverage_hits']}")

    # Save to CSV for review
    with open("rag_diagnostics_report.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["q", "a", "diag", "sources", "coverage_hits"])
        writer.writeheader()
        writer.writerows(results)
