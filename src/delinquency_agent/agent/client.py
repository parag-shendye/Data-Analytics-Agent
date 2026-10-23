"""Agent loop: connects Ollama to the MCP server.

Run:  uv run python -m delinquency_agent.agent.client "Which fields have missing values?"
      uv run python -m delinquency_agent.agent.client "..." --out output/answer.docx
      uv run python -m delinquency_agent.agent.client --docx questions.docx
      uv run python -m delinquency_agent.agent.client --build "Write a tool that counts missing values per column"
"""

import argparse
import asyncio
import json
import sys
from contextlib import asynccontextmanager

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from ollama import AsyncClient

from delinquency_agent.agent.prompts import BUILDER_PROMPT, SYSTEM_PROMPT
from delinquency_agent.agent.report import read_questions, write_report
from delinquency_agent.config import settings

MAX_STEPS = 8         # safety cap on tool-calling rounds per question
BUILD_MAX_STEPS = 12  # writing a tool may need a few fix-and-resubmit rounds
BUILDER_TOOLS = {"pandas_docs", "create_tool"}  # only visible in --build mode


# ---------------------------------------------------------------- level 1: entry point

def main() -> None:
    args = parse_args()
    asyncio.run(run(args))


async def run(args: argparse.Namespace) -> None:
    async with connect_to_server() as session:
        all_tools = await get_ollama_tools(session)
        # Permanent context: the dataset overview is read once and sent with every question,
        # so the model knows the columns before it picks a tool.
        overview = await get_dataset_overview(session)
        llm = AsyncClient(host=settings.ollama_host)

        if args.build:
            # Build mode: the model sees only the builder tools, so it must write a tool
            # instead of reusing an existing one.
            tools = [t for t in all_tools if t["function"]["name"] in BUILDER_TOOLS]
            result = await answer_question(llm, session, tools, BUILDER_PROMPT + "\n\n" + overview,
                                           args.build, max_steps=BUILD_MAX_STEPS)
            print(f"\n{result['answer']}\n\nReview with: uv run python -m delinquency_agent.tools.ai_tools.review list")
            return

        tools = [t for t in all_tools if t["function"]["name"] not in BUILDER_TOOLS]
        system_prompt = SYSTEM_PROMPT + "\n\n" + overview

        # Word input/output is handled here in the client, not by MCP tools:
        # the model only analyses, the application reads questions and writes the report.
        questions = read_questions(args.docx) if args.docx else [args.question]
        results = []
        for question in questions:
            result = await answer_question(llm, session, tools, system_prompt, question)
            print(f"\nQ: {question}\n{result['answer']}\n")
            results.append(result)

        if args.docx or args.out:
            print("Saved:", write_report(results, args.out))


# ---------------------------------------------------------------- level 2: the agent loop

async def answer_question(llm: AsyncClient, session: ClientSession, tools: list[dict],
                          system_prompt: str, question: str, max_steps: int = MAX_STEPS) -> dict:
    """Ask the model, run any tools it requests, feed results back, repeat until it answers.

    Returns {question, answer, tool_results}; tool_results keep the raw data so the
    report can build tables from it instead of trusting tables written by the model.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]
    tool_results = []

    for step in range(max_steps):
        response = await llm.chat(model=settings.ollama_model, messages=messages, tools=tools)
        messages.append(response.message)

        if not response.message.tool_calls:  # no tool requested -> final answer
            return {"question": question, "answer": response.message.content, "tool_results": tool_results}

        for call in response.message.tool_calls:
            result = await call_tool(session, call.function.name, call.function.arguments)
            log_tool_call(step, call.function.name, call.function.arguments, result)
            messages.append({"role": "tool", "tool_name": call.function.name, "content": result})
            tool_results.append({"tool": call.function.name, "data": parse_json(result)})

    return {"question": question, "answer": "Stopped: too many tool calls without a final answer.",
            "tool_results": tool_results}



def parse_args() -> argparse.Namespace:
    """question (positional, optional) or --docx PATH; --out PATH to save a Word report."""
    parser = argparse.ArgumentParser(description="Ask the delinquency analyst agent.")
    parser.add_argument("question", nargs="?", help="a single question to answer")
    parser.add_argument("--docx", help="Word document with questions to answer")
    parser.add_argument("--out", help="where to save the Word report (default: output/answers_<time>.docx)")
    parser.add_argument("--build", metavar="TASK", help="ask the model to write a new tool (saved for review)")
    args = parser.parse_args()
    if not (args.question or args.docx or args.build):
        parser.error("give a question, --docx PATH or --build TASK")
    return args


@asynccontextmanager
async def connect_to_server():
    params = StdioServerParameters(command=sys.executable, args=["-m", "delinquency_agent.server"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize() 
            yield session


async def get_ollama_tools(session: ClientSession) -> list[dict]:
    listing = await session.list_tools()
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.input_schema,  # JSON Schema, generated by MCPServer from type hints
            },
        }
        for tool in listing.tools
    ]


async def get_dataset_overview(session: ClientSession) -> str:
    result = await session.read_resource("dataset://overview")
    return "\n".join(block.text for block in result.contents if hasattr(block, "text"))


async def call_tool(session: ClientSession, name: str, arguments: dict) -> str:
    """Call an MCP tool and return its result as text for the model (errors as text too)."""
    try:
        result = await session.call_tool(name, arguments or {})
    except Exception as e:  # unknown tool, bad arguments, server crash
        return f"Tool error: {e}"
    text = "\n".join(block.text for block in result.content if block.type == "text")
    # Return errors as text so the model can see them and retry with corrected arguments
    return f"Tool error: {text}" if result.is_error else text


def log_tool_call(step: int, name: str, arguments: dict, result: str) -> None:
    """Print which tool the model used, with what arguments, and a preview of the result."""
    preview = result if len(result) <= 200 else result[:200] + "..."
    print(f"[step {step}] {name}({json.dumps(arguments)})\n    -> {preview}", file=sys.stderr)


def parse_json(text: str) -> dict | None:
    """Tool results are JSON dicts; errors are plain text and give None."""
    try:
        return json.loads(text)
    except ValueError:
        return None


if __name__ == "__main__":
    main()
