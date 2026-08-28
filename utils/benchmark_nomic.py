import sys
import logging

sys.path.append("./src/PlannedReview")
from plannedreview import PlannedReview as PR


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    pdf = "./data/aec-bench-v1/note-callout-accuracy/03addendum-joist-beam-mismatch/sheet.pdf"
    prompt_file = "./data/nomic_aec_bench/intrasheet/note-callout-accuracy/03addendum-joist-beam-mismatch/instruction_edit.md"
    with open(prompt_file, 'r', encoding="utf-8") as file:
        prompt = file.read()

    PR(pdf, prompt)



if __name__ == "__main__":
    
    main()