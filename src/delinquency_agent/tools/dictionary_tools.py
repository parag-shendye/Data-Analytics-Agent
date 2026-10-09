"""Column definitions from the data dictionary PDF."""

PLACEHOLDER = "placeholder - tool not implemented yet"


def get_data_dictionary(column: str | None = None) -> dict:
    """Official definition of a column from the dataset guide.
    Pass an exact column name, or leave empty to get all definitions."""
    return {"note": PLACEHOLDER, "tool": "get_data_dictionary", "column": column}
