import json

from fastapi import FastAPI, Cookie, Response
from fastapi.responses import StreamingResponse

from models import UserQuery, Answer, StreamChunkEvent, StreamFinalEvent, StreamErrorEvent
from services import run_chat_only_pipeline, run_agent_pipeline, stream_agent_pipeline, get_agent_answer_from_state, lifespan


app = FastAPI(lifespan=lifespan)

def make_stream_error_response(message: str, session_id: str | None = None) -> StreamingResponse:
    def generate_error_stream():
        yield StreamErrorEvent(content=message).model_dump_json() + '\n'

    stream_response = StreamingResponse(generate_error_stream(), media_type='application/x-ndjson')
    if session_id:
        stream_response.set_cookie(key='kubebot_session_id', value=session_id)
    return stream_response

@app.post('/ask_simple')
async def ask_question_simple(response: Response, query: UserQuery, kubebot_session_id: str | None = Cookie(default=None))->Answer | None:
    answer: Answer | None = None
    returned_session_id:str = ''
    try:
        answer, returned_session_id = run_chat_only_pipeline(query, kubebot_session_id)
    except Exception as e:
        return Answer(answer='Sorry, I hit a snag and couldn\'t answer your question.',sources=[])
    if kubebot_session_id:
        assert returned_session_id == kubebot_session_id, "Bad session ID returned from pipeline."
    response.set_cookie(key='kubebot_session_id',value=returned_session_id)
    return answer

@app.post('/ask', response_model=None)
async def ask_question(response: Response, query: UserQuery, kubebot_session_id: str | None = Cookie(default=None))->Answer | StreamingResponse | None:
    if query.streaming:
        returned_session_id = kubebot_session_id

        try:
            chunk_stream, returned_session_id = stream_agent_pipeline(query, kubebot_session_id)
        except Exception:
            return make_stream_error_response('Sorry, I hit a snag and couldn\'t answer your question.', returned_session_id)

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
        stream_response.set_cookie(key='kubebot_session_id', value=returned_session_id)
        return stream_response

    answer: Answer | None = None
    returned_session_id:str = ''
    try:
        answer, returned_session_id = run_agent_pipeline(query, kubebot_session_id)
    except Exception as e:
        return Answer(answer='Sorry, I hit a snag and couldn\'t answer your question.',sources=[])
    if kubebot_session_id:
        assert returned_session_id == kubebot_session_id, "Bad session ID returned from pipeline."
    response.set_cookie(key='kubebot_session_id',value=returned_session_id)
    return answer