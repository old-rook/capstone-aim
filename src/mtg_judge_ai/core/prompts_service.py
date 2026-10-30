from importlib import resources

from mtg_judge_ai.core.schemas import CardRuling


def load_judge_prompt() -> str:
    judge_prompt = resources.files("mtg_judge_ai.prompts").joinpath("JUDGE_SYSTEM_PROMPT.md")
    return judge_prompt.read_text(encoding="utf-8")

def load_user_prompt() -> str:
    user_prompt = resources.files("mtg_judge_ai.prompts").joinpath("USER_PROMPT_TEMPLATE.md")
    return user_prompt.read_text(encoding="utf-8")

def format_rulings(rulings: list[CardRuling]) -> str:
    if not rulings:
        return "No official rulings available for this card."
    return "\n".join(f"- [{r.published_at}] {r.comment}" for r in rulings)
