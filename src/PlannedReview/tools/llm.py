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
from typing import Any

from tools import db
from tools import file_tools


from dotenv import load_dotenv
load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')


@dataclass
class AgentDeps:
    query_engine: BaseQueryEngine
    pdf_path: Path

def setup_llms(llm_config: dict) -> Agent:

    llm_config = inject_local_env_keys(llm_config)

    model = setup_chat_llm(llm_config['chat'])         
    setup_embedding_llm(llm_config['embed'])

    agent = Agent(model,
                  deps_type=AgentDeps,
                  tools=[db.rag_db, 
                         file_tools.retreive_file,
                         file_tools.write_json,
                         ],
                   model_settings={'timeout': 60.0*60*24},
                   tool_timeout=600,
                   max_concurrency=2,
            )

    return agent

def setup_chat_llm(llm_chat_config: dict) -> Any:
    if llm_chat_config['local']:
        Settings.llm = OpenAILike(
                        model=llm_chat_config['model'],
                        api_base=llm_chat_config['address'],
                        api_key=llm_chat_config['api_key'],
                        is_function_calling_mode=True,
                        is_chat_model=True,
                        timeout=60.0*60*24,
                        max_concurrency=2,
                    )
        provider = OpenAIProvider(base_url = llm_chat_config['address'])
        model = OpenAIResponsesModel(model_name = llm_chat_config['model'], provider=provider)

    elif llm_chat_config['provider'] == 'google':
        Settings.llm = GoogleGenAI(
                model="gemini-3.6-flash",
                api_key=llm_chat_config['api_key'],
        )
        
        provider = GoogleProvider(api_key=llm_chat_config['api_key'])
        model = GoogleModel('gemini-3.6-flash', provider=provider)

    # TODO: add other providers here as needed

    return model

def setup_embedding_llm(llm_embed_config: dict):

    if llm_embed_config['local']:
        Settings.embed_model = OpenAILikeEmbedding(
            model_name=llm_embed_config['model'],
            api_base=llm_embed_config['address'],
            api_key=llm_embed_config['api_key'],
            embed_batch_size=32,
            timeout=120.0,
        )
    elif llm_embed_config['provider'] == 'google':
        Settings.embed_model = GoogleGenAIEmbedding(
            model_name=llm_embed_config['model'],
            api_key=llm_embed_config['api_key'],
            embed_batch_size=32,
            timeout=120.0,
        )
    # TODO: add other providers here as needed

def inject_local_env_keys(config: dict) -> dict:
    if config['chat']['local']:
        pass  # No action needed for local chat model
    elif config['chat']['provider'] == 'google':
        if os.getenv('GEMINI_API_KEY'):
            logging.info("Using API key from config for Google chat model.")
            config['chat']['api_key'] = os.getenv('GEMINI_API_KEY')
    elif config['chat']['provider'] == 'openai':
        if os.getenv('OPENAI_API_KEY'):
            logging.info("Using API key from config for OpenAI chat model.")
            config['chat']['api_key'] = os.getenv('OPENAI_API_KEY')

    if config['embed']['local']:
        pass  # No action needed for local embedding model
    elif config['embed']['provider'] == 'google':
        if os.getenv('GEMINI_API_KEY'):
            logging.info("Using API key from config for Google embedding model.")
            config['embed']['api_key'] = os.getenv('GEMINI_API_KEY')
    elif config['embed']['provider'] == 'openai':
        if os.getenv('OPENAI_API_KEY'):
            logging.info("Using API key from config for OpenAI embedding model.")
            config['embed']['api_key'] = os.getenv('OPENAI_API_KEY')

    return config