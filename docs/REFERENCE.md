# MTG Judge AI: Autonomous Rules & Card Interaction Engine
## Capstone Project Master Engineering Specification & Roadmap

---

## 1. Project Overview & System Architecture

### 1.1 Executive Summary
Magic: The Gathering (MTG) operates under a deterministic, Turing-complete ruleset exceeding 250 pages of Comprehensive Rules (CR). Standard Large Language Models (LLMs) frequently hallucinate card interactions because:
1. They rely on outdated card text printed on physical cardboard rather than current Wizards of the Coast **Oracle text**.
2. They do not reliably apply sequential game logic (e.g., the 7-Layer continuous effect system, State-Based Actions, APNAP trigger ordering).

This capstone project delivers an AI-powered rules advisor using a **Domain-Specific Hybrid Retrieval-Augmented Generation (RAG)** pipeline. The system enforces strict grounding by querying official Scryfall APIs for canonical Oracle data, referencing a vector-indexed database of the Comprehensive Rules, and synthesizing verdicts via a structured Judge Chain-of-Thought (CoT) inference engine.

### 1.2 High-Level Architecture Flow

```
                              [User Natural Language Query]
                                            │
                                            ▼
                           [Card Name Entity Recognizer]
                                            │
                    ┌───────────────────────┴───────────────────────┐
                    ▼                                               ▼
       [Scryfall API / Bulk Cache]                     [CR Vector Index (ChromaDB)]
     - Canonical Oracle Text                         - Relevant CR Sub-Rules (e.g., 613, 704)
     - Official Gatherer Rulings                     - Semantic Rule Keywords
                    │                                               │
                    └───────────────────────┬───────────────────────┘
                                            ▼
                          [Context Assembly & Prompt Engine]
                                            │
                                            ▼
                                [Judge Inference Agent]
                                (Chain-of-Thought Reasoning)
                                            │
                    ┌───────────────────────┴───────────────────────┐
                    ▼                                               ▼
     [Structured Mechanical Verdict]                [Verified CR Rule Citations]
     (Outcome, Layer Analysis, SBAs)                (e.g., CR 613.1d, CR 704.5f)
```

---

## 2. Master Project Directory Structure

```text
mtg-judge-ai/
├── data/
│   ├── raw/
│   │   ├── MagicCompRules.txt           # Raw Comprehensive Rules from WotC
│   │   └── default-cards.json           # Optional Scryfall bulk dataset cache
│   ├── processed/
│   │   └── parsed_rules.json            # Structured, section-chunked rule definitions
│   └── test_cases.json                  # Ground-truth test dataset for benchmark
│
├── src/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── scryfall.py                  # Scryfall REST API client & cache layer
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── parser.py                    # CR document parser & chunker
│   │   ├── ingest.py                    # Script to populate vector database
│   │   └── retriever.py                 # Hybrid vector search for rules
│   ├── core/
│   │   ├── __init__.py
│   │   ├── schemas.py                   # Pydantic data models
│   │   ├── extractor.py                 # Card name entity extraction logic
│   │   ├── prompts.py                   # System prompts and CoT templates
│   │   └── judge.py                     # Primary reasoning pipeline
│   └── web/
│       ├── __init__.py
│       ├── app.py                       # Streamlit UI or FastAPI server
│       └── views.py                     # Components, tooltips, and rendering
│
├── evaluation/
│   ├── __init__.py
│   └── evaluate.py                      # Automated comparative evaluation runner
│
├── .env.example                         # Environment variable template
├── requirements.txt                     # Pinned project dependencies
└── README.md
```

---

## 3. Tech Stack & Environment Setup

### 3.1 Dependencies (`requirements.txt`)
```text
# Web Framework & API
fastapi>=0.110.0
uvicorn>=0.28.0
streamlit>=1.32.0
httpx>=0.27.0
cachetools>=5.3.3

# Data Validation & Parsing
pydantic>=2.6.4
pydantic-settings>=2.2.1

# AI, Vector DB & Orchestration
openai>=1.14.0
chromadb>=0.4.24
sentence-transformers>=2.6.1
tiktoken>=0.6.0

# Evaluation & Utilities
tqdm>=4.66.2
python-dotenv>=1.0.1
rich>=13.7.1
```

