from __future__ import annotations

try:
    import httpx
except ImportError:
    raise ImportError("Please install httpx with 'pip install httpx' ")


from textual import getters, work, on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll, Horizontal
from textual.widgets import Input, Markdown
from tui_types import KubebotSessionInfo
from typing import Dict

import secrets


class KubebotApp(App):
    """Queries kubebot and displays results/sources."""

    CSS_PATH = "tui.tcss"
    BASE_URL = 'http://localhost:8000'
    BINDINGS = [
        Binding('up','move_up','Move Up'),
        Binding('down','move_down','Move Down')
    ]

    source_list = []
    sources_markdown = []
    qa_list = []
    qa_markdown = []
    qa_list_pos = 0

    qas = getters.query_one("#qas", Markdown)
    sources = getters.query_one('#sources',Markdown)
    query_input = getters.query_one(Input)
    
    #kubebot info
    current_session_details = KubebotSessionInfo(
        session_id=secrets.token_urlsafe(32)
    )

    def compose(self) -> ComposeResult:
        with Horizontal():
            with VerticalScroll(id="qas-container"):
                yield Markdown(id="qas")
            with VerticalScroll(id="sources-container"):
                yield Markdown(id="sources")
        yield Input(placeholder="Enter query >", id="kubebot-query")

    def action_move_up(self)->None:
        self.qa_list_pos = max(0,self.qa_list_pos-1)
        self.panes_refresh()
    
    def action_move_down(self)->None:
        self.qa_list_pos = min(len(self.qa_list)-1,self.qa_list_pos + 1)
        self.panes_refresh()

    def panes_refresh(self):
        self.qas.update(self.qa_markdown[self.qa_list_pos])
        self.sources.update(self.sources_markdown[self.qa_list_pos])

    @on(Input.Submitted)
    async def on_input(self, event: Input.Submitted) -> None:
        """A coroutine to handle a user query."""
        event.input.clear()
        if event.value:
            self.handle_query(event.value)

    @work(exclusive=True)
    async def handle_query(self, query:str)->None:
        url = f"{self.BASE_URL}/ask"
        async with httpx.AsyncClient() as client:
            response = (await client.post(url,timeout=30,json={
                'question':query,
                'kubebot_session_id':self.current_session_details.session_id
            })).json()
            if 'answer' not in response:
                self.qas.update(str(response))
            else:
                answer = response['answer']
                sources = response['sources']
                self.add_qa(query,answer)
                self.add_sources(sources)
                self.panes_refresh()

    def add_qa(self,query:str,answer:str):
        self.qa_list.append(
            [query,answer]
        )
        self.qa_markdown.append(
            f'# You: {query}\n\n\n# KubeBot: {answer}'
        )
        self.qa_list_pos = len(self.qa_list)-1

    def add_sources(self,sources:list[Dict[str,str]]):
        self.source_list.append(
            sources
        )
        self.sources_markdown.append(
            '\n\n'.join(
                source.get('doc_path','')
                for source in
                sources
            )
        )

if __name__ == "__main__":
    app = KubebotApp()
    app.run()