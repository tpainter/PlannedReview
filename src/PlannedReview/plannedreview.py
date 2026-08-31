
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

          
        #query_engine = db.fusionStore(pages_dir, pdf_name)
    else:
        if config['utils']['copy_pdf']:
            pages_dir = file_tools.pdf_move(pdf_path)
            query_engine = db.vectorStore(pages_dir, pdf_name, single_pdf=True) 
        else:
            pages_dir = pdf_path
            query_engine = db.vectorStore(pages_dir, pdf_name, single_pdf=True) 
     
    
    deps = llm.AgentDeps(query_engine=query_engine, pdf_path=pdf_path)

    # Run the query
    if prompt == "None":
        prompts = file_tools.read_queries(Path(__file__).resolve().parent / Path("queries"))
        for q in prompts:
            user_prompt = q
            result = agent.run_sync(user_prompt, deps=deps)
            print(f"Tokens used: {result.usage.total_tokens:,}")
            print("Agent Response:")
            print(result.output)
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