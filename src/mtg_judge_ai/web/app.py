import sys
from pathlib import Path

import random

import streamlit as st
from dotenv import dotenv_values
from google import genai
from google.genai import types

print("Python executable:", sys.executable)
print("Working directory:", Path.cwd())
print("Python path:", sys.path)


from mtg_judge_ai.api.scryfall import get_card_by_fuzzy_name
from mtg_judge_ai.core.prompts_service import (
    load_judge_prompt,
    load_user_prompt,
    format_rulings
)


# ----- Configuration -----

config = dotenv_values(".env.dev")
api_key = config.get("GEMINI_API_KEY", "")
JUDGE_SYSTEM_PROMPT = load_judge_prompt()
USER_QUESTION_TEMPLATE = load_user_prompt()
TEMPERATURE = 0.0
THINKING_BUDGET = 0


# ----- Spinner Messages -----
spinner_messages = [
    "Consulting the Judge's Handbook...",
    "Summoning official card rulings...",
    "Checking the Oracle database...",
    "Resolving the stack...",
    "Waiting for priority...",
    "Consulting the rules committee...",
    "Reading the fine print...",
    "Checking for replacement effects...",
    "Determining timestamps and layers...",
    "Investigating a possible rules interaction...",
    "Checking whether this triggers or activates...",
    "Calculating state-based actions...",
    "Asking the judges for clarification...",
    "Verifying the card's Oracle text...",
    "Checking for hidden interactions...",
    "Untangling the stack...",
    "Determining what happens next...",
    "Checking if this is a legal play...",
    "Reviewing the Comprehensive Rules...",
    "The battlefield is under investigation...",
    "Waiting for the active player to pass priority...",
    "Making sure nobody is cheating...",
    "Checking if APNAP order applies...",
    "Summoning a Level 3 Judge...",
    "Resolving layers of complexity...",
    "Making sense of this magical mess...",
    "Hold priority... the Judge is thinking.",
    "Someone activated something. Investigating...",
    "This interaction is getting complicated...",
    "Calling a judge! Just to be sure...",
    "Don't scoop yet. We're checking the rules.",
    "The stack is getting crowded...",
    "Reading the Comprehensive Rules so you don't have to...",
    "A judge has entered the battlefield.",
    "This is not how layers work... or is it?",
    "No shortcuts. We're checking everything.",
    "Your opponent claims it's legal. Let's verify.",
    "Gathering evidence before issuing a ruling...",
]



# ----- Set up our Streamlit App -----
st.set_page_config(page_title="MTG Judge QA - MVP 1", layout="wide", page_icon="⚖️")
st.title("⚖️ MTG Judge Assistant (MVP 1)")
st.caption("Ask questions about card mechanics, backed by official Scryfall & Gatherer rulings.")


# ------ Gemini Client Setup -----
if not api_key:
    api_key_input = st.sidebar.text_input("Gemini API Key", type="password")

client = genai.Client(api_key=api_key) if api_key else None

if not client:
    st.warning("Please provide your Gemini API key in your .env or through the sidebar.")


# ----- Input Form -----
with st.form("judge_query_form"):
    col1, col2 = st.columns([1, 2])
    with col1:
        card_name = st.text_input("Card Name", value="Blood Moon", placeholder="e.g. Urza's Saga")
    with col2:
        question = st.text_input(
            "Rules Question",
            value="What happens when this enters the battlefield while Urza's Saga is in play?",
            placeholder="e.g. Does this trigger if...",
        )
    submitted = st.form_submit_button("Judge Call", use_container_width=True)


# ----- Handle Submission -----
if submitted:
    if not card_name.strip() or not question.strip():
        st.error("Please enter both a card name and a question.")
    elif not client:
        st.error("GeminiAI client is not configured. Add an API key.")
    else:
        with st.spinner(random.choice(spinner_messages)):
            try:
                card = get_card_by_fuzzy_name(card_name)
            except ValueError as e:
                st.error(str(e))
                card = None
            except Exception as e:
                st.error(f"Error communicating with Scryfall: {e}")
                card = None

        if card:
            # Layout: Left column for card visual & oracle text, Right column for QA
            left_col, right_col = st.columns([1, 2])

            # ----- Card Information -----
            with left_col:
                if card.image_uri:
                    st.image(card.image_uri, use_container_width=True)
                st.markdown(f"**{card.name}** {card.mana_cost}")
                st.caption(card.type_line)
                st.info(card.oracle_text if card.oracle_text else "*No oracle text.*")

                with st.expander(f"Official Rulings ({len(card.rulings)})"):
                    if card.rulings:
                        for r in card.rulings:
                            st.markdown(f"**{r.published_at}** ({r.source})")
                            st.write(r.comment)
                            st.divider()
                    else:
                        st.write("No official rulings found.")


            # ----- AI Judge Response -----
            with right_col:
                st.subheader("Judge Ruling")
                with st.spinner(random.choice(spinner_messages)):
                    rulings_text = format_rulings(card.rulings)
                    prompt_content = USER_QUESTION_TEMPLATE.format(
                        card_name=card.name,
                        mana_cost=card.mana_cost,
                        type_line=card.type_line,
                        oracle_text=card.oracle_text,
                        rulings_text=rulings_text,
                        question=question,
                    )

                    try:
                        response = client.models.generate_content(
                            model=config.get("MODEL_NAME", "gemini-2.5-flash"),
                            contents=prompt_content,  # Plain string is valid for the user prompt
                            config=types.GenerateContentConfig(
                                system_instruction=JUDGE_SYSTEM_PROMPT,
                                temperature=TEMPERATURE,
                                thinking_config=types.ThinkingConfig(thinking_budget=THINKING_BUDGET),
                            ),
                        )
                        answer = response.text
                        st.markdown(answer)
                    except Exception as e:
                        st.error(f"Failed to generate answer from GeminiAI: {e}")