from models import UserQuery, Source, Answer
from langchain.messages import AIMessage
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from .db import search_db
from prompts import make_grounding_prompt, make_agent_prompt
from tools import search_tools

model = init_chat_model("openai:gpt-5.2")

tools = [*search_tools]
agent = create_agent("openai:gpt-5.2", tools=tools)

def run_chat_only_pipeline(query: UserQuery)->Answer | None:
    db_results: list[Source] = search_db(query)
    if not db_results:
        return Answer(answer='Oh fuck!',sources=[])
    
    prompts: dict[str,str] = make_grounding_prompt(db_results,query)

    response = model.invoke(
        [
            {'role':'system','content':prompts['system']},
            {'role':'user','content':prompts['user']}
        ]
    )

    if not response.text:
        return None
    return Answer(answer=response.text, sources=db_results)

def collect_sources(response)->list[Source]:
    # TODO: Extract Source objects from agent/tool calls in `response`,
    #       e.g., by parsing tool invocation results and mapping them to
    #       instances of `Source`. For now, this returns an empty list.
    return []

def get_last_ai_message(messages: list) -> AIMessage | None:
    """Get the last AI message from a list of messages."""
    ai_messages = [m for m in messages if isinstance(m, AIMessage)]
    return ai_messages[-1] if ai_messages else None

def extract_ai_response(response: dict) -> str | None:
    """Extract final AI message text from agent response."""
    messages = response.get('messages', [])
    last_ai = get_last_ai_message(messages)
    return last_ai.text if last_ai else None

def run_agent_pipeline(query: UserQuery, session_id: str | None)->tuple[Answer | None, str]:
    if not session_id:
        session_id = generate_session_id()

    assert agent is not None, "Agents not initialized. Call init_agents() first."
    
    user_prompt: str = make_agent_prompt(query, tools)

    response = agent.invoke(
        {'messages':
            [
                {'role':'user', 'content': user_prompt}
            ]
        }
    )
    print(response)
    
    answer_text = extract_ai_response(response)
    if not answer_text:
        return None, session_id

    return Answer(answer=answer_text, sources=collect_sources(response)), session_id
