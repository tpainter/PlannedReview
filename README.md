# PlannedReview

## Overview

PlannedReview performs an automated review of construction plan documents supplied in PDF format. The tool analyzes drawings for common completeness, compliance, and quality issues and produces review reports.

This tool is intended to assist knowledgeable staff by checking routine items automatically so reviewers can focus on higher-level design and coordination issues. It is not a replacement for professional plan review.

## Key features
- Accepts construction plan PDFs as input (multi-page PDFs supported)
- Detects common issues such as spelling, references, note and specification conflicts, inconsistent references, and common drafting mistakes
- Produces a summary of findings and a detailed per-page report
- Output can be basic JSON or markdown for adding into automated flows, or it can be a PDF to download and save in the project files.
  
## Basic CLI pattern

    uv run path/to/construction-plan.pdf [--prompt] [--verbose]

## Options
- path/to/construction-plan.pdf  : Path to the input PDF file containing construction plans.
- --prompt "prompt text"                : Optional. Prompt sent to the llm. Use this for specific or one-off questions.
- --verbose                      : Optional. Emit diagnostic and processing details during analysis.

## Input expectations and tips
- Provide the plan set as a single PDF if possible.
- If a PDF is very large, enable the PDF split option in the configuration file.
- For scanned plans, higher-quality scans work better.
- Ensure PDFs are not password protected or otherwise restricted. This also typically means not digitally sealed.

## Output
- Summary: a brief list of high-priority issues.
- Detailed findings: per-page observations with suggested corrections and references where applicable.

## Example
- PDF from: https://transportation.ky.gov/Construction-Procurement/Project%20Related%20Information/Ohio%20County%20-%20CID%2019-5044%20-%20Plan%20Set.pdf
- This is a random PDF that is publicly available.

    ```
    uv run .\src\PlannedReview\plannedreview.py .\data\OhioCounty.pdf -p "For the construction plans, check the general notes for errors coordination errors."
    ```
  
  
- The general output looks like this:

Based on a thorough review of **Sheet S1 (General Notes)** and cross-referencing with the rest of the plan set (Sheets R1 through R4 and Sheets S2 through S4), several critical **textual errors, technical errors, and inter-sheet coordination discrepancies** were identified:

---

### 1. Critical Drafting / Technical Error: Temporary Supports Note
* **Sheet S1 Note:**
  > *"Temporary Supports: Temporary Supports or shoring will not be permitted under the beams **unless** pouring the concrete deck slab or when taking 'top of beam' elevations."*
* **Error & Impact:**
  The word **`unless`** is a severe error and reverses the intended engineering specification. Precast prestressed concrete box beams are designed as simply supported, unshored members during slab placement to ensure proper dead load deflection and prevent composite cracking. The standard KYTC note states that shoring will not be permitted **`when`** (or *while*) pouring the deck slab or taking elevations. Stating that shoring is forbidden *unless* pouring the slab literally instructs the contractor to shore the beams during the pour, which will cause unpredicted load paths and severe deck cracking when shoring is removed.

---

### 2. Concrete Class & Substructure Allocation Conflict
* **Sheet S1 Note:**
  > *"Class 'AA' Concrete is to be used throughout the superstructure and in the portions of the substructure above the tops of caps. Class 'A' concrete is to be used in the substructure below the caps."*
* **Coordination Conflicts:**
  1. **Cap Concrete Omission:** The note defines concrete above the cap tops (Class AA) and below the caps (Class A), but fails to define the concrete class for the bridge caps themselves.
  2. **Direct Conflict with Sheet S4:** Sheet S4 (*Pile End Bents 1 & 2*), Note 2 explicitly dictates: **`"Concrete to be Class 'A', 3500 psi"`** for the end bent caps, backwalls, and wings. Sheet S1 claims portions above the cap tops (backwalls and wings) are Class 'AA', contradicting Sheet S4.
  3. **Omission of Prestressed Beam Concrete Strengths:** Sheet S1 lists compressive strengths only for Class 'A' ($3,500\text{ psi}$) and Class 'AA' ($4,000\text{ psi}$), but fails to define the required compressive strengths at transfer ($f'_{ci}$) and 28 days ($f'_c$) for the precast prestressed CB27 box beams anywhere on Sheet S1 or S2.

---

### 3. Expansion Joint & Bearing Fixity Coordination Conflict
* **Sheet S1 Note:**
  > *"Armored Edge: Fabricate armored edge to match cross slope and parabolic crown at each end of bridge."*
