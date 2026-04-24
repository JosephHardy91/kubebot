from __future__ import annotations
import asyncio
import json
from typing import Dict

try:
    import httpx
except ImportError:
    raise ImportError("Please install httpx with 'pip install httpx' ")


from textual import getters, work, on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll, Horizontal, Center
from textual.widgets import Input, Markdown, Static, LoadingIndicator
from textual.widget import Widget
from textual.reactive import reactive

from tui_types import KubebotSessionInfo
from rich_pixels import Pixels

from PIL import Image
from rich.spinner import Spinner


import secrets
from pathlib import Path

# Get the directory of the current script
SCRIPT_DIR = Path(__file__).parent.absolute()

# Construct the full path to your image
LOGO_PATH = SCRIPT_DIR / "kube_small.png"

# class WheelSpinner(Widget):
#     angle = reactive(0.0)

#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)
#         try:
#             # Load in __init__ so it is ready BEFORE the first render() call
#             self.base_image = Image.open(LOGO_PATH).convert("RGBA")
#             self.base_image = self.base_image.resize((32,32),resample=Image.Resampling.LANCZOS)
#         except Exception:
#             self.base_image = None

#     def on_mount(self) -> None:
#         # 20fps is smooth enough for TUI spinners
#         self.set_interval(0.05, self.rotate_logo)

#     def rotate_logo(self) -> None:
#         self.angle = (self.angle + 10) % 360

#     def render(self) -> Pixels | str:
#         if self.base_image is None:
#             return "Logo missing"
            
#         rotated_image = self.base_image.rotate(-self.angle, resample=Image.Resampling.NEAREST)
#         return Pixels.from_image(rotated_image)


from rich.spinner import Spinner
from textual.widget import Widget

class WheelSpinner(Widget):
    def on_mount(self) -> None:
        # Create the spinner once and store it
        self.spinner = Spinner("dots12", style="cyan")
        # Refresh the widget 10-20 times per second for smooth animation
        self.set_interval(0.1, self.refresh)

    def render(self) -> Spinner:
        # Return the same spinner instance so it can advance its frames
        return self.spinner



