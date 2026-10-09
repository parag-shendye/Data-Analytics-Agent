"""Read questions from and write answers to Word documents."""
import pandas as pd

PLACEHOLDER = "placeholder - tool not implemented yet"

def read_questions(path: str) -> dict:
    """Questions found in a .docx (numbered paragraphs or table rows). Returns {"questions": [...]}."""
    return {"note": PLACEHOLDER, "questions": ["Which columns have missing values?"]}


def write_answers(path: str, answers: list[dict]) -> dict:
    """Write [{question, answer}] into a new .docx under output/. Returns {"path": ...}."""
    return {"note": PLACEHOLDER, "path": "output/placeholder.docx"}
