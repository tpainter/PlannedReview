
import logging
import sys
import argparse
import tomllib
from pathlib import Path
from typing import Callable

# plannedreview imports
from tools import db, file_tools, llm




def PlannedReview(
    pdf: str,
    prompt: str,
    output_callback: Callable[[str], None] | None = None,
) -> Path | None:
    def report(message: str) -> None:
        print(message, flush=True)
        if output_callback is not None:
            output_callback(f"{message}\n")

    report(f"Loading review configuration for {pdf}...")
    # Load configuration file
    config_path = Path(__file__).resolve().parent / Path("config.toml")
    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    # Provide a pdf document
    pdf_path = Path(pdf).expanduser().resolve()
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF file does not exist: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a PDF file: {pdf_path}")
    pdf_name = pdf_path.stem    
    reviewed_pdf = pdf_path.with_name(f"{pdf_name}_reviewed.pdf")
    previous_output_mtime = (
        reviewed_pdf.stat().st_mtime_ns if reviewed_pdf.exists() else None
    )

    report("Setting up language models...")
    agent = llm.setup_llms(config['llm'])
    
    if config['utils']['split_pdf']:
        report("Splitting PDF into pages...")
        pages_dir = file_tools.pdf_split_pages(pdf_path)
        query_engine = db.fusionStore(pages_dir, pdf_name)
    else:
        if config['utils']['copy_pdf']:
            report("Copying PDF into the working directory...")
            pages_dir = file_tools.pdf_move(pdf_path)
            query_engine = db.vectorStore(pages_dir, pdf_name, single_pdf=True) 
            #query_engine = db.fusionStore(pages_dir, pdf_name, single_pdf=True)
        else:
            pages_dir = pdf_path
            query_engine = db.vectorStore(pages_dir, pdf_name, single_pdf=True) 
            #query_engine = db.fusionStore(pages_dir, pdf_name, single_pdf=True)
     
    
    deps = llm.AgentDeps(query_engine=query_engine, pdf_path=pdf_path)

    # Run the query
    total_tokens = 0
    if prompt == "None":
        prompts = file_tools.read_queries(Path(__file__).resolve().parent / Path("queries"))
        if not prompts:
            raise RuntimeError("No review prompts found; cannot run the plan review.")

        report(f"Running {len(prompts)} review prompt(s)...")
        responses_path = pdf_path.with_name(f"{pdf_name}_review_responses.md")
        with responses_path.open("w", encoding="utf-8") as responses_file:
            for index, user_prompt in enumerate(prompts, start=1):
                report(f"Running review prompt {index} of {len(prompts)}...")
                result = agent.run_sync(user_prompt, deps=deps)
                total_tokens += result.usage.total_tokens
                logging.info("Prompt %d tokens used: %s", index, f"{result.usage.total_tokens:,}")
                logging.info("Agent Response:")
                logging.info(result.output)
                report(f"Prompt {index} complete ({result.usage.total_tokens:,} tokens).")
                report(str(result.output))
                responses_file.write(
                    f"### Response {index}\n\n"
                    f"{result.output}\n\n"
                    "---\n\n"
                )
                responses_file.flush()

        saved_responses = responses_path.read_text(encoding="utf-8")
        summary_prompt = (
            "Report the findings in the saved prompt responses below. "
            "Do not summarize the reponse. Report every issue from the responses."
            "Group the responses by sheet. Do not perform a new plan review; "
            "Base the summary only on these responses. After identifying the "
            "findings, call the add_red_clouds tool once with every actionable "
            "finding that has a page number and exact visible text to locate. "
            "Include the finding as the cloud comment, and do not invent a "
            "location when the responses do not provide one.\n\n"
            f"{saved_responses}"
        )
        report("Generating the findings summary and adding PDF annotations...")
        summary_result = agent.run_sync(summary_prompt, deps=deps)
        total_tokens += summary_result.usage.total_tokens
        with responses_path.open("a", encoding="utf-8") as responses_file:
            responses_file.write(
                f"## Summary\n\n{summary_result.output}\n"
            )

        report(f"Saved prompt responses and summary to: {responses_path}")
        report(f"Summary tokens used: {summary_result.usage.total_tokens:,}")
        report("Agent Summary:")
        report(str(summary_result.output))
        if not reviewed_pdf.is_file():
            raise RuntimeError(
                "The review completed, but no marked-up PDF was created. "
                "Check that findings include page numbers and searchable text."
            )
        if (
            previous_output_mtime is not None
            and reviewed_pdf.stat().st_mtime_ns == previous_output_mtime
        ):
            raise RuntimeError(
                "The review completed, but no new marked-up PDF was created. "
                "Check that findings include page numbers and searchable text."
            )
        report(f"Reviewed PDF created: {reviewed_pdf}")
        report(f"Total tokens used: {total_tokens:,}")
        return reviewed_pdf
    else:
        user_prompt = prompt
        report("Running the requested review...")
        result = agent.run_sync(user_prompt, deps=deps)
        total_tokens += result.usage.total_tokens
        report("Agent Response:")
        report(str(result.output))
        report(f"Total tokens used: {total_tokens:,}")
        return None

if __name__ == "__main__":
    #Example: uv run .\src\PlannedReview\plannedreview.py .\data\OhioCounty.pdf -p "write 'test' to the file, output.json"
    
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", help = "The file name of the pdf to analyze.", type = str)
    parser.add_argument("-p", "--prompt", help="The prompt to sent to the plan agent.", default="None")
    args = parser.parse_args()
    PlannedReview(args.pdf, args.prompt)