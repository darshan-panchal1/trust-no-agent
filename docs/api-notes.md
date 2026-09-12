# API Notes — ground truth for Ragas + DeepEval

**Captured 2026-09-03.** Every signature below was verified by introspecting the installed
packages in a throwaway venv, not read from documentation. Where the published docs disagree
with the installed code, the code wins and the disagreement is recorded under [Traps](#traps).

Re-verify with `uv run python -c "import ragas, deepeval; print(ragas.__version__, deepeval.__version__)"`
after any dependency bump.

| Package | Pinned | Released | Notes |
|---|---|---|---|
| `ragas` | **0.4.3** | 2026-01-13 | `requires-python >=3.9` |
| `deepeval` | **4.2.0** | 2026-08-24 | `requires-python >=3.9,<4.0` |
| `langchain-community` | **0.4.1** | — | Pinned *only* to keep `import ragas` working. See Trap 2. |
| `anthropic` | **1.3.0** | — | 1.x major — built on `httpx2`, not `httpx` |
| `pytest` | **9.1.1** | — | |
| `mypy` | **2.3.1** | — | 2.x major |
| `ruff` | **0.16.5** | — | |

---

## Ragas 0.4.3

### Imports

```python
from ragas import SingleTurnSample, MultiTurnSample, EvaluationDataset, evaluate, aevaluate
from ragas.metrics import Faithfulness, ResponseRelevancy, LLMContextRecall, \
    LLMContextPrecisionWithReference, ContextEntityRecall, NoiseSensitivity, FactualCorrectness
from ragas.llms import llm_factory
from ragas.embeddings import embedding_factory
from ragas.cache import DiskCacheBackend, CacheInterface, cacher
from ragas.cost import TokenUsage, get_token_usage_for_anthropic
from ragas.run_config import RunConfig
```

`ragas.metrics` lazily exports concrete metrics — they resolve via `getattr` but do **not**
appear in `dir(ragas.metrics)`. Only base classes (`Metric`, `MetricWithLLM`,
`SingleTurnMetric`, `MultiTurnMetric`, `MetricType`, `MetricResult`) are listed.

### `SingleTurnSample` — `ragas.dataset_schema.SingleTurnSample`

**Every field is `Optional` and defaults to `None`.** Constructing a sample with missing
fields raises nothing; the failure surfaces later inside the metric.

| Field | Type |
|---|---|
| `user_input` | `Optional[str]` |
| `retrieved_contexts` | `Optional[List[str]]` |
| `reference_contexts` | `Optional[List[str]]` |
| `retrieved_context_ids` | `Optional[List[str \| int]]` |
| `reference_context_ids` | `Optional[List[str \| int]]` |
| `response` | `Optional[str]` |
| `multi_responses` | `Optional[List[str]]` |
| `reference` | `Optional[str]` |
| `rubrics` | `Optional[Dict[str, str]]` |
| `persona_name`, `query_style`, `query_length` | `Optional[str]` |

`MultiTurnSample` differs: `user_input: List[HumanMessage | AIMessage | ToolMessage]` is
**required**; plus optional `reference`, `reference_tool_calls`, `rubrics`, `reference_topics`.

### `EvaluationDataset`

```python
EvaluationDataset(samples: List[Sample], backend: Optional[str] = None, name: Optional[str] = None)
```

Constructors: `from_list`, `from_dict`, `from_pandas`, `from_hf_dataset`, `from_jsonl`.
Exporters: `to_list`, `to_pandas`, `to_hf_dataset`, `to_jsonl`, `to_csv`.
Also: `validate_samples`, `get_sample_type`, `is_multi_turn`, `features`.

### `evaluate()` — full signature

```python
evaluate(
    dataset: Dataset | EvaluationDataset,
    metrics: Optional[Sequence[Metric]] = None,
    llm: Optional[BaseRagasLLM | LangchainLLM] = None,
    embeddings: Optional[BaseRagasEmbeddings | BaseRagasEmbedding | LangchainEmbeddings] = None,
    experiment_name: Optional[str] = None,
    callbacks: Callbacks = None,
    run_config: Optional[RunConfig] = None,
    token_usage_parser: Optional[TokenUsageParser] = None,
    raise_exceptions: bool = False,
    column_map: Optional[Dict[str, str]] = None,
    show_progress: bool = True,
    batch_size: Optional[int] = None,
    return_executor: bool = False,
    allow_nest_asyncio: bool = True,
) -> EvaluationResult | Executor
```

Note `raise_exceptions=False` — metric failures become `NaN` scores, not errors.

### Metric → required sample fields (verified via `metric._required_columns`)

| Metric | Required fields |
|---|---|
| `Faithfulness` | `user_input`, `retrieved_contexts`, `response` |
| `ResponseRelevancy` / `AnswerRelevancy` | `user_input`, `response` |
| `LLMContextPrecisionWithReference` | `user_input`, `retrieved_contexts`, `reference` |
| `LLMContextRecall` | `user_input`, `retrieved_contexts`, `reference` |
| `ContextEntityRecall` | `retrieved_contexts`, `reference` |
| `NoiseSensitivity` | `user_input`, `retrieved_contexts`, `reference`, `response` |
| `FactualCorrectness` | `reference`, `response` |
| `AnswerCorrectness` | `user_input`, `reference`, `response` |

`ResponseRelevancy` and `LLMContextPrecisionWithReference` additionally need an embeddings model.

### Custom judge LLM

```python
llm_factory(
    model: str,
    provider: str = "openai",
    client: Optional[Any] = None,
    adapter: str = "auto",
    cache: Optional[CacheInterface] = None,
    **kwargs,
) -> InstructorBaseRagasLLM
```

`llm_factory` is the 0.4.x path and takes `cache=` directly. `LangchainLLMWrapper(llm, cache=...)`
still exists but is the legacy wrapper. Non-OpenAI providers route through
`provider="litellm", client=litellm.completion`.

### Caching (native — do not hand-roll)

```python
from ragas.cache import DiskCacheBackend
cache = DiskCacheBackend(cache_dir=".cache")        # ctor takes cache_dir only
llm = llm_factory("...", client=..., cache=cache)
metric = FactualCorrectness(llm=llm)                 # cache rides on the LLM
```

`CacheInterface` abstract methods: `get`, `set`, `has_key`.
`cacher(cache_backend: Optional[CacheInterface] = None)` is a decorator — it *does* exist,
contrary to the published docs.
Management: `cache.cache.clear()`, `cache.cache.reset("size_limit", 1e9)`.

Backed by `diskcache>=5.6.3`, a hard dependency of ragas.

### Cost / token accounting

```python
from ragas.cost import TokenUsage, get_token_usage_for_anthropic
result = evaluate(..., token_usage_parser=get_token_usage_for_anthropic)
```

`TokenUsage` fields: `input_tokens`, `output_tokens`, `model`.
`TokenUsage.cost(cost_per_input_token: float, cost_per_output_token: Optional[float] = None) -> float`.
Parsers available: `get_token_usage_for_openai`, `_anthropic`, `_bedrock`, `_azure_ai`.

### Test data generation

```python
from ragas.testset import TestsetGenerator
TestsetGenerator(
    llm: BaseRagasLLM,
    embedding_model: BaseRagasEmbeddings,
    knowledge_graph: KnowledgeGraph = <factory>,
    persona_list: Optional[List[Persona]] = None,
    llm_context: Optional[str] = None,
)
```

Methods: `generate`, `generate_with_chunks`, `generate_with_langchain_docs`,
`generate_with_llamaindex_docs`, `from_langchain`, `from_llama_index`.

---

## DeepEval 4.2.0

### Imports

```python
from deepeval import assert_test, evaluate, on_test_run_end
from deepeval.test_case import LLMTestCase, SingleTurnParams, ToolCall, ConversationalTestCase
from deepeval.metrics import GEval, BaseMetric, AnswerRelevancyMetric, FaithfulnessMetric, \
    ContextualPrecisionMetric, ContextualRecallMetric, ToolCorrectnessMetric, TaskCompletionMetric
from deepeval.models import AnthropicModel, DeepEvalBaseLLM
from deepeval.dataset import EvaluationDataset, Golden
from deepeval.evaluate.configs import AsyncConfig, DisplayConfig, CacheConfig, ErrorConfig
```

### `SingleTurnParams` (was `LLMTestCaseParams`)

Both names exist and expose identical members. `SingleTurnParams` is canonical in 4.x.

```
INPUT, ACTUAL_OUTPUT, EXPECTED_OUTPUT, CONTEXT, RETRIEVAL_CONTEXT, METADATA, TAGS,
TOOLS_CALLED, EXPECTED_TOOLS, MCP_SERVERS, MCP_TOOLS_CALLED, MCP_RESOURCES_CALLED,
MCP_PROMPTS_CALLED
```

`LLMTestCase` is a Pydantic model (`__init__(self, /, **data)`) — pass fields by keyword.
Core fields: `input`, `actual_output`, `expected_output`, `context`, `retrieval_context`,
`tools_called`, `expected_tools`.

### `Golden`

```
id, input, actual_output, expected_output, context, retrieval_context,
additional_metadata, comments, tools_called, expected_tools, source_file, name,
custom_column_key_values, multimodal, images_mapping
```

Only `input` is meaningfully required — a Golden is a "pending test case" whose
`actual_output` is filled in at evaluation time.

### `EvaluationDataset` (DeepEval's — name collides with Ragas')

```python
EvaluationDataset(goldens: List[Golden] | List[ConversationalGolden] = [],
                  confident_api_key: Optional[str] = None)
```

Properties: `.goldens`, `.test_cases`.
Local methods: `add_golden`, `add_test_case`, `add_goldens_from_csv_file` /
`_json_file` / `_jsonl_file`, `add_test_cases_from_csv_file` / `_json_file`, `evals_iterator`,
`evaluate`, `save_as`, `queue`.
Network methods (Confident AI — never call in CI): `pull`, `push`, `delete`, `create_version`,
`get_versions`, `generate_goldens_from_*`.

### `GEval` — full signature

```python
GEval(
    name: str,
    evaluation_params: Optional[List[SingleTurnParams]] = None,
    criteria: Optional[str] = None,
    evaluation_steps: Optional[List[str]] = None,
    rubric: Optional[List[Rubric]] = None,
    model: Union[str, DeepEvalBaseLLM, None] = None,
    threshold: Optional[float] = 0.5,
    top_logprobs: int = 20,
    async_mode: bool = True,
    strict_mode: bool = False,
    verbose_mode: bool = False,
    flaky: bool = False,
    evaluation_template: Type[GEvalTemplate] = GEvalTemplate,
)
```

`criteria` and `evaluation_steps` are mutually exclusive. Standard metrics
(`AnswerRelevancyMetric` etc.) share the shape:
`(threshold=0.5, model=None, include_reason=True, async_mode=True, strict_mode=False, verbose_mode=False, flaky=False, evaluation_template=...)`.

### Custom judge

```python
from deepeval.models import AnthropicModel
AnthropicModel(
    model: Optional[str] = None,              # library default is "claude-opus-5" — NOT our pin
    api_key: Optional[str] = None,
    temperature: Optional[float] = None,      # only sent when not None
    cost_per_input_token: Optional[float] = None,
    cost_per_output_token: Optional[float] = None,
    generation_kwargs: Optional[Dict] = None,
)
```

Or subclass `DeepEvalBaseLLM` — abstract methods are exactly:
`get_model_name`, `load_model`, `generate`, `a_generate`.

DeepEval carries a model registry at `deepeval.models.llms.constants.ANTHROPIC_MODELS_DATA`
with per-model `supports_temperature`, `supports_log_probs`, `input_price`, `output_price`.

### Judge model — history: this repo pinned `claude-sonnet-5` before the Eighth amendment

**Superseded.** The judge is now selected via `JUDGE_MODEL` (Article III, Eighth
amendment) — no model is hardcoded in this repo anymore. The measurements below are kept
as dated evidence for the provider-neutral rule they proved (any custom `DeepEvalBaseLLM`
subclass falls back to coarse GEval scoring, regardless of judge tier) — see Verification
round 6 and `CONSTITUTION.md` Article III for the current state.

**Always pass `model="claude-sonnet-5"` explicitly.** Registry rows, read from
`ANTHROPIC_MODELS_DATA` in the installed package:

| model | `supports_log_probs` | `supports_temperature` | `supports_structured_outputs` | registry price /MTok |
|---|---|---|---|---|
| `claude-sonnet-5` ← **our judge** | `False` | `False` | `True` | `$3/$15` *(stale — true rate is `$2/$10`)* |
| `claude-opus-5` ← *library default* | `False` | `False` | `True` | `$5/$25` *(correct)* |
| `claude-opus-4-8` | `False` | `False` | `True` | `$5/$25` |

`supports_log_probs=False` on **every** tier is the finding that decides the pin: GEval's
log-probability scoring path is unavailable on all Claude models alike (Trap 5), so a
higher-tier judge cannot buy finer scores — it can only cost more. Both models are equally
unable to accept sampling parameters (`supports_temperature=False`, Trap 8).

`DEFAULT_ANTHROPIC_MODEL` in `deepeval/models/llms/constants.py` is `"claude-opus-5"`, so a
bare `AnthropicModel()` selects a model **2.5× more expensive than our pin, silently** — see
Trap 18.

### This repo's judge implements `DeepEvalBaseLLM` directly — it does not wrap `AnthropicModel`

**Superseded by the Eighth amendment for the specifics, not the reasoning.** The judge
moved to Groq; there is no `GroqModel` to wrap in the first place (V5.4), so the headline
claim — implements `DeepEvalBaseLLM` directly, no vendor convenience class in the way —
still holds, now for a stronger reason than a choice. The "no cache hook" and "stale
registry price" arguments below are architectural and still apply to why a vendor wrapper
would be the wrong shape even if one existed. What is **no longer current**: `JUDGE_MODEL`
is not a module-level constant anymore — it's `evals.models.judge_model()`, reading the
`JUDGE_MODEL` env var (Article III) — and every `anthropic.Anthropic()` reference below is
what the code used to do. See Verification round 6 for the Groq-specific findings.

`evals/judge/cached.py::CachedJudge` is a deliberate, verified deviation from the plan's
original description ("`CachedJudge(DeepEvalBaseLLM)` wrapping `AnthropicModel`"). It
implements `DeepEvalBaseLLM` directly and drives the raw `anthropic.Anthropic()` SDK client
itself — the same pattern `app/generate.py::_call_live` and `evals/ragas_llm.py` already
use for the generator and the ragas judge. `AnthropicModel(` has **zero** call sites
anywhere in this repo (verified: `grep -rn "AnthropicModel(" --include="*.py" .` — no
hits). Read `AnthropicModel`'s installed source (`deepeval/models/llms/anthropic_model.py`)
to confirm why, rather than asserting it:

- **No cache hook, so wrapping it buys nothing.** `AnthropicModel.generate()` /
  `a_generate()` call `chat_model.messages.create(...)` unconditionally — there is no
  extension point to intercept before the network call, unlike ragas'
  `cacher()`/`CacheInterface`. Article III's cache-writer invariant (only `read_or_call` may
  ever write) means the cache-hit/miss decision has to be made by *our* code before any
  live call is even considered. Composing over `AnthropicModel` would not remove that
  requirement — we would still gate every call behind our own cache check first, exactly as
  `CachedJudge.generate()` does now — so an `AnthropicModel` instance sitting behind that
  gate would be pure indirection with no behavior we actually use.
- **Its cost figure is the stale one Trap 7 already warns against.** `AnthropicModel`
  computes cost from `self.model_data.input_price`/`output_price`, sourced from
  `ANTHROPIC_MODELS_DATA` — the same registry Trap 7 documents as overstating
  `claude-sonnet-5` by 50% (`$3/$15` vs. the true `$2/$10`). Using its returned cost for our
  `CacheEntry.usd` would silently reintroduce the exact bug Article VIII's "must not read
  `ANTHROPIC_MODELS_DATA`" requirement exists to prevent. `CachedJudge._call_live` writes
  `usd=0.0` instead, deferring to Slice 4's own dated pricing file — the same choice
  `app/generate.py::_call_live` already made in Slice 1.
