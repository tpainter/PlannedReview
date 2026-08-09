import chromadb
from llama_index.core import VectorStoreIndex, Settings
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import StorageContext
from llama_index.readers.docling import DoclingReader
from llama_index.core import SimpleDirectoryReader

def vectorStore(temp_dir_path: str):
    """
    
    """
    # Initialize the Docling reader and load the document
    reader = DoclingReader(export_type=DoclingReader.ExportType.JSON)       
    dir_reader = SimpleDirectoryReader(
        input_dir=temp_dir_path,
        file_extractor={".pdf": reader},
        filename_as_id=True,
    )

    print(f"Parsing documents with Docling: {temp_dir_path}...")
    documents = dir_reader.load_data(temp_dir_path)

    

    chroma_client = chromadb.EphemeralClient()
    chroma_collection = chroma_client.create_collection("test")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_documents(
        documents, storage_context=storage_context, embed_model=Settings.embed_model
    )

    print("LlamaIndex vector store complete.")
    return index

