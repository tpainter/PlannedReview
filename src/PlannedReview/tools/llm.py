import os
import logging
from pathlib import Path

from llama_index.core import Settings

from llama_index.llms.openai import OpenAI
from llama_index.llms.openai_like import OpenAILike
from llama_index.embeddings.openai_like import OpenAILikeEmbedding
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider
from llama_index.core.query_engine import BaseQueryEngine

from pydantic_ai import Agent, ConcurrencyLimit
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from dataclasses import dataclass

from tools import db
from tools import file_tools


from dotenv import load_dotenv
load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')


@dataclass
class AgentDeps:
    query_engine: BaseQueryEngine
    pdf_path: Path

def setup_llms(llm_location):
    
    if llm_location == 'google':
        Settings.llm = GoogleGenAI(
                model="gemini-3.6-flash",
                api_key=GEMINI_API_KEY,
        )
        
        provider = GoogleProvider(api_key=GEMINI_API_KEY)
        model = GoogleModel('gemini-3.6-flash', provider=provider)
    if llm_location == 'local':
        Settings.llm = OpenAILike(
                model="muse",
                api_base="http://192.168.0.50:8080/v1",
                api_key="fake",
                is_function_calling_mode=True,
                is_chat_model=True,
                timeout=7200.0,
                max_concurrency=2,
            )
        
        provider = OpenAIProvider(base_url = "http://192.168.0.50:8080/v1")
        model = OpenAIResponsesModel(model_name = "muse", provider=provider)

    agent = Agent(model,
                  deps_type=AgentDeps,
                  tools=[db.rag_db, 
                         file_tools.retreive_file,
                         ],
                   model_settings={'timeout': 3600},
                   tool_timeout=600,
                   max_concurrency=2,
            )

    Settings.embed_model = OpenAILikeEmbedding(
        model_name="gemma-embedding",
        api_base="http://192.168.0.50:8080/v1",
        api_key="fake",
        embed_batch_size=32,
        timeout=120.0,
    )

    return agent