- **No construction-time API key demand either way, so this was not the deciding factor.**
  Confirmed by reading the source: `AnthropicModel.__init__` only *resolves* `self.api_key`
  (from the `api_key=` argument or `settings.ANTHROPIC_API_KEY`); the actual
  `require_secret_api_key(...)` check that raises on a missing key lives in `_build_client`,
  called from `load_model()`, called lazily from `generate()`/`a_generate()` — not from
  `__init__`. So `AnthropicModel(model="claude-sonnet-5")` alone would have constructed
  without a key, same as `CachedJudge` does now. This rules out "avoiding an eager API-key
  requirement" as the reason for the deviation — the two points above are the real ones.

**Trap 18 does not apply to this repo's judge path, and there is no equivalent risk in the
raw SDK client that needs its own guard.** Trap 18's failure is specific to
`AnthropicModel`'s constructor: `model = model or settings.ANTHROPIC_MODEL_NAME or
DEFAULT_ANTHROPIC_MODEL` silently substitutes `"claude-opus-5"` when `model=` is omitted.
Since no `AnthropicModel` object exists anywhere in this repo's call path, that specific
substitution cannot happen here. The raw SDK has no analogous default to guard against:
confirmed by introspecting `anthropic.resources.messages.messages.Messages.create`'s
signature — `model: ModelParam` is a required keyword-only parameter with **no default at
all** (`*, max_tokens: int, messages: ..., model: ModelParam, ...`). Omitting `model=` in a
raw SDK call raises `TypeError: missing 1 required keyword-only argument: 'model'`
immediately and loudly; it cannot silently resolve to a different model the way
`AnthropicModel()` can. `CachedJudge._call_live` passes `model=JUDGE_MODEL` explicitly
regardless, matching the rest of this repo's "always explicit" convention, but the raw
client does not create the failure mode Trap 18 describes even if that discipline lapsed.

**`get_model_name()` is pinned, not inferred.** `CachedJudge.get_model_name()` returns the
module-level constant `JUDGE_MODEL = "claude-sonnet-5"` verbatim — a string literal, never
read from the SDK, an env var, or a response. The same `JUDGE_MODEL` constant is also what
`_call_live` passes as `model=` to `messages.create(...)` and what `generate()` folds into
the cache key via `make_key(self._call_kind, JUDGE_MODEL, hash_prompt(prompt))`. All three
uses — the reported model name, the actual live call, and `model_identity` in the cache key
— read the identical constant, defined once, so they cannot silently drift apart.

### `assert_test` / `evaluate`

```python
assert_test(test_case=None, metrics=None, golden=None, run_async: bool = True)

evaluate(test_cases, metrics=None, metric_collection=None, hyperparameters=None,
         mcp_servers=None, identifier=None, official=False,
         async_config=AsyncConfig(run_async=True, throttle_value=0, max_concurrent=20),
         display_config=DisplayConfig(show_indicator=True, print_results=True, ...),
         cache_config=CacheConfig(write_cache=True, use_cache=False),
         error_config=ErrorConfig(ignore_errors=False, skip_on_missing_params=False))
```

### Pytest integration — **plain `pytest` works**

DeepEval registers a `pytest11` entry point (`deepeval.plugins.plugin`), so its plugin loads
automatically under bare `pytest`. `deepeval test run` is *not* required. Verified:

```
$ python -m pytest test_bare.py -q
2 passed
```

`deepeval test run` adds caching (`-c`), parallelism (`-n`), and Confident AI reporting —
none of which we want (Articles I and VI). Use `pytest` and `@pytest.mark.parametrize`
over `dataset.goldens`.

### Agent / trajectory metrics

`ToolCorrectnessMetric` works on `LLMTestCase.tools_called` / `expected_tools`.
`TaskCompletionMetric`, `PlanAdherenceMetric`, `StepEfficiencyMetric`, `GoalAccuracyMetric`
operate on **traces**, not test cases — they require `@observe()` instrumentation on the app.

---

## Traps

Every item below differs from what I would have written from memory or from what the
published docs state. Ordered by how much damage it does.

**1. `assert_test` defaults to `run_async=True`, and the async path rebuilds your metric —
turning a failing score into a reported pass.** Score laundering, in the harness itself.

Root cause, `deepeval/metrics/utils.py`, verbatim from the installed package:

```python
def copy_metrics(metrics):
    copied_metrics = []
    for metric in metrics:
        metric_class = type(metric)
        args = vars(metric)
        superclasses = metric_class.__mro__
        valid_params = []
        for superclass in superclasses:
            signature = inspect.signature(superclass.__init__)
            valid_params.extend(signature.parameters.keys())
        valid_params = set(valid_params)
        valid_args = {key: args[key] for key in valid_params if key in args}
        copied_metrics.append(metric_class(**valid_args))   # ← rebuilt, not deep-copied
    return copied_metrics
```

`valid_args` is `vars(metric)` intersected with **constructor parameter names** across the MRO.
Any constructor argument **not stored on an attribute of the same name is absent from that
intersection, silently dropped, and replaced by the class default** on the rebuild.

**Reproduction** — `threshold` survives (stored as `self.threshold`, name matches); `score`
does not (stored as `self.injected`). That asymmetry is the whole bug:

```python
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from deepeval.metrics import BaseMetric

SEEN = []                      # module-level, so it survives the rebuild

class M(BaseMetric):
    def __init__(self, threshold=0.5, score=0.9):
        self.threshold = threshold
        self.injected = score  # stored under a DIFFERENT name than the ctor arg
    def measure(self, tc, *a, **k):
        SEEN.append(("measure", self.injected))
        self.score = self.injected
        self.success = self.score >= self.threshold
        self.reason = "stub"
        return self.score
    async def a_measure(self, tc, *a, **k):
        SEEN.append(("a_measure", self.injected))
        return self.measure(tc)
    def is_successful(self):
        return self.success
    @property
    def __name__(self):
        return "M"

tc = LLMTestCase(input="q", actual_output="a")
for run_async in (True, False):
    SEEN.clear()
    m = M(score=0.1)                      # deliberately failing: 0.1 < threshold 0.5
    try:
        assert_test(tc, [m], run_async=run_async)
        out = "NO EXCEPTION"
    except AssertionError:
        out = "AssertionError"
    print(f"run_async={run_async}: {out}; seen={SEEN}")
```

Observed on `deepeval==4.2.0`:

```
run_async=True:  NO EXCEPTION;   seen=[('a_measure', 0.9), ('measure', 0.9)]
run_async=False: AssertionError; seen=[('measure', 0.1)]
```

The metric was constructed with `0.1` and measured with `0.9` — its default. Under bare
`pytest` the same pair of cases reported **`2 passed`**, with no error, no warning and no log
line. The failing assertion never fired because the object that reached `is_successful()` was
never the object the test built.

*Consequences:* store every ctor arg under its own name (`self.threshold = threshold`, never
`self._threshold`); force `run_async=False` in one place; and prove a deliberately-failing
metric actually fails before trusting any gate. This is the exact failure mode the repo exists
to demonstrate, hiding inside the instrument meant to demonstrate it — see **Article XI**,
which exists for this trap specifically.

Note the counter-case: `ToolCorrectnessMetric` **does** survive the rebuild (Verification 2),
because it happens to store every ctor arg under a matching name. Survival is a property of
each metric's `__init__`, not of the library — check per metric, never assume.

**2. `ragas==0.4.3` will not import against current `langchain-community`.**
`ragas/llms/base.py:12` does an unconditional top-level
`from langchain_community.chat_models.vertexai import ChatVertexAI`. That module was removed
in `langchain-community` **0.4.2** specifically (the package is being sunset). A clean
`uv pip install ragas==0.4.3` resolves to 0.4.2 and `import ragas` dies with
`ModuleNotFoundError`. **0.4.1 is the highest version that works** — verified by bisection
over every release at or above 0.3.31 (see Verification 1). This breaks Article 0 on a fresh
clone, so the pin is load-bearing, not cosmetic.

**3. Versions are far ahead of intuition.** `ragas` is **0.4.3**, not 0.2.x. `deepeval` is
**4.2.0**, not 1.x/2.x. `mypy` is **2.3.1**, not 1.x. `anthropic` is **1.3.0** and is built on
`httpx2` — `httpx.Timeout` and friends are rejected at request time.

**4. `LLMTestCaseParams` was renamed to `SingleTurnParams`.** The old name still resolves in
4.2.0 with identical members, so this fails silently rather than loudly. Use the new name.

**5. GEval scores coarsely on Claude judges — on every tier, including ours.** `GEval`
defaults to `top_logprobs=20` and uses log-probability weighting for fractional scores. Every
Anthropic model in DeepEval's registry has `supports_log_probs=False` — verified on
`claude-sonnet-5` (our pin), `claude-opus-5` and `claude-opus-4-8` — so GEval falls back to a
coarse path (`raise AttributeError("log_probs unsupported.")` guards the logprob branch at
`g_eval.py:313,386`). Expect blockier scores than the OpenAI-judged examples in the docs, and
set thresholds against measured `claude-sonnet-5` scores rather than published ones. Because
the degradation is identical across tiers, paying for a larger judge buys nothing here — this
is the measurement behind the sonnet-5 pin.

**6. DeepEval's `evaluate()` has caching OFF by default.**
`CacheConfig(write_cache=True, use_cache=False)` — it writes a cache it never reads.
Article III's budget requires `use_cache=True` explicitly.

**7. DeepEval's built-in price table is stale — for our judge specifically.** It lists
`claude-sonnet-5` at `$3/$15` per MTok; the current published rate is `$2/$10`. Its
`claude-opus-5` entry (`$5/$25`) is correct. Since `claude-sonnet-5` is the pinned judge, every
cost figure DeepEval reports for this repo overstates spend by **50%**. Article VIII must own
its own dated pricing file and must not read `ANTHROPIC_MODELS_DATA`, or `cost_per_input_token`
/ `cost_per_output_token` must be passed explicitly to `AnthropicModel`.

**8. `AnthropicModel(temperature=...)` — the docs are wrong, and the fallback is dangerous.**
The published docs say `temperature` "defaults to 0.0". The installed code defaults it to
`None` and only forwards it when set — but when it is `None` it falls back to
`settings.TEMPERATURE`. Both `claude-sonnet-5` (our pin) and `claude-opus-5` carry
`supports_temperature=False`; sending a temperature returns a 400. Never set `TEMPERATURE` in
this repo's settings or environment. Determinism comes from the cache, not from sampling
parameters — there is no temperature to pin on any current Claude model.

**9. `TaskCompletionMetric` does not take an `LLMTestCase`.** It reads agent traces and
requires `@observe()` instrumentation on the application. Any trajectory metric we adopt under
Article II changes the *app*, not just the eval — budget for that.

**10. Ragas `SingleTurnSample` validates nothing.** All fields are `Optional[None]`. A typo'd
key or a missing `reference` constructs fine and fails deep inside a metric, and with
`evaluate(raise_exceptions=False)` (the default) it becomes a `NaN` score rather than an error.
Validate golden rows on load.

**11. Ragas metrics are lazily exported.** `dir(ragas.metrics)` shows only base classes;
`Faithfulness` et al. resolve through a module `__getattr__`. Tab-completion and any
`dir()`-based discovery will mislead.

**12. Ragas ships its own disk cache.** `ragas.cache.DiskCacheBackend` +
`llm_factory(..., cache=...)` already does keyed, on-disk judge caching via `diskcache`.
Article III should wrap or configure this, not reimplement it. The published docs also claim
no `cacher` decorator exists — it does (`ragas/cache.py`).

**13. Two different classes named `EvaluationDataset`.** `ragas.EvaluationDataset` takes
`samples=[SingleTurnSample]`; `deepeval.dataset.EvaluationDataset` takes `goldens=[Golden]`.
They are unrelated. Under Article II they live in different packages — never import both into
one module.

**14. `evaluate(raise_exceptions=False)` is the Ragas default.** Failures silently become
`NaN`. Set it to `True` so a broken judge is a red test, not a missing number.

**15. `deepeval` pulls in a large pytest surface.** It hard-depends on `pytest`,
`pytest-asyncio`, `pytest-repeat`, `pytest-rerunfailures`, `pytest-xdist`. `pytest-rerunfailures`
in particular can mask flaky failures — do not enable reruns (Article IV).

**Traps 16–19 were found after this section was written, and are recorded in the verification
round that found them.** They are listed here so this section stays the single entry point
`CLAUDE.md` says it is:

| # | Trap | Where |
|---|---|---|
| 16 | `ToolCorrectnessMetric()` cannot be constructed without `OPENAI_API_KEY` | Round 2 |
| 17 | DeepEval phones home to PostHog on import | Round 2 |
| 18 | A bare `AnthropicModel()` silently selects a different judge than the pin | Round 2 |
| 19 | **Ragas' cache key is model-blind** — reusing it verbatim serves a previous judge's answers with nothing raised | **Round 4, §V4.1** |
| 20 | `ragas.metrics` concrete classes (`Faithfulness` et al.) now emit a `DeprecationWarning` pointing at `ragas.metrics.collections` | Round 5 |
| 21 | `deepeval.assert_test` is exported via `global` inside a function — invisible to `mypy --strict`; import from `deepeval.evaluate` instead | Round 6 |
| 22 | Pydantic's mypy plugin ignores a positional `Field(None, ...)` default — `ToolCall.input_parameters` must be passed explicitly under `--strict` | Round 6 |
| 23 | `BaseMetric`/`DeepEvalBaseLLM.__init_subclass__` call deepeval's own untyped `observe_methods` — every subclass needs a justified `type: ignore[no-untyped-call]` | Round 6 |
| 24 | **`ruff check` never enforced our 100-char limit** — `line-length` alone feeds only `ruff format`; E501 is not in ruff's default rule set | Round 7 |
| 25 | `pytest --disable-socket` breaks any test touching an asyncio loop — the loop's self-pipe is an AF_UNIX `socketpair()`; `--allow-unix-socket` is required | Round 7 |
| 26 | Adding a `[build-system]` to get `[project.scripts]` breaks offline `uv sync` — `hatchling` needs `editables`, which is not in the cache | Round 7 |
| 27 | **`InstructorModelArgs()`'s own defaults (`temperature=0.01`, `top_p=0.1`) were spread into every live judge call unchecked** — a live Article III violation, present since the Groq era, caught only by reading source during the tenth amendment's NIM migration | Tenth amendment |
| 28 | **`deepeval/__init__.py` calls `autoload_dotenv()` unconditionally on import**, merging a real `.env` from the CWD into `os.environ` for any key not already set — silently defeats Article VI's offline-credential guarantee for anyone with a `.env` file in the repo root | Post-tenth-amendment live-pass debugging |
| 29 | **`RagasCacheBackend.set()` used `json.dumps(value, default=str)` on a pydantic model** — `default=str` silently stringified the whole model via `str(model)` instead of raising `TypeError`, so every cached ragas judge result (not embeddings) was corrupted the moment it was ever written, since the Groq era | Live-pass debugging after the max_tokens fix |
| 30 | **`CachedJudge._call_live` made a plain, unconstrained NIM completion for GEval-family metrics** — a reasoning-heavy judge emitted one complete, valid JSON object, then echoed a fragment of its own system prompt and restarted the object a second time, breaking `json.loads`. `response_format={"type": "json_object"}` narrows this but doesn't eliminate it; one retry does | `evals.behavior.live_pass` |

**Trap 19 does the most damage of anything in this document** and belongs at the top of the
damage ordering above: every other trap here fails loudly, or fails in a way a test can see. That
one produces a green suite, a `$0.00` cost table, and thresholds calibrated against a judge that
never ran.

**20 (new, Slice 2 implementation).** `from ragas.metrics import Faithfulness` (and
`ResponseRelevancy`, `LLMContextPrecisionWithReference`, `LLMContextRecall`) — the exact
import this document's own "Imports" section above specifies — now warns on the pinned
version:

```
DeprecationWarning: Importing Faithfulness from 'ragas.metrics' is deprecated and will be
removed in v1.0. Please use 'ragas.metrics.collections' instead.
```

Not present when this document was captured (2026-09-03); observed while building Slice 2
(2026-09-07) against the same pin (`ragas==0.4.3`), so this is new information about an
already-pinned version, not a version bump. `ragas.metrics.collections`'s constructor
signatures and caching behavior are **unverified** — introducing them now would mean writing
Ragas code from memory/the published migration note rather than from introspection, which is
exactly what this document exists to prevent. Slice 2 keeps the documented `ragas.metrics`
import and accepts the warning; revisit only after introspecting `ragas.metrics.collections`
with the same rigor as the rest of this document.

**21 (new, Slice 3 implementation — mypy --strict trap, not a runtime bug).**
`deepeval.assert_test` (and `evaluate`, `compare`, `on_test_run_end`, `login`, …) are not
plain module-level names. `deepeval/__init__.py` builds them via `global` assignment inside
a function, `_expose_public_api()`, called once at import time:

```python
def _expose_public_api() -> None:
    global __version__, evaluate, assert_test, compare
    ...
    from deepeval.evaluate import evaluate as _evaluate, assert_test as _assert_test
    ...
    assert_test = _assert_test