class KubebotApp(App):
    """Queries kubebot and displays results/sources."""

    CSS_PATH = "tui.tcss"
    BASE_URL = 'http://localhost:8000'
    STREAM_REVEAL_INTERVAL_SECONDS = 0.02
    STREAM_REVEAL_CHARS_PER_TICK = 1
    BINDINGS = [
        Binding('up','move_up','Move Up'),
        Binding('down','move_down','Move Down'),
        Binding('left','move_left','Move Left')
    ]

    source_list = []
    source_cache = {}
    sources_markdown = []
    qa_list = []
    qa_markdown = []
    qa_list_pos = 0

    qas = getters.query_one("#qas", Markdown)
    sources = getters.query_one('#sources',Static)
    query_input = getters.query_one(Input)
    loading_indicator = getters.query_one('#loading-wheel',WheelSpinner)
    
    #kubebot info
    current_session_details = KubebotSessionInfo(
        session_id=secrets.token_urlsafe(32)
    )

    def compose(self) -> ComposeResult:
        with Horizontal():
            with VerticalScroll(id="qas-container"):
                yield Markdown(id="qas")
                with Center(id='loading-wheel-container'):
                    yield WheelSpinner(id='loading-wheel')
            with VerticalScroll(id="sources-container"):
                yield Static(id="sources")
        yield Input(placeholder="Enter query >", id="kubebot-query")

    def on_mount(self) -> None:
        self.loading_indicator.display = False
        session_id = self.current_session_details.session_id
        assert session_id is not None
        self._http_client = httpx.AsyncClient(
            cookies={'kubebot_session_id': session_id}
        )

    def action_move_up(self)->None:
        self.qa_list_pos = max(0,self.qa_list_pos-1)
        self.panes_refresh()
    
    def action_move_down(self)->None:
        self.qa_list_pos = min(len(self.qa_list)-1,self.qa_list_pos + 1)
        self.panes_refresh()
    
    def action_move_left(self)->None:
        self.panes_refresh()

    def panes_refresh(self):
        self.qas.update(self.qa_markdown[self.qa_list_pos])
        self.sources.update(self.sources_markdown[self.qa_list_pos])

    def update_streamed_answer(self, query: str, answer: str) -> None:
        self.qa_list[self.qa_list_pos][1] = answer
        self.qa_markdown[self.qa_list_pos] = f'## You:\n{query}\n\n## KubeBot:\n{answer}'
        self.panes_refresh()

    def take_stream_reveal_chunk(self, pending_text: str) -> tuple[str, str]:
        if len(pending_text) <= self.STREAM_REVEAL_CHARS_PER_TICK:
            return pending_text, ''

        split_at = self.STREAM_REVEAL_CHARS_PER_TICK
        return pending_text[:split_at], pending_text[split_at:]

    async def pump_streamed_markdown(
        self,
        markdown_stream,
        streamed_answer_parts: list[str],
        pending_text: list[str],
        stream_complete: list[bool],
    ) -> None:
        while pending_text[0] or not stream_complete[0]:
            if pending_text[0]:
                next_chunk, remaining_text = self.take_stream_reveal_chunk(pending_text[0])
                pending_text[0] = remaining_text
                streamed_answer_parts.append(next_chunk)
                await markdown_stream.write(next_chunk)

            await asyncio.sleep(self.STREAM_REVEAL_INTERVAL_SECONDS)

    @on(Input.Submitted)
    async def on_input(self, event: Input.Submitted) -> None:
        """A coroutine to handle a user query."""
        event.input.clear()
        if event.value:
            self.handle_query(event.value)

    @work(exclusive=True)
    async def handle_query(self, query:str)->None:
        self.loading_indicator.display = True
        self.add_qa(query, "")
        self.add_sources([])
        self.qas.update(f'## You:\n{query}\n\n## KubeBot:\n')
        self.sources.update(self.sources_markdown[self.qa_list_pos])
        markdown_stream = None
        try:
            url = f"{self.BASE_URL}/ask"
            streamed_answer_parts: list[str] = []
            pending_text = ['']
            stream_complete = [False]
            markdown_stream = Markdown.get_stream(self.qas)
            pump_task = asyncio.create_task(
                self.pump_streamed_markdown(
                    markdown_stream,
                    streamed_answer_parts,
                    pending_text,
                    stream_complete,
                )
            )
            async with self._http_client.stream('POST', url, timeout=30, json={
                'question': query,
                'streaming': True,
            }) as response:
                async for line in response.aiter_lines():
                    if not line:
                        continue

                    event = json.loads(line)
                    event_type = event.get('type')

                    if event_type == 'chunk':
                        pending_text[0] += event.get('content', '')
                        continue

                    if event_type == 'final':
                        stream_complete[0] = True
                        await pump_task
                        await markdown_stream.stop()
                        answer_payload = event.get('answer', {})
                        answer = answer_payload.get('answer', ''.join(streamed_answer_parts))
                        sources = answer_payload.get('sources', [])
                        self.update_streamed_answer(query, answer)
                        self.source_list[self.qa_list_pos] = sources
                        self.sources_markdown[self.qa_list_pos] = '\n\n'.join(
                            '[@click=app.get_source_info("{}")]{}/[@click=]'.format(source.get('doc_path',''),source.get('doc_path',''))
                            for source in sources
                        )
                        self.cache_sources(sources)
                        self.panes_refresh()
                        continue

                    if event_type == 'error':
                        stream_complete[0] = True
                        await pump_task
                        await markdown_stream.stop()
                        error_message = event.get('content', 'Sorry, had trouble getting the answer to you. Try again later.')
                        self.update_streamed_answer(query, error_message)
                        break
        except:
            if markdown_stream is not None:
                await markdown_stream.stop()
            self.qas.update("Sorry, had trouble getting the answer to you. Try again later.")
        self.loading_indicator.display = False

    def action_get_source_info(self,doc_path):
        source_info = self.source_cache.get(doc_path)
        if source_info:
            self.qas.update(f'```text\n{source_info}\n```')

    def add_qa(self,query:str,answer:str):
        self.qa_list.append(
            [query,answer]
        )
        self.qa_markdown.append(
            f'## You:\n{query}\n\n## KubeBot:\n{answer}'
        )
        self.qa_list_pos = len(self.qa_list)-1

    def add_sources(self,sources:list[Dict[str,str]]):
        self.cache_sources(sources)
        self.source_list.append(
            sources
        )
        self.sources_markdown.append(
            '\n\n'.join(
                '[@click=app.get_source_info("{}")]{}[/@click=]'.format(source.get('doc_path',''),source.get('doc_path',''))
                for source in
                sources
            )
        )

    def cache_sources(self,sources:list[Dict[str,str]]):
        for source in sources:
            key = source.get('doc_path')
            if not key: continue
            if key in self.source_cache:continue
            content = source.get('relevant_info')
            if not content:continue
            self.source_cache[key] = content
            

if __name__ == "__main__":
    app = KubebotApp()
    app.run()