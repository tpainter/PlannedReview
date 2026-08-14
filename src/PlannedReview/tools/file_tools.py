
from pydantic_ai import BinaryContent, ToolReturn

from pypdf import PdfReader, PdfWriter #probably don't need this now that pymupdf is being used
import pymupdf
from pathlib import Path



def pdf_split_pages(file_path: str):
    pdf_dir = Path(file_path).parents[0]
    pdf_fname = Path(file_path).stem
    
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

def retreive_file(file_path: str):
    """Request a file name to retrieve the original pdf file. Only use filename from the database. 

    Args:
        file_path: the file name that is requested
    """

    #do some basic checking.
    #must be a *.pdf
    if not file_path.endswith('.pdf'):
        return 'Error: file is not a pdf.'

    print(f'Requested PDF: {file_path}')
    pdf_path = Path('data/temp/' + file_path)

    #TODO: tile pdf instead of returning one big image
    doc = pymupdf.open(pdf_path)
    page = doc.load_page(0)  # number of page
    pix = page.get_pixmap(dpi=150)

    binary_file = BinaryContent(data=pix.tobytes(output="png"), media_type='image/png')

    return ToolReturn(
        return_value = f'Pdf page attached as an image.',
        content=[binary_file],
    )


