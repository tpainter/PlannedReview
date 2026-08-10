import os
import asyncio
from typing import Annotated, Sequence, TypedDict

from dotenv import load_dotenv
load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

import logging
# Limit the spam from logging INFO messages
#logging.basicConfig()
#logging.getLogger().setLevel(logging.WARNING)

# LlamaIndex & Docling Imports
from llama_index.core import VectorStoreIndex, Settings
from llama_index.core.query_engine import BaseQueryEngine

from llama_index.core.agent import FunctionAgent
from llama_index.llms.openai import OpenAI
from llama_index.llms.openai_like import OpenAILike
from llama_index.embeddings.openai_like import OpenAILikeEmbedding
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider

# Pydantic Imports
from pydantic_ai import Agent, FunctionToolset
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic import BaseModel, Field
from typing import List

from dataclasses import dataclass


# plannedreview imports
from tools import db, file_tools, llm



# ==========================================
# 1. DOCLING + LLAMAINDEX: Ingest & Index
# ==========================================
def setup_llms():
    
    
    # Configure LlamaIndex to use Google Gemini
    '''
    Settings.llm = GoogleGenAI(
        model="gemini-3.6-flash",
        api_key=GEMINI_API_KEY,
    )

    '''
    Settings.llm = OpenAILike(
        model="gemma4-26b",
        api_base="http://192.168.0.50:8080/v1",
        api_key="fake",
        is_function_calling_mode=True,
        is_chat_model=True,
        timeout=600.0,
    )
    
    
    Settings.embed_model = OpenAILikeEmbedding(
        model_name="gemma-embedding",
        api_base="http://192.168.0.50:8080/v1",
        api_key="fake",
        embed_batch_size=32,
        timeout=60.0,
    )

class Output(BaseModel):
    """Output containing the response, page numbers, and confidence."""

    response: str = Field(..., description="The answer to the question.")
    page_numbers: List[int] = Field(
        ...,
        description="The page numbers of the sources used to answer this question. Do not include a page number if the context is irrelevant.",
    )
    confidence: float = Field(
        ...,
        description="Confidence value between 0-1 of the correctness of the result.",
    )
    confidence_explanation: str = Field(
        ..., description="Explanation for the confidence score"
    )

def main():
    # Provide a pdf document
    pdf_name = "OhioCounty.pdf"
    pdf_path = "data/" + pdf_name 
    
    # 0. Split PDF
    pages_dir = file_tools.pdf_split_pages(pdf_path)
    
    # 1. Setup llms
    setup_llms()

    index = db.vectorStore(pages_dir, pdf_name)

    @dataclass
    class AgentDeps:
        query_engine: BaseQueryEngine


    llm_location = 'local'
    if llm_location == 'google':
        provider = GoogleProvider(api_key=GEMINI_API_KEY)
        model = GoogleModel('gemini-3.6-flash', provider=provider)
    if llm_location == 'local':
        provider = OpenAIProvider(base_url = "http://192.168.0.50:8080/v1")
        model = OpenAIResponsesModel(model_name = "gemma4-26b", provider=provider)
    agent = Agent(model,
                  deps_type=AgentDeps,
                  tools=[db.rag_db],
            )
    
    # 2. Setup Query Engine
    query_engine = index.as_query_engine(
        similarity_top_k=5,
        response_mode="tree_summarize",  # you can also select other modes like `compact`, `refine`
    )

    # 3. Run the query
    deps = AgentDeps(query_engine=query_engine)
                     
    user_prompt = "What sheet are the general notes found on? What is the file name in the database?"
    result = agent.run_sync(user_prompt, deps=deps)
    print("Agent Response:")
    print(result.output)

if __name__ == "__main__":
    main()
