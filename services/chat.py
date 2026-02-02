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

def run_agent_pipeline(query: UserQuery)->Answer | None:
    user_prompt: str = make_agent_prompt(query, tools)

    response = agent.invoke(
        {'messages':
            [
                {'role':'user', 'content': user_prompt}
            ]
        }
    )
    print(response)
    if not response.get('messages'):
        return None
    ai_messages = list(filter(lambda m:isinstance(m,AIMessage),response['messages']))
    if not ai_messages:
        return None
    if not ai_messages[-1].text:
        return None
    return Answer(answer=ai_messages[-1].text, sources=collect_sources(response))