* **Coordination Conflicts with Sheet S2:**
  1. Sheet S2 (*Elevation*) designates both abutments as fixed: **`End Bent 1 (Fix)`** and **`End Bent 2 (Fix)`**. A single-span 64′-0″ bridge cannot be fixed against thermal movement at both ends without inducing excessive thermal forces.
  2. Sheet S2 (*End of Beam Detail*) specifies: *"Tape shall be looped as shown at **expansion ends** of bridge to prevent damage to tape."* Providing an armored edge expansion joint and looping tape at an expansion end directly contradicts labeling both bents as `(Fix)`.

---

### 4. Piling, Driving Criteria, & Pile Point Discrepancies
* **Sheet S1 Notes:**
  > *"Piling shall be driven to practical refusal as defined on the pile record sheet..."*
  > *"Pile Points: Provide pile points for all piles... and of the type shown on the pile record sheet."*
* **Coordination Conflicts:**
  1. **Pile Type Discrepancy (Sheet S4 vs. Sheets S1, S3, R1):** Sheet S4 Note 6 states: *"Piles may be HP12x53 or 16\" Steel Pipes with 1/2\" wall thickness."* However, Sheet S1, Sheet S3 (Pile Record), and Sheet R1 Standard Drawings specify and detail **only HP 12x53** steel H-piles (Standard Drawing `BPS-003-09`). Pipe piles are not coordinated, calculated, or detailed.
  2. **Pile Point Type Missing on Sheet S3:** Sheet S1 mandates providing pile points *"of the type shown on the pile record sheet."* However, Sheet S3 does **not** specify or show any pile point type or manufacturer; it only provides a generic recommendation text.
  3. **Driving Criteria Conflict (Sheet S4 vs. Sheets S1 & S3):** Sheet S4 Note 7 includes friction pile driving criteria: *"Friction Piles must be driven to (Pile Load/0.4) using the Gates Method."* However, both Sheet S1 and Sheet S3 define these strictly as **point bearing piles driven to practical refusal** on rock.

---

### 5. Outdated AASHTO Specification Reference
* **Sheet S1 Note (Under Elastomeric Bearing Pads):**
  > *"Elastomeric Bearing Pads shall conform to the AASHTO Standard Specifications for Highway Bridges, Division II, Section 18."*
* **Conflict:**
  Sheet S1 Note 1 states that all AASHTO references shall conform to the **AASHTO LRFD Bridge Design Specifications**, and Sheet R1 lists the **2017 AASHTO LRFD Specifications**. Referencing the obsolete *AASHTO Standard Specifications for Highway Bridges (Division II)* represents an outdated cut-and-paste specification.

---

### 6. Foundation Preparation & Structural Granular Backfill Scope
* **Sheet S1 Note:**
  States that Structural Granular Backfill will be included in the lump sum bid for Foundation Preparation per Standard Specification Sections 603 and 805.
* **Coordination Omission with Sheet R2:**
  Sheet R2 (*Special Notes*) explicitly invokes **Special Provision 69 (Embankment at Bridge End Structures)** and **Sepia Drawings 009 & 010**, mandating that structural granular backfill, geotextile fabric, perforated pipe, pile cores, and approach earthwork are all incidental to the Lump Sum item for *Foundation Preparation*. Sheet S1 omits Special Provision 69 and these incidental items.

---

### 7. Crossing Feature Name Discrepancy
* **Sheets R1, R2, R3, R4, S1, S2, S3:** The project crossing is identified as **Barass Ditch**.
* **Sheet S4 Title Block:** The crossing is incorrectly labeled **Barass Creek**.

---

### Summary of Recommended Actions
1. **Change `"unless"` to `"when"`** in the *Temporary Supports* note on Sheet S1 immediately to avoid improper contractor shoring during the deck pour.
2. **Clarify Concrete Classes:** Reconcile Sheet S1 with Sheet S4 Note 2 regarding End Bent concrete class, and specify $f'_c$ and $f'_{ci}$ for the precast CB27 box beams.
3. **Correct Abutment Fixity on Sheet S2:** Update one of the end bents to an expansion bearing `(Exp)` to match the armored edge and expansion joint details.
4. **Remove 16″ pipe pile option** from Sheet S4 Note 6, specify the exact pile point model on Sheet S3, and delete friction pile references.
5. **Update bearing pad specification** to reference current AASHTO LRFD Construction Specifications / Standard Drawing `BBP-003-02`.
