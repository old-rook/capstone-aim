
# 🧙‍♂️ MTG Judge AI (`capstone-aim`)

An AI-assisted Magic: The Gathering (MTG) judge built to evaluate intricate card interactions, layer systems, timing conflicts, and tournament policy in real time.
**THIS IS NOT AN OFFICIAL WOTC PRODUCT.**

Powered by **Google Gemini** models and delivered through an interactive **Streamlit** user interface.

---

## 📌 Project Overview

Magic: The Gathering features one of the most complex, comprehensive rule sets in gaming history (over 200 pages of Comprehensive Rules, including layers, continuous effects, and state-based actions). 

**MTG Judge AI** is designed to serve as an on-demand rules advisor for players, judges, and tournament organizers. It translates natural-language game state queries (such as *"What happens when Blood Moon enters while Urza's Saga is in play?"*) into accurate, rules-grounded rulings referencing official Comprehensive Rules (CR).

---

## ✨ Features

- **Accurate Rules Dissection:** Uses Google Gemini (`gemini-3.8-flash` / `gemini-2.5-flash`) guided by a tailored `JUDGE_SYSTEM_PROMPT` to analyze game actions, layers, and timestamps.
- **Configurable Reasoning (Thinking Budget):** Adjust the model's internal thinking budget dynamically to balance near-instant responses with deep chain-of-thought analysis for complex board states.
- **Multi-Environment Architecture:** Built-in configuration pipeline supporting **DEV**, **UAT**, and **PROD** environments via `.toml` configuration files.

### Under Development Features:
- **Non-Blocking Dynamic UI:** Implements multi-threaded request handling (`ThreadPoolExecutor`) in Streamlit with dynamic, cycling status spinners while the model evaluates queries.
- **Multi-card interaction:** Support for interaction and complex rules between two or more cards (*e.g. I have Card A and Card B. I cast Card C and opponent responds with casting Card D*).

---

## 🛠️ Tech Stack

- **Frontend / App Framework:** [Streamlit](https://streamlit.io/)
- **LLM Engine:** [Google GenAI SDK](https://github.com/googleapis/python-genai) (`google-genai`)
- **Model:** `gemini-3.8-flash` / `gemini-2.5-flash`
- **Concurrency:** Python `concurrent.futures`
- **Config & Secrets Management:** TOML (`tomllib`)

---

## 📁 Repository Structure

```text
capstone-aim/
├── src
│   ├── mtg_judge_ai
│   │   ├── api
│   │   │   └── scryfall.py 
│   │   ├── core
│   │   │   ├── prompts_service.py 
│   │   │   └── schemas.py 
│   │   ├── prompts
│   │   │   ├── JUDGE_SYSTEM_PROMPT.md 
│   │   │   └── USER_PROMPT_TEMPLATE.md
│   │   └── web
│   │       └── app.py
├── tests
│   └── test_api.py
├── .env.example
├── .gitignore
├── .README.md
└── pyproject.toml
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+
- A Google Gemini API Key from [Google AI Studio](https://aistudio.google.com/)

### 2. Clone the Repository
```bash
git clone https://github.com/old-rook/capstone-aim.git
cd capstone-aim
```

### 3. Set Up Virtual Environment
```bash
python -m venv venv

# On Linux/macOS:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 4. Install Dependencies (*TO FOLLOW*)
```bash
pip install -r requirements.txt
```

---

## ⚙️ Configuration & Secrets

### Environment
Use the `.env.example` and update with your own `Gemini API Key`

```toml
GEMINI_API_KEY = "your-google-ai-studio-api-key-here"
```

### PyProject Settings (`pyproject.toml`)
The application uses environment-driven configuration to manage model parameters across deployment stages:

```toml
[app]
name = "MTG Judge AI"

[environments.dev]
model_name = "gemini-3.8-flash"
temperature = 0.0
thinking_budget = 0       # Low latency for rapid UI iteration
debug = true

[environments.uat]
model_name = "gemini-3.8-flash"
temperature = 0.0
thinking_budget = 512     # Balanced reasoning for testing
debug = false

[environments.prod]
model_name = "gemini-3.8-flash"
temperature = 0.0
thinking_budget = 1024    # Deep reasoning budget for high accuracy
debug = false
```

Set your active environment with an environment variable (defaults to `dev` if omitted):
```bash
export APP_ENV=dev   # Or 'uat', 'prod'
```

---

## 🖥️ Running the Application

Launch the Streamlit web server:

```bash
streamlit run src/mtg_judge_ai/web/app.py
```

The application will be accessible at `http://localhost:8501`.

---

## 🧪 Example Test Scenarios

Try asking the judge these complex interactions to verify reasoning:

1. **Layers & State-Based Actions:**
   > *"What happens when Blood Moon enters the battlefield while Urza's Saga is already in play?"*
   > - *Expected:* Urza's Saga loses its abilities, becomes an Enchantment Land — Mountain Saga with final chapter 0, and is sacrificed immediately via SBA.
2. **APNAP Order & Triggers:**
   > *"Both players control a Sheoldred, the Apocalypse and a forced draw effect triggers. In what order do the abilities resolve?"*
3. **Replacement Effects & Layers:**
   > *"How do Humility and Opalescence interact when entering the battlefield in different timestamp orders?"*

---

## 🛡️ License

This project is developed for academic capstone purposes under the AIM curriculum. Open-sourced under the [MIT License](LICENSE).
```