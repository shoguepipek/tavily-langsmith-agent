import re
from urllib.parse import urlparse

from dotenv import load_dotenv
from langsmith import Client
from openevals.llm import create_llm_as_judge
from openevals.prompts import RAG_GROUNDEDNESS_PROMPT

from app import final_text, run_agent

load_dotenv()

DATASET_NAME = "tavily-fde-retrieval-v1-clean"

TASK_SUCCESS_PROMPT = """
You are evaluating whether an enterprise retrieval agent completed
the customer's requested task.

Question:
{inputs}

Agent answer:
{outputs}

Expected behavior:
{reference_outputs}

Assign a passing score only if the answer directly addresses the
question and substantially satisfies the expected task requirements.

Do not award a passing score merely because the answer is polished,
contains citations, or discusses the general topic.
"""


task_success_judge = create_llm_as_judge(
    prompt=TASK_SUCCESS_PROMPT,
    model="openai:gpt-5-mini",
    feedback_key="task_success",
)

claim_grounding_judge = create_llm_as_judge(
    prompt=RAG_GROUNDEDNESS_PROMPT,
    model="openai:gpt-5-mini",
    feedback_key="claim_grounding",
)


def target(inputs: dict) -> dict:
    result = run_agent(inputs["question"])

    evidence = "\n\n".join(
        str(message.content)
        for message in result["messages"]
        if getattr(message, "type", "") == "tool"
    )

    return {
        "answer": final_text(result),
        "evidence": evidence,
    }


def task_success(
    inputs: dict,
    outputs: dict,
    reference_outputs: dict,
) -> dict:
    return task_success_judge(
        inputs=inputs,
        outputs={
            "answer": outputs.get("answer", ""),
        },
        reference_outputs={
            "task_requirements": reference_outputs.get(
                "task_requirements",
                "",
            ),
        },
    )


def claim_grounding(
    outputs: dict,
    reference_outputs: dict,
) -> dict:
    must_use_search = reference_outputs.get(
        "must_use_search",
        False,
    )

    if not must_use_search:
        return {
            "key": "claim_grounding",
            "score": 1,
            "comment": (
                "Retrieved evidence was not required for this test case."
            ),
        }

    evidence = outputs.get("evidence", "")
    answer = outputs.get("answer", "")

    if not evidence.strip():
        return {
            "key": "claim_grounding",
            "score": 0,
            "comment": (
                "The test required retrieval, but no tool evidence "
                "was captured."
            ),
        }

    return claim_grounding_judge(
        context=evidence,
        outputs=answer,
    )


def extract_domains(text: str) -> set[str]:
    """Extract normalized domain names from URLs in an answer."""

    urls = re.findall(r"https?://[^\s)\]>]+", text)

    return {
        urlparse(url.rstrip(".,;")).netloc.lower().removeprefix("www.")
        for url in urls
    }


def citation_requirements(
    outputs: dict,
    reference_outputs: dict,
) -> list[dict]:
    """Check for citations and required authoritative domains."""

    answer = outputs.get("answer", "")
    found_domains = extract_domains(answer)

    required_domains = {
        domain.lower().removeprefix("www.")
        for domain in reference_outputs.get("required_domains", [])
    }

    return [
        {
            "key": "citation_presence",
            "score": int(
                bool(found_domains)
                or not required_domains
            ),
        },
        {
            "key": "required_source_authority",
            "score": int(
                not required_domains
                or bool(found_domains.intersection(required_domains))
            ),
        },
    ]


def uncertainty_handling(
    outputs: dict,
    reference_outputs: dict,
) -> bool:
    must_disclose = reference_outputs.get(
        "must_disclose_uncertainty",
        False,
    )

    if not must_disclose:
        return True

    answer = outputs.get("answer", "").lower()

    indicators = [
        "cannot conclude",
        "not established",
        "insufficient evidence",
        "public sources do not",
        "contract-specific",
        "not publicly available",
        "could not verify",
        "unclear",
    ]

    return any(
        indicator in answer
        for indicator in indicators
    )


def retrieval_behavior(
    outputs: dict,
    reference_outputs: dict,
) -> dict:
    evidence = outputs.get("evidence", "").strip()
    retrieved = bool(evidence)

    must_use_search = reference_outputs.get(
        "must_use_search",
        False,
    )

    return {
        "key": "retrieval_behavior",
        "score": int(retrieved == must_use_search),
    }


def main() -> None:
    client = Client()

    results = client.evaluate(
        target,
        data=DATASET_NAME,
        evaluators=[
            task_success,
            citation_requirements,
            claim_grounding,
            retrieval_behavior,
            uncertainty_handling,
        ],
        experiment_prefix="tavily-agent-v2-clean",
        metadata={
            "agent_version": "v2",
            "retrieval_policy": "advanced_search_no_raw_content",
            "bounded_change": "completion_and_grounding_check",
        },
    )

    results.wait()
    print(results)


if __name__ == "__main__":
    main()
