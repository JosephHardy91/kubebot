from fastapi import FastAPI, Cookie, Response
from models import UserQuery, Answer
from services import run_chat_only_pipeline, run_agent_pipeline, lifespan


app = FastAPI(lifespan=lifespan)

@app.post('/ask_simple')
async def ask_question_simple(query: UserQuery)->Answer | None:
    answer: Answer | None = run_chat_only_pipeline(query)
    return answer

@app.post('/ask')
async def ask_question(query: UserQuery)->Answer | None:
    answer: Answer | None = run_agent_pipeline(query)
    return answer