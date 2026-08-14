import chromadb
from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.core.query_engine import BaseQueryEngine
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core import SimpleDirectoryReader
from llama_index.core.storage.docstore import SimpleDocumentStore
#from llama_index.retrievers.bm25 import BM25Retriever
import Stemmer
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.readers.docling import DoclingReader
from llama_index.node_parser.docling import DoclingNodeParser


from pydantic_ai import Agent, RunContext, ToolReturn
from pydantic import BaseModel, Field
from typing import List

from dataclasses import dataclass


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

    query_engine = index.as_query_engine(
            similarity_top_k=5,
            response_mode="compact",  # you can also select other modes like `compact`, `refine`, 'tree_summarize'
        )

    return query_engine


def fusionStore(temp_dir_path: str, pdf_name: str):
    """Combined vector store and BM25 retreiver.    
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
    storage_context = StorageContext.from_defaults(docstore=docstore, vector_store=vector_store)

    if collection_exists:
        index = VectorStoreIndex(
            nodes=nodes, #TODO: get nodes from DB
            storage_context=storage_context, 
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

        node_parser = DoclingNodeParser()
        nodes = node_parser.get_nodes_from_documents(documents=documents)
        docstore = SimpleDocumentStore()
        docstore.add_documents(nodes)

        index = VectorStoreIndex(
            nodes=nodes, storage_context=storage_context, embed_model=Settings.embed_model
        )        

        print("LlamaIndex vector store complete.")

    retriever = QueryFusionRetriever(
        [
            index.as_retriever(similarity_top_k=2),
            BM25Retriever.from_defaults(
                docstore=index.docstore, similarity_top_k=2
            ),
        ],
        num_queries=1,
        use_async=False,
    )

    return RetrieverQueryEngine(retriever)

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
    print(f"Response: {response}")
    
    return ToolReturn(
        return_value= [str(response)],
    )