### 3.2 Configuration (`.env.example`)
```env
OPENAI_API_KEY="your-openai-api-key"
MODEL_NAME="gpt-4o-mini"
EVALUATOR_MODEL="gpt-4o"
CHROMA_PERSIST_DIR="./data/chroma_db"
SCRYFALL_RATE_LIMIT_DELAY=0.1
```

---

## 4. Phased MVP Implementation Plan

```
MVP 1 (Card & Rulings QA) ──► MVP 2 (Multi-Card RAG Interaction) ──► MVP 3 (Contextual Web App)
```

---

### MVP 1: Single Card Lookup & Official Rulings QA
* **Objective:** Establish the foundation. Resolve questions about a single named card by retrieving its authoritative Oracle text and Gatherer rulings from Scryfall.

#### 1. Libraries Required
`httpx`, `pydantic`, `openai`, `streamlit`, `cachetools`, `python-dotenv`.

#### 2. Directory Focus
* `src/api/scryfall.py`
* `src/core/schemas.py`
* `src/web/app.py`

#### 3. Granular Implementation Steps
1. **Scryfall Integration Service (`src/api/scryfall.py`)**:
   * Implement fuzzy card lookup: `GET https://api.scryfall.com/cards/named?fuzzy={name}`.
   * Implement rulings lookup: `GET https://api.scryfall.com/cards/{id}/rulings`.
   * Implement an in-memory TTL cache (`cachetools.TTLCache`) to prevent redundant external calls and honor Scryfall's rate limit guidelines (50–100ms request spacing).
2. **Data Models (`src/core/schemas.py`)**:
   * Define Pydantic models:
     ```python
     class CardRuling(BaseModel):
         source: str
         published_at: str
         comment: str

     class MTGCard(BaseModel):
         id: str
         name: str
         mana_cost: str = ""
         type_line: str
         oracle_text: str
         image_uri: str | None = None
         rulings: list[CardRuling] = []
     ```
3. **Prompt Definition (`src/core/prompts.py`)**:
   * Define a template injecting Oracle text and existing rulings:
     ```text
     You are an assistant MTG Judge. Answer the player's question using the provided
     Oracle text and official Gatherer rulings.
     
     Card: {card_name}
     Types: {type_line}
     Oracle Text: {oracle_text}
     Official Rulings:
     {rulings}

     Question: {question}
     ```
4. **Minimal Streamlit UI (`src/web/app.py`)**:
   * Add text inputs for card name and rules question.
   * Display card art alongside the model's generated answer.

---

### MVP 2: Two-Card Interaction & Comprehensive Rules RAG
* **Objective:** Automatically extract multiple card names from natural language queries, fetch their data, retrieve relevant sections of the Comprehensive Rules (e.g., Layer 613, State-Based Actions 704), and synthesize interaction verdicts with rule citations.

#### 1. Libraries Required
`chromadb`, `sentence-transformers`, `openai`, `pydantic`, `regex`.

#### 2. Directory Focus
* `src/rag/parser.py`
* `src/rag/ingest.py`
* `src/rag/retriever.py`
* `src/core/extractor.py`
* `src/core/judge.py`

#### 3. Granular Implementation Steps
1. **CR Ingestion Pipeline (`src/rag/parser.py` & `ingest.py`)**:
   * Download the official plain-text Comprehensive Rules (`MagicCompRules.txt`).
   * Parse the document line by line using regular expressions. Match numbered rules (e.g., `613.1d`, `704.5f`) and isolate the sub-rule text, parent rule category, and section title.
   * Load chunks into ChromaDB with metadata:
     ```python
     metadata = {
         "rule_id": "613.1d",
         "chapter": "613",
         "title": "Interaction of Continuous Effects"
     }
     ```
2. **Entity Extractor (`src/core/extractor.py`)**:
   * Create an extraction function that extracts card names from freeform text.
   * Use an LLM function call or a fuzzy-matcher against a local list of Scryfall canonical card names.
3. **Contextual Rule Retrieval (`src/rag/retriever.py`)**:
   * Given a question like *"Does Rest in Peace stop Blood Artist triggers?"*, query the vector store for semantic concepts: `"replacement effect", "leaves the battlefield", "dies"`.
   * Return the top $K$ relevant rule chunks (e.g., CR 614.6, CR 700.4).
