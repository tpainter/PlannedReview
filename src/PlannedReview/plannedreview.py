
import logging
import sys
import argparse
import tomllib
from pathlib import Path

# plannedreview imports
from tools import db, file_tools, llm




def PlannedReview(pdf: str, prompt: str) -> None:

    # Load configuration file
    config_path = Path(__file__).resolve().parent / Path("config.toml")
    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    # Provide a pdf document
    pdf_path = Path(pdf) 
    pdf_name = pdf_path.stem    

    agent = llm.setup_llms(config['llm'])
    
    if config['utils']['split_pdf']:
        pages_dir = file_tools.pdf_split_pages(pdf_path)
        query_engine = db.fusionStore(pages_dir, pdf_name)
    else:
        if config['utils']['copy_pdf']:
            pages_dir = file_tools.pdf_move(pdf_path)
            query_engine = db.vectorStore(pages_dir, pdf_name, single_pdf=True) 
            #query_engine = db.fusionStore(pages_dir, pdf_name, single_pdf=True)
        else:
            pages_dir = pdf_path
            query_engine = db.vectorStore(pages_dir, pdf_name, single_pdf=True) 
            #query_engine = db.fusionStore(pages_dir, pdf_name, single_pdf=True)
     
    
    deps = llm.AgentDeps(query_engine=query_engine, pdf_path=pdf_path)

    # Run the query
    if prompt == "None":
        prompts = file_tools.read_queries(Path(__file__).resolve().parent / Path("queries"))
        if not prompts:
            logging.warning("No prompts found; skipping review.")
            return

        responses_path = pdf_path.with_name(f"{pdf_name}_review_responses.md")
        with responses_path.open("w", encoding="utf-8") as responses_file:
            for index, user_prompt in enumerate(prompts, start=1):
                result = agent.run_sync(user_prompt, deps=deps)
                logging.info("Prompt %d tokens used: %s", index, f"{result.usage.total_tokens:,}")
                logging.info("Agent Response:")
                logging.info(result.output)
                responses_file.write(
                    f"## Prompt {index}\n\n"
                    f"{user_prompt}\n\n"
                    f"### Response\n\n"
                    f"{result.output}\n\n"
                    "---\n\n"
                )
                responses_file.flush()

        saved_responses = responses_path.read_text(encoding="utf-8")
        summary_prompt = (
            "Summarize the findings in the saved prompt responses below. "
            "Synthesize recurring issues, highlight important individual findings, "
            "and note any conflicts or uncertainties. Do not perform a new plan review; "
            "base the summary only on these responses.\n\n"
            f"{saved_responses}"
        )
        summary_result = agent.run_sync(summary_prompt, deps=deps)
        with responses_path.open("a", encoding="utf-8") as responses_file:
            responses_file.write(
                f"## Summary\n\n{summary_result.output}\n"
            )

        print(f"Saved prompt responses and summary to: {responses_path}")
        print(f"Summary tokens used: {summary_result.usage.total_tokens:,}")
        print("Agent Summary:")
        print(summary_result.output)
    else:
        user_prompt = prompt
        result = agent.run_sync(user_prompt, deps=deps)
        print(f"Tokens used: {result.usage.total_tokens:,}")
        print("Agent Response:")
        print(result.output)

if __name__ == "__main__":
    #Example: uv run .\src\PlannedReview\plannedreview.py .\data\OhioCounty.pdf -p "write 'test' to the file, output.json"
    
    logging.basicConfig(level=logging.INFO)
    
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", help = "The file name of the pdf to analyze.", type = str)
    parser.add_argument("-p", "--prompt", help="The prompt to sent to the plan agent.", default="None")
    args = parser.parse_args()
    PlannedReview(args.pdf, args.prompt)