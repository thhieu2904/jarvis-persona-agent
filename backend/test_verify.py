"""
E2E Agent Test — Gemini 3 Flash + All Tools (Academic + Web + Image).

Run: python test_verify.py
"""

import asyncio
import os
import sys
import io

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage

from app.features.academic.tools import academic_tools
from app.features.agent.tools.web_search import web_tools
from app.features.agent.tools.image_gen import image_tools
from app.features.agent.prompts import build_system_prompt

ALL_TOOLS = academic_tools + web_tools + image_tools
SYSTEM_PROMPT = build_system_prompt()


def extract_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                parts.append(item["text"])
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts)
    return str(content)


async def run_query(agent, query: str, test_name: str):
    print(f"\n{'=' * 60}")
    print(f"TEST: {test_name}")
    print(f"USER: {query}")
    print(f"{'=' * 60}")

    result = await agent.ainvoke({"messages": [HumanMessage(content=query)]})

    for msg in result["messages"]:
        role = msg.__class__.__name__.replace("Message", "")
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            tools = [tc["name"] for tc in msg.tool_calls]
            print(f"  [{role}] -> Calling: {tools}")
        elif hasattr(msg, "name") and msg.name:
            text = extract_text(msg.content)
            preview = text[:150] + "..." if len(text) > 150 else text
            print(f"  [Tool:{msg.name}] {preview}")
        elif role == "AI":
            text = extract_text(msg.content)
            if text:
                print(f"  [{role}] {text[:250]}")

    final = extract_text(result["messages"][-1].content)
    print(f"\nANSWER: {final[:400]}")
    return final


async def main():
    model_name = os.getenv("LLM_MODEL", "gemini-3-flash-preview")
    temperature = float(os.getenv("LLM_TEMPERATURE", "1.0"))

    llm = ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=os.getenv("LLM_API_KEY"),
        temperature=temperature,
    )

    agent = create_react_agent(model=llm, tools=ALL_TOOLS, prompt=SYSTEM_PROMPT)

    print("=" * 60)
    print(f"Model: {model_name} | Temp: {temperature}")
    print(f"Tools: {[t.name for t in ALL_TOOLS]}")
    print("=" * 60)

    # Test 1: Academic
    await run_query(agent, "GPA tich luy cua minh la bao nhieu?", "Academic: get_grades")

    # Test 2: Web search
    await run_query(agent, "Gia vang SJC hom nay bao nhieu?", "Web: search_web")

    # Test 3: No tool
    await run_query(agent, "Ban la ai?", "No tool: self-intro")

    # Test 4: Image generation
    await run_query(agent, "Ve cho minh hinh mascot dai hoc Tra Vinh", "Image: generate_image")

    # Test 5: Mixed
    await run_query(agent, "Cho minh xem diem HK gan nhat, roi tim tin tuc moi ve tuyen sinh Tra Vinh", "Mixed: multi-tool")

    print(f"\n{'=' * 60}")
    print("ALL TESTS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
