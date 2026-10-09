import logging

from mcp.server.mcpserver import MCPServer

from delinquency_agent.config import settings
from delinquency_agent.data.loader import load_data
from delinquency_agent.tools import data_tools, dictionary_tools, quality_tools

logging.basicConfig(level=logging.INFO)

mcp = MCPServer(
    "delinquency-analyst",
    instructions=(
        "Tools for analysing a credit-card delinquency dataset (500 customers). "
        "Target column: Delinquent_Account (1 = delinquent). "
        "Use these tools for every figure; do not estimate numbers."
    ),
)

# Each function's name, type hints and docstring become the tool's name,
# input schema and description - the description is what the model reads
# to decide which tool to call.
TOOLS = [
    # what is in the data
    data_tools.get_schema,
    dictionary_tools.get_data_dictionary,
    data_tools.describe_column,
    data_tools.value_counts,
    # data quality
    quality_tools.missing_values,
    quality_tools.range_violations,
    quality_tools.check_payment_consistency,
    # relationship with delinquency
    data_tools.rate_by_group,
    data_tools.correlation_with_target,
    # Word input/output is not a tool: the client handles it (agent/report.py)
]

for tool in TOOLS:
    mcp.add_tool(tool)


# A resource is read-only context the client fetches (not something the model calls).
# The client reads this once and adds it to the system prompt.
@mcp.resource("dataset://overview", description="Columns, types and value ranges of the dataset", mime_type="text/plain")
def dataset_overview() -> str:
    schema = data_tools.get_schema()
    lines = [
        f"Dataset: {schema['rows']} customers, one row each. "
        f"Target: {schema['target']} (1 = delinquent, 0 = not).",
        "Columns:",
    ]
    for col in schema["columns"]:
        if col["type"] == "numeric":
            detail = f"numeric, {col['min']} to {col['max']}"
        elif col["type"] == "categorical":
            detail = "categorical: " + ", ".join(map(str, col["values"]))
        else:
            detail = col["type"]
        derived = f" [derived: {col['derived']}]" if col.get("derived") else ""
        lines.append(f"- {col['name']} ({detail}){derived}")
    return "\n".join(lines)


def main() -> None:
    load_data()  # load the Excel file at startup: fails fast if the path is wrong, first tool call is quick
    if settings.mcp_transport == "stdio":
        mcp.run()
    else:  # in this SDK version host/port are run() options, not constructor options
        mcp.run(transport=settings.mcp_transport, port=settings.mcp_port)


if __name__ == "__main__":
    main()
