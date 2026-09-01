import os
from datetime import datetime

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch

load_dotenv()

required = ["TAVILY_API_KEY", "OPENAI_API_KEY", "LANGSMITH_API_KEY"]

missing = [name for name in required if not os.getenv(name)]

if missing:
    raise RuntimeError(
        f"Missing environment variables: {', '.join(missing)}"
    )

today = datetime.now().strftime("%B %d, %Y")

search_tool = TavilySearch(
    max_results=5,
    topic="general",
    search_depth="advanced",
    include_answer=False,
    include_raw_content=False,
)

model = ChatOpenAI(model="gpt-5-mini", temperature=0)
agent = create_agent(
    model=model,
    tools=[search_tool],
    system_prompt=f"""
    You are an enterprise research agent.
    Today's date is {today}.
    Use Tavily Search when the answer depends on current or external information.
    Prefer authoritative and primary sources.
    Do not claim more than the evidence supports.
    Include source URLs in the final answer.
    If evidence is weak, conflicting, or incomplete, say so explicitly.
    Evidence policy:
    - Use retrieved sources for factual claims.
    - Explicitly identify missing, conflicting, stale, or incomplete evidence.
    - Place each limitation next to the affected claim, not only in a closing disclaimer.
    - Do not infer exact limits, availability, security guarantees, or pricing when the sources do not establish them.
    - Label unsupported details as "Not established by the retrieved evidence."
    Before finalizing:
    - Break the user's question into its explicit requested dimensions and address each one.
    - Support every material claim directly with retrieved evidence.
    - If a requested dimension is not established by the evidence, say so rather than omitting it or speculating.
    """.strip(),
)


def run_agent(question: str) -> dict:
    return agent.invoke(
        {"messages": [{"role": "user", "content": question}]},

        config={
            "run_name": "tavily_enterprise_research_agent",
            "tags": ["tavily", "fde", "retrieval"],
            "metadata": {
                "environment": "development",
                "agent_version": "v2",
                "retrieval_policy": "advanced_search_no_raw_content",
            },
        },
    )


def final_text(result: dict) -> str:
    message = result["messages"][-1]
    return message.content if isinstance(message.content, str) else str(message.content)


if __name__ == "__main__":
    question = input("Question: ").strip()

    if not question:
        raise SystemExit("Please enter a question.")
    result = run_agent(question)
    print("\nAnswer:\n")
    print(final_text(result))
