# Build Record

This document records how I developed and verified the Tavily + LangSmith Retrieval Agent. It is a decision log rather than a raw transcript: it captures the important prompts, engineering choices, evidence, failures, and corrections that shaped the submission.

## Objective

I chose Option 1 of the Tavily FDE take-home: meaningfully improve the starter agent for a real enterprise use case.

My target user is a technical enterprise customer who needs current, source-backed research and must be able to inspect answer quality, execution behavior, latency, token usage, and cost before promoting an agent change.

The improvement focused on four connected capabilities:

1. Evidence-first retrieval with Tavily Search
2. Explicit source and uncertainty policies
3. LangSmith tracing and evaluation
4. A repeatable V1-to-V2 improvement loop

## Tools and responsibilities

I used:

- **Python** for the application and evaluation scripts;
- **LangChain** for agent orchestration;
- **OpenAI** for agent reasoning and model-based evaluation;
- **Tavily Search** for current external evidence;
- **LangSmith** for traces, datasets, evaluators, and experiments;
- **Git and GitHub** for version control and delivery; and
- **ChatGPT/Codex** as a coding and reasoning partner.

The AI partner helped with implementation, unfamiliar APIs, debugging, and evaluation patterns. I chose the problem, designed the test cases and evaluators, inspected the traces and evaluator comments, decided what to change, and verified the final results.

I did not treat generated code or prose as correct by default. I ran the application, inspected LangSmith traces, opened evaluator reasoning, compared experiments, corrected defects, and documented regressions rather than hiding them.

## Development sequence

### 1. Established a reproducible local environment

I initially created a virtual environment with the macOS system Python 3.9.6. After identifying that mismatch, I rebuilt `.venv` using the installed `uv` Python 3.13.15 runtime and verified that the active `python` executable resolved inside the project environment.

### 2. Built the first traced retrieval agent

I created a small CLI using `create_agent`, `ChatOpenAI`, and `TavilySearch`. The initial system policy required the agent to:

- use Tavily for current or external information;
- prefer authoritative and primary sources;
- avoid claims beyond the retrieved evidence;
- include source URLs; and
- disclose weak, conflicting, or incomplete evidence.

I added LangSmith run names, tags, and metadata so I could distinguish agent versions and retrieval policies in traces.

### 3. Verified the execution path in LangSmith

I traced a question from user input through:

1. the root agent run;
2. the first model call;
3. Tavily tool selection and arguments;
4. the `tavily_search` tool run and result;
5. the final model call; and
6. the source-attributed answer.

This confirmed the role of each component:

- `TavilySearch` is the Python integration object;
- `tavily_search` is the agent-facing tool name and traced run; and
- the Tavily Search API is the external retrieval service.

I also inspected latency, tokens, cost, tool-call count, tags, and metadata instead of looking only at the final response.

### 4. Designed a deliberate five-case dataset

I created a compact dataset covering different failure surfaces:

1. Official documentation lookup
2. Fresh product information
3. Search-versus-Extract comparison
4. A conceptual question where retrieval should be unnecessary
5. A deliberately difficult SLA question requiring uncertainty disclosure

Each example contains expected behavior rather than a single ideal paragraph. Reference fields specify requirements such as authoritative domains, whether search is expected, whether uncertainty must be disclosed, and what constitutes task completion.

### 5. Refined the evaluation rubric

The initial framing emphasized authority, grounding, citations, tool use, and uncertainty. I revised it after asking what each score could honestly prove.

The final experiment reports:

- `task_success`
- `citation_presence`
- `required_source_authority`
- `claim_grounding`
- `retrieval_behavior`
- `uncertainty_handling`

I intentionally did not combine these into a weighted score. A weighted average could allow a critical grounding failure to be hidden by several easy passes.

I also kept the evaluator claims narrow:

- URL extraction establishes that the answer contains a URL, not that the source supports a nearby claim.
- Domain matching establishes that at least one answer URL matches an expected domain.
- Retrieval behavior establishes whether a Tavily tool result was present when search was expected, not whether the query or returned results were good.
- The model judge assesses whether the answer is grounded in the captured Tavily evidence.

### 6. Corrected an evaluation execution issue

My first evaluation command returned an `ExperimentResults` object before all model-based feedback had finished. Adding `results.wait()` made the script wait for asynchronous evaluator completion and exposed stored evaluator failures rather than making a partially evaluated experiment look complete.

I also encountered a LangSmith error when attempting to pass `experiment_prefix` while evaluating an existing experiment. I corrected the call by treating creation of a new experiment and attachment of evaluators to an existing experiment as different operations.