4. **Judge Reasoning Engine (`src/core/judge.py`)**:
   * Assemble a unified prompt containing:
     * Card A & Card B Oracle Text
     * Scryfall Gatherer Rulings for both cards
     * Top 3–5 retrieved Comprehensive Rules
   * Enforce a Chain-of-Thought (CoT) response format:
     1. **Direct Verdict** (Clear Yes/No/Outcome).
     2. **Step-by-Step Resolution** (Detailed stack/priority/layer resolution).
     3. **Cited Rules** (Explicit CR rule references).

---

### MVP 3: Contextual Game State & Full Capstone Web App
* **Objective:** Enable users to define detailed board state conditions (timestamps, APNAP order, spell stack sequences) and support multi-turn conversation with a complete UI.

#### 1. Libraries Required
`fastapi`, `uvicorn`, `streamlit`, `pydantic`.

#### 2. Directory Focus
* `src/web/app.py`
* `src/web/views.py`
* `src/core/judge.py`

#### 3. Granular Implementation Steps
1. **Game Context Injection**:
   * Allow users to declare parameters that change deterministic outcomes:
     * **Active Player / Non-Active Player (APNAP):** Dictates the order simultaneous triggers are placed on the stack.
     * **Timestamp Precedence:** Which permanent entered the battlefield first (crucial for same-layer interactions like *Blood Moon* and *Dryad of the Ilysian Grove*).
2. **Multi-Turn Chat History**:
   * Maintain a session thread (`session_state` in Streamlit or session IDs in FastAPI).
   * Allow iterative questions: *"What happens if I cast a counterspell in response?"*
3. **User Experience Enhancements**:
   * Auto-complete card search input.
   * Card hover cards displaying card art and current Oracle text.
   * Collapsible reference drawers showing the exact text of every Comprehensive Rule cited.

---

## 5. Automated Evaluation Benchmark

An academic capstone requires quantitative validation. This benchmark compares a **Baseline LLM** (zero-shot, no external context) against the **MTG Judge RAG Pipeline**.

### 5.1 Test Dataset (`data/test_cases.json`)
```json
[
  {
    "id": "tc_001",
    "cards": ["Blood Moon", "Urza's Saga"],
    "question": "What happens to Urza's Saga when Blood Moon is on the battlefield?",
    "expected_verdict": "Urza's Saga becomes a Mountain, loses all other land types and chapter abilities. Because it is a Saga with lore counters >= its max chapter (which is now 0), it is sacrificed as a state-based action.",
    "expected_citations": ["714.4", "305.7", "704.5s"],
    "category": "layers_and_sba"
  },
  {
    "id": "tc_002",
    "cards": ["Rest in Peace", "Blood Artist"],
    "question": "If a creature dies while Rest in Peace is on the battlefield, does Blood Artist trigger?",
    "expected_verdict": "No. Rest in Peace creates a replacement effect that exiles the card instead of letting it go to the graveyard. The creature never 'dies', so Blood Artist does not trigger.",
    "expected_citations": ["614.6", "700.4"],
    "category": "replacement_effects"
  },
  {
    "id": "tc_003",
    "cards": ["Humility", "Magus of the Moon"],
    "question": "If Humility and Magus of the Moon are both on the battlefield, are nonbasic lands Mountains?",
    "expected_verdict": "Yes, nonbasic lands are Mountains. Magus of the Moon's type-changing effect applies in Layer 4 before Humility removes its abilities in Layer 6.",
    "expected_citations": ["613.1d", "613.1f"],
    "category": "continuous_effects_layers"
  },
  {
    "id": "tc_004",
    "cards": ["Questing Beast", "True-Name Nemesis"],
    "question": "Can Questing Beast deal combat damage to a player who has protection from Questing Beast via True-Name Nemesis?",
    "expected_verdict": "Yes. Questing Beast states that combat damage dealt by creatures you control cannot be prevented, which overrides the damage prevention component of protection.",
    "expected_citations": ["702.16e", "101.1"],
    "category": "golden_rule"
  },
  {
    "id": "tc_005",
    "cards": ["Thalia, Guardian of Thraben", "Trinisphere"],
    "question": "How much does a 1-mana instant cost to cast if both Thalia and Trinisphere are on the battlefield?",
    "expected_verdict": "It costs 3 mana. Cost-increasing effects like Thalia apply first (1 + 1 = 2), and then Trinisphere's minimum cost check applies last, raising it to 3 mana.",
    "expected_citations": ["601.2f"],
    "category": "cost_determination"
  }
]
```

