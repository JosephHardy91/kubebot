import json
import re

from fastapi import FastAPI, Cookie, Response
from fastapi.responses import StreamingResponse

from models import UserQuery, Answer, StreamChunkEvent, StreamFinalEvent, StreamErrorEvent
from services import run_chat_only_pipeline, run_agent_pipeline, stream_agent_pipeline, get_agent_answer_from_state, lifespan
from services.memory import generate_session_id


app = FastAPI(lifespan=lifespan)

SESSION_ID_PATTERN = re.compile(r'^[A-Za-z0-9_-]{43}$')

def normalize_session_id(session_id: str | None) -> str | None:
    if session_id and SESSION_ID_PATTERN.fullmatch(session_id):
        return session_id
    return None

def set_session_cookie(response: Response, session_id: str | None) -> None:
    if not session_id:
        return

    response.set_cookie(
        key='kubebot_session_id',
        value=session_id,
        httponly=True,
        secure=True,
        samesite='lax',
        path='/',
    )

def make_stream_error_response(message: str, session_id: str | None = None) -> StreamingResponse:
    def generate_error_stream():
        yield StreamErrorEvent(content=message).model_dump_json() + '\n'

    stream_response = StreamingResponse(generate_error_stream(), media_type='application/x-ndjson')
    set_session_cookie(stream_response, normalize_session_id(session_id))
    return stream_response

@app.post('/ask_simple')
async def ask_question_simple(response: Response, query: UserQuery, kubebot_session_id: str | None = Cookie(default=None))->Answer | None:
    kubebot_session_id = normalize_session_id(kubebot_session_id)
    new_session_id = generate_session_id() if not kubebot_session_id else None
    session_id = kubebot_session_id or new_session_id
    answer: Answer | None = None
    returned_session_id:str = ''
    try:
        answer, returned_session_id = run_chat_only_pipeline(query, session_id)
    except Exception as e:
        return Answer(answer='Sorry, I hit a snag and couldn\'t answer your question.',sources=[])
    if session_id and returned_session_id != session_id:
        return Answer(answer='Sorry, I hit a snag and couldn\'t answer your question.',sources=[])
    if new_session_id:
        set_session_cookie(response, returned_session_id)
    return answer

@app.post('/ask', response_model=None)
async def ask_question(response: Response, query: UserQuery, kubebot_session_id: str | None = Cookie(default=None))->Answer | StreamingResponse | None:
    kubebot_session_id = normalize_session_id(kubebot_session_id)
    new_session_id = generate_session_id() if not kubebot_session_id else None
    session_id = kubebot_session_id or new_session_id
    if query.streaming:
        returned_session_id = session_id

        try:
            chunk_stream, returned_session_id = stream_agent_pipeline(query, session_id)
        except Exception:
            return make_stream_error_response(
                'Sorry, I hit a snag and couldn\'t answer your question.',
                new_session_id,
            )
        if session_id and returned_session_id != session_id:
            return make_stream_error_response('Sorry, I hit a snag and couldn\'t answer your question.')

        def generate_stream():
            try:
                for chunk in chunk_stream:
                    yield StreamChunkEvent(content=chunk).model_dump_json() + '\n'

                answer = get_agent_answer_from_state(returned_session_id)
                if answer is None:
                    yield StreamErrorEvent(content='Sorry, I hit a snag and couldn\'t answer your question.').model_dump_json() + '\n'
                    return

                yield StreamFinalEvent(answer=answer).model_dump_json() + '\n'
            except Exception:
                yield StreamErrorEvent(content='Sorry, I hit a snag and couldn\'t answer your question.').model_dump_json() + '\n'

        stream_response = StreamingResponse(generate_stream(), media_type='application/x-ndjson')
        if new_session_id:
            set_session_cookie(stream_response, returned_session_id)
        return stream_response

    answer: Answer | None = None
    returned_session_id:str = ''
    try:
        answer, returned_session_id = run_agent_pipeline(query, session_id)
    except Exception as e:
        return Answer(answer='Sorry, I hit a snag and couldn\'t answer your question.',sources=[])
    if session_id and returned_session_id != session_id:
        return Answer(answer='Sorry, I hit a snag and couldn\'t answer your question.',sources=[])
    if new_session_id:
        set_session_cookie(response, returned_session_id)
    return answer
