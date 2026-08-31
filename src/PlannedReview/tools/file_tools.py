
import logging
import os

from pydantic_ai import BinaryContent, ToolReturn

from pypdf import PdfReader, PdfWriter #probably don't need this now that pymupdf is being used
import pymupdf
from pathlib import Path
import shutil

from pydantic_ai import RunContext
from tools import llm


def pdf_split_pages(file_path: str) -> Path:
    pdf_dir = Path(file_path).parents[0]
    pdf_fname = Path(file_path).stem
    
    temp_dir = pdf_dir.joinpath("temp")   
    logging.info("Created temporary directory: {}".format(temp_dir.absolute()))
    
    pdf = PdfReader(file_path)
    
    for page in range(len(pdf.pages)):
        pdf_writer = PdfWriter()
        pdf_writer.add_page(pdf.pages[page])

        output_filename = '{}\\{}_page_{}.pdf'.format(temp_dir,pdf_fname, page+1)

        with open(output_filename, 'wb') as out:
            pdf_writer.write(out)

        logging.info('Created: {}'.format(output_filename))
        
    return temp_dir  

def pdf_move(file_path: Path) -> Path:
    pdf_dir = file_path.parent
    pdf_fname = file_path.name
    
    temp_dir = pdf_dir.joinpath("temp")   
    logging.info("Created temporary directory: {}".format(temp_dir.absolute()))

    if os.path.exists(temp_dir / pdf_fname):
        logging.info("File alread exists in temp folder. Skipping.")
    else:
        shutil.copy(file_path, temp_dir) 
        logging.info(f"Copied file {pdf_fname}")
            
    return temp_dir 

def retreive_file(ctx: RunContext[llm.AgentDeps], page: int = 1) -> ToolReturn:
    """Request page from the pdf document. Only use filename from the database. 

    Args:
        page: the page number to retreive from the pdf. default is the first page (1)
    """
    pdf_path = ctx.deps.pdf_path
    logging.info(f'Requested PDF: {pdf_path} page {page}')
    
    
    #do some basic checking.
    # must be a *.pdf
    if not pdf_path.suffix == '.pdf':
        return ToolReturn(
            return_value = f'File is not a PDF. Only PDF files can be requested.',
        )

    if not pdf_path.exists():
        return ToolReturn(
            return_value = f'File does not exist. {pdf_path} ',
        )

    # requested page must be in the range of pages in the pdf
    pdf = PdfReader(pdf_path)
    if page < 1:
        ToolReturn(return_value = 'Minimum page number is 1.',)
    elif page > len(pdf.pages):
        ToolReturn(
            return_value = f'''Error page number must be within number of pages in pdf. 
            {pdf_path} contains {pdf.pages} pages.''',
            )

    try:
        #TODO: tile pdf instead of returning one big image
        doc = pymupdf.open(pdf_path)
        page = doc.load_page(page - 1)  # number of page. Page 1 is 0 index
        pix = page.get_pixmap(dpi=150)

        binary_file = BinaryContent(data=pix.tobytes(output="png"), media_type='image/png')

        return ToolReturn(
            return_value = f'Pdf page attached as an image.',
            content=[binary_file],
        )
    except:
        return ToolReturn(
                    return_value = f'Error retrieving file.',
                )
        
def write_json(ctx: RunContext[llm.AgentDeps], file_name: str, content: str) -> ToolReturn:
    """Request file to be writen to the system. 

    Args:
        file_name: the file name to write information
        content: the text to write to the file
    """

    
    try:
        file_path = ctx.deps.pdf_path / Path(file_name)

        file_path.write_text(content, encoding="utf-8")

        logging.info(f'Wrote to file: {file_path} ')

        return ToolReturn(
            return_value = f'Successfully wrote file.',
        )
    except:
        return ToolReturn(
                    return_value = f'Error writing file. {file_path} ',
                )

def read_queries(query_path: Path) -> list:
    """Read the queries from the queries directory and return them as a list of strings."""
    queries = []
    for query_file in query_path.glob("*.txt"):
        with open(query_file, "r") as f:
            queries.append(f.read())

    logging.info(f"Loaded queries from {query_path}: {len(queries)}")
    return queries