_expose_public_api()
```

This works perfectly at runtime — `deepeval.assert_test` and `from deepeval import
assert_test` both resolve fine under Python. `mypy --strict` cannot see it: it does not
execute `_expose_public_api()`, so it never observes the `global assert_test = ...`
assignment, and reports `Module "deepeval" has no attribute "assert_test"` on both
`import deepeval; deepeval.assert_test(...)` and `from deepeval import assert_test`.

**Fix — copy-paste this import, not the documented one:**

```python
from deepeval.evaluate import assert_test  # NOT `from deepeval import assert_test`
```

Confirmed by identity check to be the exact same object as the top-level name:
`deepeval.assert_test is deepeval.evaluate.assert_test` → `True`. The same applies to
`evaluate` (`from deepeval.evaluate import evaluate`) and, by the same mechanism, to every
other name `_expose_public_api()` sets (`compare`, `on_test_run_end`,
`log_hyperparameters`, `login`, `flush_traces`, `a_flush_traces`, `telemetry`,
`instrument`) — re-derive each one's real submodule the same way (grep
`deepeval/__init__.py::_expose_public_api()` for `from deepeval.<submodule> import <name>`)
before writing `from deepeval import <name>` anywhere in this repo.

**22 (new, Slice 3 implementation — mypy --strict trap, not a runtime bug).** Pydantic's
mypy plugin is active by default under this pin (`pydantic==2.13.5`, `mypy==2.3.1`) with no
explicit `plugins = ["pydantic.mypy"]` entry anywhere in this repo's config — confirmed by
reproducing the trap below in total isolation from this repo's own `pyproject.toml`. The
plugin only recognizes a field as optional when its default is passed as the `default=`
**keyword** to `Field(...)`; a **positional** default — `Field(None, ...)` — is not
recognized, and the plugin then requires that field at every call site under `--strict`,
even though it is genuinely optional at runtime. `deepeval.test_case.ToolCall` hits this
exactly:

```python
class ToolCall(BaseModel):
    input_parameters: Optional[Dict[str, Any]] = Field(
        None,  # positional — the mypy plugin does not treat this as a default
        serialization_alias="inputParameters",
        validation_alias=AliasChoices("inputParameters", "input_parameters"),
    )
```

`ToolCall(name="x")` is fine at runtime; under `mypy --strict` it is
`error: Missing named argument "input_parameters" for "ToolCall"  [call-arg]`.

**Fix, this instance:** pass the field explicitly at every call site, even when absent:

```python
ToolCall(name="lookup_policy", input_parameters=None)  # not just ToolCall(name=...)
```

**Fix, the general case:** this is not `ToolCall`-specific — it is a property of the
pydantic-mypy-plugin/pydantic-version combination pinned here, and will recur on any
pydantic field (ours or a dependency's) that mypy reports as a phantom "missing named
argument" for a field that genuinely has a runtime default. Before assuming a field is
really required, check its source for a **positional** `Field(<value>, ...)` default:
  - **Field we don't control (a library's, e.g. `ToolCall`):** pass it explicitly at every
    call site, as above — there is nothing else to fix.
  - **Field we do control (anything in `app/models.py`, `evals/golden/schema.py`, etc.):**
    fix it at the source instead of working around every call site — change
    `Field(None, ...)` to `Field(default=None, ...)` (keyword form), which the plugin
    recognizes correctly. Verified in isolation: `Field(None)` triggers the phantom
    "missing named argument" error; `Field(default=None)` does not, on the exact
    `pydantic==2.13.5` / `mypy==2.3.1` pin used here.

**23 (new, Slice 3 implementation — mypy --strict trap, not a runtime bug).** Both
`deepeval.metrics.BaseMetric` and `deepeval.models.DeepEvalBaseLLM` define
`__init_subclass__`, which calls deepeval's own untyped `observe_methods(cls)` (from
`deepeval.tracing.internal`) to wire tracing instrumentation onto every subclass. Under
`mypy --strict` (`disallow_untyped_calls`), simply writing `class Foo(BaseMetric):` or
`class Foo(DeepEvalBaseLLM):` — with no untyped call of our own anywhere in the body —
raises `error: Call to untyped function "__init_subclass__" in typed context
[no-untyped-call]` at the class line itself, since the implicit `__init_subclass__` call
that Python makes when the subclass is defined is what mypy is checking. There is no
workaround that avoids subclassing either base (both are abstract and central to Article
VI.a's factory).

**Fix — copy-paste this pattern for any new subclass of either base:**

```python
class MyMetric(BaseMetric):  # type: ignore[no-untyped-call]
    # BaseMetric.__init_subclass__ calls deepeval's own untyped observe_methods(cls).
    ...

class MyJudge(DeepEvalBaseLLM):  # type: ignore[no-untyped-call]
    # DeepEvalBaseLLM.__init_subclass__ calls deepeval's own untyped observe_methods(cls).
    ...
```

The `# type: ignore[no-untyped-call]` goes on the `class` line itself (that is where mypy
reports it, not on `__init__` or any method), paired with a one-line comment naming the
mechanism so a reader doesn't have to rediscover it. Applied in this repo to
`evals/judge/cached.py::CachedJudge`, `evals/judge/stub.py::StubJudge`, and
`evals/judge/probe.py::_ScoreLaunderingProbe`.

---

## Verification log

```
uv venv --python 3.12 && uv pip install ragas==0.4.3 deepeval==4.2.0 \
    langchain-community==0.4.1 anthropic==1.3.0 pytest==9.1.1 pytest-socket==0.8.1 pyyaml==6.0.3
python -c "import ragas, deepeval, anthropic, pytest, yaml; ..."   # ALL IMPORTS OK
python -m pytest test_bare.py -q                                    # plugin auto-loads, 2 passed
```

**24 (new, Slice 4 implementation — a rule we believed was enforced and was not).**
`CONSTITUTION.md` Article VII says "≤ 60 lines per module. ≤ 100 characters per line. **Both
machine-enforced.**" The line-length half was not enforced at all. `[tool.ruff] line-length
= 100` configures the *formatter*; the lint rule that acts on it is **E501, which is not in
ruff's default rule set**, and this repo runs `ruff check`, never `ruff format`. Measured
2026-09-07: four lines were over the limit, two of them committed in Slice 1 and reviewed
three times since without anything objecting.

```
$ uv run ruff check .                 # "All checks passed!"
$ uv run ruff check --select E501 .   # Found 4 errors.
```

Fix, in `pyproject.toml` — `extend-select`, not `select`, so ruff's defaults are kept:

```toml
[tool.ruff.lint]
extend-select = ["E501"]
```

This is the repository's own thesis landing on the repository: a green check that meant
nothing, for a rule the constitution explicitly called machine-enforced.

**25 (new, Slice 4 implementation).** `--disable-socket` (pytest-socket) is how Article VI's
"blocked at the socket layer for the entire default run" is actually implemented — but on
its own it breaks **any test that touches an asyncio event loop**, including
`tests/test_harness_integrity.py`'s `run_async=True` reproduction:

```
AttributeError: '_UnixSelectorEventLoop' object has no attribute '_ssock'
```

`asyncio`'s selector event loop builds its internal self-pipe with `socket.socketpair()`,
which is AF_UNIX, and pytest-socket blocks `socket.socket` wholesale. The fix is
`--allow-unix-socket` alongside it: AF_UNIX is local IPC with no network egress, so the
zero-outbound-packets guarantee is untouched while local event loops keep working.

```
addopts = "-q --strict-markers -m 'not live' --disable-socket --allow-unix-socket"
```

**26 (new, Slice 4 implementation — Article 0 beats a task's literal wording).** T4.5 asked
for a `[project.scripts]` entry point. `uv sync` warns that entry points are skipped for a
non-packaged project, and adding the `[build-system]` that would fix it **breaks the Prime
Contract on a cold clone**, verified 2026-09-07:

```
$ # with requires = ["hatchling"] added
$ uv sync --offline
  × Failed to build `trust-no-agent`
  ╰─▶ Because editables was not found in the cache and you require editables>=0.3,<1.dev0,
      we can conclude that your requirements are unsatisfiable.
```

`hatchling` pulls `editables`, which is not in the lockfile's cache because it is a *build*
dependency, so a fresh offline clone cannot install the project. Article 0 outranks T4.5, so
this repo ships **no `[project.scripts]` and no `[build-system]`**, and the operator entry
point is `uv run python -m evals.cli` — which needs no build step, and which Article I's
enforcement already carves out `evals/cli.py` by name to permit.

**27 (new, tenth amendment implementation — a constitutional violation that shipped, was
never caught, and is not new to this migration).** `evals/ragas_llm.py`'s `build_judge_llm`
constructs `InstructorLLM(client=..., model=model, provider="groq", model_args=
InstructorModelArgs(), cache=cache)`. `InstructorModelArgs` is not the empty defaults it
looks like:

```python
class InstructorModelArgs(BaseModel):
    temperature: float = 0.01
    top_p: float = 0.1
    max_tokens: int = 1024
    system_prompt: t.Optional[str] = None
```

`InstructorLLM.__init__` stores these as a plain dict — `self.model_args = {
**model_args.model_dump(), **kwargs}` — and `generate()`/`agenerate()` spread that dict
straight into the live call: `self.client.chat.completions.create(model=self.model,
messages=messages, response_model=response_model, **provider_kwargs)`, where
`provider_kwargs` is `self.model_args.copy()` for any provider not `"google"`/`"openai"`/
`"azure"` — which `"groq"` was. **`temperature` and `top_p` were therefore sent on every
live Groq judge call**, a direct violation of Article III's "`temperature`, `top_p`, and
`top_k` must not appear anywhere in this repo," present since Slice 3, not introduced by
this migration.

**Why nothing caught it.** Static review of `ragas_llm.py` sees `InstructorModelArgs()`
called with no arguments and reasonably reads that as "no sampling parameters set" — the
defaults are invisible unless the class itself is opened. The full offline suite could not
catch it either: the leak fires inside `InstructorLLM.generate()`'s live branch, and no
`mode="live"` call had ever run this session before the migration — Article VI.a's own
offline-stub discipline, which exists to keep a real client from being touched by accident,
also kept this particular accident from ever executing where a test could see it. It surfaced
only because rewriting the client construction for NIM required reading `InstructorLLM`'s
source directly (this document's own standing rule — verify, don't assume), and the source
was sitting right next to the bug.

**Fix:** `build_judge_llm` now pops both keys from the constructed `InstructorLLM`'s
`model_args` immediately after construction, before any call — offline or live — can ever
read it:

```python
llm.model_args.pop("temperature", None)
llm.model_args.pop("top_p", None)
```

`tests/test_ragas_llm.py::test_build_judge_llm_never_carries_a_sampling_parameter` is the
regression test: it asserts neither key is present in `model_args` after construction, so
this cannot silently reappear under whatever provider replaces NIM next. `max_tokens` is left
alone — Article III names only `temperature`, `top_p`, and `top_k`, and a completion-length
cap is not a sampling parameter.

**28 (new, found debugging a live pass after the tenth amendment — a credential leak this
repo's own code review could never have caught).** Running
`evals.component.live_pass`'s `main()` with a real `.env` in the repo root produced a
passing offline suite the *next* time `pytest` ran — except one test now failed:
`test_the_nvidia_credential_is_absent_and_the_suite_is_green_anyway` (`NVIDIA_API_KEY` present
in `os.environ`), with no shell export, no `source .env`, nothing ambient in the process that
started `pytest`. Read `deepeval/__init__.py` directly rather than guessing:

```python
from deepeval.config.settings import autoload_dotenv, get_settings
...
autoload_dotenv()
```

`autoload_dotenv()` (`deepeval/config/settings.py`) runs on **every `import deepeval`**,
unconditionally, and merges `.env` → `.env.{APP_ENV}` → `.env.local` from the current working
directory into `os.environ` for any key not already set:

```python
for k, v in merged.items():
    if k not in os.environ:
        os.environ[k] = v
