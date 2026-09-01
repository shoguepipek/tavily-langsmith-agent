from dotenv import load_dotenv
from langsmith import Client
from langsmith.utils import LangSmithNotFoundError

load_dotenv()

DATASET_NAME = "tavily-fde-retrieval-v1-clean"

examples = [
    {
        "inputs": {
            "question": (
                "What search-depth options does Tavily Search support? "
                "Prefer official Tavily documentation."
            )
        },
        "outputs": {
            "required_domains": ["docs.tavily.com"],
            "must_use_search": True,
            "must_disclose_uncertainty": False,
            "task_requirements": (
                "Identify the supported search-depth options and explain "
                "their principal relevance, latency, and cost tradeoffs."
            ),
        },
    },
    {
        "inputs": {
            "question": (
                "What are Tavily's most recent officially announced "
                "product capabilities?"
            )
        },
        "outputs": {
            "required_domains": [
                "tavily.com",
                "docs.tavily.com",
            ],
            "must_use_search": True,
            "must_disclose_uncertainty": True,
            "task_requirements": (
                "Identify recent officially announced capabilities, "
                "include dates when available, and avoid presenting "
                "undated or third-party claims as current announcements."
            ),
        },
    },
    {
        "inputs": {
            "question": (
                "When should an enterprise retrieval agent use "
                "Search versus Extract?"
            )
        },
        "outputs": {
            "required_domains": ["docs.tavily.com"],
            "must_use_search": True,
            "must_disclose_uncertainty": False,
            "task_requirements": (
                "Explain that Search discovers relevant sources when URLs "
                "are not yet known, while Extract retrieves cleaned content "
                "from URLs already selected."
            ),
        },
    },
    {
        "inputs": {
            "question": (
                "Is Tavily always the correct retrieval operation for "
                "every enterprise research task?"
            )
        },
        "outputs": {
            "required_domains": [],
            "must_use_search": False,
            "must_disclose_uncertainty": False,
            "task_requirements": (
                "Answer no and explain that operation selection depends "
                "on whether the workflow needs discovery, extraction, "
                "site mapping, crawling, or deeper research."
            ),
        },
    },
    {
        "inputs": {
            "question": (
                "What exact availability SLA does Tavily guarantee to "
                "every enterprise customer today? Prefer official sources."
            )
        },
        "outputs": {
            "required_domains": [
                "tavily.com",
                "docs.tavily.com",
            ],
            "must_use_search": True,
            "must_disclose_uncertainty": True,
            "task_requirements": (
                "Search for authoritative evidence but do not infer a "
                "universal SLA if public sources do not establish one. "
                "Distinguish public evidence from contract-specific terms."
            ),
        },
    },
]


def main() -> None:
    client = Client()

    try:
        dataset = client.read_dataset(dataset_name=DATASET_NAME)
        print(f"Dataset already exists: {dataset.name}")

    except LangSmithNotFoundError:
        dataset = client.create_dataset(
            dataset_name=DATASET_NAME,
            description=(
                "Enterprise retrieval-agent evaluation: "
                "task success, citation presence, required source authority, "
                "claim grounding, retrieval behavior, "
                "and uncertainty handling."
            ),
        )

        client.create_examples(
            dataset_id=dataset.id,
            examples=examples,
        )

        print(f"Created dataset: {dataset.name}")


if __name__ == "__main__":
    main()
