from models import Source, UserQuery

GROUNDING_PROMPT = """
You will be given a piece of source information from the Kubernetes documentation and a user query.
You must answer from the provided documentation only. Ground your answer to the provided documentation.
Answer the user query with respect only to the Kubernetes documentation.
"""

SOURCE_PROMPT = """
Kubernetes Documentation relevant to the user query:
{relevant_info}

The User Query itself:
{query}
"""

def make_grounding_prompt(docs: list[Source], query: UserQuery):
    relevant_info = '\n'.join((f"{doc.title} says: {doc.relevant_info}" for doc in docs))
    return {'system':GROUNDING_PROMPT,'user':SOURCE_PROMPT.format(relevant_info=relevant_info,query=query.question)}