```

**This defeats Article VI's offline-credential guarantee for anyone who has ever run a live
pass and left the `.env` it needed sitting in the repo root** — not because any code in this
repository does anything wrong, but because the mere *presence* of that file on disk is
enough. No amount of auditing `evals/` or `app/` would surface this: the leak is entirely
inside a dependency's import-time side effect, one directory swap in `os.getcwd()` away from
never firing at all.

**First attempt, and why it wasn't enough.** `autoload_dotenv()`'s own docstring documents
an escape hatch — `DEEPEVAL_DISABLE_DOTENV=1 -> skip. Tip: set to 1 in pytest/CI` — added to
`pyproject.toml`'s `env` block alongside `DEEPEVAL_TELEMETRY_OPT_OUT`/`RAGAS_DO_NOT_TRACK`,
Article III.a's existing mechanism. **The suite still failed.** Confirmed why by reading
pytest's own bootstrap order, not assuming III.a's precedent applied unchanged: `deepeval`
registers a `pytest11` entry-point plugin (`deepeval.plugins.plugin`, importing
`deepeval.constants` — which runs `deepeval/__init__.py`, hence `autoload_dotenv()`) that
pytest imports during its **plugin-discovery phase**, strictly before any hook — including
`pytest-env`'s own `pytest_load_initial_conftests`, marked `tryfirst=True` — gets to run.
`tryfirst` orders hooks *among already-imported plugins*; it cannot run before a plugin is
imported, and `DEEPEVAL_TELEMETRY_OPT_OUT` only ever worked because deepeval reads it lazily
at telemetry-send time, not at import time — the two opt-outs are not the same shape.

**The actual fix: `conftest.py` cleans up rather than prevents.** Nothing at the
pytest-configuration level can run before entry-point plugin import, but this repo's own root
`conftest.py` is still guaranteed to load before test *collection*, which is early enough.
Module-level (not inside a fixture or hook), it pops `NVIDIA_API_KEY`/`OPENAI_API_KEY`/
`GROQ_API_KEY` from `os.environ` unconditionally. The `DEEPEVAL_DISABLE_DOTENV=1` ini entry
is kept — real, verified effect for anything that imports `deepeval` fresh *after*
pytest-env applies it (e.g. `evals/cli.py`), just not for this specific race.
`test_the_nvidia_credential_is_absent_and_the_suite_is_green_anyway` is the end-to-end
regression test: it now passes because `conftest.py` cleaned up, not because the leak never
happened, and `test_env_block_opt_outs_took_effect_before_import` (renamed) confirms the ini
declaration itself is real.

**29 (new, found chasing what looked like a `max_tokens` truncation — a data-corruption bug
present since the Groq era, in this repo's own code, not NIM or ragas).** Raising
`InstructorModelArgs(max_tokens=...)` from 4096 to 16000 did not fix a live-pass crash:
`AttributeError: 'str' object has no attribute 'model_dump_json'`, now firing immediately, on
the *first* task of every metric, not deep into a run. That pattern — instant, universal,
survives a config change that should have mattered — pointed away from truncation and toward
the cache.

`RagasCacheBackend.set()` (`evals/cache/ragas_backend.py`) stored every value with:

```python
payload = json.dumps(value, default=str, sort_keys=True)
```

`value` here is whatever `InstructorLLM.generate()` returned — for every ragas metric except
embeddings, always a pydantic model instance (instructor's structured-output contract).
Pydantic models are not natively JSON-serializable, so `json.dumps` falls back to `default`,
which is `str` — silently converting the **entire model** to its `str()` repr instead of
raising:

```python
>>> json.dumps(SomeModel(x=1, y="hi"), default=str)
'"x=1 y=\'hi\'"'
```

That string round-trips fine through `json.loads` on the next `get()` — it is valid JSON, just
JSON of the wrong thing. The crash only fires on a cache **hit**: a cache **miss** returns the
real, correctly-typed object straight from `func(*args, **kwargs)`, never touching this path.
A hit happens whenever the exact same prompt is requested twice — ragas' self-consistency
re-asks (`n=3` per statement) are the common case in a single run, and any second `pytest`/live
pass reading previously-written evidence is another. The masking mechanism explains why this
went uncaught for so long: **every first-ever call works**; only the second exposes the bug,
and most of this project's runs are the first (or only) touch of a given key.

**Scope, measured, not assumed:** grepping every cache entry's `response` field for a
top-level JSON string (rather than object/array) found **408 of 581** entries in the current
tree corrupted, and — checked directly against the commit that recorded it —
**121 of the 191** entries in `4584441` ("Record the Groq-era evidence store") were *already*
corrupted the moment that commit was made. The bug predates this session entirely; only the
symptom (a full-run crash instead of a silent bad value) was new, because this was the first
time the same key was ever requested twice in one run.

**Fix:** `evals/cache/model_json.py` adds a minimal `ModelJson` wrapper exposing only
`.model_dump_json()` — the one method the only consumer
(`ragas/prompt/pydantic_prompt.py:272`, `Generation(text=result.model_dump_json())`) ever
calls on a cache hit. `set()` now stores `value.model_dump_json()` under a sentinel key when
`value` has that method, and plain `json.dumps(...)` otherwise (embeddings, untouched); `get()`
returns a `ModelJson` on the sentinel, the parsed value otherwise. The exact original pydantic
*class* can never be reconstructed at read time — ragas' key carries no type information — so
the fix reproduces exactly what the one real consumer needs, not the object's full identity.

`tests/test_ragas_cache_backend.py::test_a_pydantic_model_round_trips_through_a_cache_hit` is
the regression test: reproducing the old code inline (`json.dumps(model, default=str)` →
`json.loads(...)` → `.model_dump_json()`) confirms it raises the exact same `AttributeError`
the live pass hit, before asserting the fixed backend round-trips correctly. The 408 corrupted
entries were deleted, not repaired — their stored payload was a Python repr, not recoverable
structured data.

**30 (new, `evals.behavior.live_pass` — a different judge path than Trap 27/29, and a
different failure shape).** `CachedJudge._call_live` (`evals/judge/cached.py`), the path
every `GEval`-family metric (`RefusalCorrectness`, etc.) goes through, made a plain
`client.chat.completions.create(model=model, messages=[...])` call with no `response_format`
and no schema enforcement of any kind — unlike the ragas path, which goes through
`instructor` and gets structured-output guarantees for free. deepeval's own `GEval` prompt
template asks the model to emit JSON and nothing else, then parses the raw text with
`trimAndLoadJson`.

On a live `evals.behavior.live_pass` run, one call (`RefusalCorrectness`, scoring `v1_naive`
on a case it genuinely got wrong — answered instead of refusing) produced this, verbatim:

```
{
  "reason": "The expected output calls for a refusal stating the information is unavailable,
  but the actual output provides an answer claiming there is no evidence of a policy, which
  is not a refusal and thus misaligned.",
  "score": 0

Make sure no

{
  "reason": "The expected output calls for a refusal stating the information is unavailable,
  ...
  "score": 0
}
```

A complete, correct, valid JSON object — followed by an echoed fragment of the judge's own
system prompt ("Make sure not to..."), followed by the model restarting the entire object a
second time. Two valid JSON values glued together by stray text is not one valid JSON
document, and `trimAndLoadJson` (even with its trailing-comma regex fixup) can't parse it:
`json.decoder.JSONDecodeError: Expecting ',' delimiter`, surfacing as deepeval's own
`ValueError: Evaluation LLM outputted an invalid JSON. Please use a better evaluation model.`

**Not a truncation (Trap 27's `max_tokens` fix does not apply here) and not a caching bug
(Trap 29's fix does not apply here either)** — the model's own decoding genuinely produced
two answers instead of one. This is a model-reliability characteristic of
`nvidia/nemotron-3-super-120b-a12b` under this prompt shape, discovered only by running the
live pass and reading the malformed cache entry it actually wrote.

**Fix, verified against the exact failing case, not assumed.** Live-probed
`response_format={"type": "json_object"}` against this same model and endpoint first — NIM
honors OpenAI's JSON mode (confirmed: `finish_reason="stop"`, clean single-object output on a
probe call). Narrows the failure but doesn't structurally guarantee against it (JSON mode
constrains grammar, not the model's decision to start a second message), so
`evals/judge/json_completion.py` adds one retry: on `json.JSONDecodeError`, ask again once
before giving up. Deleted the one corrupted cache entry and reran the exact same live pass
end to end — 30/30 calls (both variants, 15 cases each), zero malformed entries.

**A note, not a numbered trap — this one's in code we wrote, not a third-party library.**
`tests/vibes_checks.py` (the deterministic half of the vibes gate, FR-028) shipped with
three latent false-positive bugs: a `MIN_LENGTH=20` floor that rejected terse, correct
answers (`"$65 USD per day."`, 16 chars); an error-string check that substring-matched
ordinary English (`"none"` inside "...at least none is described..."); and a sentence-end
check that rejected trailing brackets and citation lines (`"...material.)"`,
`"Source: password-policy.md"`). All three were invisible for the same reason every trap
above was: nothing had run the check against real output. `test_vibes.py` skipped on
`CacheMiss` until today's first live pass populated the cache, so the heuristics had never
once seen a real answer. All three surfaced, and were only fixed, once live answers existed
to check them against — the identical failure shape as every trap in this document, just
authored here instead of found in a dependency.

---

---

# Verification round 2 — 2026-09-03

## Verification 1 — the `langchain-community` pin

**Still load-bearing, but the pin was wrong. Moved `0.3.31` → `0.4.1`.**

Natural resolution, fresh venv, `uv pip install ragas==0.4.3` and nothing else:

```
langchain-community      0.4.2
  File ".../ragas/llms/base.py", line 12, in <module>
    from langchain_community.chat_models.vertexai import ChatVertexAI
ModuleNotFoundError: No module named 'langchain_community.chat_models.vertexai'
```

So the pin stays. But bisecting every release at or above 0.3.31 — the full candidate set is
`0.3.31`, `0.4.1`, `0.4.2`; there is no stable `0.4.0` — shows the removal landed in 0.4.2
alone, not across 0.4.x:

| `langchain-community` | `import ragas` |
|---|---|
| `0.4.2` | **FAIL** — `No module named 'langchain_community.chat_models.vertexai'` |
| `0.4.1` | OK |
| `0.3.31` | OK |

`0.4.1` verified against the full pinned stack: identical resolved langchain graph as 0.3.31
(`langchain 1.3.18`, `langchain-core 1.6.1`, `langchain-openai 1.6.0`), metrics instantiate,
`EvaluationDataset` round-trips, `DiskCacheBackend` constructs. Pin updated in
`pyproject.toml`; only the upper bound moved, so nothing else changes.

## Verification 2 — `ToolCorrectnessMetric`

**Yes: it scores purely off `LLMTestCase(input=..., tools_called=..., expected_tools=...)`
with no `@observe()` instrumentation and no judge call.** Verified with `socket.connect`
patched to raise and a stub judge whose `generate`/`a_generate` raise `AssertionError` —
neither fired.

`_required_params = [INPUT, TOOLS_CALLED, EXPECTED_TOOLS]`. The LLM path is reached only when
`available_tools` is passed:

```python
tool_calling_score = self._calculate_score()          # pure Python
if self.available_tools and not test_case.multimodal:
    tool_selection_score = self._get_tool_selection_score(...)   # LLM call
else:
    tool_selection_score = ToolSelectionScore(score=1, ...)      # hardcoded
score = min(tool_calling_score, tool_selection_score.score)
```

`_generate_reason()` is string formatting only — no LLM, even with `include_reason=True`.
**Leave `available_tools=None` and this metric is fully offline and deterministic.**

### Runnable proof

```python
from deepeval import assert_test
from deepeval.test_case import LLMTestCase, ToolCall
from deepeval.metrics import ToolCorrectnessMetric

PASSES = LLMTestCase(input="q", actual_output="a",
                     tools_called=[ToolCall(name="search"), ToolCall(name="fetch")],
                     expected_tools=[ToolCall(name="search"), ToolCall(name="fetch")])

FAILS = LLMTestCase(input="q", actual_output="a",
                    tools_called=[ToolCall(name="search")],
                    expected_tools=[ToolCall(name="search"), ToolCall(name="fetch")])

def test_tools_correct() -> None:
    assert_test(PASSES, [ToolCorrectnessMetric(threshold=0.9)])   # passes

def test_tools_incomplete() -> None:
    assert_test(FAILS, [ToolCorrectnessMetric(threshold=0.9)])    # AssertionError, score 0.5
```

Observed failure message:
`Metrics: Tool Correctness (score: 0.5, threshold: 0.9, strict: False, error: None, ...) failed.`

### Scoring semantics (measured, names only)

Three mutually exclusive modes. Default is **both flags `False`**.

| called | expected | default | `should_exact_match` | `should_consider_ordering` |
|---|---|---|---|---|
| `[a, b]` | `[a, b]` | 1.0 | 1.0 | 1.0 |
| `[b, a]` | `[a, b]` | **1.0** | **0.0** | **0.5** |
| `[a, b, c]` | `[a, b]` | **1.0** | **0.0** | 1.0 |
| `[a]` | `[a, b]` | 0.5 | 0.0 | 0.5 |
| `[z]` | `[a, b]` | 0.0 | 0.0 | 0.0 |
| `[]` | `[]` | 1.0 | 1.0 | 1.0 |
| `[a]` | `[]` | 0.0 | 0.0 | 0.0 |

- **Default = unordered recall over `expected_tools`.** Greedy match on `(name, type)`, each
  called tool consumed at most once, `score = Σ best_match / len(expected_tools)`.
  Order is ignored and **extra called tools are not penalised at all** — `[a,b,c]` against
  `[a,b]` scores a perfect 1.0. It is a subset/recall check, not a match check.
- **`should_exact_match=True`** — positional and binary: lengths must be equal, then
  `name` and `type` must match index-for-index. Any reorder or extra tool ⇒ 0.0.
- **`should_consider_ordering=True`** — weighted longest-common-subsequence over the called
  sequence, divided by `len(expected_tools)`. Fractional and order-sensitive.
- `strict_mode=True` forces `threshold = 1` and floors any sub-threshold score to 0.

### Per-tool-argument comparison

Off by default. Opt in with `evaluation_params=[ToolCallParams.INPUT_PARAMETERS]` (and/or
`ToolCallParams.OUTPUT`).

| called args | expected args | default | `should_exact_match` |
|---|---|---|---|
| `{q:x, k:1}` | `{q:x, k:1}` | 1.0 | 1.0 |
| `{q:x, k:2}` | `{q:x, k:1}` | **0.5** | **0.0** |

`_compare_dicts` gives **partial credit**: `(keys present in both and equal) / (keys in union)`,
recursing into nested dicts. `OUTPUT` is binary — any mismatch zeroes that tool.

### `copy_metrics()` survival — **it survives**

Unlike a naive custom metric (Trap 1), `ToolCorrectnessMetric` stores every constructor
argument under an identically-named attribute, so the async rebuild is lossless:

| attribute | original | after `copy_metrics()` |
|---|---|---|
| `threshold` | 0.9 | 0.9 |
| `should_exact_match` | True | True |
| `should_consider_ordering` | True | True |
| `evaluation_params` | `[INPUT_PARAMETERS]` | `[INPUT_PARAMETERS]` |
| `strict_mode` / `include_reason` | False / True | False / True |

Confirmed end-to-end: `assert_test(..., run_async=True)` (the default) raised correctly on
the failing case. No new trap — this metric is safe on the async path.

### New trap found while testing

**16. `ToolCorrectnessMetric()` cannot be constructed without `OPENAI_API_KEY`.**
`__init__` calls `initialize_model(model)` eagerly, and `initialize_model(None)` builds an
`OpenAIModel`, which raises at construction time:

```
deepeval.errors.DeepEvalError: OpenAI API key is not configured.
Set OPENAI_API_KEY in your environment or pass `api_key` to OpenAIModel(...).
```

This fires even though the model is never used when `available_tools is None`. Under Article VI
the default CI environment has no API key at all, so **every** DeepEval metric must be
constructed with an explicit `model=` — a real `AnthropicModel`, or an offline stub judge for
the deterministic metrics. This applies to all metrics, not just this one; the eager
`initialize_model` call is in the shared constructor pattern.

**17. DeepEval phones home to PostHog on import/run.** Observed
`[PostHog] error uploading: network!` with sockets blocked. Set
`DEEPEVAL_TELEMETRY_OPT_OUT=YES` — verified to silence it completely (1 upload attempt → 0).
Article VI's socket guard turns this into a hard failure otherwise. The variable is read at
**import** time, so it must be set before `deepeval` is imported — hence the `env` block in
`[tool.pytest.ini_options]` (which needs the `pytest-env` plugin; `env` is not a pytest core
ini key) rather than an assignment in `conftest.py`.

**18. A bare `AnthropicModel()` silently selects a different judge than our pin.**
`DEFAULT_ANTHROPIC_MODEL` in `deepeval/models/llms/constants.py` is `"claude-opus-5"`. This
repo pins `claude-sonnet-5`. Omitting `model=` therefore yields a judge that is **2.5× more
expensive** ($5/$25 against $2/$10 per MTok) and — because Article III's cache key includes the
judge identity — **invalidates every cache entry**, converting an offline `$0.00` run into a
live billed one. Nothing raises; the scores merely come from a different model than the
thresholds were calibrated against. Combined with Trap 16 (the eager `initialize_model(None)`
that demands `OPENAI_API_KEY`), the rule is the same in both directions: **never construct a
DeepEval metric or model without an explicit `model=`.**

### Verification-2 commands

```
uv pip install ragas==0.4.3                      # → langchain-community 0.4.2, import FAILS
uv pip install langchain-community==0.4.1        # → import ragas OK  (0.4.2 FAILS, 0.3.31 OK)
python tc_probe2.py                              # sockets blocked + stub judge; all tables above
```

---

# Verification round 3 — 2026-09-04

Spec §12 named six unresolved items plus two direct questions about the cache extension
points. All eight are resolved below by introspecting the repo's own pinned `.venv`, not by
reading documentation. Two are genuinely new traps; one corrects the *stated mechanism* (not
the conclusion) behind an existing trap; one is a material correction to the spec's Ragas
embeddings plan.

## V3.1 — `ragas.cache.CacheInterface`: exists, and implementing it truly bypasses diskcache

Verbatim from the installed package:

```python
class CacheInterface(ABC):
    @abstractmethod
    def get(self, key: str) -> Any: ...
    @abstractmethod
    def set(self, key: str, value) -> None: ...
    @abstractmethod
    def has_key(self, key: str) -> bool: ...
```

The `cacher()` decorator calls only these three methods — `has_key` / `get` / `set` — on
whatever object is passed. It never touches `diskcache` unless the object handed to it *is* a
`DiskCacheBackend`:

```python
def cacher(cache_backend=None):
    def decorator(func):
        if cache_backend is None:
            return func
        backend: CacheInterface = cache_backend
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            cache_key = _generate_cache_key(func, args, kwargs)
            if backend.has_key(cache_key):
                return backend.get(cache_key)
            result = func(*args, **kwargs)
            backend.set(cache_key, _make_pydantic_picklable(result))
            return result
        # ...async_wrapper mirrors this
        return async_wrapper if is_async else sync_wrapper
    return decorator
```

Traced the wiring end to end: `llm_factory(..., cache=cache)` → `get_adapter("instructor")
.create_llm(client, model, provider, cache=cache)` → `InstructorLLM.__init__` does

```python
self.cache = cache
if self.cache is not None:
    self.generate = cacher(cache_backend=self.cache)(self.generate)
    self.agenerate = cacher(cache_backend=self.cache)(self.agenerate)
```

A custom `CacheInterface` therefore **fully replaces** `DiskCacheBackend` for LLM calls — no
SQLite, no `diskcache` import, ever touched. Confirmed, not assumed.

**New finding along the way — `llm_factory` fires ragas' own telemetry, unconditionally:**

```python
track(LLMUsageEvent(provider=provider, model=model, llm_type="llm_factory", ...))
```

`ragas._analytics.track()` — decorated `@silent`, so it never raises — does
`requests.post(USAGE_TRACKING_URL, json=payload, timeout=1)` where `USAGE_TRACKING_URL =
"https://t.explodinggradients.com"`. Confirmed as a real outbound attempt: calling `track()`
directly (bypassing `@silent`) raised a genuine `ConnectionError` from a DNS resolution
attempt against that host. Opt-out is `RAGAS_DO_NOT_TRACK=true`, gated by
`@lru_cache(maxsize=1)` on `do_not_track()` — same footgun class as DeepEval's PostHog call
(Trap 17): it must be set **before ragas is imported**, verified:

```
$ python -c "import ragas._analytics as a; print(a.do_not_track())"     # False (unset)
$ RAGAS_DO_NOT_TRACK=true python -c "import ragas._analytics as a; print(a.do_not_track())"
True   # and track() then returns cleanly with no connection attempted
```

**This is a genuine gap in the repo as it stands today**: `pyproject.toml`'s
`[tool.pytest.ini_options] env` block currently sets `DEEPEVAL_TELEMETRY_OPT_OUT=YES` but does
**not** set `RAGAS_DO_NOT_TRACK=true`. Under Article VI's socket-blocking fixture this call
would be silently swallowed by `@silent` exactly like the PostHog case — it would not fail the
suite, but it is a real outbound-call attempt on every `evaluate()`/`llm_factory()` invocation,
which is precisely what "zero outbound calls" (success criterion 4) forbids regardless of
whether the failure is visible.

## V3.2 — `DiskCacheBackend`'s real on-disk format: hybrid, and the large-value path is non-deterministic

Read `diskcache/core.py` (the installed `diskcache==5.6.3`) rather than assuming from
reputation. `Cache.store()`:

```python
if type_value is str and len(value) < min_file_size:      # default min_file_size = 32KB
    return 0, MODE_RAW, None, value                         # → inline in SQLite
...
else:  # pickled value (our case — dicts)
    result = pickle.dumps(value, protocol=self.pickle_protocol)
    if len(result) < min_file_size:
        return 0, MODE_PICKLE, None, sqlite3.Binary(result)  # → inline BLOB in cache.db
    else:
        filename, full_path = self.filename(key, value)      # → separate file
        self._write(full_path, io.BytesIO(result), 'xb')
        return len(result), MODE_PICKLE, filename, None
```

`filename()`, the method that names the spillover file, **ignores both `key` and `value`**:

```python
def filename(self, key=UNKNOWN, value=UNKNOWN):
    hex_name = codecs.encode(os.urandom(16), 'hex').decode('utf-8')   # random, not content-derived
    sub_dir = op.join(hex_name[:2], hex_name[2:4])
    name = hex_name[4:] + '.val'
    return op.join(sub_dir, name), op.join(self._directory, op.join(sub_dir, name))
```

**Empirically confirmed**, not just read:

```
$ python -c "
from ragas.cache import DiskCacheBackend
c = DiskCacheBackend(cache_dir='/tmp/dc_probe')
c.set('small_key', {'response': 'short', 'score': 0.8})
c.set('large_key', {'response': 'X'*40000, 'score': 0.2})   # 40KB, > 32KB threshold
"
$ find /tmp/dc_probe
06/ad/1d65bf9015c35d5e7e30316281d2.val   (40050 bytes)   ← large_key
cache.db                                (32768 bytes, SQLite 3.x)   ← small_key, inline
```

Two fresh directories, **identical** 40KB content written to each:

```
run 1: 76/57/a407ac136aa034f364adb12554f7.val
run 2: b3/87/089d2de543deb9610a4e206bf50e.val
```

Different filenames for byte-identical content. **Answer to "is it genuinely one SQLite file,
or does diskcache write per-key files above a size threshold": neither, cleanly — it's a
hybrid.** Small values (the common case for judge JSON responses) live as opaque BLOB rows
inside one binary `cache.db`; anything ≥32KB spills to a file named by 16 random bytes, tied to
neither the key nor the content, so re-running an identical calibration does not reproduce the
same bytes on disk. This is worse for a committed, reviewable cache than the spec's original
characterization ("a SQLite file, not one JSON file per key") suggested — it isn't just the
wrong format, the large-value path is actively non-reproducible. **Confirms and sharpens** the
spec §3.3 decision to implement `CacheInterface` directly rather than use `DiskCacheBackend`
for the committed store; no change to the decision itself.

## V3.3 — §12 item: `embedding_factory`'s `cache=` support — confirmed, but with a bypass trap

**Superseded 2026-09-08 (ninth amendment) on the provider only, not the finding.** This round
tested `embedding_factory(provider="openai", ...)` because OpenAI was the only embeddings
provider available at the time; `evals/embeddings.py` has since moved to a local
`sentence-transformers` model (Verification round 7). The trap this section documents — the
modern `BaseRagasEmbedding` interface silently bypasses `cache=` on its plural methods — is a
fact about ragas' own class hierarchy, not about OpenAI, and still governs why
`evals/embeddings.py` avoids the modern interface regardless of which provider backs it. Kept
as dated evidence rather than rewritten, per this repo's own standard for retired material.

`embedding_factory(provider="openai", model=..., client=..., cache=cache)` (modern interface)
does accept and use `cache=`. Traced: `_create_modern_embedding` pops `cache` from kwargs and
passes it to `provider_cls._from_factory(..., cache=cache)`; `BaseRagasEmbedding.__init__`:

```python
def __init__(self, cache: Optional[CacheInterface] = None):
    self.cache = cache
    if self.cache is not None:
        self.embed_text = cacher(cache_backend=self.cache)(self.embed_text)
        self.aembed_text = cacher(cache_backend=self.cache)(self.aembed_text)
```

**New trap: only the singular `embed_text`/`aembed_text` are wrapped. The plural
`embed_texts`/`aembed_texts` are not — and `OpenAIEmbeddings` (the concrete class
`embedding_factory("openai", ...)` returns) overrides `embed_texts` with a genuinely different,
uncached implementation:**

```python
def embed_texts(self, texts, **kwargs):
    ...
    response = self.client.embeddings.create(input=texts, model=self.model, **kwargs)  # direct API call
    result = [item.embedding for item in response.data]
    track(EmbeddingUsageEvent(...))   # ragas telemetry again, per call
    return result
```

Any code path that calls `embed_texts`/`aembed_texts` (batch) on a modern `OpenAIEmbeddings`
instance **silently bypasses the cache**, even though `cache=` was passed at construction and
no error is raised. Whether this matters depends entirely on which method the caller (in our
case, `ResponseRelevancy` — see V3.4) actually invokes.

## V3.4 — §12 item: does `ResponseRelevancy` accept an injected embeddings object? Yes — but only the *legacy* one, and it's deprecated

**Superseded 2026-09-08 (ninth amendment) on the provider only, not the finding.** The
conclusion below — `ResponseRelevancy` requires the legacy `LangchainEmbeddingsWrapper`,
because it is the only class exposing `embed_query`/`embed_documents` — is provider-neutral
and is exactly what Verification round 7 (§V7.2) re-confirmed before wrapping a local
`sentence-transformers` model in it instead of `OpenAIEmbeddings`. Only the concrete
embeddings object named below (`OpenAIEmbeddings`) is no longer what `evals/embeddings.py`
constructs. Kept as dated evidence rather than rewritten.

`ResponseRelevancy.calculate_similarity` calls:

```python
question_vec = np.asarray(self.embeddings.embed_query(question))
gen_question_vec = np.asarray(self.embeddings.embed_documents(generated_questions))
```

These are **LangChain-interface method names** (`embed_query` / `embed_documents`), not the
modern ragas names (`embed_text` / `embed_texts`). Confirmed the modern `BaseRagasEmbedding`
(what `embedding_factory("openai", ...)` returns) simply does not have them:

```
>>> 'embed_query' in dir(BaseRagasEmbedding)       # False
>>> 'embed_documents' in dir(BaseRagasEmbedding)    # False
>>> dir(BaseRagasEmbedding)  # non-dunder
['aembed_text', 'aembed_texts', 'embed_text', 'embed_texts']
```

**Passing a modern `embedding_factory()` result to `ResponseRelevancy` crashes at scoring time
with `AttributeError: 'OpenAIEmbeddings' object has no attribute 'embed_query'`.** This is not
a hypothetical — it is the object type the spec's §7.1 plan implicitly assumed.

The class that actually works is the **legacy** `ragas.embeddings.base.BaseRagasEmbeddings`
(plural — not to be confused with the modern singular `BaseRagasEmbedding`), whose `__init__`
wraps exactly the methods `ResponseRelevancy` calls:

```python
def __init__(self, cache: Optional[CacheInterface] = None):
    self.cache = cache
    if self.cache is not None:
        self.embed_query = cacher(cache_backend=self.cache)(self.embed_query)
        self.embed_documents = cacher(cache_backend=self.cache)(self.embed_documents)
        self.aembed_query = cacher(cache_backend=self.cache)(self.aembed_query)
        self.aembed_documents = cacher(cache_backend=self.cache)(self.aembed_documents)
```

The usable concrete class is `ragas.embeddings.LangchainEmbeddingsWrapper(langchain_embeddings,
cache=cache)`. **It is deprecated and slated for removal**, confirmed via the warning it emits
on access:

```
DeprecationWarning: LangchainEmbeddingsWrapper is deprecated and will be removed in a future
version. Use the modern embedding providers instead: embedding_factory('openai', ...)
```

— i.e. ragas' own deprecation notice recommends the exact path that `ResponseRelevancy` cannot
consume. **This is a real conflict in the installed package, not a hypothetical migration
concern**, and it directly changes spec §7.1: caching for `ResponseRelevancy`'s embeddings must
go through `LangchainEmbeddingsWrapper(..., cache=...)`, not `embedding_factory(...,
cache=...)`. Flagging for the spec rather than resolving unilaterally: either accept the
deprecated class now (it still fully functions and is cached correctly), or drop
`ResponseRelevancy` to avoid depending on a class ragas has already marked for removal.

## V3.5 — §12 item: does `GEval` hard-require `a_generate_raw_response`? No — confirmed with a live, network-blocked run

`no_log_prob_support(model)`, the guard that decides whether `GEval` attempts the
logprob-weighted scoring path, only branches on `OpenAIModel` / `AzureOpenAIModel` / `str`,
consulting `OPENAI_MODELS_DATA`:

```python
def no_log_prob_support(model):
    if isinstance(model, str):
        if not OPENAI_MODELS_DATA.get(model).supports_log_probs: return True
    elif isinstance(model, OpenAIModel) and not model.model_data.supports_log_probs: return True
    elif isinstance(model, AzureOpenAIModel) and not model.model_data.supports_log_probs: return True
    return False
```

**For `AnthropicModel` or any custom `DeepEvalBaseLLM`, this returns `False` — the opposite of
what Article III's justification currently implies.** Confirmed empirically:

```
>>> no_log_prob_support(AnthropicModel(model="claude-sonnet-5", api_key="sk-fake"))
False
>>> no_log_prob_support(CustomDeepEvalBaseLLMSubclass())
False
```

**Correction to Trap 5 / Article III's stated mechanism (the conclusion is still correct):**
the fallback to coarse scoring does not happen because DeepEval's registry says
`supports_log_probs=False` for Claude models — that flag is **never consulted** for Anthropic
or custom judges in this code path; `ANTHROPIC_MODELS_DATA` doesn't even appear in
`no_log_prob_support`. The real cause: neither `AnthropicModel` nor a bare `DeepEvalBaseLLM`
defines `a_generate_raw_response` / `generate_raw_response` at all —

```
>>> hasattr(AnthropicModel(model="claude-sonnet-5", api_key="sk-fake"), "a_generate_raw_response")
False
```

— so the call `await self.model.a_generate_raw_response(prompt, top_logprobs=...)` raises a
plain `AttributeError` from a **missing attribute**, caught by the same `except AttributeError:`
handler that the logprob guard would have triggered. The fallback is therefore **unconditional
and automatic** for every Anthropic-family or custom judge, regardless of what any registry
says — the registry flag could be flipped to `True` and nothing would change, because it is
never read for these model types. The *conclusion* ("GEval scores coarsely on Claude judges, on
every tier, so a pricier judge buys nothing here") holds; the *mechanism* recorded in
`CONSTITUTION.md` Article III and Trap 5 should eventually be corrected to say so (not done
here — out of scope for this pass, which only touches this file).

The fallback path is `a_generate_with_schema_and_extract`, which calls
`metric.model.a_generate_with_schema(prompt, schema=schema_cls)` — **not**
`a_generate_raw_response`. `a_generate_with_schema` is **not abstract** on `DeepEvalBaseLLM`; it
has a working default:

```python
async def a_generate_with_schema(self, *args, schema=None, **kwargs):
    if schema is not None:
        try:
            return await self.a_generate(*args, schema=schema, **kwargs)
        except TypeError:
            pass
    return await self.a_generate(*args, **kwargs)
```

**Confirmed end-to-end** with sockets patched to raise on `connect`, a bare `DeepEvalBaseLLM`
subclass implementing only the four required abstract methods, returning plain JSON strings:

```python
class StubJudge(DeepEvalBaseLLM):
    def get_model_name(self): return "stub-judge"
    def load_model(self): return None
    def generate(self, prompt, *a, **k): return json.dumps({"score": 8, "reason": "..."})
    async def a_generate(self, prompt, *a, **k): return json.dumps({"score": 3, "reason": "..."})
```

Both `m.measure(tc)` (async_mode=True, the default) and the sync path
(`m.async_mode = False; m.measure(tc)`) returned real scores (`0.8`, `0.3`) with real reasons,
no crash, no network. **A bare `DeepEvalBaseLLM` returning plain JSON strings is sufficient for
`GEval` — confirmed by execution, not inference.**

**New finding, not previously recorded: `GEval(criteria=...)` issues *two* cached calls, not
one.** Before scoring, it calls the model again to auto-generate CoT evaluation steps,
expecting a *different* JSON shape (`{"steps": [...]}`, not `{"score", "reason"}`). Discovered
by feeding a stub that always returned `{"score", "reason"}` and getting a real
`KeyError: 'steps'` from deepeval's own extraction code — not a guess. Passing
`evaluation_steps=[...]` directly instead of `criteria=` skips this and reduces `GEval` to one
call, confirmed by running both configurations side by side. **This affects Article III's cache
key design and Article VIII's cost table**: `RefusalCorrectness` and any other `criteria=`-based
custom metric costs two cache entries and two judge calls per case, not one, unless it is
rewritten to pass `evaluation_steps=` explicitly.

## V3.6 — §12 item: `TestsetGenerator.generate_with_langchain_docs` on markdown

Signature confirmed:

```python
generate_with_langchain_docs(documents: Sequence[LCDocument], testset_size: int,
    transforms=None, transforms_llm=None, transforms_embedding_model=None, ...)
```

Takes plain `langchain_core.documents.Document` objects (`page_content` + `metadata`) — no
ragas-specific document type needed for markdown input. Confirmed it **raises `ValueError`
explicitly** if no `llm`/`embedding_model` is available (instance or argument) — it never
silently falls back to a hidden default provider:

```
"An llm client was not provided. Provide an LLM on TestsetGenerator instantiation ..."
```

Read `default_transforms()`: builds a pipeline of `HeadlinesExtractor`, `SummaryExtractor`,
`ThemesExtractor`, `NERExtractor`, `EmbeddingExtractor`, `CosineSimilarityBuilder` — every one
constructed with the `llm`/`embedding_model` objects we pass in, so every LLM/embedding call
this pipeline makes is cacheable through the same `CacheInterface` mechanism as everything
else. Token counting uses `num_tokens_from_string` (tiktoken-based — already a hard ragas
dependency); no `nltk` reference or download call found in this path. `nltk` is gated behind
ragas' `[all]` extra (confirmed earlier from the PyPI dependency dump) and is not required here.
**No extra dependencies beyond the current pin set are needed** to run synthetic generation
over the markdown corpus.

## V3.7 — §12 item: is `pytest-rerunfailures` silently active?

Confirmed installed (`deepeval`'s hard dependency) and registered as a `pytest11` plugin
(`rerunfailures` → `pytest_rerunfailures`). **Confirmed inert without an explicit flag** — a
deliberately flaky test (fails on attempts 1–2, passes on 3) was run under plain `pytest -q`
with no `--reruns` and no `reruns` ini option:

```
FAILED test_flaky.py::test_flaky - AssertionError: attempt 1
1 failed in 0.12s
```

No retry occurred. Trap 15's existing guidance ("do not enable reruns") was already correct;
this closes the open question with a passing/failing demonstration rather than leaving it
assumed.

### Verification-3 commands

```
python -c "from ragas.cache import CacheInterface; ..."           # method signatures, §V3.1
python -c "from ragas.cache import DiskCacheBackend; c=...; ..."  # empirical layout, §V3.2
python -c "from ragas.embeddings.base import embedding_factory; ..." # cache wiring, §V3.3
python -c "from ragas.metrics import ResponseRelevancy; ..."      # embed_query/embed_documents, §V3.4
python geval_stub_probe.py                                        # sockets blocked, live scoring, §V3.5
python -c "from ragas.testset import TestsetGenerator; ..."       # signature + default_transforms, §V3.6
pytest test_flaky.py -q                                           # 1 failed, no rerun, §V3.7
```

---

# Verification round 4 — 2026-09-05

Found while designing the judge cache. One finding, and it is the most dangerous in this
document: it fails silently, in the direction of a green run.

## V4.1 — Trap 19: ragas' cache key is **model-blind**, and using it verbatim would serve a stale judge's answers

`cacher()` does **not** let us supply a key. It computes one itself:

```python
def _generate_cache_key(func, args, kwargs):
    filtered_kwargs = {k: v for k, v in kwargs.items() if k not in EXCLUDE_KEYS}  # ['callbacks']
    key_data = {
        "function": func.__qualname__,
        "args": _make_hashable(args),
        "kwargs": _make_hashable(filtered_kwargs),
    }
    key_string = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.sha256(key_string.encode("utf-8")).hexdigest()
```

`cacher` wraps the **bound** method `InstructorLLM.generate(self, prompt, response_model)`, so
`self` is not in `args`. The key therefore covers `("InstructorLLM.generate", prompt,
response_model)` — **and nothing about the model.** The model name, the client, the provider and
the system prompt all live on `self`, which the key never sees.

Measured, two `llm_factory` instances differing only in model:

```
>>> l1 = llm_factory("claude-sonnet-5", provider="anthropic", client=c, cache=p1)
>>> l2 = llm_factory("claude-opus-5",   provider="anthropic", client=c, cache=p2)
>>> k1 = _generate_cache_key(l1.generate, ("who approves travel?", Out), {})
>>> k2 = _generate_cache_key(l2.generate, ("who approves travel?", Out), {})
sonnet key: 495542df537934cdb7d0e05c
opus   key: 495542df537934cdb7d0e05c
IDENTICAL ACROSS MODELS: True
```

**Consequence if ragas' key is stored as-is:** changing the judge pin silently reuses the previous
judge's cached answers. Nothing raises, the run is green, the cost table reads `$0.00`, and every
threshold is now calibrated against a judge that never ran. This directly contradicts
`CONSTITUTION.md` Article III — *"Anything that moves the output moves the key, or the cache is
lying"* and *"changing the judge model invalidates the entire cache by design."*

**Resolution used in this repo:** the `CacheInterface` implementation **re-keys**. It accepts
ragas' key as the `prompt_hash` component only, then derives the real key through the shared
`make_key(call_kind, model_identity, prompt_hash)`. Ragas' key is a legitimate prompt hash — a
deterministic SHA-256 over function, prompt and response model — it is simply not a *complete*
one. Model identity is supplied by us, on the outside.

**What is safe here, verified alongside:** the key is stable across processes and machines.
`_make_hashable` resolves pydantic instances via `model_dump()`, and the only non-JSON argument is
`response_model`, a **class**, which `default=str` renders as `<class 'module.Name'>` — no memory
address, so no per-process drift. The danger is exclusively the missing model identity.

## V4.2 — a sync `anthropic.Anthropic` client keeps ragas off the event loop

`InstructorLLM.generate` branches on `self.is_async` and, when true, calls
`self._run_async_in_current_loop(...)`. With a plain sync `anthropic.Anthropic` client:

```
>>> llm_factory("claude-sonnet-5", provider="anthropic", client=anthropic.Anthropic(...), cache=p)
is_async: False
```

This matters because DeepEval is forced to `run_async=False` (Article XI) and the two libraries
must share one pytest process. A sync client keeps ragas' per-call path off the event loop
entirely; `evaluate()`'s own executor still uses one, but with no loop already running under plain
pytest, `allow_nest_asyncio=True` is inert rather than re-entrant.

Also confirmed in passing: `provider="anthropic"` routes through the **instructor** adapter with a
pre-initialised client, so no `litellm` dependency is needed despite the docstring's emphasis on
it; `DeepEvalBaseLLM.__abstractmethods__` is exactly `{generate, a_generate, get_model_name,
load_model}`; `a_generate_with_schema` has a working default (consistent with V3.5); and
`deepeval.metrics.utils.copy_metrics` is still present on the pin, so the harness-integrity test
of Article XI still passes for the right reason.

### Verification-4 commands

```
python -c "import ragas.cache as c; inspect.getsource(c._generate_cache_key)"   # key derivation, §V4.1
python - <<'PY' ... _generate_cache_key(l1.generate, ...) vs l2 ...             # model-blind proof, §V4.1
python -c "llm_factory(..., client=anthropic.Anthropic(...)); print(l.is_async)" # sync path, §V4.2
python -c "from deepeval.models.base_model import DeepEvalBaseLLM; ..."          # abstract set, §V4.2
```

# Verification round 5 — 2026-09-08 — Groq

Speculative: no code in this repo uses `groq` yet. Investigated ahead of any integration
decision, per the same rule as everything else in this document — verify the installed
package, not recall or a vendor's docs.

## V5.1 — `uv add groq` resolves clean, no pin conflicts

```
uv add groq
Resolved 134 packages in 17.07s
 + groq==1.7.0
```

`uv add` proposed a range (`groq>=1.7.0`); repinned to `groq==1.7.0` by hand to match this
file's "exact pins only" rule (Article IX) before it ever landed as a range. `uv lock` +
`uv sync` afterward left every existing pin untouched — confirmed by reading installed
versions directly, not by trusting a clean resolver exit code:

```
anthropic 1.3.0 · deepeval 4.2.0 · ragas 0.4.3 · langchain-community 0.4.1 · pydantic 2.13.5
```

No shared transitive dependency needed to move. `groq` vendors its own `httpx`-based client
stack, independent of `anthropic`'s.

## V5.2 — `groq.Groq()` is sync by default, same shape as `anthropic.Anthropic` — but its
credential check is eager, where Anthropic's (V4.2) is lazy

```
>>> groq.Groq.__mro__
(<class 'groq.Groq'>, <class 'groq._base_client.SyncAPIClient'>, ..., <class 'object'>)
```

`Groq(SyncAPIClient)` — confirmed sync, matching `anthropic.Anthropic`'s shape (V4.2). But
unlike Anthropic's client (lazy — `_build_client` defers), `Groq.__init__` resolves the
credential and raises immediately if none is found, before any network call:

```python
# groq/_client.py, Groq.__init__
if api_key is None:
    api_key = os.environ.get("GROQ_API_KEY")
if api_key is None:
    raise GroqError(
        "The api_key client option must be set either by passing api_key to the client or "
        "by setting the GROQ_API_KEY environment variable"
    )
```

Measured with `GROQ_API_KEY` unset:

```
>>> groq.Groq()
GroqError: The api_key client option must be set either by passing api_key to the client or
by setting the GROQ_API_KEY environment variable
```

Same eager check on `AsyncGroq.__init__`, verbatim. **Consequence for any future Article
VI.a work:** offline test collection would need a real (or dummy) `GROQ_API_KEY` present
just to construct the client — `anthropic.Anthropic()`'s laziness is not something to
assume carries over to a different provider's SDK just because both wrap `DeepEvalBaseLLM`
the same way; each provider's eagerness has to be checked on its own.

## V5.3 — `logprobs` is a real, typed parameter — but the SDK's own docstring says no
current Groq model honors it

`chat.completions.create(..., logprobs: Optional[bool] | Omit = omit, top_logprobs:
Optional[int] | Omit = omit, ...)` exists on both the sync and async clients, and the
response type models the full shape if it were ever populated —
`Choice.logprobs: Optional[ChoiceLogprobs]`, `ChoiceLogprobs.content:
Optional[List[ChatCompletionTokenLogprob]]`, each entry carrying `token`, `logprob`, and
`top_logprobs: List[TopLogprob]` (up to 20 alternatives, per-token) — token-level, with
top-k, identical in shape to OpenAI's format, since Groq's API is OpenAI-compatible.

But the SDK's own bundled docstring (generated from Groq's OpenAPI spec at build time —
package-shipped, not marketing docs, though still a claim rather than a network-verified
fact) states plainly, on both `logprobs` and `top_logprobs`:

> This is not yet supported by any of our models.

**Not verified against a live call** — no `GROQ_API_KEY` is available in this environment,
so this could not be confirmed by actually sending `logprobs=True` and reading back a
response. Treat as a strong, code-adjacent signal, not a proven fact.

**Consequence for `a_generate_raw_response`-style fine-grained GEval scoring:** if the
docstring is accurate, real per-token log-probability scoring is not currently reachable
through Groq at all, regardless of DeepEval-side plumbing — the ceiling stays coarse
scoring, the same limitation this repo already lives with for its own `claude-sonnet-5`
judge (no logprobs from Anthropic's Messages API either). This is a provider-side ceiling,
not a plumbing gap this repo could code around.

## V5.4 — deepeval ships **no** `GroqModel` — searched the whole installed package, zero hits

```
grep -rli "groq" .venv/…/site-packages/deepeval   # every file, every extension
(no output)
```

So questions 4's two sub-checks (cache hook before the network call; pricing table reading
from a library-owned registry) don't apply — there is nothing to check. `deepeval.models.llms`
ships `anthropic_model.py`, `openai_model.py`, `gemini_model.py`, `grok_model.py` (xAI's
**Grok** — note the name collision with Gro**q**, easy to mis-grep or mis-remember; this repo
came within one letter of documenting the wrong provider), `deepseek_model.py`,
`amazon_bedrock_model.py`, `azure_model.py`, `kimi_model.py`, `litellm_model.py`,
`openrouter_model.py`, `portkey_model.py`, `gateway_model.py`, `local_model.py`,
`ollama_model.py` — no `groq_model.py` among them, on `deepeval==4.2.0`. A Groq judge would
have to be hand-written against `DeepEvalBaseLLM` directly, the same way this repo's own
`CachedJudge` is (V3's "implements `DeepEvalBaseLLM` directly" section) — which also means
there is no library-side cache-hook or pricing-table risk to inherit, because there is no
library code in the path at all yet.

## V5.5 — no embedded pricing or model registry in the `groq` package itself

```
grep -rli "price\|pricing\|cost\|MODELS_DATA" .venv/…/site-packages/groq --include="*.py"
(no output)
```

Unlike `anthropic`'s `ANTHROPIC_MODELS_DATA` (Trap 7), `groq` ships no pricing table to be
stale in the first place — there is no second Trap-7 waiting inside the SDK. The flip side:
there is also no fallback, so a future `pricing.yaml` row for any Groq model rests entirely
on an external, dated source, same as this repo's existing `text-embedding-3-small` row.

Also confirmed while reading `chat.completions.create`'s signature: `model` is a required
parameter with no default (`Union[str, Literal[...]]`, not `Omit`-defaulted) — the raw SDK
has no Trap-18-style silent-default-model risk either, same finding as V3's conclusion for
raw `anthropic` (and consistent with V5.4: since no `GroqModel` wrapper exists yet, neither
risk currently reaches this repo through any path).

## V5.6 — published pricing: unstable ground, flagged UNVERIFIED

Checked live via web search and fetch (not from training-data recall, and not from the
`groq` package, which carries no pricing data per V5.5). Groq's own marketing pricing page,
`groq.com/pricing/`, was fetched directly today and **contains no pricing table** — it
now redirects to generic homepage content with no per-model rates, matching third-party
reporting that the public pricing page was pulled around 2026-08-26. The Console billing
page (`console.groq.com/settings/billing/plans`) confirms three tiers (Free / Developer /
Enterprise) but also defers to the now-empty marketing page for actual numbers, and full
pricing detail requires an authenticated console session this environment doesn't have.

Third-party aggregators disagree with each other on at least one model: whether
`llama-3.3-70b-versatile` is still self-serve-priced or moved to enterprise-only
contact-sales is contradicted across sources dated within days of each other. **Not used**
for that reason.

`openai/gpt-oss-20b` — one of the models in this SDK's own `chat.completions.create`
`Literal[...]` type — was consistently reported as self-serve-priced across every source
checked, so it is the number recorded here:

```yaml
openai/gpt-oss-20b:
  input_per_mtok: 0.075
  output_per_mtok: 0.30
  source: >-
    UNVERIFIED — Groq's own pricing page (groq.com/pricing/) carried no pricing table as
    of 2026-09-08 (confirmed by direct fetch); this number is triangulated from
    third-party aggregators only (cloudzero.com, last confirmed by that site
    2026-09-04) and has no primary-source confirmation. Re-verify against Groq's console
    billing page (requires an authenticated account) before this number is trusted for
    anything that spends money.
```

Not written into `evals/pricing.yaml` — no Groq call is wired into this repo yet, and
Article VIII's table exists to price calls that actually happen. Recorded here so the
number doesn't need to be re-derived if a Groq judge or generator is added later.

### Verification-5 commands

```
uv add groq                                                              # §V5.1
uv run python3 -c "import importlib.metadata as m; print(m.version('anthropic'), ...)"  # §V5.1
env -u GROQ_API_KEY uv run python3 -c "import groq; groq.Groq()"         # eager check, §V5.2
grep -n "def create\|logprobs\|top_logprobs" groq/resources/chat/completions.py  # §V5.3
grep -rli "groq" .venv/…/site-packages/deepeval                          # §V5.4
grep -rli "price\|pricing\|cost\|MODELS_DATA" .venv/…/site-packages/groq --include="*.py"  # §V5.5
WebFetch groq.com/pricing/ , console.groq.com/settings/billing/plans     # §V5.6
```

# Verification round 6 — 2026-09-08 — writing the Groq migration

Round 5 introspected the installed packages ahead of any decision. This round is what
actually broke while wiring the three call sites through Groq (Eighth amendment) — found by
execution, not by reading source in isolation, per this document's own rule.

## V6.1 — ragas 0.4.3's `llm_factory(provider="groq", ...)` is broken for a real client

The docstring lists `groq` as a supported `provider=` example. It is not, on this pin.
`ragas.llms.base._get_instructor_client` special-cases `openai`/`anthropic`/`google`/
`gemini`/`litellm`/`perplexity`; everything else — including `"groq"` — falls to
`_patch_client_for_provider`, which hardcodes Anthropic's method shape for *every*
unrecognized provider:

```python
# ragas/llms/base.py, _patch_client_for_provider — the generic fallback
return instructor.Instructor(client=client, create=client.messages.create, ...)
```

`groq.Groq()` has no `.messages` attribute at all (its cached properties are `chat`,
`embeddings`, `audio`, `models`, `batches`, `files` — confirmed by reading `groq/_client.py`
in V5.2). Reproduced by execution, with a throwaway `GROQ_API_KEY` (construction-time
failure only — no network reached):

```
>>> llm_factory("openai/gpt-oss-20b", provider="groq", client=groq.Groq())
ValueError: Failed to initialize groq client with instructor adapter. Ensure you've
created a valid groq client.
Error: Failed to patch groq client with Instructor: 'Groq' object has no attribute
'messages'
```

`provider="openai"` does not work around it either: `instructor.from_openai` isinstance-
checks strictly against `(openai.OpenAI, openai.AsyncOpenAI)` and raises `ClientError` on
anything else, `groq.Groq()` included — confirmed by reading
`instructor/v2/providers/openai/client.py`.

**Fix used in this repo:** bypass `ragas.llm_factory()` entirely and call
`instructor.from_groq(client)` directly — `instructor` ships a correct, dedicated factory
for Groq (`instructor/v2/providers/groq/client.py`) that uses `client.chat.completions.create`
and isinstance-checks against `(groq.Groq, groq.AsyncGroq)`, which `ragas` simply never
wires up to its own `provider=` dispatch. The result is then passed straight into
`ragas.llms.base.InstructorLLM(client=..., model=..., provider="groq", ...)`, whose own
`__init__` does not validate `client`'s type at all — confirmed by reading its signature
(`client: t.Any`). See `evals/ragas_llm.py`.

## V6.2 — a real `groq.Groq()`, wrapped via `instructor.from_groq()`, is confirmed sync

Not run inside the pytest suite — VI.a forbids constructing a real Groq client on any
offline or test path, and this environment has no real `GROQ_API_KEY`. Verified instead by
direct execution in this repo's venv (pinned `groq==1.7.0`, `ragas==0.4.3`), with a
throwaway credential, construction only, no live call:

```
>>> client = instructor.from_groq(groq.Groq())
>>> llm = InstructorLLM(client=client, model="openai/gpt-oss-20b", provider="groq",
...                      model_args=InstructorModelArgs())
>>> llm.is_async
False
```

Mechanism, read from `InstructorLLM._check_client_async`: it inspects
`self.client.client` (the raw client `instructor.from_groq` stored on the wrapper) for
`.chat.completions.create`, then checks `inspect.iscoroutinefunction(...)` on it — `False`
for the sync `groq.Groq`. **This is a different branch than whatever covered Anthropic's
client** (V4.2's finding): `anthropic.Anthropic()` has no `.chat.completions` attribute at
all — its shape is `.messages.create` — so `_check_client_async`'s OpenAI-shaped branch
could never have matched it; some other branch (the `AsyncInstructor`-class-name check or
the closure-inspection fallback) must have been doing the work there. The offline stub in
`evals/ragas_llm.py` (`_NeverCalledClient`) exists specifically to hit this same
`.chat.completions.create`-shaped branch without ever touching the real SDK, and is
confirmed (in-suite, offline, no live key involved) to produce the same `is_async: False`.

## V6.3 — `ChatCompletion.usage` is `Optional`, unlike Anthropic's required `Message.usage`

Caught by `mypy --strict`, not by reading the field list — a first read of
`groq/types/chat/chat_completion.py` found a `usage: CompletionUsage` line and assumed it
was `ChatCompletion`'s; it belongs to a different class in the same file. `ChatCompletion`'s
own field, lower in the file, is `usage: Optional[CompletionUsage] = None`. Groq's
`compound-beta` models report `usage_breakdown` instead, which is presumably why the field
is optional at the type level even though every model this repo pins should always return
one. **This repo's `_call_live` (both `app/generate.py` and `evals/judge/cached.py`) raises
`RuntimeError` if `usage` is `None`** rather than defaulting token counts to `0` — a $0.00,
0-token row for a call that really happened would misreport what the run actually cost,
which is the exact failure Article VIII exists to prevent.

### Verification-6 commands

```
GROQ_API_KEY=dummy uv run python3 -c "llm_factory('...', provider='groq', client=groq.Groq())"  # §V6.1
GROQ_API_KEY=dummy uv run python3 -c "instructor.from_groq(groq.Groq()); InstructorLLM(...).is_async"  # §V6.2
uv run mypy evals/judge/cached.py app/generate.py                        # surfaced §V6.3
```

# Verification round 7 — 2026-09-08 — local embeddings

Motivation: `ResponseRelevancy`'s embeddings (`evals/embeddings.py`) are the last live path
still needing `OPENAI_API_KEY` (see the credential audit two turns prior). Investigated
whether a local `sentence-transformers` model can replace it. **Pure introspection —
`uv add sentence-transformers` was run, measured, and then fully reverted** (`pyproject.toml`
and `uv.lock` restored from a pre-check copy, `uv sync` re-run to uninstall); `git status`
is clean and the suite is still 86 passed / 18 skipped after reverting. No code, constitution
or spec touched.

## V7.1 — no dependency conflict, but not a small addition either

`uv add sentence-transformers` resolves clean against the existing pinned stack — verified
by diffing every package's version between the pre- and post-add `uv.lock`, not by reading
the exit code: **zero already-pinned packages changed version** (`ragas`, `deepeval`,
`langchain-community`, `pydantic`, etc. all identical). Resolved:

```
sentence-transformers==6.0.1
torch==2.14.0
transformers==5.16.1
```

31 new lockfile entries total, but `uv.lock` is a universal lock covering every platform —
19 of the 31 are `nvidia-*`/`cuda-*`/`triton` markers for Linux+CUDA that never install on
this Darwin machine. What actually installs here is 12 packages (`torch`, `transformers`,
`sentence-transformers`, `scikit-learn`, `sympy`, `tokenizers`, `safetensors`, `joblib`,
`threadpoolctl`, `cloudpickle`, `mpmath`, `narwhals`).

**This is not contained on disk or on the wire.** Measured directly:

```
Downloading torch (121.4MiB)             # compressed wheel, this run
.venv/lib/python3.12/site-packages/torch          527M   # unpacked
.venv/lib/python3.12/site-packages/transformers    52M
.venv/lib/python3.12/site-packages/sklearn         32M
.venv total: 610M -> 1.2G                          # roughly doubles
```

No conflict is not the same as free. Article 0's ten-minute cold-clone budget and Article
IX's "boring dependencies" both have to weigh a ~120MB additional download and a doubled
`.venv` against removing the last `OPENAI_API_KEY` requirement — a real trade-off, not
merely a compatibility question, and not this round's call to make. **Decided in the ninth
amendment (2026-09-08): the trade was accepted, gated behind the `calibration` dependency
group so the cost lands only on the author's machine, never a viewer's `uv sync`.**

## V7.2 — the LangChain-interface wrapper exists, and needs no new package

Two candidates exist; only one is already in the pinned stack.

**`langchain_community.embeddings.HuggingFaceEmbeddings`** (`langchain_community.embeddings.
huggingface`) — already importable from the pinned `langchain-community==0.4.1`, **zero new
package beyond `sentence-transformers` itself**. Confirmed by reading the class directly:
`embed_query`/`embed_documents` are real methods (not the modern `embed_text` shape), it
imports `sentence_transformers.SentenceTransformer` internally, and `model_name` accepts
any HF hub ID. It carries a class-level `@deprecated(since="0.2.2", removal="1.0",
alternative_import="langchain_huggingface.HuggingFaceEmbeddings")` decorator — deprecated,
not removed, and **the same posture this repo already accepted for `LangchainEmbeddingsWrapper`
itself** ("the legacy wrapper is required, deprecation warning and all" — `evals/embeddings.py`'s
own docstring).

**`langchain_huggingface.HuggingFaceEmbeddings`** — the non-deprecated successor the warning
above points to. **Would be a new dependency** (`langchain-huggingface`, not currently
resolved by anything pinned). Not installed or introspected this round — the community
version already satisfies the interface and needs nothing new, so pulling in a second
package to avoid one deprecation warning is a judgment call for whoever implements this,
not a functional requirement.

**Ragas has its own native HuggingFace provider too** (`ragas.embeddings.HuggingFaceEmbeddings`,
`ragas/embeddings/huggingface_provider.py`, reachable via `embedding_factory("huggingface",
model=...)`) — checked because it would avoid LangChain entirely. It implements
`embed_text`/`aembed_text`/`embed_texts`/`aembed_texts`, **not** `embed_query`/
`embed_documents` — the same modern-interface gap V3.4 already found for ragas' OpenAI
provider. `ResponseRelevancy` needs the LangChain names specifically, so this native
provider is not usable here regardless of backend; the `LangchainEmbeddingsWrapper` route
is required no matter which embedding provider backs it.

## V7.3 — `all-MiniLM-L6-v2`: ~90MB, one-time, reasonable

Checked via the model's own HuggingFace repo listing, not memory. `model.safetensors` is
90.9MB (the modern, non-pickle format — preferred over `pytorch_model.bin`, same 90.9MB,
for not executing arbitrary code on load); tokenizer assets add roughly 700KB more. One
download, ~91MB total, well inside "reasonable for a one-time calibration download" — small
against the 527MB `torch` install itself, which dominates the actual cost of this change.
Not downloaded or loaded this round (no model weights fetched) — sizing only.

## V7.4 — cache-wrapping works the same way OpenAI's did, but async is sync-in-a-thread

`LangchainEmbeddingsWrapper.__init__` (`ragas/embeddings/base.py`) wraps all four methods
identically regardless of what LangChain `Embeddings` subclass it holds:

```python
self.embed_query = cacher(cache_backend=self.cache)(self.embed_query)
self.embed_documents = cacher(cache_backend=self.cache)(self.embed_documents)
self.aembed_query = cacher(cache_backend=self.cache)(self.aembed_query)
self.aembed_documents = cacher(cache_backend=self.cache)(self.aembed_documents)
```

So `cache=` support is unconditional on the wrapper, not something `HuggingFaceEmbeddings`
has to provide itself — confirmed by reading `__init__`, not assumed from `OpenAIEmbeddings`
working. But `langchain_community`'s `HuggingFaceEmbeddings` defines only the two sync
methods (`embed_query`, `embed_documents`); it does not override `aembed_query`/
`aembed_documents`. Those come from `langchain_core.embeddings.Embeddings`'s base class,
which implements them as `return await run_in_executor(None, self.embed_query, text)` —
**real `async def` methods that exist and are callable, but sync-in-a-thread underneath,
not genuine async I/O.** `OpenAIEmbeddings` had true async HTTP for the same methods;
`HuggingFaceEmbeddings` does not, because there is no network call to make async — the
model runs in-process. This is not a defect for this repo: `ResponseRelevancy`'s live pass
already runs generation and judging synchronously per Article XI's `run_async=False`
discipline, so a thread-executor shim costs nothing observable here. **Calibration does not
need to stay sync-only for this reason** — the async methods work, they are simply
local-CPU-bound rather than network-bound underneath.

## V7.5 — cache location: outside the repo, confirmed by the resolution chain, not by convention

`langchain_community.HuggingFaceEmbeddings.cache_folder` defaults to `None`, which
`sentence_transformers`'s own model loader (`sentence_transformers/base/model.py`) resolves
as: `SENTENCE_TRANSFORMERS_HOME` env var if set, otherwise deferred to `huggingface_hub`'s
own default. Read `huggingface_hub/constants.py` directly:

```python
default_home = os.path.join(os.path.expanduser("~"), ".cache")
HF_HOME = os.getenv("HF_HOME", os.path.join(os.getenv("XDG_CACHE_HOME", default_home), "huggingface"))
default_cache_path = os.path.join(HF_HOME, "hub")
```

Default resolves to `~/.cache/huggingface/hub` — under the user's home directory, entirely
outside `/Users/darshanpanchal/trust-no-agent`. It cannot land in the repo or get swept into
`git add .` by default; the only way it would is if someone explicitly set `HF_HOME` or
`SENTENCE_TRANSFORMERS_HOME` to a path under the repo, which nothing here does. No
`.gitignore` entry is needed for the default case.

### Verification-7 commands

```
cp pyproject.toml uv.lock /tmp/...-pre-check   # snapshot before touching either
uv add sentence-transformers                    # §V7.1 — resolution + download sizes
diff pre/post uv.lock, parsed for version changes per package  # §V7.1 — zero conflicts
du -sh .venv/lib/python3.12/site-packages/{torch,transformers,sklearn}  # §V7.1
grep -n "def embed_query\|def embed_documents\|async def aembed" \
  langchain_community/embeddings/huggingface.py                 # §V7.2, §V7.4
grep -n "class HuggingFaceEmbeddings" -A5 ragas/embeddings/huggingface_provider.py  # §V7.2
WebFetch huggingface.co/sentence-transformers/all-MiniLM-L6-v2/tree/main  # §V7.3
grep -n "HF_HOME\|default_cache_path" huggingface_hub/constants.py       # §V7.5
cp /tmp/...-pre-check pyproject.toml uv.lock && uv sync         # revert — confirmed clean
```

# Verification round 8 — 2026-09-09 — NVIDIA NIM

Motivation: evaluate NVIDIA's hosted NIM catalog (`build.nvidia.com` / `integrate.api.nvidia.com`)
as a candidate provider, the same way Groq was evaluated in round 5. **Pure introspection —
`uv add langchain-nvidia-ai-endpoints` was run against a snapshotted `pyproject.toml`/`uv.lock`,
measured, then fully reverted**; both files diff identical to the pre-check copies afterward,
`uv sync` re-run to uninstall, and the suite still collects at the same 86/18 split it did before
this round (a separate, pre-existing local-environment issue with `GROQ_API_KEY` being ambient in
this shell is unrelated to this round and is not this round's finding). No code, constitution or
spec touched.

## V8.1 — canonical access path: a dedicated LangChain package that does *not* wrap `openai`

Two structurally different candidates exist, and the question in the prompt ("`openai` library
with custom `base_url`, or a dedicated package?") turns out not to be either/or — both work,
for different reasons.

**`langchain-nvidia-ai-endpoints`** is the canonical LangChain-ecosystem package (`ChatNVIDIA`,
`NVIDIA`, `NVIDIAEmbeddings`). `uv add langchain-nvidia-ai-endpoints --no-sync` resolved cleanly
to **1.4.3** against the existing lock — 165 packages resolved, one new top-level package, zero
version changes to anything already pinned. Its own dependencies, read from the resolved
`uv.lock` entry, are `aiohttp`, `langchain-core`, `requests` — **not `openai`**. So this package
builds its own HTTP client rather than wrapping the `openai` SDK, even though the endpoint it
targets is OpenAI-schema-compatible (`ChatNVIDIA(model=...)` constructs with
`base_url='https://integrate.api.nvidia.com/v1'` by default, confirmed by construction — and
independently by fetching NVIDIA's own hosted API reference at
`docs.api.nvidia.com/nim/reference/llm-apis`, which documents `POST /v1/chat/completions`
against that same host).

**The raw "`openai` library + custom `base_url`" passthrough also works structurally**, and
needs no new package at all — see §V8.7. Nothing pins this path; it would be
`openai.OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=os.environ["NVIDIA_API_KEY"])`
written by hand.

**Pin-candidate correction: the prompt asked for `uv add --dry-run`; that flag does not exist**
on the installed `uv 0.11.23` (`uv add --help` lists no such option — checked directly, not
assumed). `--no-sync` is the actual non-installing substitute: it resolves and writes the lock
without touching `.venv`. Also load-bearing for Article IX: **`uv add langchain-nvidia-ai-endpoints`
with no version given writes a *range*, not a pin** — `langchain-nvidia-ai-endpoints>=1.4.3` —
into `[project.dependencies]`, exactly what "no ranges, anywhere" forbids. An exact pin requires
spelling out the version: `uv add "langchain-nvidia-ai-endpoints==1.4.3"`.

## V8.2 — construction is lazy, not eager: no parity with Groq's V5.2

Constructed `ChatNVIDIA(model="meta/llama3-8b-instruct")` with `NVIDIA_API_KEY` absent from the
environment. **It succeeded — no exception.** It printed one `UserWarning`:

> An API key is required for the hosted NIM. This will become an error in the future.

Confirmed independently that construction makes no network call either, by patching
`socket.socket.connect` to raise and constructing again — no `AssertionError`, so nothing
reached the wire. This is the *opposite* of Groq's eager `GroqError` (V5.2) and matches the old
lazy `anthropic.Anthropic()` shape instead. **Do not assume parity across providers** — this
prompt's own instruction, and confirmed by execution: Groq and NVIDIA sit on opposite sides of
this exact question, in the same SDK generation.

The package's own maintainers say this is temporary ("will become an error in the future"), so
treat it as a landmine rather than a permanent guarantee: if this repo ever adopts NVIDIA, VI.a's
"never construct a real client on an offline path" rule should still apply on day one, rather
than being deferred until the warning becomes the error it's already announced it will become.

For comparison, checked the *other* candidate from §V8.1: the raw `openai` library (`2.54.0`,
already installed — see §V8.7) **is eager**. `openai.OpenAI(base_url="https://integrate.api.nvidia.com/v1")`
with no key raises immediately:

```
OpenAIError: Missing credentials. Please pass an `api_key`, ... or set the `OPENAI_API_KEY` ...
```

So which VI.a-style discipline is even needed depends on which of the two packages gets chosen
— the dedicated NVIDIA package needs "never construct on an offline path" for a forward-looking
reason (today a warning, tomorrow an error); the raw-`openai`-library path needs it because
construction is eager *right now*, matching the template VI.a already uses for Groq.

## V8.3 — async is genuine, not sync-in-a-thread

`ChatNVIDIA._generate` (sync) and `._agenerate` (async) are independent methods reading from
independent client objects — `self._client` vs. `self._async_client`. Read `_agenerate`'s body
directly:

```python
async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
    _, payload, extra_headers = self._prepare_inputs_and_payload(messages, stop, stream=False, **kwargs)
    response = await self._async_client.aget_req(payload=payload, extra_headers=extra_headers)
    return self._process_generate_response(response, run_manager, ...)
