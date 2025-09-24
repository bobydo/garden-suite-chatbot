from fastapi import FastAPI
from pydantic import BaseModel
from service.pipeline_service import PipelineService

app = FastAPI(title="Garden Suite Chatbot API")
pipeline = PipelineService()

class ChatRequest(BaseModel):
    question: str
    history: list = []

@app.post("/chat")
def chat(req: ChatRequest):
    answer = pipeline.run_chat(req.question, req.history)
    return {"answer": answer}

@app.get("/health")
def health():
    return {"status": "ok"}
