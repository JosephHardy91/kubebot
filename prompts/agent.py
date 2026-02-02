from models import UserQuery

AGENTIC_PROMPT = '''
You must use tools to answer this user query. Ground your answer solely to the information you find with the tools.

Answer the user query using only information you find with available tools.

This is the list of your tools:
{tools}

This is the user query:
{query}
'''

def make_agent_prompt(query: UserQuery, tools: list)->str:
    tool_strings = ''
    for tool in tools:
        tool_strings += f'{tool.name}: {tool.description}\n'
    return AGENTIC_PROMPT.format(query=query.question,tools=tool_strings)