```

This is real async I/O (`aiohttp`-backed), unlike `HuggingFaceEmbeddings`'s
sync-in-a-thread shim (V7.4). Of the three providers introspected so far (Groq, local
`sentence-transformers`, NVIDIA), this is the only one confirmed to have genuine async under
the hood — moot for this repo either way, since Article XI's `run_async=False` discipline means
nothing here would ever exercise the difference.

## V8.4 — logprobs: a recognized name on the completions endpoint, silent everywhere on whether any model honors it

**`ChatNVIDIA` (chat completions):** no mention of `logprobs`/`top_logprobs` anywhere in the
class's source. It does forward arbitrary kwargs straight into the request payload
(`payload.update(kwargs)`, no allowlist) — a caller could pass `logprobs=True` and it would
reach the wire, but the wrapper gives no signal either way about server-side support.

**`NVIDIA` (the older completions-style class, `/v1/completions`):** here `logprobs` **is** one
of fifteen names in an explicit allowlist read directly from source
(`__check_kwargs`'s `completions_arguments` set: `frequency_penalty, max_tokens,
presence_penalty, seed, stop, temperature, top_p, best_of, echo, logit_bias, logprobs, n,
suffix, user, stream`) — the classic OpenAI legacy-completions shape. Anything outside that set
triggers `warnings.warn(f"Unrecognized, ignored arguments: {unrecognized_kwargs}")`; `logprobs`
does not trigger it, so the wrapper treats the name as legitimate.

**Neither class states, in source or docstring, whether any currently-served NIM model actually
honors it.** This is a *weaker* signal than Groq's V5.3: Groq's SDK volunteered an explicit
negative ("This is not yet supported by any of our models"); NVIDIA's package is simply silent.
Checked NVIDIA's own hosted reference page directly (`docs.api.nvidia.com/nim/reference/llm-apis`)
rather than relying on memory — it documents the endpoint shape and lists available models, but
says nothing about per-model logprobs support. **Not verified against a live call — no
`NVIDIA_API_KEY` in this environment.** Switching providers is not shown to fix GEval's
coarse-scoring ceiling; it is shown to be an open question, same honest non-answer this repo
already gives for Groq.

## V8.5 — no built-in deepeval NIM class; the closest path is a generic gateway that clears a bar Groq's hand-written judge doesn't

`deepeval==4.2.0`'s `deepeval/models/llms/` package (`pkgutil.iter_modules`) contains:
`amazon_bedrock_model, anthropic_model, azure_model, deepseek_model, gateway_model,
gemini_model, grok_model, kimi_model, litellm_model, local_model, ollama_model, openai_model,
openrouter_model, portkey_model`. **No `nvidia_model.py` or `nim_model.py`.** A repo-wide,
case-insensitive grep for "nvidia"/"nim" inside the installed `deepeval` package returns exactly
two hits, both in `utils.py`, both `os.system("nvidia-smi ...")` GPU-memory diagnostics —
unrelated to the NIM API, a false positive worth naming so nobody re-discovers it and gets
excited.

The closest existing path is `deepeval.models.llms.litellm_model.LiteLLMModel`, a generic
gateway dispatching through the (not installed this round) `litellm` package, which supports an
`nvidia_nim/` model-string prefix upstream. Checked the same way `AnthropicModel`/`GroqModel`
were checked:

- **Construction is lazy.** `LiteLLMModel(model="nvidia_nim/meta/llama3-8b-instruct")` with no
  credential present in the environment constructs without error — no eager check.
- **It defines `a_generate_raw_response`.** Confirmed via `dir(LiteLLMModel)`. Per the third
  amendment's finding (V3.5): a missing `a_generate_raw_response` is exactly what forces GEval's
  coarse-scoring `AttributeError` fallback for *any* `DeepEvalBaseLLM` subclass, including this
  repo's own hand-written Groq judge. `LiteLLMModel` clears that bar — the first path found,
  across every round that has looked at judge providers, that might actually reach
  fine-grained scoring.

**Not confirmed end-to-end.** `litellm` itself was never installed this round, no live call was
made, and no cache-hook or cost-table-source inspection was performed on `LiteLLMModel` — it
isn't this repo's judge, so that depth of check wasn't warranted yet. Flagging the discovery for
whoever looks at this next; not a recommendation to switch.

## V8.6 — pricing: "free" is a marketing claim, not a price; no dated number exists to pin

`langchain_nvidia_ai_endpoints.callbacks` ships `DEFAULT_MODEL_COST_PER_1K_TOKENS` — read
directly: **`{}`, empty.** Its docstring points a caller who wants to fill in their own
`price_map` at "AI Foundation Endpoint pricing per `https://www.together.ai/pricing`" — the
package's own in-code guidance names a *competitor's* pricing page as the convention to follow,
not NVIDIA's own rates. Unlike deepeval's `ANTHROPIC_MODELS_DATA` (Trap 7), there is no bundled
number here to be *wrong* — there is simply nothing bundled at all.

