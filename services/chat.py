from typing import TYPE_CHECKING, Iterable, TypeVar, get_origin, get_args
from models import UserQuery, Source, Answer
from langchain.messages import AIMessage, ToolMessage
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from .db import search_db, map_source
from .memory import generate_session_id
from prompts import make_grounding_prompt, make_agent_prompt
from tools import search_tools
from ordered_set import OrderedSet

T = TypeVar('T')

if TYPE_CHECKING:
    from langchain.chat_models import BaseChatModel
    from langgraph.graph.state import CompiledStateGraph

tools = [*search_tools.values()]
search_tool_names = list(search_tools.keys())
model: "BaseChatModel | None" = None
agent: "CompiledStateGraph | None" = None

def init_agents(checkpointer):
    """Initialize agents with the given checkpointer. Called from app lifespan."""
    global model, agent
    model = init_chat_model("openai:gpt-5.2")
    agent = create_agent("openai:gpt-5.2", 
                         tools=tools,
                         checkpointer=checkpointer)

def run_chat_only_pipeline(query: UserQuery, session_id: str | None)->tuple[Answer | None, str]:
    if not session_id:
        session_id = generate_session_id()
    
    assert model is not None, "Agents not initialized. Call init_agents() first."

    db_results: list[Source] = search_db(query)
    if not db_results:
        return Answer(answer='Oh fuck!',sources=[]), session_id
    
    prompts: dict[str,str] = make_grounding_prompt(db_results,query)

    response = model.invoke(
        [
            {'role':'system','content':prompts['system']},
            {'role':'user','content':prompts['user']}
        ],
        config = {'configurable':{'thread_id': session_id}}
    )

    if not response.text:
        return None, session_id
    return Answer(answer=response.text, sources=db_results), session_id

def ensure_type(obj, expected_type) -> bool:
    """Check if obj matches expected_type, supporting generics like list[Source]."""
    origin = get_origin(expected_type)
    
    if origin is None:
        # Not a generic type, use regular isinstance
        return isinstance(obj, expected_type)
    
    # Check the container type first
    if not isinstance(obj, origin):
        return False
    
    args = get_args(expected_type)
    if not args:
        return True
    
    # For list[T], check all elements
    if origin is list:
        return all(ensure_type(item, args[0]) for item in obj)
    
    # For dict[K, V], check keys and values
    if origin is dict:
        return all(
            ensure_type(k, args[0]) and ensure_type(v, args[1])
            for k, v in obj.items()
        )
    
    # For other generics, just check the container
    return True

def flatten_list_of_lists(list_of_lists:list[list[T]])->list[T]:
    flattened: list[T] = [
        v for l in list_of_lists for v in l
    ]
    return flattened

def to_source(item) -> Source:
    """Convert item to Source - handles both Source instances and dicts."""
    if isinstance(item, Source):
        return item
    if isinstance(item, dict):
        return Source.model_validate(item)
    raise ValueError(f"Cannot convert {type(item)} to Source")

def collect_sources(response: dict)->OrderedSet[Source]:
    messages = response.get('messages',[])
    tool_messages: Iterable[ToolMessage] = filter(lambda m:isinstance(m, ToolMessage), messages)
    search_tool_results: Iterable[ToolMessage] = filter(lambda tm:tm.name in search_tool_names,tool_messages)
    search_tool_artifacts = [stm.artifact for stm in search_tool_results if stm.artifact is not None]
    if not search_tool_artifacts:
        return OrderedSet([])
    
    # Convert dicts to Source instances (artifacts may be serialized as dicts in history)
    search_tool_contents: list[list[Source]] = [
        [to_source(item) for item in artifact] 
        for artifact in search_tool_artifacts
    ]
    
    if not ensure_type(search_tool_contents, list[list[Source]]):
        raise ValueError(f"Search tool contents not verifiable as list of list `Source`s:{str(search_tool_contents)}")
    
    sources = flatten_list_of_lists(search_tool_contents)
    if not ensure_type(sources, list[Source]):
        raise ValueError(f"Sources not verifiable as list of `Sources`s:{str(sources)}")

    return OrderedSet(sources)

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
        },
        config = {'configurable':{'thread_id': session_id}}
    )
    
    answer_text = extract_ai_response(response)
    if not answer_text:
        return None, session_id

    return Answer(answer=answer_text, sources=collect_sources(response)), session_id
