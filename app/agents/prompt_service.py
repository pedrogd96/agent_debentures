from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
PROMPTS_DIR = BASE_DIR / "prompts"

PROMPT_FILES = {
    "identification": "identification.md",
    "dates_values": "dates_values.md",
    "interest_correction": "interest_correction.md",
    "amortization": "amortization.md"
}


def load_prompt(stage: str) -> str:
    if stage not in PROMPT_FILES:
        raise ValueError(f"Etapa de extração inválida: {stage}")

    prompt_path = PROMPTS_DIR / PROMPT_FILES[stage]

    if not prompt_path.is_file():
        raise FileNotFoundError(f"Arquivo de prompt não encontrado: {prompt_path}")

    content = prompt_path.read_text(encoding="utf-8").strip()

    if not content:
        raise ValueError(f"O arquivo de prompt está vazio: {prompt_path.name}")

    return content