
import logging
import argparse
from pathlib import Path

# plannedreview imports
from tools import db, file_tools, llm
from queries import Q000




def PlannedReview(pdf: str, prompt: str) -> None:
    
    # Provide a pdf document
    pdf_path = Path(pdf) 
    pdf_name = pdf_path.stem    
    
    # Split PDF
    split = False
    pdf_copy = False
    if split:
        pages_dir = file_tools.pdf_split_pages(pdf_path)
    else:
        if pdf_copy:
            pages_dir = file_tools.pdf_move(pdf_path)
        else:
            pages_dir = pdf_path.parent

    # Setup llms
    llm_location = 'google' # local, google
    agent = llm.setup_llms(llm_location)

    query_engine = db.vectorStore(pages_dir, pdf_name)   
    #query_engine = db.fusionStore(pages_dir, pdf_name) 
    
    deps = llm.AgentDeps(query_engine=query_engine, pdf_path=pdf_path.parent)

    # Run the query
    if prompt == "None":
        for q in Q000.queries:
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