Fetched `build.nvidia.com` directly (2026-09-09, not from memory): its "Use Inference Endpoints"
section states **"Free inference with leading models."** No credit amount, expiry, or
rate-limit figure appears anywhere on that page or on `docs.api.nvidia.com/nim/reference/llm-apis`.

**Conclusion: no stable, dated price exists to pin — same finding as Groq's V5.5–V5.6.** If NIM
is ever adopted, `pricing.yaml` gets the identical `UNVERIFIED` treatment Groq's rows already
carry. "Free" is an unquantified marketing claim, not a $0.00 verified against a primary source,
and Article VIII doesn't treat the two as interchangeable.

## V8.7 — base install already covers the raw-REST path; the dedicated package is a small, clean addition

`openai==2.54.0` is already installed, transitively, via `langchain-openai` — confirmed by
`import openai; openai.__version__` in this environment, no new package required. So the
"`openai` library + custom `base_url`" path from §V8.1 costs nothing new.

The dedicated-package path costs one real pin, and a small one: `aiohttp` and `requests` are new
(`langchain-core` is already present); `uv add ... --no-sync` resolved 165 packages against the
existing lock with **zero version changes to anything already pinned**. Nothing like V7.1's
650MB `torch` addition — either candidate is lightweight.

### Verification-8 commands