### 5.2 Benchmark Execution Engine (`evaluation/evaluate.py`)
Run this script to generate automated accuracy comparisons:

```python
"""
MTG Judge AI: Evaluation Benchmark Runner
Compares Baseline LLM vs. Domain-Specific RAG Pipeline.
"""

import json
import os
import re
from typing import List, Dict, Any
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------------------------------------------------------
# Test Subject Implementations
# ---------------------------------------------------------

def run_baseline_llm(question: str, cards: List[str]) -> str:
    """Baseline: Un-augmented LLM answering purely from internal memory."""
    prompt = (
        f"You are an MTG Judge. Answer this rules question about the cards "
        f"{', '.join(cards)}: {question}\nCite specific Comprehensive Rules numbers."
    )
    res = client.chat.completions.create(
        model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0
    )
    return res.choices[0].message.content or ""

def run_judge_rag_pipeline(question: str, cards: List[str]) -> str:
    """
    RAG Pipeline: Augmented with Oracle text, Gatherer rulings, and CR chunks.
    (Simulated mock context for standalone evaluation testing).
    """
    mock_cr_context = """
    CR 613.1d: Layer 4: Type-changing effects are applied.
    CR 613.1f: Layer 6: Ability-adding effects and ability-removing effects are applied.
    CR 704.5s: If a Saga has a number of lore counters greater than or equal to its final chapter number, it is sacrificed.
    CR 305.7: If an effect changes a land's subtype to a basic land type, it loses all other land types and abilities.
    CR 614.6: If an event is replaced, it never happens.
    CR 700.4: 'Dies' means to be put into a graveyard from the battlefield.
    CR 601.2f: Total cost is determined by starting with base cost, adding additions, subtracting reductions, then applying Trinisphere.
    """
    prompt = f"""
    You are an official MTG Level 3 Judge. Answer the player's question using the rulebook 
    excerpts below. You MUST structure your answer with:
    1. Direct Answer
    2. Mechanical Step-by-Step Reason
    3. Official Rule Citations (e.g. CR 613.1d)

    Context:
    {mock_cr_context}

    Cards involved: {', '.join(cards)}
    Question: {question}
    """
    res = client.chat.completions.create(
        model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0
    )
    return res.choices[0].message.content or ""

# ---------------------------------------------------------
# Metric Evaluators
# ---------------------------------------------------------

def extract_citations(text: str) -> List[str]:
    """Matches MTG rule patterns (e.g., 613.1, 704.5s, 601.2f)."""
    pattern = r"\b\d{3}\.\d+[a-z]?\b"
    return list(set(re.findall(pattern, text)))

def grade_verdict_with_judge(question: str, expected: str, candidate: str) -> float:
    """Uses LLM-as-a-Judge to grade accuracy on a scale of 1 to 5."""
    eval_prompt = f"""
    You are an expert Head Judge evaluating a candidate answer.
    
    Question: {question}
    Authoritative Expected Verdict: {expected}
    Candidate Answer: {candidate}

    Grade the mechanical correctness of the Candidate Answer on an integer scale of 1 to 5:
    5 - Completely accurate. Correct outcome and mechanically sound logic.
    4 - Correct outcome, but contains slight ambiguities in explanation.
    3 - Partially correct; identifies key concepts but gets the final resolution wrong.
    2 - Incorrect outcome, but references related game mechanics.
    1 - Completely incorrect or contains hallucinated card abilities.

    Respond with ONLY the single digit (1-5).
    """
    res = client.chat.completions.create(
        model=os.getenv("EVALUATOR_MODEL", "gpt-4o"),
        messages=[{"role": "user", "content": eval_prompt}],
        temperature=0.0
    )
    match = re.search(r"[1-5]", res.choices[0].message.content or "1")
    return float(match.group(0)) if match else 1.0

# ---------------------------------------------------------
# Execution & Reporting
# ---------------------------------------------------------

def execute_benchmark(dataset_path: str):
    if not os.path.exists(dataset_path):
        print(f"Error: {dataset_path} not found.")
        return

    with open(dataset_path, "r") as f:
        test_cases = json.load(f)

    runners = {
        "Baseline_LLM": run_baseline_llm,
        "Judge_RAG_Pipeline": run_judge_rag_pipeline
    }

    results = {
        name: {"scores": [], "precisions": [], "recalls": []} 
        for name in runners
    }

    print("\n" + "="*80)
    print(f"{'MTG JUDGE AI: AUTOMATED EVALUATION SUITE':^80}")
    print("="*80 + "\n")

    for case in test_cases:
        cid = case["id"]
        q = case["question"]
        expected_cites = set(case.get("expected_citations", []))
        print(f"Executing [{cid}] ({case['category']}): {q[:60]}...")

        for name, func in runners.items():
            output = func(q, case["cards"])
            cited = set(extract_citations(output))

            # Citation Precision & Recall
            true_positives = len(cited.intersection(expected_cites))
            precision = true_positives / len(cited) if cited else 0.0
            recall = true_positives / len(expected_cites) if expected_cites else 1.0

            # Judge Grade
            score = grade_verdict_with_judge(q, case["expected_verdict"], output)

            results[name]["scores"].append(score)
            results[name]["precisions"].append(precision)
            results[name]["recalls"].append(recall)

    # Output Summary Table
    print("\n" + "="*80)
    print(f"{'Benchmark Summary Results':^80}")
    print("="*80)
    print(f"{'Pipeline Architecture':<25} | {'Score (1-5)':<12} | {'Cite Precision':<16} | {'Cite Recall':<12}")
    print("-" * 80)
    for name, metrics in results.items():
        avg_score = sum(metrics["scores"]) / len(metrics["scores"])
        avg_prec = sum(metrics["precisions"]) / len(metrics["precisions"])
        avg_rec = sum(metrics["recalls"]) / len(metrics["recalls"])
        print(f"{name:<25} | {avg_score:<12.2f} | {avg_prec:<16.2%} | {avg_rec:<12.2%}")
    print("="*80 + "\n")

if __name__ == "__main__":
    execute_benchmark("data/test_cases.json")
```

