import os
from typing import Annotated, Sequence, TypedDict

from dotenv import load_dotenv

from pypdf import PdfReader, PdfWriter
import pathlib
import logging

# LlamaIndex & Docling Imports
from llama_index.core import VectorStoreIndex, Settings
from llama_index.readers.docling import DoclingReader
from llama_index.node_parser.docling import DoclingNodeParser
from llama_index.core import SimpleDirectoryReader
from llama_index.llms.openai_like import OpenAILike
from llama_index.embeddings.openai_like import OpenAILikeEmbedding

# LangGraph & LangChain Imports
from langchain_core.tools import Tool
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent

# Limit the spam from logging INFO messages
logging.basicConfig()
logging.getLogger().setLevel(logging.WARNING)


# ==========================================
# 0. PyPDF: Split PDF into individual pages
# ==========================================
def pdf_split_pages(file_path: str):
    pdf_dir = pathlib.Path(file_path).parents[0]
    pdf_fname = pathlib.Path(file_path).stem
    
    temp_dir = pdf_dir.joinpath("temp")   
    print("Created temporary directory: {}".format(temp_dir.absolute()))
    
    pdf = PdfReader(file_path)
    
    for page in range(len(pdf.pages)):
        pdf_writer = PdfWriter()
        pdf_writer.add_page(pdf.pages[page])

        output_filename = '{}\\{}_page_{}.pdf'.format(temp_dir,pdf_fname, page+1)

        with open(output_filename, 'wb') as out:
            pdf_writer.write(out)

        print('Created: {}'.format(output_filename))
        
    return temp_dir
    

# ==========================================
# 1. DOCLING + LLAMAINDEX: Ingest & Index
# ==========================================
def setup_document_index(temp_dir_path: str):
    
    
    # Configure LlamaIndex to use OpenAI
    Settings.llm = OpenAILike(
        model="gemma4-26b",
        api_base="http://192.168.0.50:8080/v1",
        is_chat_model = True,
        is_function_calling_model=True,
        api_key="fake",
        timeout=600.0,
    )
    Settings.embed_model = OpenAILikeEmbedding(
        model_name="gemma-embedding",
        api_base="http://192.168.0.50:8080/v1",
        api_key="fake",
        embed_batch_size=32,
        timeout=60.0,
    )

    # Initialize the Docling reader and load the document
    reader = DoclingReader(export_type=DoclingReader.ExportType.JSON)
    node_parser = DoclingNodeParser()    
    dir_reader = SimpleDirectoryReader(
        input_dir=temp_dir_path,
        file_extractor={".pdf": reader},
        filename_as_id=True,
    )

    print(f"Parsing documents with Docling: {temp_dir_path}...")
    documents = dir_reader.load_data(temp_dir_path)

    storage_type = 'db'
    if storage_type == 'vector_store':
        # Create a VectorStoreIndex from the parsed documents
        print("Building LlamaIndex vector store...")
        index = VectorStoreIndex.from_documents(
            documents, 
            transformation=[node_parser],
            embed_model = Settings.embed_model,
            show_progress=True,
        )
    elif storage_type == 'db':
        import chromadb
        from llama_index.vector_stores.chroma import ChromaVectorStore
        from llama_index.core import StorageContext

        chroma_client = chromadb.EphemeralClient()
        chroma_collection = chroma_client.create_collection("test")
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        index = VectorStoreIndex.from_documents(
            documents, storage_context=storage_context, embed_model=Settings.embed_model
        )
    
    # Create a Query Engine (the retriever)
    query_engine = index.as_query_engine(similarity_top_k=3)
    
    print("LlamaIndex vector store complete.")
    return query_engine

# ==========================================
# 2. LANGCHAIN: Wrap the Index as a Tool
# ==========================================
def create_rag_tool(query_engine):
    # Wrap the LlamaIndex query engine so the LangGraph agent can use it
    def query_wrapper(query: str) -> str:
        response = query_engine.query(query)
        return str(response)

    rag_tool = Tool(
        name="document_retriever",
        description="Use this tool to search the document for information. Input should be a specific search query.",
        func=query_wrapper
    )
    return rag_tool

# ==========================================
# 3. LANGGRAPH: Orchestrate the Agent
# ==========================================
def main():
    # Provide a pdf document
    pdf_path = "data/OhioCounty.pdf" 
    
    # 0. Split PDF
    pages_dir = pdf_split_pages(pdf_path)
    
    # 1. Setup Index
    query_engine = setup_document_index(pages_dir)
    
    # 2. Create Tool
    rag_tool = create_rag_tool(query_engine)
    tools = [rag_tool]
    
    # 3. Initialize the LLM for the Agent
    llm = ChatOpenAI(
        model="gemma4-26b",
        base_url="http://192.168.0.50:8080/v1",
        api_key="fake",
        timeout=600.0,
    )
    
    # 4. Compile the LangGraph Agent
    # We use prebuilt.create_react_agent for a standard tool-calling loop
    #agent_executor = create_react_agent(llm, tools)
    agent_executor = create_agent(llm, tools)
    
    # 5. Run the Graph
    user_query = "Use the document_retreiver tool. Look for references from one sheet to another sheet. Check that the referenced sheet contains the detail that is needed."
    
    inputs = {"messages": [HumanMessage(content=user_query)]}
    
    #print(f"\nUser: {user_query}\n")
    
    # Stream the agent's thought process
    for event in agent_executor.stream(inputs, stream_mode="values"):
        message = event["messages"][-1]
        message.pretty_print()

if __name__ == "__main__":
    main()