```
uv add langchain-nvidia-ai-endpoints --no-sync                          # §V8.1 — resolves, no install
grep -A5 'name = "langchain-nvidia-ai-endpoints"' uv.lock                # §V8.1 — deps: aiohttp, langchain-core, requests
uv sync                                                                   # actually install, for introspection
NVIDIA_API_KEY unset; ChatNVIDIA(model=...)                              # §V8.2 — lazy, UserWarning only
socket.socket.connect patched to raise; ChatNVIDIA(model=...)           # §V8.2 — zero network calls at construction
openai.OpenAI(base_url="https://integrate.api.nvidia.com/v1")           # §V8.2 — eager, OpenAIError
inspect.getsource(ChatNVIDIA._agenerate)                                 # §V8.3 — real aiohttp async client
grep -n logprob .venv/.../langchain_nvidia_ai_endpoints/llm.py           # §V8.4 — completions_arguments allowlist
WebFetch docs.api.nvidia.com/nim/reference/llm-apis                      # §V8.4, §V8.1 — endpoint shape, no logprobs claim
pkgutil.iter_modules(deepeval.models.llms.__path__)                      # §V8.5 — no nvidia/nim module
dir(LiteLLMModel); LiteLLMModel(model="nvidia_nim/...") with no key      # §V8.5
langchain_nvidia_ai_endpoints.callbacks.DEFAULT_MODEL_COST_PER_1K_TOKENS # §V8.6 — {}
WebFetch build.nvidia.com                                                # §V8.6 — "Free inference with leading models"
cp /tmp/v8-precheck/{pyproject.toml,uv.lock} . && uv sync                # revert — confirmed identical, suite re-collects
```

