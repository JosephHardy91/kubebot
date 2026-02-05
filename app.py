from fastapi import FastAPI, Cookie, Response
from models import UserQuery, Answer
from services import run_chat_only_pipeline, run_agent_pipeline, lifespan


app = FastAPI(lifespan=lifespan)

@app.post('/ask_simple')
async def ask_question_simple(response: Response, query: UserQuery, kubebot_session_id: str | None = Cookie(default=None))->Answer | None:
    answer: Answer | None = None
    returned_session_id:str = ''
    answer, returned_session_id = run_chat_only_pipeline(query, kubebot_session_id)
    if kubebot_session_id:
        assert returned_session_id == kubebot_session_id, "Bad session ID returned from pipeline."
    response.set_cookie(key='kubebot_session_id',value=returned_session_id)
    return answer

@app.post('/ask')
async def ask_question(response: Response, query: UserQuery, kubebot_session_id: str | None = Cookie(default=None))->Answer | None:
    answer: Answer | None = None
    returned_session_id:str = ''
    answer, returned_session_id = run_agent_pipeline(query, kubebot_session_id)
    if kubebot_session_id:
        assert returned_session_id == kubebot_session_id, "Bad session ID returned from pipeline."
    response.set_cookie(key='kubebot_session_id',value=returned_session_id)
    return answer