import os
from typing import Annotated, Sequence, TypedDict

from dotenv import load_dotenv
load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

import logging
# Limit the spam from logging INFO messages
logging.basicConfig()
logging.getLogger().setLevel(logging.WARNING)

# LlamaIndex & Docling Imports
from llama_index.core import VectorStoreIndex, Settings

from llama_index.core.agent import FunctionAgent
from llama_index.llms.openai_like import OpenAILike
from llama_index.embeddings.openai_like import OpenAILikeEmbedding
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding

# Pydantic Imports
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from typing import List

# plannedreview imports
from tools import db, file_tools, llm



# ==========================================
# 1. DOCLING + LLAMAINDEX: Ingest & Index
# ==========================================
def setup_llms():
    
    
    # Configure LlamaIndex to use Google Gemini
    
    Settings.llm = GoogleGenAI(
        model="gemini-3.6-flash",
        api_key=GEMINI_API_KEY,
    )
    # TODO: local model calls have an error when used.
    '''
    Settings.llm = OpenAILike(
        model_name="qwen3.6-27B",
        api_base="http://192.168.0.50:8080/v1",
        api_key="fake",
        is_function_calling_mode=True,
        is_chat_model=True,
        timeout=60.0,
    )
    '''
    
    Settings.embed_model = OpenAILikeEmbedding(
        model_name="gemma-embedding",
        api_base="http://192.168.0.50:8080/v1",
        #api_base="http://localhost:8080/v1",
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
    pdf_path = "data/OhioCounty.pdf" 
    
    # 0. Split PDF
    pages_dir = file_tools.pdf_split_pages(pdf_path)
    
    # 1. Setup llms
    setup_llms()
    sllm = Settings.llm.as_structured_llm(output_cls=Output)

    index = db.vectorStore(pages_dir)
    
    # 2. Setup Query Engine
    query_engine = index.as_query_engine(
        similarity_top_k=5,
        llm=sllm,
        response_mode="tree_summarize",  # you can also select other modes like `compact`, `refine`
    )

    # 3. Run the query
    user_query = "What is file name of the sheet where the general notes are located?"

    response = query_engine.query(user_query)
    print(str(response))

if __name__ == "__main__":
    main()
