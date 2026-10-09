# Data Analytics Agent

Learning project: an **MCP server** that exposes data-analysis tools over the delinquency dataset, used by an **Ollama model (Qwen)** as an agent to answer questions, including questions read from a Word document.

## Architecture

```
questions (.docx / chat)                      answers (.docx report)
        │                                              ▲
        ▼                                              │
  agent/client.py  ──────────────────────────► agent/report.py
        │   ◄──►  Ollama (Qwen, running in a container)
        │          decides which tools to call and writes the answer
        ▼  MCP (stdio / http)
  server.py  ── resource: dataset://overview (sent to the model as context)
             ── tools/
                 ├─ data_tools.py        schema, describe, value counts, rates, correlation
                 ├─ quality_tools.py     missing values, consistency rules
                 └─ dictionary_tools.py  column definitions from the PDF guide
```

Word input/output lives in the client, not in MCP tools: the model analyses, the application
reads questions and writes the report. Report tables are built from tool results, not model text.

**Rule:** the model never computes numbers itself. Every figure in an answer must come from a tool result.

## Experiment: let the model write pandas

Question: when should an agent write its own code instead of choosing from tested tools,
and how much does model size matter?

**Build**
- Add a `run_pandas(code: str)` tool. `df` is a copy of the dataset; the code must assign its answer to `result`.
- Restrict it:
  - no imports
  - no file, network or OS access
  - a timeout
  - result size capped
  - `df` is a copy, so the shared cached DataFrame can't be modified
- Return errors as text so the model can fix its code and retry.
- Log every generated snippet for review.

**Compare**
- Run a fixed question set (with known answers from the notebook) in three setups:
  1. fixed tools only
  2. `run_pandas` only
  3. both
- Models: `qwen3.5:2b` vs a larger Qwen (7–9B).
- Measure:
  - correct numbers
  - silent wrong answers (plausible but incorrect)
  - retries per question
  - time per question

**Watch for**
- Domain mistakes: using raw `Employment_Status` instead of `emp_clean`, mishandling missing values,
  ignoring the 12-month vs 6-month payment rule.
- Prompt injection: a question in a .docx that asks for harmful code.

**Follow-up**: any snippet the model writes repeatedly and correctly → review it and promote it to a fixed tool.

## Setup (uv)
```
cd delinquency_agent
uv sync                  # creates .venv, installs the project + dev group
copy .env.example .env   # then fill in the Ollama details
```

## Run
```
uv run pytest                                                   # tool tests
uv run mcp dev src/delinquency_agent/server.py                  # MCP Inspector
uv run python -m delinquency_agent.server                       # server alone (debug crashes)
uv run python -m delinquency_agent.agent.client "your question" # agent
```
