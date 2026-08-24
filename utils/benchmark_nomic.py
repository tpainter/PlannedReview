import sys
import subprocess


def main():

    pdf = "../data/aec-bench-v1/cross-reference-resolution/2021-0525_uccs-cybersecurity-broken/2021-0525_UCCS BID SET - Drawings_new.pdf"
    prompt_file = "../data/nomic_aec_bench/intradrawing/cross-reference-resolution/2021-0525_uccs-cybersecurity-broken/instruction.md"
    with open(prompt_file, 'r', encoding="utf-8") as file:
        prompt = file.read()

    result = subprocess.run(
        [sys.executable, "../plannedreview.py", pdf, "-p", prompt],
        capture_output=True,
        text=True,
    )

if __name__ == "__main__":
    
    main()