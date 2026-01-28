from models import UserQuery, Source, Answer
from langchain.chat_models import init_chat_model
from .db import search_db
from prompts import make_grounding_prompt

model = init_chat_model("openai:gpt-5.2")

def run_pipeline(query: UserQuery)->Answer | None:
    db_results: list[Source] = search_db(query)
    if not db_results:
        return Answer(answer='Oh fuck!',sources=[])
    
    prompts = make_grounding_prompt(db_results,query)

    response = model.invoke(
        [
            {'role':'system','content':prompts['system']},
            {'role':'user','content':prompts['user']}
        ]
    )

    if not response.text:
        return None
    return Answer(answer=response.text, sources=db_results)