from fastapi import FastAPI
from models import UserQuery, Answer
from services import run_pipeline


app = FastAPI()

@app.post('/ask')
async def ask_question(query: UserQuery)->Answer | None:
    answer: Answer | None = run_pipeline(query)
    return answer