---

## Judge noise floor — measured 2026-09-11

Not a Trap (this is our own harness's measured behavior, not a library gotcha) and not a
provider verification round — a standalone, dated measurement that `evals/thresholds.yaml`'s
`comparison_tolerance` and `evals/ops/calibrate.py`'s `MARGIN_MIN` both cite, because they
answer two different questions and this is the evidence that keeps them from being conflated.

**Method.** Real `v2_fixed`'s already-committed, unchanged answers, re-scored under a fresh
`regression_demo:*` cache namespace each time — so every call is a genuine live NIM call, not
a cache hit, while the input (question, retrieved context, answer text) is held byte-identical
across runs. 4 independent runs per metric, `nvidia/nemotron-3-super-120b-a12b`, no sampling
parameters set (Article III bans them; the model's own defaults apply, unmeasured — this noise
is a property of what NIM actually does with this model, not of a knob we could have tuned).

| metric | run 1 | run 2 | run 3 | run 4 | min | max | spread | stdev |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| faithfulness | 0.8667 | 0.8933 | 0.8987 | 0.8040 | 0.8040 | 0.8987 | **0.0947** | 0.0434 |
| context_recall | 0.8000 | 0.7800 | 0.8000 | 0.7600 | 0.7600 | 0.8000 | **0.0400** | 0.0191 |
| RefusalCorrectness | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | **0.0000** | 0.0000 |

`context_recall`'s ragas prompt structurally never reads the `response` field (confirmed by
reading `LLMContextRecall._ascore` in the installed package: it builds its judge prompt from
`row["user_input"]`, `row["retrieved_contexts"]`, `row["reference"]` only) — so its 0.04 spread
here is 100% judge non-determinism, not measurement error from unstable inputs. `faithfulness`
is the noisiest gated metric. `RefusalCorrectness` showed **zero** variance across all 4 runs —
plausibly a ceiling/floor effect (15 relevant cases, an unambiguous refuse/answer call on each),
not proof the metric is noise-free in general, but the only one of the three with an empirical
basis for treating it that way.

**Two thresholds, two questions — do not conflate them.**

| | `MARGIN_MIN` (0.05) | `comparison_tolerance` (0.15) |
|---|---|---|
| Question | Can this metric tell v1 from v2 at all? | Did a rerun of the *same* system actually regress? |
| Compares | The full v1→v2 separation delta | One run's score against a prior run's score |
| Consumer | `evals/ops/calibrate.py`, at calibration time | `evals/ops/compare.py`, at compare time |
| Sized against | Nothing in this table — it is a floor on genuine signal | This table, directly — it must clear same-run noise |

`MARGIN_MIN` was never at risk from this noise floor — the separation deltas it gates are an
order of magnitude larger than anything measured here:

| metric | v1→v2 separation delta | noise spread (this table) | delta ÷ spread |
|---|---:|---:|---:|
| faithfulness | 0.1412 | 0.0947 | 1.5x |
| context_recall | 0.3200 | 0.0400 | 8.0x |
| RefusalCorrectness | 0.2000 | 0.0000 | ∞ |

`comparison_tolerance` is the one these numbers actually constrain, and the old value (0.02,
set before any live noise measurement existed) was roughly 5x too tight against `faithfulness`
alone — a same-model rerun with zero real change would have false-flagged as a regression on
faithfulness alone almost every time. `comparison_tolerance=0.15` is 1.5x the largest observed
spread (`faithfulness`, 0.0947), rounded to 0.05, giving headroom for the fact that n=4 is a
small sample and the true tail is presumably wider than what four draws happened to show.

**What this does not establish.** `RefusalCorrectness`'s n=4-exact-zero result is suggestive,
not proof of zero noise in general — a harder golden case, a different model, or a borderline
refuse/answer call could show variance this sample never exercised. `comparison_tolerance` was
sized to the noisiest of the three *as measured*, not to a theoretical worst case.

---

## `live.yml`'s `usd_ceiling` input is currently inert — flagged, not fixed

Not a Trap (this is our own workflow, not a library gotcha). Recorded here because it was
found while documenting `--allow-unpriced`'s comment in `.github/workflows/live.yml` and is
easy to miss on a read of that file alone: the dispatcher-facing `usd_ceiling` input looks
like a live spending cap, and today it is not one.

`record` (`evals/ops/record.py`) needs `--allow-unpriced` to start at all, because
`nvidia/nemotron-3-super-120b-a12b` has no row in `evals/pricing.yaml` (V8.6) and
`estimated_usd()` returns `None` for an unpriced model — there is nothing to check the
ceiling against before spending starts. Once that flag is set, the *in-run* check goes dark
too: the first uncached NIM call gives `cost.total_usd()` (`evals/cost.py`) a `None` row,
which makes the run's total `None` for good — a total cannot be known once one input isn't.
`_abort_if_over` (`evals/ops/record.py`) reads `allow_unpriced=True` plus `spent is None` as
"nothing to check" and returns without raising, for the rest of the run.

So as dispatched today, `usd_ceiling` bounds nothing — it is not read again after the
pre-flight estimate check, which itself never runs because the estimate is `None`. The actual
spending control on this workflow is upstream of the ceiling entirely: `workflow_dispatch` is
the only trigger (never `push`/`pull_request`, `tests/test_ci_config.py` enforces this), and
`environment: live-evidence` (`live.yml:21`) puts a human reviewer between "someone clicks
Run workflow" and any credential becoming readable. Those two hold; the number a dispatcher
types into `usd_ceiling` does not currently do anything.

**Not fixed here.** Fixing it means deciding what an unpriced run's ceiling behavior *should*
be — options include capping by call count instead of USD, refusing to run past N missing
entries regardless of price, or accepting the current human-approval-only posture as
sufficient and removing the input so it stops implying a guarantee it doesn't provide. That's
a decision for whoever picks this up next, not a one-line fix.
