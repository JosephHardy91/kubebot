import dagster as dg
from langchain_openai import OpenAIEmbeddings

class EmbeddingsResource(dg.ConfigurableResource):
    api_key: str
    model: str = "text-embedding-3-small"

    def get_client(self) -> OpenAIEmbeddings:
        return OpenAIEmbeddings(
            api_key=self.api_key,
            model=self.model
        )