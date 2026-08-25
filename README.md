# PlannedReview

## Overview

PlannedReview performs an automated review of construction plan documents supplied in PDF format. The tool analyzes drawings for common completeness, compliance, and quality issues and produces review reports.

This tool is intended to assist knowledgeable staff by checking routine items automatically so reviewers can focus on higher-level design and coordination issues. It is not a replacement for professional plan review.

## Key features
- Accepts construction plan PDFs as input (multi-page PDFs supported)
- Detects common issues such as missing or conflicting dimensions, unlabeled details, inconsistent references, and common drafting mistakes
- Produces a summary of findings and a detailed per-page report
- Outputs machine-readable JSON for integration with CI pipelines or issue trackers, and optional HTML or plain-text reports for human consumption

## Basic CLI pattern

    uv run path/to/construction-plan.pdf [--prompt] [--verbose]

## Options
- path/to/construction-plan.pdf  : Path to the input PDF file containing construction plans.
- --prompt "prompt text"                : Optional. Prompt sent to the llm.
- --verbose                      : Optional. Emit diagnostic and processing details during analysis.

## Input expectations and tips
- Provide the plan set as a single PDF if possible.
- For scanned plans, higher-quality scans (300 DPI or greater) yield better extraction and detection results.
- Ensure PDFs are not password protected or otherwise restricted.

## Output
- Summary: a brief list of high-priority issues.
- Detailed findings: per-page observations with suggested corrections and references where applicable.



