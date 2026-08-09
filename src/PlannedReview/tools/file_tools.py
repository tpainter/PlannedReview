
from pydantic import BaseModel, Field
from pydantic_ai import Agent


from pypdf import PdfReader, PdfWriter
import pathlib


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


