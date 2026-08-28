#
# Download test files for local testing.
#

import os
from pathlib import Path
import logging
import json 
from urllib.parse import urlparse
from urllib.parse import unquote
import requests

import fsspec

def nomic_github() -> None:
    logging.info("Downloading local test files...")
    
    #nomic-ai/aec-bench: https://github.com/nomic-ai/aec-bench/tree/main/tasks
    destination = Path("data") / "nomic_aec_bench"
    destination.mkdir(exist_ok=True, parents=True)

    fs = fsspec.filesystem("github", org="nomic-ai", repo="aec-bench")
    fs.get(fs.ls("tasks/"), 
            destination.as_posix(), 
            recursive=True, 
            auto_mkdir=True, 
            batch_size=1, 
            use_listing_cache=True,
            listings_expiry_time=6000,)

def nomic_pdf() -> None:
    destination = Path("data") / "nomic_aec_bench"
    pdf_files: list[str] = []
    n = 0
    err = 0

    for root, dirs, files in os.walk(destination):
        for file in files:
            if (file.endswith('.jsonl')):
                n += 1
                try:
                    with open(root + "/" + file, 'r', encoding='utf-8') as f:
                        for line in f:
                            data: list[dict[str, object]] = []
                            data.append(json.loads(line))
                            pdf_files.append(data[0]['key'])
                except Exception as e:
                    print(repr(e))
                    print(f"Error with file in: {root}")
                    with open(root + "/" + file, 'r', encoding='utf-8') as f:
                        print(f.read())
                    err += 1

    n_unique = list(set(pdf_files))
    print(f"Json files: {n} \nUnique files: {len(n_unique)} \nErrors: {err}")

    #Download files locally
    for url in n_unique:
        #get file name
        a = urlparse(url) 
        #add a period to ensure that it saves to local reference instead of filesystem root
        fn = "." + unquote(a.path)         
        if not os.path.isfile(fn):            
            response = requests.get(url)
            if response.status_code == 200:
                #create directory
                file_path = Path(fn)
                file_path.parent.mkdir(parents=True, exist_ok=True)

                with open(fn, 'wb') as file:
                    logging.info(f"Saving file: {fn}")
                    file.write(response.content)
        else:
            logging.info(f"Skipping file. Already exists: {fn}")
    
                


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    
    #nomic_github()
    nomic_pdf()






if __name__ == "__main__":
    main()