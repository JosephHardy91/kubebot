from contextlib import asynccontextmanager
from fastapi import FastAPI, Cookie, Response
from models import UserQuery, Answer
from services import run_chat_only_pipeline, run_agent_pipeline
from services.memory import get_checkpointer
from services.chat import init_agents


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: open checkpointer connection and initialize agents
    with get_checkpointer() as checkpointer:
        init_agents(checkpointer)
        yield
    # Shutdown: checkpointer connection closes automatically

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