from llama_index.readers.docling import DoclingReader
from llama_index.node_parser.docling import DoclingNodeParser
from llama_index.core.node_parser import MarkdownNodeParser
from llama_index.core import SimpleDirectoryReader

single_pdf = True
temp_dir_path = "C:/Users/travi/Desktop/github/construction_plan_checks/data/OhioCounty"
temp_pdf_path = "C:/Users/travi/Desktop/github/construction_plan_checks/data/OhioCounty.pdf"
parse_type = "json"  # or "markdown" or "json"

if parse_type == "json":
    reader = DoclingReader(export_type=DoclingReader.ExportType.JSON)
    node_parser = DoclingNodeParser()
elif parse_type == "markdown":
    reader = DoclingReader(export_type=DoclingReader.ExportType.MARKDOWN)
    node_parser = MarkdownNodeParser()

if single_pdf:
    documents = reader.load_data(temp_pdf_path)
else:
    file_reader = SimpleDirectoryReader(
        input_dir=temp_dir_path,
        file_extractor={".pdf": reader},
        filename_as_id=True,
    )
    documents = file_reader.load_data()


nodes = node_parser.get_nodes_from_documents(documents)

with open("temp_output.txt", "w") as f:
    for node in nodes:
        if parse_type == "json":
            f.write(node.text + "\n\n")
        elif parse_type == "markdown":
            f.write(node.text + "\n\n")