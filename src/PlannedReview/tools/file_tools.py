
import logging
import math
import os
from pathlib import Path
import shutil
import tempfile

from pydantic import BaseModel, Field
from pydantic_ai import BinaryContent, ToolReturn
from pydantic_ai import RunContext

from pypdf import PdfReader, PdfWriter #probably don't need this now that pymupdf is being used
import pymupdf
from markdown_pdf import MarkdownPdf, Section

from tools import llm


class CloudFinding(BaseModel):
    page: int = Field(ge=1, description="One-based PDF page number containing the finding.")
    search_text: str = Field(min_length=1, description="Exact text visible near the finding on that page.")
    comment: str = Field(min_length=1, description="Review comment to attach to the red cloud.")


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

def retreive_file(
    ctx: RunContext[llm.AgentDeps],
    page: int = 1,
    tiled: bool = False,
) -> ToolReturn:
    """Request page from the pdf document. Only use filename from the database. 

    Args:
        page: the page number to retreive from the pdf. default is the first page (1)
        tiled: return the page as six overlapping images instead of one full-page image to improve readability. default is False
    """
    pdf_path = ctx.deps.pdf_path
    logging.info("Requested PDF: %s page %s (tiled=%s)", pdf_path, page, tiled)

    if pdf_path.suffix.lower() != ".pdf":
        return ToolReturn(
            return_value="File is not a PDF. Only PDF files can be requested.",
        )

    if not pdf_path.exists():
        return ToolReturn(
            return_value=f"File does not exist. {pdf_path}",
        )

    try:
        with pymupdf.open(pdf_path) as doc:
            if page < 1:
                return ToolReturn(return_value="Minimum page number is 1.")
            if page > len(doc):
                return ToolReturn(
                    return_value=(
                        f"Error: page number must be within the PDF's page range. "
                        f"{pdf_path} contains {len(doc)} pages."
                    ),
                )

            pdf_page = doc.load_page(page - 1)
            if not tiled:
                pix = pdf_page.get_pixmap(dpi=150)
                return ToolReturn(
                    return_value="PDF page attached as one image.",
                    content=[
                        BinaryContent(data=pix.tobytes(output="png"), media_type="image/png")
                    ],
                )

            page_rect = pdf_page.rect
            columns = 3
            rows = 2
            overlap_x = page_rect.width / columns * 0.1
            overlap_y = page_rect.height / rows * 0.1
            tile_images = []

            for row in range(rows):
                for column in range(columns):
                    tile_rect = pymupdf.Rect(
                        max(
                            page_rect.x0,
                            page_rect.x0 + column * page_rect.width / columns - overlap_x / 2,
                        ),
                        max(
                            page_rect.y0,
                            page_rect.y0 + row * page_rect.height / rows - overlap_y / 2,
                        ),
                        min(
                            page_rect.x1,
                            page_rect.x0 + (column + 1) * page_rect.width / columns + overlap_x / 2,
                        ),
                        min(
                            page_rect.y1,
                            page_rect.y0 + (row + 1) * page_rect.height / rows + overlap_y / 2,
                        ),
                    )
                    pix = pdf_page.get_pixmap(dpi=150, clip=tile_rect)
                    tile_images.append(
                        BinaryContent(data=pix.tobytes(output="png"), media_type="image/png")
                    )

            return ToolReturn(
                return_value=(
                    "PDF page attached as six overlapping image tiles in row-major order "
                    "(top-left to bottom-right)."
                ),
                content=tile_images,
            )
    except Exception as error:
        logging.exception("Error retrieving PDF page %s from %s", page, pdf_path)
        return ToolReturn(
            return_value=f"Error retrieving file: {error}",
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

def markdown_to_pdf(ctx: RunContext[llm.AgentDeps], markdown_text: str, pdf_file: str) -> ToolReturn:
    """Write markdown text to a PDF file.

    Args:
        markdown_text: the markdown text to write to the PDF file
        pdf_file: the PDF filename to write the converted text to
    """

    pdf_path = Path(ctx.deps.pdf_path).parent / pdf_file
    pdf_path = pdf_path.with_suffix(".pdf")

    try:
        pdf = MarkdownPdf(toc_level=2,optimize=True)
        pdf.add_section(Section(markdown_text))        
        pdf.save(pdf_path)

        logging.info(f'Wrote to {pdf_path}')

        return ToolReturn(
            return_value = f'Successfully wrote to {pdf_path}.',
        )
    except Exception as e:
        logging.error(f'Error writing {pdf_path}: {e}')
        return ToolReturn(
            return_value = f'Error writing {pdf_path}: {e}',
        )


def prepend_markdown_to_pdf(markdown_text: str, pdf_path: Path) -> None:
    """Render markdown text as PDF pages and prepend them to an existing PDF."""
    with tempfile.TemporaryDirectory(
        prefix="plannedreview-report-",
        dir=pdf_path.parent,
    ) as temporary_directory:
        temporary_path = Path(temporary_directory)
        report_path = temporary_path / "review-report.pdf"
        merged_path = temporary_path / "merged-review.pdf"

        report_pdf = MarkdownPdf(toc_level=0, optimize=True)
        report_pdf.add_section(Section(markdown_text))
        report_pdf.save(report_path)

        with pymupdf.open(report_path) as merged_pdf:
            with pymupdf.open(pdf_path) as annotated_pdf:
                merged_pdf.insert_pdf(annotated_pdf, annots=True)
            merged_pdf.save(merged_path, garbage=4, deflate=True)

        merged_path.replace(pdf_path)


def add_red_clouds(
    ctx: RunContext[llm.AgentDeps], findings: list[CloudFinding]
) -> ToolReturn:
    """Mark review findings on the source PDF with red cloud annotations.

    Args:
        findings: Findings to mark. For each item, provide the one-based PDF
            page number, a short exact text snippet visible on that page, and
            the review comment to attach to the cloud.
    """
    pdf_path = ctx.deps.pdf_path
    if pdf_path.suffix.lower() != ".pdf":
        return ToolReturn(return_value="Cannot add red clouds: the source file is not a PDF.")
    if not pdf_path.exists():
        return ToolReturn(return_value=f"Cannot add red clouds: source PDF does not exist: {pdf_path}")
    if not findings:
        return ToolReturn(return_value="Cannot add red clouds: no findings were provided.")
    if any(not finding.search_text.strip() or not finding.comment.strip() for finding in findings):
        return ToolReturn(
            return_value="Cannot add red clouds: each finding needs searchable text and a comment."
        )
    if pdf_path.stem.lower().endswith("_reviewed"):
        return ToolReturn(
            return_value="Cannot add red clouds to a _reviewed PDF; provide the original PDF instead."
        )

    output_path = pdf_path.with_name(f"{pdf_path.stem}_reviewed.pdf")
    with pymupdf.open(pdf_path) as doc:
        page_count = len(doc)
        invalid_pages = [finding.page for finding in findings if finding.page > page_count]
        if invalid_pages:
            return ToolReturn(
                return_value=(
                    f"Cannot add red clouds: page number(s) {invalid_pages} exceed "
                    f"the source PDF's {page_count} pages."
                )
            )

        marked = 0
        unmatched = []
        for finding in findings:
            page = doc.load_page(finding.page - 1)
            matches = page.search_for(finding.search_text)
            if not matches:
                unmatched.append(f"page {finding.page}: {finding.search_text!r}")
                continue

            for match in matches:
                margin = max(3.0, match.height * 0.25)
                bounds = match + (-margin, -margin, margin, margin)
                width = bounds.width / 2
                height = bounds.height / 2
                lobe_count = max(8, round(math.pi * (bounds.width + bounds.height) / 10))
                vertices = []
                for index in range(lobe_count * 10):
                    angle = 2 * math.pi * index / (lobe_count * 10)
                    scallop = 1 + 0.08 * math.cos(lobe_count * angle)
                    vertices.append(
                        pymupdf.Point(
                            bounds.x0 + width + width * scallop * math.cos(angle),
                            bounds.y0 + height + height * scallop * math.sin(angle),
                        )
                    )

                annotation = page.add_polygon_annot(vertices)
                annotation.set_colors(stroke=(1, 0, 0))
                annotation.set_border(width=1.5)
                annotation.set_info(
                    title="Plan review comment",
                    subject="Red cloud",
                    content=finding.comment,
                )
                annotation.update()
                marked += 1

        if marked == 0:
            return ToolReturn(
                return_value=(
                    "No red clouds were added because none of the provided text snippets "
                    f"matched the PDF. Unmatched findings: {'; '.join(unmatched)}"
                )
            )

        doc.save(output_path, garbage=4, deflate=True)

    logging.info("Added %d red cloud annotation(s) to %s", marked, output_path)

    result = f"Added {marked} red cloud annotation(s). Saved reviewed PDF to {output_path}."
    if unmatched:
        result += f" Unmatched findings: {'; '.join(unmatched)}"
    return ToolReturn(return_value=result)