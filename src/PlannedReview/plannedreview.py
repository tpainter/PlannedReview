
import logging
import argparse
from pathlib import Path

# plannedreview imports
from tools import db, file_tools, llm
from queries import Q000




def main():
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", help = "The file name of the pdf to analyze.", type = str)
    args = parser.parse_args()

    # Provide a pdf document
    pdf_path = Path(args.pdf) 
    pdf_name = pdf_path.stem
    
    
    # 0. Split PDF
    split = False
    if split:
        pages_dir = file_tools.pdf_split_pages(pdf_path)
    else:
        pages_dir = file_tools.pdf_move(pdf_path)
    
    # 1. Setup llms
    llm_location = 'local' # local, google
    agent = llm.setup_llms(llm_location)

    query_engine = db.vectorStore(pages_dir, pdf_name)   
    #query_engine = db.fusionStore(pages_dir, pdf_name) 

    # 3. Run the query
    deps = llm.AgentDeps(query_engine=query_engine, pdf_path=pdf_path.parents[0])

    for q in Q000.queries:
        user_prompt = q

        result = agent.run_sync(user_prompt, deps=deps)
        print("Agent Response:")
        print(result.output)

if __name__ == "__main__":
    main()