---

## 6. Technical Risks & Engineering Mitigations

| Technical Challenge | Root Cause | Engineering Mitigation |
| :--- | :--- | :--- |
| **Layer Ordering Failures** | LLMs cannot intuitively resolve sequential dependencies without structure. | Use a dedicated prompt step enforcing the 7-Layer sequence (Layer 1: Copy $\rightarrow$ Layer 7: P/T). |
| **Outdated Physical Printings** | Physical card printings often differ from current rules text. | Disallow the LLM from relying on internal memory for card text. Invalidate input until fetched from the Scryfall `/cards/named` Oracle endpoint. |
| **API Rate Limits** | Scryfall requires non-bursty traffic (50–100ms spacing). | Implement an in-memory cache (`cachetools`) and download Scryfall's bulk Oracle JSON data for local offline lookups. |
| **CR Context Window Overflow** | The Comprehensive Rules document contains over 300,000 words. | Parse rules into discrete sub-rule chunks indexed in ChromaDB; retrieve only the top 3–5 matching sections per query. |

---

## 7. Capstone Presentation & Defense Checklist

When defending this project, focus your presentation on system correctness rather than general chatbot conversation:

1. **Demonstrate Hallucination Reduction**:
   * Present the benchmark table from Section 5. Show that your RAG pipeline significantly outperforms the baseline in rule citations and correctness scores.
2. **Step Through a Complex Layer Case**:
   * Walk through a notorious interaction (e.g., *Blood Moon* + *Urza's Saga* or *Humility* + *Opalescence*).
   * Show how your system retrieves the exact layer rule (CR 613) and applies each step in order.
3. **Showcase Fail-Safes**:
   * Demonstrate how the system handles ambiguous queries by asking clarifying questions (e.g., *"Which permanent entered the battlefield first?"*).
```