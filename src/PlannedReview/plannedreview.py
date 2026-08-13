import os
from typing import Annotated, Sequence, TypedDict

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
from tools.llm import AgentDeps




def main():
    # Provide a pdf document
    pdf_name = "OhioCounty.pdf"
    pdf_path = "data/" + pdf_name 
    
    # 0. Split PDF
    pages_dir = file_tools.pdf_split_pages(pdf_path)
    
    # 1. Setup llms
    llm_location = 'local' # local, google
    agent = llm.setup_llms(llm_location)

    query_engine = db.vectorStore(pages_dir, pdf_name)   
    #query_engine = db.fusionStore(pages_dir, pdf_name) 

    # 3. Run the query
    deps = AgentDeps(query_engine=query_engine)
                     
    user_prompt = "Summarize the file OhioCounty_page_7.pdf"
    result = agent.run_sync(user_prompt, deps=deps)
    print("Agent Response:")
    print(result.output)

if __name__ == "__main__":
    main()
