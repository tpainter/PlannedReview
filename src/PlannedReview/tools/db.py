import chromadb
from llama_index.core import VectorStoreIndex, Settings
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import StorageContext
from llama_index.readers.docling import DoclingReader
from llama_index.core import SimpleDirectoryReader
from pydantic_ai import Agent, RunContext
from pydantic import BaseModel, Field
from typing import List

from dataclasses import dataclass
from llama_index.core.query_engine import BaseQueryEngine

def vectorStore(temp_dir_path: str, pdf_name: str):
    """
    
    """

    chroma_client = chromadb.PersistentClient(path='./data/chroma_db')
    #check if vectors are already in db for pdf
    try:
        chroma_collection = chroma_client.get_collection("pdf_name")
        collection_exists = True
        print("Found existing collection. Skipping re-embedding...")
    except:
        chroma_collection = chroma_client.get_or_create_collection("pdf_name")
        collection_exists = False
        print("Existing collection not found.")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    if collection_exists:
        index = VectorStoreIndex.from_vector_store(
            vector_store, 
            embed_model=Settings.embed_model,)        
    else:
        # Initialize the Docling reader and load the document
        reader = DoclingReader(export_type=DoclingReader.ExportType.JSON)       
        dir_reader = SimpleDirectoryReader(
            input_dir=temp_dir_path,
            file_extractor={".pdf": reader},
            filename_as_id=True,
        )

        print(f"Parsing documents with Docling: {temp_dir_path}...")
        documents = dir_reader.load_data(temp_dir_path)
        index = VectorStoreIndex.from_documents(
            documents, storage_context=storage_context, embed_model=Settings.embed_model
        )

        print("LlamaIndex vector store complete.")

    return index

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

@dataclass
class AgentDeps:
    query_engine: BaseQueryEngine


def rag_db(ctx: RunContext[AgentDeps], query: str) -> str:
    """Database to query for information from the pdf documents.

    Args:
        query: the query string to send to the database
    """
    print(f"Query: {query}")
    response = ctx.deps.query_engine.query(query)
    
    return str(response)