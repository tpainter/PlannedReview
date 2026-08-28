import logging

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
import json

from tools import llm


def vectorStore(temp_dir_path: str, pdf_name: str) -> BaseQueryEngine:
    """
    
    """
    # clean special characters from pdf name to use as collection name
    pdf_collection = "".join(char for char in pdf_name if char.isalnum())

    chroma_client = chromadb.PersistentClient(path='./data/chroma_db')
    #check if vectors are already in db for pdf
    try:
        chroma_collection = chroma_client.get_collection(pdf_collection)
        collection_exists = True
        logging.info(f"Found existing collection({pdf_collection}). Skipping re-embedding...")
    except:
        chroma_collection = chroma_client.get_or_create_collection(pdf_collection)
        collection_exists = False
        logging.info(f"Existing collection({pdf_collection}) not found.")
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

        logging.info(f"Parsing documents with Docling: {temp_dir_path}...")
        documents = dir_reader.load_data()

        node_parser = DoclingNodeParser()
        nodes = node_parser.get_nodes_from_documents(documents)

        #Clean up error from VectorStor where it can't use a list in the node.metadata       
        for n in nodes:
            for k in n.metadata:
                n.metadata[k] = json.dumps(n.metadata[k])

                
        index = VectorStoreIndex(
            nodes=nodes, 
            storage_context=storage_context, 
            embed_model=Settings.embed_model,
            )

        logging.info("LlamaIndex vector store complete.")

    query_engine = index.as_query_engine(
            similarity_top_k=5,
            response_mode="compact",  # you can also select other modes like `compact`, `refine`, 'tree_summarize'
        )

    return query_engine


def fusionStore(temp_dir_path: str, pdf_name: str) -> RetrieverQueryEngine:
    """Combined vector store and BM25 retreiver.    
    """

    # clean special characters from pdf name to use as collection name
    pdf_collection = "".join(char for char in pdf_name if char.isalnum())
    chroma_client = chromadb.PersistentClient(path='./data/chroma_db')
    #check if vectors are already in db for pdf
    try:
        chroma_collection = chroma_client.get_collection(pdf_collection)
        collection_exists = True
        logging.info(f"Found existing collection({pdf_collection}). Skipping re-embedding...")
    except:
        chroma_collection = chroma_client.get_or_create_collection(pdf_collection)
        collection_exists = False
        logging.info(f"Existing collection({pdf_collection}) not found.")
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


def rag_db(ctx: RunContext[llm.AgentDeps], query: str) -> ToolReturn:
    """Database to query for information from the pdf documents.

    Args:
        query: the query string to send to the database
    """
    logging.debug(f"Query: {query}")
    response = ctx.deps.query_engine.query(query)
    logging.debug(f"Response: {response}")
    
    return ToolReturn(
        return_value= [str(response)],
    )