### 7. Diagnosed V1 from evaluator reasoning

The V1 experiment produced the following aggregate quality results:

| Signal | V1 |
| --- | ---: |
| Citation presence | 1.00 |
| Claim grounding | 0.80 |
| Required source authority | 0.80 |
| Retrieval behavior | 0.80 |
| Task success | 0.80 |
| Uncertainty handling | 1.00 |

The most useful failure was the search-depth case. I opened the evaluator comments rather than stopping at the red scores.

The grounding evaluator found that most core claims were supported but that the answer incorrectly grouped `fast` with an unsupported value, despite the retrieved changelog mentioning `fast` historically.

The task-success evaluator found a different failure: the answer did not satisfy the evaluation requirement to explain relevance, latency, and cost dimensions. This showed that an answer can contain sources and still fail a defined evaluation criterion.

### 8. Made one bounded V2 change

I added a short pre-finalization instruction requiring the agent to:

- break the question into its explicit requested dimensions;
- support each material claim with evidence; and
- disclose when a requested detail is not established.

I did not change the model, Tavily configuration, test dataset, or evaluators. Holding those variables constant allowed a meaningful V1-to-V2 comparison.

### 9. Compared quality and operational tradeoffs

V2 improved both targeted quality signals:

| Signal | V1 | V2 |
| --- | ---: | ---: |
| Claim grounding | 0.80 | 1.00 |
| Task success | 0.80 | 1.00 |

The target search-depth case also became faster and used fewer tokens. Across the complete five-case dataset, however, V2 was less efficient overall:

| Metric | V1 | V2 | Change |
| --- | ---: | ---: | ---: |
| Median latency | 44.48 s | 66.36 s | +49% |
| Total tokens | 115,426 | 192,301 | +67% |
| Total cost | $0.0380 | $0.0549 | +44% |

I kept this regression in the submission because it is an important engineering result. V2 fixed the two failed checks in the targeted case, but it is not automatically the best production policy for every request.

## Key decisions

### Why use Tavily Search?

The agent needs current external evidence. Tavily supplies ranked, LLM-oriented search results and source metadata without requiring the agent application to implement its own search-and-scrape pipeline.

### Why use LangSmith?

The application needed semantic observability: model decisions, tool arguments, retrieved evidence, final outputs, evaluator feedback, and experiment comparisons. Infrastructure monitoring alone would not explain why a fluent answer was ungrounded or incomplete.

### Why not use a single aggregate score?

The criteria represent different failure modes. A response that is well written but ungrounded should not pass because citation presence and uncertainty checks raised its average. Separate signals preserve diagnostic value and allow critical criteria to function as quality gates.

### Why not continue immediately to V3?

The assignment asks for a small thing done well. V1-to-V2 already demonstrates the complete development loop: build, trace, evaluate, diagnose, change, compare, and identify the next optimization. A rushed V3 would add scope without necessarily adding confidence.

## Verification performed

I verified the submission by:

- running the CLI against current-product questions;
- confirming Tavily tool calls and results in LangSmith traces;
- inspecting root, model, and tool runs;
- checking source URLs in generated answers;
- running the five-case dataset through V1 and V2;
- reading model-evaluator reasoning for failed cases;
- comparing quality, latency, tokens, and cost;
- parsing all Python source files successfully;
- checking Markdown for whitespace errors;
- confirming that referenced screenshots exist; and
- confirming that `.env`, virtual environments, bytecode, and macOS metadata are ignored by Git.

## Known limitations and next iteration

This is intentionally a small take-home implementation, not a production service.

Known limitations include:

- the five-case dataset is diagnostic but not statistically representative;
- model-based evaluators require human calibration as the dataset grows;
- citation presence and domain checks do not fully verify claim-to-citation alignment;
- retrieval behavior does not yet score search count, latency, tokens, or cost against per-case budgets;
- the deeper V2 completion policy is applied globally; and
- the CLI does not include production authentication, rate limiting, managed secrets, retention controls, or deployment infrastructure.

My next V3 hypothesis would be a lightweight complexity router. Straightforward lookups would use the simpler path, while ambiguous, multi-part, or high-risk questions would invoke deeper decomposition and evidence checking. I would test that policy against a larger human-calibrated dataset and define explicit quality, latency, and cost gates before release.

## Final takeaway

The project is not valuable merely because it calls Tavily or produces cited text. Its value is the evaluation loop around retrieval: it makes answer defects observable, converts evaluator reasoning into a bounded change, and reveals when a quality improvement creates a broader operational regression.

That is the foundation I would use with an enterprise customer to move from an impressive agent demo to a controlled agent-development lifecycle.
