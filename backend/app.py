import json

from fastapi import FastAPI, Cookie, Response
from fastapi.responses import StreamingResponse

from models import UserQuery, Answer, StreamChunkEvent, StreamFinalEvent, StreamErrorEvent
from services import run_chat_only_pipeline, run_agent_pipeline, stream_agent_pipeline, get_agent_answer_from_state, lifespan
from services.memory import generate_session_id, normalize_session_id


app = FastAPI(lifespan=lifespan)

def make_stream_error_response(message: str) -> StreamingResponse:
    def generate_error_stream():
        yield StreamErrorEvent(content=message).model_dump_json() + '\n'

    return StreamingResponse(generate_error_stream(), media_type='application/x-ndjson')

@app.post('/ask_simple')
async def ask_question_simple(response: Response, query: UserQuery, kubebot_session_id: str | None = Cookie(default=None))->Answer | None:
    client_session_id = normalize_session_id(kubebot_session_id)
    answer: Answer | None = None

    if client_session_id is not None:
        try:
            return run_chat_only_pipeline(query, client_session_id)
        except Exception as e:
            return Answer(answer='Sorry, I hit a snag and couldn\'t answer your question.',sources=[])

    new_session_id = generate_session_id()
    try:
        answer = run_chat_only_pipeline(query, new_session_id)
    except Exception as e:
        return Answer(answer='Sorry, I hit a snag and couldn\'t answer your question.',sources=[])

    response.set_cookie(
        key='kubebot_session_id',
        value=new_session_id,
        httponly=True,
        secure=True,
        samesite='lax',
        path='/',
    )
    return answer

@app.post('/ask', response_model=None)
async def ask_question(response: Response, query: UserQuery, kubebot_session_id: str | None = Cookie(default=None))->Answer | StreamingResponse | None:
    client_session_id = normalize_session_id(kubebot_session_id)

    if query.streaming:
        if client_session_id is not None:
            try:
                chunk_stream = stream_agent_pipeline(query, client_session_id)
            except Exception:
                return make_stream_error_response('Sorry, I hit a snag and couldn\'t answer your question.')

            def generate_stream():
                try:
                    for chunk in chunk_stream:
                        yield StreamChunkEvent(content=chunk).model_dump_json() + '\n'

                    answer = get_agent_answer_from_state(client_session_id)
                    if answer is None:
                        yield StreamErrorEvent(content='Sorry, I hit a snag and couldn\'t answer your question.').model_dump_json() + '\n'
                        return

                    yield StreamFinalEvent(answer=answer).model_dump_json() + '\n'
                except Exception:
                    yield StreamErrorEvent(content='Sorry, I hit a snag and couldn\'t answer your question.').model_dump_json() + '\n'

            return StreamingResponse(generate_stream(), media_type='application/x-ndjson')

        new_session_id = generate_session_id()
        try:
            chunk_stream = stream_agent_pipeline(query, new_session_id)
        except Exception:
            return make_stream_error_response('Sorry, I hit a snag and couldn\'t answer your question.')

        def generate_stream():
            try:
                for chunk in chunk_stream:
                    yield StreamChunkEvent(content=chunk).model_dump_json() + '\n'

                answer = get_agent_answer_from_state(new_session_id)
                if answer is None:
                    yield StreamErrorEvent(content='Sorry, I hit a snag and couldn\'t answer your question.').model_dump_json() + '\n'
                    return

                yield StreamFinalEvent(answer=answer).model_dump_json() + '\n'
            except Exception:
                yield StreamErrorEvent(content='Sorry, I hit a snag and couldn\'t answer your question.').model_dump_json() + '\n'

        stream_response = StreamingResponse(generate_stream(), media_type='application/x-ndjson')
        stream_response.set_cookie(
            key='kubebot_session_id',
            value=new_session_id,
            httponly=True,
            secure=True,
            samesite='lax',
            path='/',
        )
        return stream_response

    if client_session_id is not None:
        try:
            return run_agent_pipeline(query, client_session_id)
        except Exception as e:
            return Answer(answer='Sorry, I hit a snag and couldn\'t answer your question.',sources=[])

    new_session_id = generate_session_id()
    try:
        answer = run_agent_pipeline(query, new_session_id)
    except Exception as e:
        return Answer(answer='Sorry, I hit a snag and couldn\'t answer your question.',sources=[])

    response.set_cookie(
        key='kubebot_session_id',
        value=new_session_id,
        httponly=True,
        secure=True,
        samesite='lax',
        path='/',
    )
    return answer
