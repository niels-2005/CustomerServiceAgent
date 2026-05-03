# DeepEval 5-min Quickstart (/docs/getting-started)

This quickstart takes you from installing DeepEval to your first passing eval in a few
minutes. You'll create a small test case, choose a metric, and run it with
`deepeval test run`.

By the end of this quickstart, you should be able to:

* Run your first local eval with a test case, metric, and `deepeval test run`.
* Add tracing when you want to evaluate an AI agent or its internal components.
* Know where to go next for datasets, synthetic data, integrations, and the
  Confident AI platform.

<Callout type="info">
  New to DeepEval? Checkout the [introduction](/introduction) to learn more about this framework.
</Callout>

## Installation [#installation]

In a newly created virtual environment, run:

```bash
pip install -U deepeval
```

`deepeval` runs evaluations locally on your environment. To keep your testing reports in a centralized place on the cloud, use [Confident AI](https://www.confident-ai.com), an AI quality platform with observability, evals, and monitoring that DeepEval integrates with natively:

```bash
deepeval login
```

<details>
  <summary>
    Configure Environment Variables
  </summary>

  DeepEval autoloads environment files (at import time)

  * **Precedence:** existing process env -> `.env.local` -> `.env`
  * **Opt-out:** set `DEEPEVAL_DISABLE_DOTENV=1`

  More information on `env` settings can be [found here.](/docs/evaluation-flags-and-configs#environment-flags)

  ```bash
  # quickstart
  cp .env.example .env.local
  # then edit .env.local (ignored by git)
  ```
</details>

<Callout type="note">
  Confident AI is free and allows you to keep all evaluation results on the cloud. Sign up [here.](https://app.confident-ai.com)
</Callout>

## Create Your First Test Run [#create-your-first-test-run]

Create a test file to run your first **end-to-end evaluation**.

<Tabs items="[&#x22;Single-Turn&#x22;, &#x22;Multi-Turn&#x22;]">
  <Tab value="Single-Turn">
    An [LLM test case](/docs/evaluation-test-cases#llm-test-case) in `deepeval` represents a **single unit of LLM app interaction**, and contains mandatory fields such as the `input` and `actual_output` (LLM generated output), and optional ones like `expected_output`.

    <ImageDisplayer src="ASSETS.llmTestCase" alt="LLM Test Case" />

    Run `touch test_example.py` in your terminal and paste in the following code:

    ```python title="test_example.py"
    from deepeval import assert_test
    from deepeval.test_case import LLMTestCase, SingleTurnParams
    from deepeval.metrics import GEval

    def test_correctness():
        correctness_metric = GEval(
            name="Correctness",
            criteria="Determine if the 'actual output' is correct based on the 'expected output'.",
            evaluation_params=[SingleTurnParams.ACTUAL_OUTPUT, SingleTurnParams.EXPECTED_OUTPUT],
            threshold=0.5
        )
        test_case = LLMTestCase(
            input="I have a persistent cough and fever. Should I be worried?",
            # Replace this with the actual output from your LLM application
            actual_output="A persistent cough and fever could be a viral infection or something more serious. See a doctor if symptoms worsen or don't improve in a few days.",
            expected_output="A persistent cough and fever could indicate a range of illnesses, from a mild viral infection to more serious conditions like pneumonia or COVID-19. You should seek medical attention if your symptoms worsen, persist for more than a few days, or are accompanied by difficulty breathing, chest pain, or other concerning signs."
        )
        assert_test(test_case, [correctness_metric])
    ```

    Then, run `deepeval test run` from the root directory of your project to evaluate your LLM app **end-to-end**:

    ```bash
    deepeval test run test_example.py
    ```

    Congratulations! Your test case should have passed ✅ Let's breakdown what happened.

    * The variable `input` mimics a user input, and `actual_output` is a placeholder for what your application's supposed to output based on this input.
    * The variable `expected_output` represents the ideal answer for a given `input`, and [`GEval`](/docs/metrics-llm-evals) is a research-backed metric provided by `deepeval` for you to evaluate your LLM output's on any custom metric with human-like accuracy.
    * In this example, the metric `criteria` is correctness of the `actual_output` based on the provided `expected_output`, but not all metrics require an `expected_output`.
    * All metric scores range from 0 - 1, which the `threshold=0.5` threshold ultimately determines if your test have passed or not.

    If you run more than one test run, you will be able to **catch regressions** by comparing test cases side-by-side. This is also made easier if you're using `deepeval` alongside Confident AI ([see below](/docs/getting-started#save-results-on-cloud) for video demo).
  </Tab>

  <Tab value="Multi-Turn">
    A [conversational test case](/docs/evaluation-multiturn-test-cases#conversational-test-case) in `deepeval` represents a **multi-turn interaction with your LLM app**, and contains information such as the actual conversation that took place in the format of `turn`s, and optionally the scenario of which a conversation happened.

    <ImageDisplayer src="ASSETS.conversationalTestCase" alt="Conversational Test Case" />

    Run `touch test_example.py` in your terminal and paste in the following code:

    ```python title="test_example.py"
    from deepeval import assert_test
    from deepeval.test_case import Turn, ConversationalTestCase
    from deepeval.metrics import ConversationalGEval

    def test_professionalism():
        professionalism_metric = ConversationalGEval(
            name="Professionalism",
            criteria="Determine whether the assistant has acted professionally based on the content.",
            threshold=0.5
        )
        test_case = ConversationalTestCase(
            turns=[
                Turn(role="user", content="What is DeepEval?"),
                Turn(role="assistant", content="DeepEval is an open-source LLM eval package.")
            ]
        )
        assert_test(test_case, [professionalism_metric])
    ```

    Then, run `deepeval test run` from the root directory of your project to evaluate your LLM app **end-to-end**:

    ```bash
    deepeval test run test_example.py
    ```

    🎉 Congratulations! Your test case should have passed ✅ Let's breakdown what happened.

    * The variable `role` distinguishes between the end user and your LLM application, and `content` contains either the user’s input or the LLM’s output.
    * In this example, the `criteria` metric evaluates the professionalism of the sequence of `content`.
    * All metric scores range from 0 - 1, which the `threshold=0.5` threshold ultimately determines if your test have passed or not.

    If you run more than one test run, you will be able to **catch regressions** by comparing test cases side-by-side. This is also made easier if you're using `deepeval` alongside Confident AI ([see below](/docs/getting-started#save-results-on-cloud) for video demo).
  </Tab>
</Tabs>

<Callout type="info">
  Since almost all `deepeval` metrics including `GEval` are LLM-as-a-Judge metrics, you'll need to set your `OPENAI_API_KEY` as an env variable. You can also customize the model used for evals:

  ```python
  correctness_metric = GEval(..., model="o1")
  ```

  DeepEval also integrates with these model providers: [Ollama](https://deepeval.com/integrations/models/ollama), [Azure OpenAI](https://deepeval.com/integrations/models/azure-openai), [Anthropic](https://deepeval.com/integrations/models/anthropic), [Gemini](https://deepeval.com/integrations/models/gemini), etc. To use **ANY** custom LLM of your choice, [check out this part of the
  docs](/guides/guides-using-custom-llms).

  <details>
    <summary>
      Evaluations getting "stuck"?
    </summary>

    Most likely your evaluation LLM is failing and this might be due to rate limits or insufficient quotas. By default, `deepeval` retries **transient** LLM errors once (2 attempts total):

    * **Retried:** network/timeout errors and **5xx** server errors.
    * **Rate limits (429):** retried unless the provider marks them non-retryable
      (for OpenAI, `insufficient_quota` is treated as non-retryable).
    * **Backoff:** exponential with jitter (initial **1s**, base **2**, jitter **2s**, cap **5s**).

    You can tune these via environment flags (no code changes). See [environment variables](/docs/environment-variables) for details.
  </details>
</Callout>

### Save Results [#save-results]

It is recommended that you push your test runs to Confident AI — an AI quality platform `deepeval` integrates with natively for observability, evals, and monitoring.

<Tabs items="[&#x22;Confident AI&#x22;, &#x22;Locally in JSON&#x22;]">
  <Tab value="Confident AI">
    Confident AI is an AI quality platform with observability, evals, and monitoring that `deepeval` integrates with natively, and helps you build the best LLM evals pipeline. Run `deepeval view` to view your newly ran test run on the platform:

    ```bash
    deepeval view
    ```

    The `deepeval view` command requires that the test run that you ran above has been successfully cached locally. If something errors, simply run a new test run after logging in with `deepeval login`:

    ```bash
    deepeval login
    ```

    After you've pasted in your API key, Confident AI will **generate testing reports and automate regression testing** whenever you run a test run to evaluate your LLM application inside any environment, at any scale, anywhere.

    <VideoDisplayer src="ASSETS.evaluationOverview" confidentUrl="/docs/getting-started/setup" label="Watch Full Guide on Confident AI" />

    **Once you've run more than one test run**, you'll be able to use the [regression testing page](https://www.confident-ai.com/docs/llm-evaluation/dashboards/ab-regression-testing) shown near the end of the video. Green rows indicate that your LLM has shown improvement on specific test cases, whereas red rows highlight areas of regression.
  </Tab>

  <Tab value="Locally in JSON">
    Simply set the `DEEPEVAL_RESULTS_FOLDER` environment variable to your relative path of choice.

    ```bash
    # linux
    export DEEPEVAL_RESULTS_FOLDER="./data"

    # or windows
    set DEEPEVAL_RESULTS_FOLDER=.\data
    ```
  </Tab>
</Tabs>

## Evals With LLM Tracing [#evals-with-llm-tracing]

While end-to-end evals treat your LLM app as a black-box, you also evaluate **individual components** within your LLM app through **LLM tracing**. This is the recommended way to evaluate AI agents.

<ImageDisplayer src="ASSETS.componentLevelEvals" alt="component level evals" />

First paste in the following code:

```python title="main.py"
from deepeval.tracing import observe, update_current_span
from deepeval.test_case import LLMTestCase
from deepeval.dataset import EvaluationDataset, Golden
from deepeval.metrics import AnswerRelevancyMetric

# 1. Decorate your app
@observe()
def llm_app(input: str):
  # 2. Decorate components with metrics you wish to evaluate or debug
  @observe(metrics=[AnswerRelevancyMetric()])
  def inner_component():
      # 3. Create test case at runtime
      update_current_span(test_case=LLMTestCase(input="Why is the blue sky?", actual_output="You mean why is the sky blue?"))

  return inner_component()

# 4. Create dataset
dataset = EvaluationDataset(goldens=[Golden(input="Test input")])

# 5. Loop through dataset
for golden in dataset.evals_iterator():
  # 6. Call LLM app
  llm_app(golden.input)
```

Then run `python main.py` to run a **component-level** eval:

```bash
python main.py
```

🎉 Congratulations! Your test case should have passed again ✅ Let's breakdown what happened.

* The `@observe` decorate tells `deepeval` where each component is and **creates an LLM trace** at execution time
* Any `metrics` supplied to `@observe` allows `deepeval` to evaluate that component based on the `LLMTestCase` you create
* In this example `AnswerRelevancyMetric()` was used to evaluate `inner_component()`
* The `dataset` specifies the **goldens** which will be used to invoke your `llm_app` during evaluation, which happens in a simple for loop

Once the for loop has ended, `deepeval` will aggregate all metrics, test cases in each component, and run evals across them all, before generating the final testing report.

<Callout type="tip" title="Persisting runs locally for AI tools">
  Pass `DisplayConfig(results_folder="./evals/prompt-v3")` into `evals_iterator()` to save each run as `test_run_<YYYYMMDD_HHMMSS>.json`, then sweep hyperparameters in a plain `for` loop:

  ```python
  from deepeval.evaluate import DisplayConfig

  for temp in [0.0, 0.4, 0.8]:
      for golden in dataset.evals_iterator(
          metrics=[AnswerRelevancyMetric()],
          hyperparameters={"model": "gpt-4o-mini", "temperature": temp},
          display_config=DisplayConfig(results_folder="./evals/prompt-v3"),
      ):
          llm_app(golden.input)
  ```

  The folder then holds one file per run — hyperparameters, metric reasons, and scores all live inside each file — so Cursor or Claude Code can `ls` the folder and read the runs directly. See [Saving test runs locally](/docs/evaluation-flags-and-configs#saving-test-runs-locally) for the full layout options.
</Callout>

## DeepEval for Online Evals [#deepeval-for-online-evals]

When you do LLM tracing using `deepeval`, you can automatically run online evals to monitor **traces, spans, and threads (conversations) in production**.

You'll need to use Confident AI to provide the necessary backend infrastructure and dashboard for this.

Simply get an [API key from Confident AI](https://app.confident-ai.com) and set it in the CLI:

```bash
CONFIDENT_API_KEY="confident_us..."
```

Then add a "metric collection" to your trace:

```python
from deepeval.tracing import observe, update_current_trace

@observe()
def ai_agent(input: str) -> str:
    output = "Your AI agent output"
    update_current_trace(metric_collection="My Online Evals",)
    return output
```

✅ Done. All invocations of your AI agent will now have online evals ran on it.

<Callout type="tip">
  To learn more on what a "metric collection" is, and how to pair observability with online evals, checkout the [docs on Confident AI.](https://www.confident-ai.com/docs/llm-tracing/quickstart)
</Callout>

`deepeval`'s LLM tracing implementation is **non-instrusive**, meaning it will not affect any part of your code.

<Tabs items="[&#x22;Trace (end-to-end) Evals in Prod&#x22;, &#x22;Span (component-level) Evals in Prod&#x22;, &#x22;Thread (conversation) Evals in Prod&#x22;]">
  <Tab value="Trace (end-to-end) Evals in Prod">
    Evals on traces are [end-to-end evaluations](/docs/evaluation-end-to-end-llm-evals), where a single LLM interaction is being evaluated.

    <VideoDisplayer src="ASSETS.tracingTraces" confidentUrl="/docs/llm-tracing/introduction" label="Trace-Level Evals in Production" />
  </Tab>

  <Tab value="Span (component-level) Evals in Prod">
    Spans make up a trace and evals on spans represents [component-level evaluations](/docs/evaluation-component-level-llm-evals), where individual components in your LLM app are being evaluated.

    <VideoDisplayer src="ASSETS.tracingSpans" confidentUrl="/docs/llm-tracing/introduction" label="Span-Level Evals in Production" />
  </Tab>

  <Tab value="Thread (conversation) Evals in Prod">
    Threads are made up of **one or more traces**, and represents a multi-turn interaction to be evaluated.

    <VideoDisplayer src="ASSETS.tracingThreads" confidentUrl="/docs/llm-tracing/introduction" label="Thread (conversation) Evals in Production" />
  </Tab>
</Tabs>

## Next Steps [#next-steps]

* Learn the core concepts if you want to build a repeatable eval suite:

  * [Test cases](/docs/evaluation-test-cases)
  * [Metrics](/docs/metrics-introduction)
  * [Datasets](/docs/evaluation-datasets)

* Follow a use-case quickstart if you want a path tailored to your system:

  * [AI agents](/docs/getting-started-agents)
  * [RAG](/docs/getting-started-rag)
  * [Chatbots](/docs/getting-started-chatbots)

* Explore other workflows when you're ready to go beyond a single eval:

  * [Generate synthetic data](/docs/synthesizer-introduction)
  * [Simulate conversations](/docs/conversation-simulator)
  * [Use integrations](/integrations) with LangChain, LangGraph, OpenAI, CrewAI, and more

If your team needs shared reports, regression analysis, or production monitoring,
DeepEval integrates natively with [Confident AI](https://www.confident-ai.com/docs).

## FAQs [#faqs]

<FAQs
  qas="[
  {
    question: &#x22;Why did my eval get stuck?&#x22;,
    answer:
      &#x22;Most LLM-as-a-judge metrics call an evaluation model. If the provider is rate-limited, out of quota, or slow to respond, the eval may appear stuck. Check your model provider key, quota, and network access.&#x22;,
  },
  {
    question: &#x22;Do I need Confident AI for this quickstart?&#x22;,
    answer: (
      <>
        No. DeepEval runs locally. Confident AI is optional and useful when
        you want shared reports, regression tracking, observability, or
        production monitoring.
      </>
    ),
  },
  {
    question: &#x22;Where should I put this test file?&#x22;,
    answer: (
      <>
        Put it anywhere Pytest can discover it, usually alongside your app or
        in a <code>tests/</code> folder. Then run{&#x22; &#x22;}
        <code>deepeval test run path/to/test_file.py</code>.
      </>
    ),
  },
  {
    question: &#x22;Can I use a model other than OpenAI?&#x22;,
    answer:
      &#x22;Yes. DeepEval supports multiple model providers and custom/local models for evaluation. OpenAI is only the quickest default path for many examples.&#x22;,
  },
  {
    question: &#x22;What should I read after this?&#x22;,
    answer: (
      <>
        If you're evaluating an agent, start with tracing. If you're building
        a repeatable eval suite, start with datasets and metrics.
      </>
    ),
  },
]"
/>

## Full Example [#full-example]

You can find the full example [here on our Github](https://github.com/confident-ai/deepeval/blob/main/examples/getting_started/test_example.py).

# Introduction to LLM Evals (/docs/evaluation-introduction)

## Quick Summary [#quick-summary]

Evaluation refers to the process of testing your LLM application outputs, and requires the following components:

* Test cases
* Metrics
* Evaluation dataset

Here's a diagram of what an ideal evaluation workflow looks like using `deepeval`:

<Mermaid
  chart="sequenceDiagram
    participant Dev as Developer
    participant DS as EvaluationDataset
    participant M as Metrics
    participant App as LLMApp
    participant DE as `deepeval`

    Dev->>DS: Generate or load dataset
    Dev->>M: Define evaluation metrics
    loop Evaluate, improve, re-run
        DS->>App: Run LLM app on dataset
        App->>DE: Produce outputs to evaluate
        DE->>Dev: Report failing cases + metric scores
        Dev->>App: Improve prompts, tools, or logic
    end"
/>

There are **TWO** types of LLM evaluations in `deepeval`:

* [End-to-end evaluation](/docs/evaluation-end-to-end-llm-evals): The overall input and outputs of your LLM system.

* [Component-level evaluation](/docs/evaluation-component-level-llm-evals): The individual inner workings of your LLM system.

Both can be done using either `deepeval test run` in CI/CD pipelines, or via the `evaluate()` function in Python scripts.

<Callout type="note">
  Your test cases will typically be in a single python file, and executing them will be as easy as running `deepeval test run`:

  ```
  deepeval test run test_example.py
  ```
</Callout>

## Test Run [#test-run]

Running an LLM evaluation creates a **test run** — a collection of test cases that benchmarks your LLM application at a specific point in time. If you're logged into Confident AI, you'll also receive a fully sharable [LLM testing report](https://www.confident-ai.com/docs/llm-evaluation/dashboards/testing-reports) on the cloud.

## Metrics [#metrics]

`deepeval` offers 30+ evaluation metrics, most of which are evaluated using LLMs (visit the [metrics section](/docs/metrics-introduction#types-of-metrics) to learn why).

```
from deepeval.metrics import AnswerRelevancyMetric

answer_relevancy_metric = AnswerRelevancyMetric()
```

You'll need to create a test case to run `deepeval`'s metrics.

## Test Cases [#test-cases]

In `deepeval`, a test case represents an [LLM interaction](/docs/evaluation-test-cases#what-is-an-llm-interaction) and allows you to use evaluation metrics you have defined to unit test LLM applications.

```python
from deepeval.test_case import LLMTestCase

test_case = LLMTestCase(
  input="Who is the current president of the United States of America?",
  actual_output="Joe Biden",
  retrieval_context=["Joe Biden serves as the current president of America."]
)
```

In this example, `input` mimics an user interaction with a RAG-based LLM application, where `actual_output` is the output of your LLM application and `retrieval_context` is the retrieved nodes in your RAG pipeline. Creating a test case allows you to evaluate using `deepeval`'s default metrics:

```python
from deepeval.test_case import LLMTestCase
from deepeval.metrics import AnswerRelevancyMetric

answer_relevancy_metric = AnswerRelevancyMetric()
test_case = LLMTestCase(
  input="Who is the current president of the United States of America?",
  actual_output="Joe Biden",
  retrieval_context=["Joe Biden serves as the current president of America."]
)

answer_relevancy_metric.measure(test_case)
print(answer_relevancy_metric.score)
```

## Datasets [#datasets]

Datasets in `deepeval` is a collection of goldens. It provides a centralized interface for you to evaluate a collection of test cases using one or multiple metrics.

```python
from deepeval.test_case import LLMTestCase
from deepeval.dataset import EvaluationDataset, Golden
from deepeval.metrics import AnswerRelevancyMetric
from deepeval import evaluate

answer_relevancy_metric = AnswerRelevancyMetric()
dataset = EvaluationDataset(goldens=[Golden(input="Who is the current president of the United States of America?")])

for golden in dataset.goldens:
  dataset.add_test_case(
    LLMTestCase(
      input=golden.input,
      actual_output=you_llm_app(golden.input)
    )
  )

evaluate(test_cases=dataset.test_cases, metrics=[answer_relevancy_metric])
```

<Callout type="note">
  You don't need to create an evaluation dataset to evaluate individual test cases. Visit the [test cases section](/docs/evaluation-test-cases#assert-a-test-case) to learn how to assert individual test cases.
</Callout>

## Synthesizer [#synthesizer]

In `deepeval`, the `Synthesizer` allows you to generate synthetic datasets. This is especially helpful if you don't have production data or you don't have a golden dataset to evaluate with.

```python
from deepeval.synthesizer import Synthesizer
from deepeval.dataset import EvaluationDataset

synthesizer = Synthesizer()
goldens = synthesizer.generate_goldens_from_docs(
  document_paths=['example.txt', 'example.docx', 'example.pdf']
)

dataset = EvaluationDataset(goldens=goldens)
```

<Callout type="info">
  `deepeval`'s `Synthesizer` is highly customizable, and you can learn more about it [here.](/docs/golden-synthesizer)
</Callout>

## Evaluating With Pytest [#evaluating-with-pytest]

<Callout type="caution">
  Although `deepeval` integrates with Pytest, we highly recommend you to **AVOID** executing `LLMTestCase`s directly via the `pytest` command to avoid any unexpected errors.
</Callout>

`deepeval` allows you to run evaluations as if you're using Pytest via our Pytest integration. Simply create a test file:

```python title="test_example.py"
from deepeval import assert_test
from deepeval.dataset import EvaluationDataset, Golden
from deepeval.test_case import LLMTestCase
from deepeval.metrics import AnswerRelevancyMetric

dataset = EvaluationDataset(goldens=[...])

for golden in dataset.goldens:
  dataset.add_test_case(...) # convert golden to test case

@pytest.mark.parametrize(
    "test_case",
    dataset.test_cases,
)
def test_customer_chatbot(test_case: LLMTestCase):
    assert_test(test_case, [AnswerRelevancyMetric()])
```

And run the test file in the CLI using `deepeval test run`:

```python
deepeval test run test_example.py
```

There are **TWO** mandatory and **ONE** optional parameter when calling the `assert_test()` function:

* `test_case`: an `LLMTestCase`
* `metrics`: a list of metrics of type `BaseMetric`
* \[Optional] `run_async`: a boolean which when set to `True`, enables concurrent evaluation of all metrics. Defaulted to `True`.

You can find the full documentation on `deepeval test run`, for both [end-to-end](/docs/evaluation-end-to-end-llm-evals#use-deepeval-test-run-in-cicd-pipelines) and [component-level](/docs/evaluation-component-level-llm-evals#use-deepeval-test-run-in-cicd-pipelines) evaluation by clicking on their respective links.

<Callout type="info">
  `@pytest.mark.parametrize` is a decorator offered by Pytest. It simply loops through your `EvaluationDataset` to evaluate each test case individually.
</Callout>

You can include the `deepeval test run` command as a step in a `.yaml` file in your CI/CD workflows to run pre-deployment checks on your LLM application.

## Evaluating Without Pytest [#evaluating-without-pytest]

Alternately, you can use `deepeval`'s `evaluate` function. This approach avoids the CLI (if you're in a notebook environment), and allows for parallel test execution as well.

```python
from deepeval import evaluate
from deepeval.metrics import AnswerRelevancyMetric
from deepeval.dataset import EvaluationDataset

dataset = EvaluationDataset(goldens=[...])
for golden in dataset.goldens:
  dataset.add_test_case(...) # convert golden to test case

evaluate(dataset, [AnswerRelevancyMetric()])
```

There are **TWO** mandatory and **SIX** optional parameters when calling the `evaluate()` function:

* `test_cases`: a list of `LLMTestCase`s **OR** `ConversationalTestCase`s, or an `EvaluationDataset`. You cannot evaluate `LLMTestCase`s and `ConversationalTestCase`s in the same test run.
* `metrics`: a list of metrics of type `BaseMetric`.
* \[Optional] `hyperparameters`: a dict of type `dict[str, Union[str, int, float]]`. You can log any arbitrary hyperparameter associated with this test run to pick the best hyperparameters for your LLM application on Confident AI.
* \[Optional] `identifier`: a string that allows you to better identify your test run on Confident AI.
* \[Optional] `async_config`: an instance of type `AsyncConfig` that allows you to [customize the degree concurrency](/docs/evaluation-flags-and-configs#async-configs) during evaluation. Defaulted to the default `AsyncConfig` values.
* \[Optional] `display_config`:an instance of type `DisplayConfig` that allows you to [customize what is displayed](/docs/evaluation-flags-and-configs#display-configs) to the console during evaluation. Defaulted to the default `DisplayConfig` values.
* \[Optional] `error_config`: an instance of type `ErrorConfig` that allows you to [customize how to handle errors](/docs/evaluation-flags-and-configs#error-configs) during evaluation. Defaulted to the default `ErrorConfig` values.
* \[Optional] `cache_config`: an instance of type `CacheConfig` that allows you to [customize the caching behavior](/docs/evaluation-flags-and-configs#cache-configs) during evaluation. Defaulted to the default `CacheConfig` values.

You can find the full documentation on `evaluate()`, for both [end-to-end](/docs/evaluation-end-to-end-llm-evals#use-evaluate-in-python-scripts) and [component-level](/docs/evaluation-component-level-llm-evals#use-evaluate-in-python-scripts) evaluation by clicking on their respective links.

<Callout type="tip">
  You can also replace `dataset` with a list of test cases, as shown in the [test cases section.](/docs/evaluation-test-cases#evaluate-test-cases-in-bulk)
</Callout>

## Evaluating Nested Components [#evaluating-nested-components]

You can also run metrics on nested components by setting up tracing in `deepeval`, and requires under 10 lines of code:

```python showLineNumbers {8}
from deepeval.test_case import LLMTestCase
from deepeval.metrics import AnswerRelevancyMetric
from deepeval.tracing import observe, update_current_span
from openai import OpenAI

client = OpenAI()

@observe(metrics=[AnswerRelevancyMetric()])
def complete(query: str):
  response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": query}]).choices[0].message.content

  update_current_span(
    test_case=LLMTestCase(input=query, output=response)
  )
  return response
```

This is very useful especially if you:

* Want to run a different set of metrics on different components
* Wish to evaluate multiple components at once
* Don't want to rewrite your codebase just to bubble up returned variables to create an `LLMTestCase`

By defauly, `deepeval` will not run any metrics when you're running your LLM application outside of `evaluate()` or `assert_test()`. For the full guide on evaluating with tracing, visit [this page.](/docs/evaluation-component-level-llm-evals)

# Single-Turn Test Case (/docs/evaluation-test-cases)





## Quick Summary [#quick-summary]

A **single-turn test case** is a blueprint provided by `deepeval` to unit test LLM outputs, and **represents a single, atomic unit of interaction** with your LLM app.

<Callout type="caution">
  Throughout this documentation, you should assume the term 'test case' refers to an `LLMTestCase` instead of `MLLMImage` or `ConversationalTestCase`.
</Callout>

An `LLMTestCase` is the most prominent type of test case in `deepeval`. It has **NINE** parameters:

* `input`
* \[Optional] `actual_output`
* \[Optional] `expected_output`
* \[Optional] `context`
* \[Optional] `retrieval_context`
* \[Optional] `tools_called`
* \[Optional] `expected_tools`
* \[Optional] `token_cost`
* \[Optional] `completion_time`

Here's an example implementation of an `LLMTestCase`:

```python title="main.py"
from deepeval.test_case import LLMTestCase, ToolCall

test_case = LLMTestCase(
    input="What if these shoes don't fit?",
    expected_output="You're eligible for a 30 day refund at no extra cost.",
    actual_output="We offer a 30-day full refund at no extra cost.",
    context=["All customers are eligible for a 30 day full refund at no extra cost."],
    retrieval_context=["Only shoes can be refunded."],
    tools_called=[ToolCall(name="WebSearch")]
)
```

<Callout type="info">
  Since `deepeval` is an LLM evaluation framework, the \*\* `input` and `actual_output` are always mandatory.\*\* However, this does not mean they are necessarily used for evaluation, and you can also add additional parameters such as the `tools_called` for each `LLMTestCase`.

  <video width="100%">
    <source src="ASSETS.testCaseToolsCalled" type="video/mp4" />
  </video>

  To get your own sharable testing report with `deepeval`, [sign up to Confident AI](https://app.confident-ai.com), or run `deepeval login` in the CLI:

  ```bash
  deepeval login
  ```
</Callout>

## What Is An LLM "Interaction"? [#what-is-an-llm-interaction]

An **LLM interaction** is any **discrete exchange** of information between **components of your LLM system** — from a full user request to a single internal step. The scope of interaction is arbitrary and is entirely up to you.

<Callout type="note">
  Since an `LLMTestCase` represents a single, atomic unit of interaction in your LLM app, it is important to understand what this means.
</Callout>

Let’s take this LLM system as an example:

<div style="{textAlign: 'center', margin: &#x22;2rem 0&#x22;}">
  <Mermaid
    chart="graph TD
    A[Research Agent] --> B[RAG Pipeline]
    A --> C[Web Search Tool]
    B --> D[Retriever]
    B --> E[LLM]
    A --> E"
  />
</div>

There are different ways you scope an interaction:

* **Agent-Level:** The entire process initiated by the agent, including the RAG pipeline and web search tool usage

* **RAG Pipeline:** Just the RAG flow — retriever + LLM
  * **Retriever:** Only test whether relevant documents are being retrieved
  * **LLM:** Focus purely on how well the LLM generates text from the input/context

An interaction is where you want to define your `LLMTestCase`. For example, when using RAG-specific metrics like `AnswerRelevancyMetric`, `FaithfulnessMetric`, or `ContextualRelevancyMetric`, the interaction is best scoped at the RAG pipeline level.

In this case:

* `input` should be the user question or text to embed

* `retrieval_context` should be the retrieved documents from the retriever

* `actual_output` should be the final response generated by the LLM

<div style="{textAlign: 'center', margin: &#x22;2rem 0&#x22;}">
  <Mermaid
    chart="graph TD
    A[Research Agent]
    B[RAG Pipeline]
    C[Web Search Tool]
    D[Retriever]
    E[LLM]

    A --> B
    A --> C
    B --> D
    B --> E
    A --> E

    classDef rag fill:#E3F2FD,stroke:#1E88E5,stroke-width:2px;
    class B,D,E rag;"
  />
</div>

If you would want to evaluate using the `ToolCorrectnessMetric` however, you'll need to create an `LLMTestCase` at the **Agent-Level**, and supply the `tools_called` parameter instead:

<div style="{textAlign: 'center', margin: &#x22;2rem 0&#x22;}">
  <Mermaid
    chart="graph TD
    A[Research Agent]
    B[RAG Pipeline]
    C[Web Search Tool]
    D[Retriever]
    E[LLM]

    A --> B
    A --> C
    B --> D
    B --> E
    A --> E

    classDef allblue fill:#E3F2FD,stroke:#1E88E5,stroke-width:2px;

    class A,B,C,D,E allblue;"
  />
</div>

We'll go through the requirements for an `LLMTestCase` before showing how to create an `LLMTestCase` for an interaction.

<Callout type="tip">
  For users starting out, scoping the interaction as the overall LLM application will be the easiest way to run evals.
</Callout>

## LLM Test Case [#llm-test-case]

An `LLMTestCase` in `deepeval` can be used to unit test interactions within your LLM application (which can just be an LLM itself), which includes use cases such as RAG and LLM agents (for individual components, agents within agents, or the agent altogether). It contains the necessary information (`tools_called` for agents, `retrieval_context` for RAG, etc.) to evaluate your LLM application for a given `input`.

<ImageDisplayer src="ASSETS.llmTestCase" alt="LLM Test Case" />

An `LLMTestCase` is used for both end-to-end and component-level evaluation:

* [End-to-end:](/docs/evaluation-end-to-end-llm-evals) An `LLMTestCase` represents the inputs and outputs of your "black-box" LLM application

* [Component-level:](/docs/evaluation-component-level-llm-evals) Many `LLMTestCase`s represents many interactions in different components

**Different metrics will require a different combination of `LLMTestCase` parameters, but they all require an `input` and `actual_output`** - regardless of whether they are used for evaluation or not. For example, you won't need `expected_output`, `context`, `tools_called`, and `expected_tools` if you're just measuring answer relevancy, but if you're evaluating hallucination you'll have to provide `context` in order for `deepeval` to know what the **ground truth** is.

With the exception of conversational metrics, which are metrics to evaluate conversations instead of individual LLM responses, you can use any LLM evaluation metric `deepeval` offers to evaluate an `LLMTestCase`.

<Callout type="note">
  You cannot use conversational metrics to evaluate an `LLMTestCase`. Conveniently, most metrics in `deepeval` are non-conversational.
</Callout>

Keep reading to learn which parameters in an `LLMTestCase` are required to evaluate different aspects of an LLM applications - ranging from pure LLMs, RAG pipelines, and even LLM agents.

### Input [#input]

The `input` mimics a user interacting with your LLM application. The `input` can contain just text or text with images as well, it is the direct input to your prompt template, and so **SHOULD NOT CONTAIN** your prompt template.

```python
from deepeval.test_case import LLMTestCase

test_case = LLMTestCase(
    input="Why did the chicken cross the road?",
    # Replace this with your actual LLM application
    actual_output="Quite frankly, I don't want to know..."
)
```

<Callout type="tip">
  Not all `input`s should include your prompt template, as this is determined by the metric you're using. Furthermore, the `input` should **NEVER** be a json version of the list of messages you are passing into your LLM.

  If you're logged into Confident AI, you can associate hyperparameters such as prompt templates with each test run to easily figure out which prompt template gives the best `actual_output`s for a given `input`:

  ```bash
  deepeval login
  ```

  ```python title="test_file.py"
  import deepeval

  from deepeval import assert_test
  from deepeval.test_case import LLMTestCase
  from deepeval.metrics import AnswerRelevancyMetric

  def test_llm():
      test_case = LLMTestCase(input="...", actual_output="...")
      answer_relevancy_metric = AnswerRelevancyMetric()
      assert_test(test_case, [answer_relevancy_metric])

  # You should aim to make these values dynamic
  @deepeval.log_hyperparameters(model="gpt-4.1", prompt_template="...")
  def hyperparameters():
      # You can also return an empty dict {} if there's no additional parameters to log
      return {
          "temperature": 1,
          "chunk size": 500
      }
  ```

  ```bash
  deepeval test run test_file.py
  ```
</Callout>

### Actual Output [#actual-output]

The `actual_output` is an **optional** parameter and represents what your LLM app outputs for a given input. Typically, you would import your LLM application (or parts of it) into your test file, and invoke it at runtime to get the actual output. The `actual_output` can be text or image or both as well depending on what your LLM application outputs.

```python
# A hypothetical LLM application example
import chatbot

input = "Why did the chicken cross the road?"

test_case = LLMTestCase(
    input=input,
    actual_output=chatbot.run(input)
)
```

The `actual_output` is an optional parameter because some systems (such as RAG retrievers) does not require an LLM output to be evaluated.

<Callout type="note">
  You may also choose to evaluate with precomputed `actual_output`s, instead of generating `actual_output`s at evaluation time.
</Callout>

### Expected Output [#expected-output]

The `expected_output` is an **optional** parameter and represents you would want the ideal output to be. Note that this parameter is **optional** depending on the metric you want to evaluate.

The expected output doesn't have to exactly match the actual output in order for your test case to pass since `deepeval` uses a variety of methods to evaluate non-deterministic LLM outputs. We'll go into more details [in the metrics section.](/docs/metrics-introduction)

```python
# A hypothetical LLM application example
import chatbot

input = "Why did the chicken cross the road?"

test_case = LLMTestCase(
    input=input,
    actual_output=chatbot.run(input),
    expected_output="To get to the other side!"
)
```

### Context [#context]

The `context` is an **optional** parameter that represents additional data received by your LLM application as supplementary sources of golden truth. You can view it as the ideal segment of your knowledge base relevant as support information to a specific input. Context is **static** and should not be generated dynamically.

Unlike other parameters, a context accepts a list of strings.

```python
# A hypothetical LLM application example
import chatbot

input = "Why did the chicken cross the road?"

test_case = LLMTestCase(
    input=input,
    actual_output=chatbot.run(input),
    expected_output="To get to the other side!",
    context=["The chicken wanted to cross the road."]
)
```

<Callout type="note">
  Often times people confuse `expected_output` with `context` since due to their similar level of factual accuracy. However, while both are (or should be) factually correct, `expected_output` also takes aspects like tone and linguistic patterns into account, whereas context is strictly factual.
</Callout>

### Retrieval Context [#retrieval-context]

The `retrieval_context` is an **optional** parameter that represents your RAG pipeline's retrieval results at runtime. By providing `retrieval_context`, you can determine how well your retriever is performing using `context` as a benchmark.

```python
# A hypothetical LLM application example
import chatbot

input = "Why did the chicken cross the road?"

test_case = LLMTestCase(
    input=input,
    actual_output=chatbot.run(input),
    expected_output="To get to the other side!",
    context=["The chicken wanted to cross the road."],
    retrieval_context=["The chicken liked the other side of the road better"]
)
```

<Callout type="note">
  Remember, `context` is the ideal retrieval results for a given input and typically come from your evaluation dataset, whereas `retrieval_context` is your LLM application's actual retrieval results. So, while they might look similar at times, they are not the same.
</Callout>

### Tools Called [#tools-called]

The `tools_called` parameter is an **optional** parameter that represents the tools your LLM agent actually invoked during execution. By providing `tools_called`, you can evaluate how effectively your LLM agent utilized the tools available to it.

<Callout type="note">
  The `tools_called` parameter accepts a list of `ToolCall` objects.
</Callout>

```python
class ToolCall(BaseModel):
    name: str
    description: Optional[str] = None
    reasoning: Optional[str] = None
    output: Optional[Any] = None
    input_parameters: Optional[Dict[str, Any]] = None
```

A `ToolCall` object accepts 1 mandatory and 4 optional parameters:

* `name`: a string representing the **name** of the tool.
* \[Optional] `description`: a string describing the **tool's purpose**.
* \[Optional] `reasoning`: A string explaining the **agent's reasoning** to use the tool.
* \[Optional] `output`: The tool's **output**, which can be of any data type.
* \[Optional] `input_parameters`: A dictionary with string keys representing the **input parameters** (and respective values) passed into the tool function.

```python
# A hypothetical LLM application example
import chatbot

test_case = LLMTestCase(
    input="Why did the chicken cross the road?",
    actual_output=chatbot.run(input),
    # Replace this with the tools that were actually used
    tools_called=[
        ToolCall(
            name="Calculator Tool",
            description="A tool that calculates mathematical equations or expressions.",
            input={"user_input": "2+3"},
            output=5
        ),
        ToolCall(
            name="WebSearch Tool",
            reasoning="Knowledge base does not detail why the chicken crossed the road.",
            input={"search_query": "Why did the chicken crossed the road?"},
            output="Because it wanted to, duh."
        )
    ]
)
```

<Callout type="info">
  `tools_called` and `expected_tools` are LLM test case parameters that are utilized only in **agentic evaluation metrics**. These parameters allow you to assess the [tool usage correctness](/docs/metrics-tool-correctness) of your LLM application and ensure that it meets the expected tool usage standards.
</Callout>

### Expected Tools [#expected-tools]

The `expected_tools` parameter is an **optional** parameter that represents the tools that ideally should have been used to generate the output. By providing `expected_tools`, you can assess whether your LLM application used the tools you anticipated for optimal performance.

```python
# A hypothetical LLM application example
import chatbot

input = "Why did the chicken cross the road?"

test_case = LLMTestCase(
    input=input,
    actual_output=chatbot.run(input),
    # Replace this with the tools that were actually used
    tools_called=[
        ToolCall(
            name="Calculator Tool",
            description="A tool that calculates mathematical equations or expressions.",
            input={"user_input": "2+3"},
            output=5
        ),
        ToolCall(
            name="WebSearch Tool",
            reasoning="Knowledge base does not detail why the chicken crossed the road.",
            input={"search_query": "Why did the chicken crossed the road?"},
            output="Because it wanted to, duh."
        )
    ]
    expected_tools=[
        ToolCall(
            name="WebSearch Tool",
            reasoning="Knowledge base does not detail why the chicken crossed the road.",
            input={"search_query": "Why did the chicken crossed the road?"},
            output="Because it needed to escape from the hungry humans."
        )
    ]
)
```

### Token cost [#token-cost]

The `token_cost` is an **optional** parameter and is of type float that allows you to log the cost of a particular LLM interaction for a particular `LLMTestCase`. No metrics use this parameter by default, and it is most useful for either:

1. Building custom metrics that relies on `token_cost`
2. Logging `token_cost` on Confident AI

```python
from deepeval.test_case import LLMTestCase

test_case = LLMTestCase(token_cost=1.32, ...)
```

### Completion Time [#completion-time]

The `completion_time` is an **optional** parameter and is similar to the `token_cost` is of type float that allows you to log the time in **SECONDS** it took for a LLM interaction for a particular `LLMTestCase` to complete. No metrics use this parameter by default, and it is most useful for either:

1. Building custom metrics that relies on `completion_time`
2. Logging `completion_time` on Confident AI

```python
from deepeval.test_case import LLMTestCase

test_case = LLMTestCase(completion_time=7.53, ...)
```

## Including Images [#including-images]

By default `deepeval` supports passing both text and images inside your test cases using the `MLLMImage` object. The `MLLMImage` class in `deepeval` is used to reference multimodal images in your test cases. It allows you to create test cases using local images, remote URLs and `base64` data.

```python
from deepeval.test_case import LLMTestCase, MLLMImage

shoes = MLLMImage(url='./shoes.png', local=True)
blue_shoes = MLLMImage(url='https://shoe-images.com/edited-shoes', local=False)

test_case = LLMTestCase(
    input=f"Change the color of these shoes to blue: {shoes}",
    expected_output=f"Here's the blue shoes you asked for: {expected_shoes}"
    retrieval_context=[f"Some reference shoes: {MLLMImage(...)}"]
)
```

<Callout type="info">
  Multimodal test cases are automatically detected when you include `MLLMImage` objects in your inputs or outputs. You can use them with various multimodal supported metrics like the [RAG metrics](/docs/metrics-answer-relevancy) and [multimodal-specific metrics](/docs/multimodal-metrics-image-coherence).
</Callout>

### `MLLMImage` Data Model [#mllmimage-data-model]

Here's the data model of the `MLLMImage` in `deepeval`:

```python
class MLLMImage:
    dataBase64: Optional[str] = None
    mimeType: Optional[str] = None
    url: Optional[str] = None
    local: Optional[bool] = None
    filename: Optional[str] = None
```

You **MUST** either provide `url` or `dataBase64` and `mimeType` parameters when initializing an `MLLMImage`. The `local` attribute should be set to `True` for locally stored images and `False` for images hosted online (default is `False`).

<Callout type="note">
  All the `MLLMImage` instances are converted to a special `deepeval` slug, (e.g `[DEEPEVAL:IMAGE:uuid]`). This is how your `MLLMImage`s look like in your test cases after you embed them in f-strings:

  ```python
  from deepeval.test_case import LLMTestCase, MLLMImage

  shoes = MLLMImage(url='./shoes.png', local=True)

  test_case = LLMTestCase(
      input=f"Change the color of these shoes to blue: {shoes}",
      expected_output=f"..."
  )

  print(test_case.input)
  ```

  This outputs the following:

  ```
  Change the color of these shoes to blue: [DEEPEVAL:IMAGE:awefv234fvbnhg456]
  ```

  Users who'd like to access their images themselves for any ETL can use the `convert_to_multi_modal_array` method to convert your test cases to a list of strings and `MLLMImage` in order. Here's how to use it:

  ```python
  from deepeval.test_case import LLMTestCase, MLLMImage
  from deepeval.utils import convert_to_multi_modal_array

  shoes = MLLMImage(url='./shoes.png', local=True)

  test_case = LLMTestCase(
      input=f"Change the color of these shoes to blue: {shoes}",
      expected_output=f"..."
  )

  print(convert_to_multi_modal_array(test_case.input))
  ```

  This will output the following:

  ```
  ["Change the color of these shoes to blue:",  [DEEPEVAL:IMAGE:awefv234fvbnhg456]]
  ```

  The `[DEEPEVAL:IMAGE:awefv234fvbnhg456]` here is actually the instance of `MLLMImage` you passed inside your test case.
</Callout>

## Label Test Cases For Confident AI [#label-test-cases-for-confident-ai]

If you're using Confident AI, these are some additional parameters to help manage your test cases.

### Name [#name]

The optional `name` parameter allows you to provide a string identifier to label `LLMTestCase`s and `ConversationalTestCase`s for you to easily search and filter for on Confident AI. This is particularly useful if you're importing test cases from an external datasource.

```python
from deepeval.test_case import LLMTestCase

test_case = LLMTestCase(name="my-external-unique-id", ...)
```

### Tags [#tags]

Alternatively, you can also tag test cases for filtering and searching on Confident AI:

```python
from deepeval.test_case import LLMTestCase

test_case = LLMTestCase(tags=["Topic 1", "Topic 3"], ...)
```

## Using Test Cases For Evals [#using-test-cases-for-evals]

You can create test cases for three types of evaluation:

* [End-to-end](/docs/evaluation-end-to-end-llm-evals) - Treats your LLM app as a black-box, and evaluates the overall system inputs and outputs. Your test case lives at the **system level** and covers the entire application
* [Component-level](/docs/evaluation-component-level-llm-evals) - Evaluates individual components within your LLM system using the `@observe` decorator. Your test case lives at the **component level** and focuses on specific parts of your system
* One-Off Standalone - Executes individual metrics on single test cases for debugging or custom evaluation pipelines

Click on each of the links to learn how to use test cases for evals.

# Datasets (/docs/evaluation-datasets)





In `deepeval`, an evaluation dataset, or just dataset, is a collection of goldens. A golden is a precursor to a test case. At evaluation time, you would first convert all goldens in your dataset to test cases, before running evals on these test cases.

## Quick Summary [#quick-summary]

There are two approaches to running evals using datasets in `deepeval`:

1. Using `deepeval test run`
2. Using `evaluate`

Depending on the type of goldens you supply, datasets are either **single-turn** or **mult-turn**. Evaluating a dataset means exactly the same as evaluating your LLM system, because by definition a dataset contains all the information produced by your LLM needed for evaluation.

<details>
  <summary>
    What are the best practices for curating an evaluation dataset?
  </summary>

  * **Ensure telling test coverage:** Include diverse real-world inputs, varying complexity levels, and edge cases to properly challenge the LLM.
  * **Focused, quantitative test cases:** Design with clear scope that enables meaningful performance metrics without being too broad or narrow.
  * **Define clear objectives:** Align datasets with specific evaluation goals while avoiding unnecessary fragmentation.
</details>

<Callout type="info">
  If you don't already have an `EvaluationDataset`, a great starting point is to simply write down the prompts you're currently using to manually eyeball your LLM outputs. You can also do this on Confident AI, which integrates 100% with `deepeval`:

  <VideoDisplayer src="ASSETS.datasetsCreate" confidentUrl="/docs/dataset-editor/annotate-datasets" label="Learn Dataset Annotation on Confident AI" />

  Full documentation for datasets on [Confident AI
  here.](https://www.confident-ai.com/docs/llm-evaluation/dataset-management/create-goldens)
</Callout>

## Create A Dataset [#create-a-dataset]

An `EvaluationDataset` in `deepeval` is simply a collection of goldens. You can initialize an empty dataset to start with:

```python
from deepeval.dataset import EvaluationDataset

dataset = EvaluationDataset()
```

A dataset can either be a single-turn one, **or** a multi-turn one (but not both). During initialization supplying your dataset with a list of `Golden`s will make it a single-turn one, whereas supplying it with `ConversationalGolden`s will make it multi-turn:

<Tabs items="[&#x22;Single-Turn&#x22;, &#x22;Multi-Turn&#x22;]">
  <Tab value="Single-Turn">
    ```python
    from deepeval.dataset import EvaluationDataset, Golden

    dataset = EvaluationDataset(goldens=[Golden(input="What is your name?")])
    print(dataset._multi_turn) # prints False
    ```
  </Tab>

  <Tab value="Multi-Turn">
    ```python
    from deepeval.dataset import EvaluationDataset, ConversationalGolden

    dataset = EvaluationDataset(
        goldens=[
            ConversationalGolden(
                scenario="Frustrated user asking for a refund.",
                expected_outcome="Redirected to a human agent."
            )
        ]
    )
    print(dataset._multi_turn) # prints True
    ```
  </Tab>
</Tabs>

To ensure best practices, datasets in `deepeval` are stateful and opinionated. This means you cannot change the value of `_multi_turn` once its value has been set. However, you can always add new goldens after initialization using the `add_golden` method:

<Tabs items="[&#x22;Single-Turn&#x22;, &#x22;Multi-Turn&#x22;]">
  <Tab value="Single-Turn">
    ```python
    ...

    dataset.add_golden(Golden(input="Nice."))
    ```
  </Tab>

  <Tab value="Multi-Turn">
    ```python
    ...

    dataset.add_golden(
        ConversationalGolden(
            scenario="User expressing gratitude for redirecting to human.",
            expected_outcome="Appreciates the gratitude."
        )
    )
    ```
  </Tab>
</Tabs>

## Run Evals On Dataset [#run-evals-on-dataset]

You run evals on test cases in datasets, which you'll create at evaluation time using the goldens in the same dataset.

<ImageDisplayer src="ASSETS.evaluationDataset" alt="Evaluation Dataset" />

First step is to load in the goldens to your dataset. This example will load datasets from Confident AI, but you can also explore [other options below.](#load-dataset)

```python title="main.py"
from deepeval.dataset import EvaluationDataset

dataset = EvaluationDataset()
dataset.pull(alias="My Dataset") # replace with your alias
print(dataset.goldens) # print to sanity check yourself
```

<Callout type="tip">
  Your dataset is either single or multi-turn the moment you pull your dataset.
</Callout>

Once you have your dataset and can see a non-empty list of goldens, you can start generating outputs and **add it back to your dataset** as test cases via the `add_test_case()` method:

<Tabs items="[&#x22;Single-Turn&#x22;, &#x22;Multi-Turn&#x22;]">
  <Tab value="Single-Turn">
    ```python title="main.py" {9}
    from deepeval.test_case import LLMTestCase
    ...

    for golden in dataset.goldens:
        test_case = LLMTestCase(
            input=golden.input,
            actual_output=your_llm_app(golden.input) # replace with your LLM app
        )
        dataset.add_test_case(test_case)

    print(dataset.test_cases) # print to santiy check yourself
    ```

    Lastly, you can run evaluations on the list of test cases in your dataset:

    <Tabs items="[&#x22;Unit-Testing In CI/CD&#x22;, &#x22;In Python Scripts&#x22;]">
      <Tab value="Unit-Testing In CI/CD">
        ```python title="test_llm_app.py" {5}
        import pytest

        from deepeval.metrics import AnswerRelevancyMetric
        ...

        @pytest.mark.parametrize("test_case", dataset.test_cases)
        def test_llm_app(test_case: LLMTestCase):
            assert_test(test_case=test_case, metrics=[AnswerRelevancyMetric()])
        ```

        And execute the test file:

        ```bash
        deepeval test run test_llm_app.py
        ```

        You can learn more about `assert_test` in [this section.](/docs/evaluation-end-to-end-llm-evals#use-deepeval-test-run-in-cicd-pipelines)
      </Tab>

      <Tab value="In Python Scripts">
        ```python title="main.py" {5}
        from deepeval.metrics import AnswerRelevancyMetric
        from deepeval import evaluate
        ...

        evaluate(test_cases=dataset.test_cases, metrics=[AnswerRelevancyMetric()])
        ```

        And run `main.py`:

        ```bash
        python main.py
        ```

        You can learn more about `evaluate` in [this section.](/docs/evaluation-end-to-end-llm-evals#use-evaluate-in-python-scripts)
      </Tab>
    </Tabs>
  </Tab>

  <Tab value="Multi-Turn">
    ```python title="main.py" {9}
    from deepeval.test_case import ConversationalTestCase
    ...

    for golden in dataset.goldens:
        test_case = ConversationalTestCase(
            scenario=golden.scenario,
            turns=generate_turns(golden.scenario) # replace with your method to simulate conversations
        )
        dataset.add_test_case(test_case)

    print(dataset.test_cases) # print to santiy check yourself
    ```

    Lastly, you can run evaluations on the list of test cases in your dataset:

    <Tabs items="[&#x22;Unit-Testing In CI/CD&#x22;, &#x22;In Python Scripts&#x22;]">
      <Tab value="Unit-Testing In CI/CD">
        ```python title="test_llm_app.py" {5}
        import pytest

        from deepeval.metrics import ConversationalRelevancyMetric
        ...

        @pytest.mark.parametrize("test_case", dataset.test_cases)
        def test_llm_app(test_case: ConversationalTestCase):
            assert_test(test_case=test_case, metrics=[ConversationalRelevancyMetric()])
        ```

        And execute the test file:

        ```bash
        deepeval test run test_llm_app.py
        ```

        You can learn more about `assert_test` in [this section.](/docs/evaluation-end-to-end-llm-evals#use-deepeval-test-run-in-cicd-pipelines)
      </Tab>

      <Tab value="In Python Scripts">
        ```python title="main.py" {5}
        from deepeval.metrics import ConversationalRelevancyMetric
        from deepeval import evaluate
        ...

        evaluate(test_cases=dataset.test_cases, metrics=[ConversationalRelevancyMetric()])
        ```

        And run `main.py`:

        ```bash
        python main.py
        ```

        You can learn more about `evaluate` in [this section.](/docs/evaluation-end-to-end-llm-evals#use-evaluate-in-python-scripts)
      </Tab>
    </Tabs>
  </Tab>
</Tabs>

## Manage Your Dataset [#manage-your-dataset]

Dataset management is an essential part of your evaluation lifecycle. We recommend Confident AI as the choice for your dataset management workflow as it comes with dozens of collaboration features out of the box, but you can also do it locally as well.

### Save Dataset [#save-dataset]

You can store both single-turn and multi-turn datasets with `deepeval`. The single-turn datasets contains a list of `Golden`s and the multi-turn would contain `ConversationalGolden`s instead.

<Tabs items="[&#x22;Confident AI&#x22;, &#x22;Locally as JSON&#x22;, &#x22;Locally as CSV&#x22;]">
  <Tab value="Confident AI">
    You can save your dataset on the cloud by using the `push` method:

    ```python
    from deepeval.dataset import EvaluationDataset

    dataset = EvaluationDataset(goldens)
    dataset.push(alias="My dataset")
    ```

    This pushes all goldens in your evaluation dataset to Confident AI. If you're unsure whether your goldens are ready for evaluation, you should set `finalized` to `False` instead:

    ```python
    ...

    dataset.push(alias="My dataset", finalized=False)
    ```

    This means they won't be pulled until you've manually marked them as finalized on the platform. You can learn more on Confident AI's docs [here.](https://www.confident-ai.com/docs/llm-evaluation/dataset-management/create-goldens)

    <Callout type="tip">
      You can also push multi-turn datasets exactly the same way.
    </Callout>
  </Tab>

  <Tab value="Locally as JSON">
    You can save your dataset locally to a JSON file by using the `save_as()` method:

    ```python
    from deepeval.dataset import EvaluationDataset

    dataset = EvaluationDataset(goldens)
    dataset.save_as(
        file_type="json",
        directory="./deepeval-test-dataset",
    )
    ```

    There are **TWO** mandatory and **TWO** optional parameter when calling the `save_as()` method:

    * `file_type`: a string of either `"csv"` or `"json"` and specifies which file format to save `Golden`s in.
    * `directory`: a string specifying the path of the directory you wish to save `Golden`s at.
    * `file_name`: a string specifying the custom filename for the dataset file. Defaulted to the "YYYYMMDD\_HHMMSS" format of time now.
    * `include_test_cases`: a boolean which when set to `True`, will also save any test cases within your dataset. Defaulted to `False`.

    <Callout type="note">
      By default the `save_as()` method only saves the `Golden`s within your `EvaluationDataset` to file. If you wish to save test cases as well, set `include_test_cases` to `True`.
    </Callout>
  </Tab>

  <Tab value="Locally as CSV">
    You can save your dataset locally to a CSV file by using the `save_as()` method:

    ```python
    from deepeval.dataset import EvaluationDataset

    dataset = EvaluationDataset(goldens)
    dataset.save_as(
        file_type="csv",
        directory="./deepeval-test-dataset",
    )
    ```

    There are **TWO** mandatory and **TWO** optional parameter when calling the `save_as()` method:

    * `file_type`: a string of either `"csv"` or `"json"` and specifies which file format to save `Golden`s in.
    * `directory`: a string specifying the path of the directory you wish to save `Golden`s at.
    * `file_name`: a string specifying the custom filename for the dataset file. Defaulted to the "YYYYMMDD\_HHMMSS" format of time now.
    * `include_test_cases`: a boolean which when set to `True`, will also save any test cases within your dataset. Defaulted to `False`.

    <Callout type="note">
      By default the `save_as()` method only saves the `Golden`s within your `EvaluationDataset` to file. If you wish to save test cases as well, set `include_test_cases` to `True`.
    </Callout>
  </Tab>
</Tabs>

### Load Dataset [#load-dataset]

`deepeval` offers support for loading datasets stored in JSON, JSONL, CSV, and hugging face datasets into an `EvaluationDataset` as either test cases or goldens.

<Tabs items="[&#x22;Confident AI&#x22;, &#x22;From JSON&#x22;, &#x22;From JSONL&#x22;, &#x22;From CSV&#x22;]">
  <Tab value="Confident AI">
    You can load entire datasets on Confident AI's cloud in one line of code.

    ```python
    from deepeval.dataset import EvaluationDataset

    dataset = EvaluationDataset()
    dataset.pull(alias="My Evals Dataset")
    ```

    Non-technical domain experts can **create, annotate, and comment** on datasets on Confident AI. You can also upload datasets in CSV format, or push synthetic datasets created in `deepeval` to Confident AI in one line of code.

    For more information, visit the [Confident AI datasets section.](https://www.confident-ai.com/docs/llm-evaluation/dataset-management/create-goldens)
  </Tab>

  <Tab value="From JSON">
    You can loading an existing `EvaluationDataset` you might have generated elsewhere by supplying a `file_path` to your `.json` file as **either test cases or goldens**. Your `.json` file should contain an array of objects (or list of dictionaries).

    ```python
    from deepeval.dataset import EvaluationDataset

    dataset = EvaluationDataset()

    # Add goldens from a JSON file
    dataset.add_goldens_from_json_file(
        file_path="example.json",
    ) # file_path is the absolute path to your .json file
    ```

    If your JSON file has different keys from `deepeval`'s conventional `Golden` or `ConversationalGolden` parameters. You can supply your custom key names in the [function parameters](https://github.com/confident-ai/deepeval/blob/main/deepeval/dataset/dataset.py#L584).

    You can also add single-turn `LLMTestCase`s to your dataset from a JSON file.

    ```python
    from deepeval.dataset import EvaluationDataset

    dataset = EvaluationDataset()

    # Add as test cases
    dataset.add_test_cases_from_json_file(
        # file_path is the absolute path to you .json file
        file_path="example.json",
        input_key_name="query",
        actual_output_key_name="actual_output",
        expected_output_key_name="expected_output",
        context_key_name="context",
        retrieval_context_key_name="retrieval_context",
    )
    ```

    <Callout type="info">
      Loading datasets as goldens are especially helpful if you're looking to generate LLM `actual_output`s at evaluation time. You might find yourself in this situation if you are generating data for testing or using historical data from production.
    </Callout>
  </Tab>

  <Tab value="From JSONL">
    You can load existing `Golden`s or `ConversationalGolden`s from a `.jsonl` file by supplying a `file_path`. Each line should contain one JSON object that maps to either a `Golden` or a `ConversationalGolden`.

    ```python
    from deepeval.dataset import EvaluationDataset

    dataset = EvaluationDataset()

    # Add goldens from a JSONL file
    dataset.add_goldens_from_jsonl_file(
        file_path="example.jsonl",
    ) # file_path is the absolute path to your .jsonl file
    ```

    For single-turn goldens, each line can look like:

    ```json
    {"input": "What is DeepEval?", "expected_output": "An LLM evaluation framework.", "context": ["DeepEval helps evaluate LLM apps."]}
    ```

    For multi-turn goldens, each line can look like:

    ```json
    {"scenario": "A user asks for help evaluating an LLM app.", "expected_outcome": "The user understands how to create an evaluation dataset.", "context": ["DeepEval supports evaluation datasets."]}
    ```

    <Callout type="note">
      An `EvaluationDataset` can contain either single-turn or multi-turn goldens, but not both. If a JSONL file mixes `Golden` and `ConversationalGolden` rows, `deepeval` will raise an error.
    </Callout>
  </Tab>

  <Tab value="From CSV">
    You can add test cases or goldens into your `EvaluationDataset` by supplying a `file_path` to your `.csv` file. Your `.csv` file should contain rows that can be mapped into `Golden` or `ConversationalGolden` through their column names.

    Remember, parameters such as `context` should be a list of strings and in the context of CSV files, it means you have to supply a `context_col_delimiter` argument to tell `deepeval` how to split your context cells into a list of strings.

    ```python
    from deepeval.dataset import EvaluationDataset

    dataset = EvaluationDataset()

    # Add goldens
    dataset.add_goldens_from_csv_file(
        file_path="example.csv",
    ) # file_path is the absolute path to you .csv file
    ```

    If your CSV file has different column names from `deepeval`'s conventional `Golden` or `ConversationalGolden` parameters. You can supply your custom column names in the [function parameters](https://github.com/confident-ai/deepeval/blob/main/deepeval/dataset/dataset.py#L433).

    You can also add single-turn `LLMTestCase`s to your dataset from a CSV file.

    ```python
    from deepeval.dataset import EvaluationDataset

    dataset = EvaluationDataset()

    # Add as test cases
    dataset.add_test_cases_from_csv_file(
        # file_path is the absolute path to you .csv file
        file_path="example.csv",
        input_col_name="query",
        actual_output_col_name="actual_output",
        expected_output_col_name="expected_output",
        context_col_name="context",
        context_col_delimiter= ";",
        retrieval_context_col_name="retrieval_context",
        retrieval_context_col_delimiter= ";"
    )
    ```

    <Callout type="note">
      Since `expected_output`, `context`, `retrieval_context`, `tools_called`, and `expected_tools` are optional parameters for an `LLMTestCase`, these fields are similarly **optional** parameters when adding test cases from an existing dataset.
    </Callout>
  </Tab>
</Tabs>

## Generate A Dataset [#generate-a-dataset]

Sometimes, you might not have datasets ready to use, and that's ok. `deepeval` provides two options for both single-turn and multi-turn use cases:

* `Synthesizer` for generating single-turn goldens
* `ConversationSimulator` for generating `turn`s in a [`ConversationalTestCase`](/docs/evaluation-multiturn-test-cases#conversational-test-case)

### Synthesizer [#synthesizer]

`deepeval` offers anyone the ability to easily generate synthetic datasets from documents locally on your machine. This is especially helpful if you don't have an evaluation dataset prepared beforehand.

```python
from deepeval.synthesizer import Synthesizer

goldens = Synthesizer().generate_goldens_from_docs(
    document_paths=['example.txt', 'example.docx', 'example.pdf']
)

dataset = EvaluationDataset(goldens=goldens)
```

In this example, we've used the `generate_goldens_from_docs` method, which is one of the four generation methods offered by `deepeval`'s `Synthesizer`. The four methods include:

* [`generate_goldens_from_docs()`](/docs/synthesizer-generate-from-docs): useful for generating goldens to evaluate your LLM application based on contexts extracted from your knowledge base in the form of documents.
* [`generate_goldens_from_contexts()`](/docs/synthesizer-generate-from-contexts): useful for generating goldens to evaluate your LLM application based on a list of prepared context.
* [`generate_goldens_from_scratch()`](/docs/synthesizer-generate-from-scratch): useful for generating goldens to evaluate your LLM application without relying on contexts from a knowledge base.
* [`generate_goldens_from_goldens()`](/docs/synthesizer-generate-from-goldens): useful for generating goldens by augmenting a known set of goldens.

`deepeval`'s `Synthesizer` uses a series of evolution techniques to complicate and make generated goldens more realistic to human prepared data.

<Callout type="info">
  For more information on how `deepeval`'s `Synthesizer` works, visit the [Golden Synthesizer section.](/docs/golden-synthesizer#how-does-it-work)
</Callout>

### Conversation Simulator [#conversation-simulator]

While a `Synthesizer` generates goldens, the `ConversationSimulator` works slightly different as it generates `turns` in a `ConversationalTestCase` instead:

```python
from deepeval.simulator import ConversationSimulator

# Define simulator
simulator = ConversationSimulator(
    user_intentions={"Opening a bank account": 1},
    user_profile_items=[
        "full name",
        "current address",
        "bank account number",
        "date of birth",
        "mother's maiden name",
        "phone number",
        "country code",
    ],
)

# Define model callback
async def model_callback(input: str, conversation_history: List[Dict[str, str]]) -> str:
    return f"I don't know how to answer this: {input}"

# Start simluation
convo_test_cases = simulator.simulate(
  model_callback=model_callback,
  stopping_criteria="Stop when the user's banking request has been fully resolved.",
)
print(convo_test_cases)
```

You can learn more in the [conversation simulator page.](/docs/conversation-simulator)

## What Are Goldens? [#what-are-goldens]

Goldens represent a more flexible alternative to test cases in the `deepeval`, and **is the preferred way to initialize a dataset**. Unlike test cases, goldens:

* Only require `input`/`scenario` to initialize
* Store expected results like `expected_output`/`expected_outcome`
* Serve as templates before becoming fully-formed test cases

Goldens excel in development workflows where you need to:

* Evaluate changes across different iterations of your LLM application
* Compare performance between model versions
* Test with `input`s that haven't yet been processed by your LLM

Think of goldens as "pending test cases" - they contain all the input data and expected results, but are missing the dynamic elements (`actual_output`, `retrieval_context`, `tools_called`) that will be generated when your LLM processes them.

### Data model [#data-model]

The golden data model is nearly identical to their single/multi-turn test case counterparts (aka. `LLMTestCase` and `ConversationalTestCase`).

For single-turn `Golden`s:

```python
from pydantic import BaseModel

class Golden(BaseModel):
    input: str
    expected_output: Optional[str] = None
    context: Optional[List[str]] = None
    expected_tools: Optional[List[ToolCall]] = None

    # Useful metadata for generating test cases
    additional_metadata: Optional[Dict] = None
    comments: Optional[str] = None
    custom_column_key_values: Optional[Dict[str, str]] = None

    # Fields that you should ideally not populate
    actual_output: Optional[str] = None
    retrieval_context: Optional[List[str]] = None
    tools_called: Optional[List[ToolCall]] = None
```

<Callout type="info">
  The `actual_output`, `retrieval_context`, and `tools_called` are meant to be populated dynamically instead of passed directly from a golden to test case at evaluation time.
</Callout>

For multi-turn `ConversationalGolden`s:

```python
from pydantic import BaseModel

class ConversationalGolden(BaseModel):
    scenario: str
    expected_outcome: Optional[str] = None
    user_description: Optional[str] = None
    context: Optional[List[str]] = None

    # Useful metadata for generating test cases
    additional_metadata: Optional[Dict] = None
    comments: Optional[str] = None
    custom_column_key_values: Optional[Dict[str, str]] = None

    # Fields that you should ideally not populate
    turns: Optional[Turn] = None
```

You can easily add and edit custom columns on [Confident AI.](https://www.confident-ai.com/docs/llm-evaluation/dataset-management/create-goldens#custom-dataset-columns)

<Callout type="tip">
  The `turns` parameter should &#x2A;*100%** be generated at evaluation time in your `ConversationalTestCase` instead. However, the `turns` parameter exists in case users want to either:

  * [Simulate turns](/docs/conversation-simulator) starting from a certain point of a prior conversation that was previously left off
  * Continue from a specific turn when test cases usually fail at the last turn where agents are calling multiple tools
</Callout>

# End-to-End LLM Evaluation (/docs/evaluation-end-to-end-llm-evals)





End-to-end evaluation assesses the "observable" inputs and outputs of your LLM application - it is what users see, and treats your LLM application as a black-box.

<ImageDisplayer src="ASSETS.endToEndLlmEvals" alt="end-to-end evals" />

<details>
  <summary>
    <strong>When should you run End-to-End evaluations?</strong>
  </summary>

  For simple LLM applications like basic RAG pipelines with "flat" architectures
  that can be represented by a single <code>LLMTestCase</code>, end-to-end
  evaluation is ideal. Common use cases that are suitable for end-to-end
  evaluation include (not inclusive):

  * RAG QA
  * PDF extraction
  * Writing assitants
  * Summarization
  * etc.

  You'll notice that use cases with simplier architectures are more suited for end-to-end evaluation. However, if your system is an extremely complex agentic workflow, you might also find end-to-end evaluation more suitable as you'll might conclude that that component-level evaluation gives you too much noise in its evaluation results.

  Most of what you saw in `deepeval`'s <a href="/docs/getting-started">quickstart</a> is end-to-end evaluation!
</details>

## What Are E2E Evals [#what-are-e2e-evals]

Running an end-to-end LLM evaluation creates a **test run** — a collection of test cases that benchmarks your LLM application at a specific point in time. You would typically:

* Loop through a list of `Golden`s
* Invoke your LLM app with each golden's `input`
* Generate a set of test cases ready for evaluation
* Apply metrics to your test cases and run evaluations

<Callout type="info">
  To get a more fully sharable [LLM test report](https://www.confident-ai.com/docs/llm-evaluation/dashboards/testing-reports) login to Confident AI [here](https://app.confident-ai.com) or run the following in your terminal:

  ```bash
  deepeval login
  ```
</Callout>

## Setup Your Test Environment [#setup-your-test-environment]

<Steps>
  <Step>
    ### Create a dataset [#create-a-dataset]

    [Datasets](/docs/evaluation-datasets) in `deepeval` allow you to store [`Golden`](/docs/evaluation-datasets#what-are-goldens)s, which are like a precursors to test cases. They allow you to create test case dynamically during evaluation time by calling your LLM application. Here's how you can create goldens:

    <Tabs items="[&#x22;Single-Turn&#x22;, &#x22;Multi-Turn&#x22;]">
      <Tab value="Single-Turn">
        ```python
        from deepeval.dataset import Golden

        goldens=[
            Golden(input="What is your name?"),
            Golden(input="Choose a number between 1 to 100"),
            ...
        ]
        ```
      </Tab>

      <Tab value="Multi-Turn">
        ```python
        from deepeval.dataset import ConversationalGolden

        goldens = [
            ConversationalGolden(
                scenario="Andy Byron wants to purchase a VIP ticket to a Coldplay concert.",
                expected_outcome="Successful purchase of a ticket.",
                user_description="Andy Byron is the CEO of Astronomer.",
            ),
            ...
        ]
        ```
      </Tab>
    </Tabs>

    You can also generate synthetic goldens automatically using the `Synthesizer`. Learn more [here](/docs/golden-synthesizer). You can now use these goldens to create an evaluation dataset that can be stored and loaded them anytime.

    Here's an example showing how you can create and store datasets in `deepeval`:

    <Tabs items="[&#x22;Confident AI&#x22;, &#x22;Locally as CSV&#x22;, &#x22;Locally as JSON&#x22;]">
      <Tab value="Confident AI">
        ```python
        from deepeval.dataset import EvaluationDataset

        dataset = EvaluationDataset(goldens)
        dataset.push(alias="My dataset")
        ```
      </Tab>

      <Tab value="Locally as CSV">
        ```python
        from deepeval.dataset import EvaluationDataset

        dataset = EvaluationDataset(goldens)
        dataset.save_as(
            file_type="csv",
            directory="./example"
        )
        ```
      </Tab>

      <Tab value="Locally as JSON">
        ```python
        from deepeval.dataset import EvaluationDataset

        dataset = EvaluationDataset(goldens)
        dataset.save_as(
            file_type="json",
            directory="./example"
        )
        ```
      </Tab>
    </Tabs>

    ✅ Done. You can now use this dataset anywhere to run your evaluations automatically by looping over them and generating test cases.
  </Step>

  <Step>
    ### Select metrics [#select-metrics]

    When it comes to selecting metrics for your application, we recommend choosing no more than 5 metrics, comprising of:

    * (2 - 3) **Generic metrics** for your application type. (*e.g. Agents, RAG, Chabot*)
    * (1 - 2) **Custom metrics** for your specific use case.

    You can read our [metrics section](/docs/metrics-introduction) to learn about the 50+ metrics we offer. Or come to [our discord](https://discord.com/invite/a3K9c8GRGt) and get some tailored recommendations from our team.
  </Step>
</Steps>

You can now use these test cases and metrics to run [single-turn](#single-turn-end-to-end-evals) and [multi-turn](#multi-turn-end-to-end-evals) end-to-end evals. If you've setup [tracing](/docs/evaluation-llm-tracing) for your LLM application, you can automatically [run end-to-end evals for traces](#end-to-end-evals-for-tracing) using a single line of code.

## Single-Turn E2E Evals [#single-turn-e2e-evals]

<Steps>
  <Step>
    ### Load your dataset [#load-your-dataset]

    `deepeval` offers support for loading datasets stored in JSON files, CSV files, and hugging face datasets into an `EvaluationDataset` as either test cases or goldens.

    <Tabs items="[&#x22;Confident AI&#x22;, &#x22;From CSV&#x22;, &#x22;From JSON&#x22;]">
      <Tab value="Confident AI">
        ```python
        from deepeval.dataset import EvaluationDataset

        dataset = EvaluationDataset()
        dataset.pull(alias="My Evals Dataset")
        ```
      </Tab>

      <Tab value="From CSV">
        ```python
        from deepeval.dataset import EvaluationDataset

        dataset = EvaluationDataset()

        dataset.add_goldens_from_csv_file(
            # file_path is the absolute path to your .csv file
            file_path="example.csv",
            input_col_name="query"
        )
        ```
      </Tab>

      <Tab value="From JSON">
        ```python
        from deepeval.dataset import EvaluationDataset

        dataset = EvaluationDataset()

        dataset.add_goldens_from_json_file(
            # file_path is the absolute path to your .json file
            file_path="example.json",
            input_key_name="query"
        )
        ```
      </Tab>
    </Tabs>

    You can [learn more about loading datasets here](/docs/evaluation-datasets#load-dataset).
  </Step>

  <Step>
    ### Create test cases using dataset [#create-test-cases-using-dataset]

    You can now create `LLMTestCase`s using the goldens by calling your LLM application.

    ```python title="main.py"
    from your_agent import your_llm_app # Replace with your LLM app
    from deepeval.dataset import EvaluationDataset
    from deepeval.test_case import LLMTestCase

    dataset = EvaluationDataset()

    test_cases = []

    # Create test cases from goldens
    for golden in dataset.goldens:
        res, text_chunks = your_llm_app(golden.input)
        test_case = LLMTestCase(input=golden.input, actual_output=res, retrieval_context=text_chunks)
        test_cases.append(test_case)
    ```

    You can also add test cases directly into your dataset by using the `add_test_case()` method.
  </Step>

  <Step>
    ### Run end-to-end evals [#run-end-to-end-evals]

    You should pass the `test_cases` and `metrics` you've decided in the `evaluate()` function to run end-to-end evals.

    ```python title="main.py" {}
    from your_agent import your_llm_app # Replace with your LLM app
    from deepeval.metrics import AnswerRelevancyMetric
    from deepeval import evaluate
    ...

    evaluate(
        test_cases=test_cases,
        metrics=[AnswerRelevancyMetric()],
        hyperparameters={
            model="gpt-4.1",
            system_prompt="..."
        }
    )
    ```

    There are **TWO** mandatory and **SIX** optional parameters when calling the `evaluate()` function for **END-TO-END** evaluation:

    * `test_cases`: a list of `LLMTestCase`s **OR** `ConversationalTestCase`s, or an `EvaluationDataset`. You cannot evaluate `LLMTestCase`s and `ConversationalTestCase`s in the same test run.
    * `metrics`: a list of metrics of type `BaseMetric`.
    * \[Optional] `hyperparameters`: a dict of type `dict[str, Union[str, int, float]]`. You can log any arbitrary hyperparameter associated with this test run to pick the best hyperparameters for your LLM application on Confident AI.
    * \[Optional] `identifier`: a string that allows you to better identify your test run on Confident AI.
    * \[Optional] `async_config`: an instance of type `AsyncConfig` that allows you to [customize the degree of concurrency](/docs/evaluation-flags-and-configs#async-configs) during evaluation. Defaulted to the default `AsyncConfig` values.
    * \[Optional] `display_config`:an instance of type `DisplayConfig` that allows you to [customize what is displayed](/docs/evaluation-flags-and-configs#display-configs) to the console during evaluation. Defaulted to the default `DisplayConfig` values.
    * \[Optional] `error_config`: an instance of type `ErrorConfig` that allows you to [customize how to handle errors](/docs/evaluation-flags-and-configs#error-configs) during evaluation. Defaulted to the default `ErrorConfig` values.
    * \[Optional] `cache_config`: an instance of type `CacheConfig` that allows you to [customize the caching behavior](/docs/evaluation-flags-and-configs#cache-configs) during evaluation. Defaulted to the default `CacheConfig` values.

    This is exactly the same as `assert_test()` in `deepeval test run`, but in a different interface.
  </Step>
</Steps>

<Callout type="tip">
  We recommend logging your `hyperparameters` during your evauations as they allow you find the best model configuration for your application.

  <VideoDisplayer src="ASSETS.evaluationParameterInsights" confidentUrl="https://www.confident-ai.com/docs/llm-evaluation/dashboards/model-and-prompt-insights" label="Parameter Insights To Find Best Model" />
</Callout>

<Callout type="info" title="Sweep hyperparameters in a for loop">
  Pass `DisplayConfig(results_folder="./evals/prompt-v3")` to persist each call to `evaluate()` as `test_run_<YYYYMMDD_HHMMSS>.json`:

  ```python
  from deepeval.evaluate import DisplayConfig

  for temp in [0.0, 0.4, 0.8]:
      evaluate(
          test_cases=test_cases,
          metrics=metrics,
          hyperparameters={"model": "gpt-4o-mini", "temperature": temp},
          display_config=DisplayConfig(results_folder="./evals/prompt-v3"),
      )
  ```

  The folder is the set of test runs; an [Experiment](/docs/evaluation-introduction) is formed later by comparing multiple test runs. See [Saving test runs locally](/docs/evaluation-flags-and-configs#saving-test-runs-locally) for the full layout and how AI tools like Cursor / Claude Code read the files.
</Callout>

## Multi-Turn E2E Evals [#multi-turn-e2e-evals]

<Steps>
  <Step>
    ### Wrap chatbot in callback [#wrap-chatbot-in-callback]

    You need to define a chatbot callback to generate synthetic test cases from goldens using the `ConversationSimulator`. So, define a callback function to generate the **next chatbot response** in a conversation, given the conversation history.

    <Tabs items="[&#x22;Python&#x22;, &#x22;OpenAI&#x22;, &#x22;LangChain&#x22;, &#x22;LlamaIndex&#x22;, &#x22;OpenAI Agents&#x22;, &#x22;Pydantic&#x22;]">
      <Tab value="Python">
        ```python title="main.py" showLineNumbers={true}  "
        from deepeval.test_case import Turn

        async def model_callback(input: str, turns: List[Turn], thread_id: str) -> Turn:
            # Replace with your chatbot
            response = await your_chatbot(input, turns, thread_id)
            return Turn(role="assistant", content=response)
        ```
      </Tab>

      <Tab value="OpenAI">
        ```python title=main.py showLineNumbers={true} {6}
        from deepeval.test_case import Turn
        from openai import OpenAI

        client = OpenAI()

        async def model_callback(input: str, turns: List[Turn]) -> str:
            messages = [
                {"role": "system", "content": "You are a ticket purchasing assistant"},
                *[{"role": t.role, "content": t.content} for t in turns],
                {"role": "user", "content": input},
            ]
            response = await client.chat.completions.create(model="gpt-4.1", messages=messages)
            return Turn(role="assistant", content=response.choices[0].message.content)
        ```
      </Tab>

      <Tab value="LangChain">
        ```python title=main.py showLineNumbers={true} {11}
        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
        from langchain_core.runnables.history import RunnableWithMessageHistory
        from langchain_community.chat_message_histories import ChatMessageHistory

        store = {}
        llm = ChatOpenAI(model="gpt-4")
        prompt = ChatPromptTemplate.from_messages([("system", "You are a ticket purchasing assistant."), MessagesPlaceholder(variable_name="history"), ("human", "{input}")])
        chain_with_history = RunnableWithMessageHistory(prompt | llm, lambda session_id: store.setdefault(session_id, ChatMessageHistory()), input_messages_key="input", history_messages_key="history")

        async def model_callback(input: str, thread_id: str) -> Turn:
            response = chain_with_history.invoke(
                {"input": input},
                config={"configurable": {"session_id": thread_id}}
            )
            return Turn(role="assistant", content=response.content)
        ```
      </Tab>

      <Tab value="LlamaIndex">
        ```python title="main.py"  showLineNumbers={true} {9}
        from llama_index.core.storage.chat_store import SimpleChatStore
        from llama_index.llms.openai import OpenAI
        from llama_index.core.chat_engine import SimpleChatEngine
        from llama_index.core.memory import ChatMemoryBuffer

        chat_store = SimpleChatStore()
        llm = OpenAI(model="gpt-4")

        async def model_callback(input: str, thread_id: str) -> Turn:
            memory = ChatMemoryBuffer.from_defaults(chat_store=chat_store, chat_store_key=thread_id)
            chat_engine = SimpleChatEngine.from_defaults(llm=llm, memory=memory)
            response = chat_engine.chat(input)
            return Turn(role="assistant", content=response.response)
        ```
      </Tab>

      <Tab value="OpenAI Agents">
        ```python title="main.py" showLineNumbers={true} {6}
        from agents import Agent, Runner, SQLiteSession

        sessions = {}
        agent = Agent(name="Test Assistant", instructions="You are a helpful assistant that answers questions concisely.")

        async def model_callback(input: str, thread_id: str) -> Turn:
            if thread_id not in sessions:
                sessions[thread_id] = SQLiteSession(thread_id)
            session = sessions[thread_id]
            result = await Runner.run(agent, input, session=session)
            return Turn(role="assistant", content=result.final_output)
        ```
      </Tab>

      <Tab value="Pydantic">
        ```python title="main.py" showLineNumbers={true} {9}
        from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart, TextPart
        from deepeval.test_case import Turn
        from datetime import datetime
        from pydantic_ai import Agent
        from typing import List

        agent = Agent('openai:gpt-4', system_prompt="You are a helpful assistant that answers questions concisely.")

        async def model_callback(input: str, turns: List[Turn]) -> Turn:
            message_history = []
            for turn in turns:
                if turn.role == "user":
                    message_history.append(ModelRequest(parts=[UserPromptPart(content=turn.content, timestamp=datetime.now())], kind='request'))
                elif turn.role == "assistant":
                    message_history.append(ModelResponse(parts=[TextPart(content=turn.content)], model_name='gpt-4', timestamp=datetime.now(), kind='response'))
            result = await agent.run(input, message_history=message_history)
            return Turn(role="assistant", content=result.output)
        ```
      </Tab>
    </Tabs>

    <Callout type="info">
      Your model callback should accept an `input`, and optionally `turns` and `thread_id`. It should return a `Turn` object.
    </Callout>
  </Step>

  <Step>
    ### Load your dataset [#load-your-dataset-1]

    `deepeval` offers support for loading datasets stored in JSON files, CSV files, and hugging face datasets into an `EvaluationDataset` as either test cases or goldens.

    <Tabs items="[&#x22;Confident AI&#x22;, &#x22;From JSON&#x22;, &#x22;From CSV&#x22;]">
      <Tab value="Confident AI">
        ```python
        from deepeval.dataset import EvaluationDataset

        dataset = EvaluationDataset()
        dataset.pull(alias="My Evals Dataset")
        ```
      </Tab>

      <Tab value="From JSON">
        ```python
        from deepeval.dataset import EvaluationDataset

        dataset = EvaluationDataset()

        dataset.add_goldens_from_json_file(
            # file_path is the absolute path to your .json file
            file_path="example.json",
            input_key_name="query"
        )
        ```
      </Tab>

      <Tab value="From CSV">
        ```python
        from deepeval.dataset import EvaluationDataset

        dataset = EvaluationDataset()

        dataset.add_goldens_from_csv_file(
            # file_path is the absolute path to your .csv file
            file_path="example.csv",
            input_col_name="query"
        )
        ```
      </Tab>
    </Tabs>

    You can [learn more about loading datasets here](/docs/evaluation-datasets#load-dataset).
  </Step>

  <Step>
    ### Simulate turns [#simulate-turns]

    Use `deepeval`'s `ConversationSimulator` to simulate turns using goldens in your dataset:

    ```python title="main.py"
    from deepeval.conversation_simulator import ConversationSimulator

    simulator = ConversationSimulator(model_callback=chatbot_callback)
    conversational_test_cases = simulator.simulate(goldens=dataset.goldens, max_turns=10)
    ```

    Here, we only have 1 test case, but in reality you'll want to simulate from at least 20 goldens.

    <details>
      <summary>
        Click to view an example simulated test case
      </summary>

      Your generated test cases should be populated with simulated `Turn`s, along with the `scenario`, `expected_outcome`, and `user_description` from the conversation golden.

      ```python
      ConversationalTestCase(
          scenario="Andy Byron wants to purchase a VIP ticket to a Coldplay concert.",
          expected_outcome="Successful purchase of a ticket.",
          user_description="Andy Byron is the CEO of Astronomer.",
          turns=[
              Turn(role="user", content="Hello, how are you?"),
              Turn(role="assistant", content="I'm doing well, thank you!"),
              Turn(role="user", content="How can I help you today?"),
              Turn(role="assistant", content="I'd like to buy a ticket to a Coldplay concert."),
          ]
      )
      ```
    </details>
  </Step>

  <Step>
    ### Run an evaluation [#run-an-evaluation]

    Run an evaluation like how you learnt in the previous section:

    ```python title="main.py"
    from deepeval.metrics import TurnRelevancyMetric
    from deepeval import evaluate
    ...

    evaluate(
      conversational_test_cases,
      metrics=[TurnRelevancyMetric()],
      hyperparameters={
          model="gpt-4.1",
          system_prompt="..."
      }
    )
    ```

    There are **TWO** mandatory and **SIX** optional parameters when calling the `evaluate()` function for **END-TO-END** evaluation:

    * `test_cases`: a list of `LLMTestCase`s **OR** `ConversationalTestCase`s, or an `EvaluationDataset`. You cannot evaluate `LLMTestCase`s and `ConversationalTestCase`s in the same test run.
    * `metrics`: a list of metrics of type `BaseConversationalMetric`.
    * \[Optional] `hyperparameters`: a dict of type `dict[str, Union[str, int, float]]`. You can log any arbitrary hyperparameter associated with this test run to pick the best hyperparameters for your LLM application on Confident AI.
    * \[Optional] `identifier`: a string that allows you to better identify your test run on Confident AI.
    * \[Optional] `async_config`: an instance of type `AsyncConfig` that allows you to [customize the degree of concurrency](/docs/evaluation-flags-and-configs#async-configs) during evaluation. Defaulted to the default `AsyncConfig` values.
    * \[Optional] `display_config`:an instance of type `DisplayConfig` that allows you to [customize what is displayed](/docs/evaluation-flags-and-configs#display-configs) to the console during evaluation. Defaulted to the default `DisplayConfig` values.
    * \[Optional] `error_config`: an instance of type `ErrorConfig` that allows you to [customize how to handle errors](/docs/evaluation-flags-and-configs#error-configs) during evaluation. Defaulted to the default `ErrorConfig` values.
    * \[Optional] `cache_config`: an instance of type `CacheConfig` that allows you to [customize the caching behavior](/docs/evaluation-flags-and-configs#cache-configs) during evaluation. Defaulted to the default `CacheConfig` values.

    This is exactly the same as `assert_test()` in `deepeval test run`, but in a difference interface.
  </Step>
</Steps>

We highly recommend setting up [Confident AI](https://app.confident-ai.com) with your `deepeval` evaluations to get professional test reports and observe trends of your LLM application's performance overtime like this:

<VideoDisplayer src="ASSETS.evaluationMultiTurnE2eReport" confidentUrl="https://www.confident-ai.com/docs/llm-evaluation/dashboards/testing-reports" label="Test Reports After Running Evals on Confident AI" />

## E2E Evals For Tracing [#e2e-evals-for-tracing]

If you've [setup tracing](/docs/evaluation-llm-tracing) for you LLM application, you can run end-to-end evals using the `evals_iterator()` function.

<Steps>
  <Step>
    ### Load your dataset [#load-your-dataset-2]

    `deepeval` offers support for loading datasets stored in JSON files, CSV files, and hugging face datasets into an `EvaluationDataset` as either test cases or goldens.

    <Tabs items="[&#x22;Confident AI&#x22;, &#x22;From CSV&#x22;, &#x22;From JSON&#x22;]">
      <Tab value="Confident AI">
        ```python
        from deepeval.dataset import EvaluationDataset

        dataset = EvaluationDataset()
        dataset.pull(alias="My Evals Dataset")
        ```
      </Tab>

      <Tab value="From CSV">
        ```python
        from deepeval.dataset import EvaluationDataset

        dataset = EvaluationDataset()

        dataset.add_goldens_from_csv_file(
            # file_path is the absolute path to your .csv file
            file_path="example.csv",
            input_col_name="query"
        )
        ```
      </Tab>

      <Tab value="From JSON">
        ```python
        from deepeval.dataset import EvaluationDataset

        dataset = EvaluationDataset()

        dataset.add_goldens_from_json_file(
            # file_path is the absolute path to your .json file
            file_path="example.json",
            input_key_name="query"
        )
        ```
      </Tab>
    </Tabs>

    You can [learn more about loading datasets here](/docs/evaluation-datasets#load-dataset).
  </Step>

  <Step>
    ### Update your test cases for trace [#update-your-test-cases-for-trace]

    You can update your end-to-end test cases for trace by using the `update_current_trace` function provided by `deepeval`

    ```python {2,10,17}
    from openai import OpenAI
    from deepeval.tracing import observe, update_current_trace

    @observe()
    def my_ai_agent(query: str) -> str:

        @observe()
        def retriever(query: str) -> list[str]:
            chunks = ["List", "of", "text", "chunks"]
            update_current_trace(retrieval_context=chunks)
            return chunks

        @observe()
        def generator(query: str, text_chunks: list[str]) -> str:
            res = OpenAI().chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": query}]
            ).choices[0].message.content
            update_current_trace(input=query, output=res)
            return res

        return generator(query, retriever(query))
    ```

    There are **TWO** ways to create test cases when using the `update_current_trace` function:

    * \[Optional] `test_case`: Takes an `LLMTestCase` to create a trace-level test case.

    * Or, You can also opt to give the values of `LLMTestCase` directly by using the following attributes:
      * \[Optional] `input`
      * \[Optional] `output`
      * \[Optional] `retrieval_context`
      * \[Optional] `context`
      * \[Optional] `expected_output`
      * \[Optional] `tools_called`
      * \[Optional] `expected_tools`

    <Callout type="note">
      You can use the individual `LLMTestCase` params in the `update_current_trace` function to override the values of the `test_case` you passed.
    </Callout>
  </Step>

  <Step>
    ### Run end-to-end evals [#run-end-to-end-evals-1]

    You can run end-to-end evals for your traces by supplying your `metrics` in the `evals_iterator` function.

    ```python
    from deepeval.metrics import AnswerRelevancyMetric
    from deepeval.dataset import EvaluationDataset

    dataset = EvaluationDataset()
    dataset.pull(alias="YOUR-DATASET-ALIAS")

    for golden in dataset.evals_iterator(metrics=[AnswerRelevancyMetric()]):
        my_ai_agent(golden.input)  # captures trace
    ```

    There are **SIX** optional parameters when using the `evals_iterator()`:

    * \[Optional] `metrics`: a list of `BaseMetric` that allows you to run end-to-end evals for your traces.
    * \[Optional] `identifier`: a string that allows you to better identify your test run on Confident AI.
    * \[Optional] `async_config`: an instance of type `AsyncConfig` that allows you to [customize the degree concurrency](/docs/evaluation-flags-and-configs#async-configs) during evaluation. Defaulted to the default `AsyncConfig` values.
    * \[Optional] `display_config`:an instance of type `DisplayConfig` that allows you to [customize what is displayed](/docs/evaluation-flags-and-configs#display-configs) to the console during evaluation. Defaulted to the default `DisplayConfig` values.
    * \[Optional] `error_config`: an instance of type `ErrorConfig` that allows you to [customize how to handle errors](/docs/evaluation-flags-and-configs#error-configs) during evaluation. Defaulted to the default `ErrorConfig` values.
    * \[Optional] `cache_config`: an instance of type `CacheConfig` that allows you to [customize the caching behavior](/docs/evaluation-flags-and-configs#cache-configs) during evaluation. Defaulted to the default `CacheConfig` values.

    This is all it takes to run end-to-end evaluations, with the added benefit of a full testing report with tracing included on Confident AI.

    <VideoDisplayer src="ASSETS.evaluationSingleTurnE2eReportTracing" confidentUrl="https://www.confident-ai.com/docs/llm-evaluation/dashboards/testing-reports" label="Test Reports For Evals and Traces on Confident AI" />
  </Step>
</Steps>

If you want to run end-to-end evaluations in CI/CD piplines, [click here](/docs/evaluation-unit-testing-in-ci-cd#end-to-end-evals-in-cicd).


# Unit Testing in CI/CD (/docs/evaluation-unit-testing-in-ci-cd)





Integrate LLM evaluations into your CI/CD pipeline with `deepeval` to catch regressions and ensure reliable performance. You can use `deepeval` with your CI/CD pipelines to run both end-to-end and component level evaluations.

`deepeval` allows you to run evaluations as if you're using `pytest` via our Pytest integration.

## End-to-End Evals in CI/CD [#end-to-end-evals-in-cicd]

Run tests against your LLM app using golden datasets for every push you make. End-to-end evaluations validate overall behavior across single-turn and multi-turn interactions. Perfect for catching regressions before deploying to production.

### Single-Turn Evals [#single-turn-evals]

<Steps>
  <Step>
    ### Load your dataset [#load-your-dataset]

    `deepeval` offers support for loading datasets stored in JSON files, CSV files, and hugging face datasets into an `EvaluationDataset` as either test cases or goldens.

    <Tabs items="[&#x22;Confident AI&#x22;, &#x22;From CSV&#x22;, &#x22;From JSON&#x22;]">
      <Tab value="Confident AI">
        ```python
        from deepeval.dataset import EvaluationDataset

        dataset = EvaluationDataset()
        dataset.pull(alias="My Evals Dataset")
        ```
      </Tab>

      <Tab value="From CSV">
        ```python
        from deepeval.dataset import EvaluationDataset

        dataset = EvaluationDataset()

        dataset.add_goldens_from_csv_file(
            # file_path is the absolute path to you .csv file
            file_path="example.csv",
            input_col_name="query"
        )
        ```
      </Tab>

      <Tab value="From JSON">
        ```python
        from deepeval.dataset import EvaluationDataset

        dataset = EvaluationDataset()

        dataset.add_goldens_from_json_file(
            # file_path is the absolute path to you .json file
            file_path="example.json",
            input_key_name="query"
        )
        ```
      </Tab>
    </Tabs>

    You can [learn more about loading datasets here](/docs/evaluation-datasets#load-dataset).
  </Step>

  <Step>
    ### Assert your tests [#assert-your-tests]

    You can use `deepeval`'s `assert_test` function to write test files.

    ```python title="test_llm_app.py" showLineNumbers {14}
    from your_agent import your_llm_app # Replace with your LLM app
    import pytest

    from deepeval.dataset import Golden
    from deepeval.test_case import LLMTestCase
    from deepeval import assert_test

    # Loop through goldens using pytest

    @pytest.mark.parametrize("golden",dataset.goldens)
    def test_llm_app(golden: Golden):
        res, text_chunks = your_llm_app(golden.input)
        test_case = LLMTestCase(input=golden.input, actual_output=res, retrieval_context=text_chunks)
        assert_test(test_case=test_case, metrics=[AnswerRelevancyMetric()])

    @deepeval.log_hyperparameters(model="gpt-4", prompt_template="...")
    def hyperparameters():
        return {"model": "gpt-4.1", "system prompt": "..."}
    ```

    Then, run the following command in your CLI:

    ```bash
    deepeval test run test_llm_app.py
    ```

    There are **TWO** mandatory and **ONE** optional parameter when calling the `assert_test()` function for **END-TO-END** evaluation:

    * `test_case`: an `LLMTestCase`.
    * `metrics`: a list of metrics of type `BaseMetric`.
    * \[Optional] `run_async`: a boolean which when set to `True`, enables concurrent evaluation of all metrics in `@observe`. Defaulted to `True`.

    Create a YAML file to execute your test file automatically in CI/CD pipelines. [Click here for an example YAML file](#yaml-file-for-cicd-evals).
  </Step>
</Steps>

### Multi-Turn Evals [#multi-turn-evals]

<Steps>
  <Step>
    ### Wrap chatbot in callback [#wrap-chatbot-in-callback]

    You need to define a chatbot callback to generate synthetic test cases from goldens using the `ConversationSimulator`. So, define a callback function to generate the **next chatbot response** in a conversation, given the conversation history.

    <Tabs items="[&#x22;Python&#x22;, &#x22;OpenAI&#x22;, &#x22;LangChain&#x22;, &#x22;LlamaIndex&#x22;, &#x22;OpenAI Agents&#x22;, &#x22;Pydantic&#x22;]">
      <Tab value="Python">
        ```python title="main.py" showLineNumbers={true}  "
        from deepeval.test_case import Turn

        async def model_callback(input: str, turns: List[Turn], thread_id: str) -> Turn:
            # Replace with your chatbot
            response = await your_chatbot(input, turns, thread_id)
            return Turn(role="assistant", content=response)
        ```
      </Tab>

      <Tab value="OpenAI">
        ```python title=main.py showLineNumbers={true} {6}
        from deepeval.test_case import Turn
        from openai import OpenAI

        client = OpenAI()

        async def model_callback(input: str, turns: List[Turn]) -> str:
            messages = [
                {"role": "system", "content": "You are a ticket purchasing assistant"},
                *[{"role": t.role, "content": t.content} for t in turns],
                {"role": "user", "content": input},
            ]
            response = await client.chat.completions.create(model="gpt-4.1", messages=messages)
            return Turn(role="assistant", content=response.choices[0].message.content)
        ```
      </Tab>

      <Tab value="LangChain">
        ```python title=main.py showLineNumbers={true} {11}
        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
        from langchain_core.runnables.history import RunnableWithMessageHistory
        from langchain_community.chat_message_histories import ChatMessageHistory

        store = {}
        llm = ChatOpenAI(model="gpt-4")
        prompt = ChatPromptTemplate.from_messages([("system", "You are a ticket purchasing assistant."), MessagesPlaceholder(variable_name="history"), ("human", "{input}")])
        chain_with_history = RunnableWithMessageHistory(prompt | llm, lambda session_id: store.setdefault(session_id, ChatMessageHistory()), input_messages_key="input", history_messages_key="history")

        async def model_callback(input: str, thread_id: str) -> Turn:
            response = chain_with_history.invoke(
                {"input": input},
                config={"configurable": {"session_id": thread_id}}
            )
            return Turn(role="assistant", content=response.content)
        ```
      </Tab>

      <Tab value="LlamaIndex">
        ```python title="main.py"  showLineNumbers={true} {9}
        from llama_index.core.storage.chat_store import SimpleChatStore
        from llama_index.llms.openai import OpenAI
        from llama_index.core.chat_engine import SimpleChatEngine
        from llama_index.core.memory import ChatMemoryBuffer

        chat_store = SimpleChatStore()
        llm = OpenAI(model="gpt-4")

        async def model_callback(input: str, thread_id: str) -> Turn:
            memory = ChatMemoryBuffer.from_defaults(chat_store=chat_store, chat_store_key=thread_id)
            chat_engine = SimpleChatEngine.from_defaults(llm=llm, memory=memory)
            response = chat_engine.chat(input)
            return Turn(role="assistant", content=response.response)
        ```
      </Tab>

      <Tab value="OpenAI Agents">
        ```python title="main.py" showLineNumbers={true} {6}
        from agents import Agent, Runner, SQLiteSession

        sessions = {}
        agent = Agent(name="Test Assistant", instructions="You are a helpful assistant that answers questions concisely.")

        async def model_callback(input: str, thread_id: str) -> Turn:
            if thread_id not in sessions:
                sessions[thread_id] = SQLiteSession(thread_id)
            session = sessions[thread_id]
            result = await Runner.run(agent, input, session=session)
            return Turn(role="assistant", content=result.final_output)
        ```
      </Tab>

      <Tab value="Pydantic">
        ```python title="main.py" showLineNumbers={true} {9}
        from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart, TextPart
        from deepeval.test_case import Turn
        from datetime import datetime
        from pydantic_ai import Agent
        from typing import List

        agent = Agent('openai:gpt-4', system_prompt="You are a helpful assistant that answers questions concisely.")

        async def model_callback(input: str, turns: List[Turn]) -> Turn:
            message_history = []
            for turn in turns:
                if turn.role == "user":
                    message_history.append(ModelRequest(parts=[UserPromptPart(content=turn.content, timestamp=datetime.now())], kind='request'))
                elif turn.role == "assistant":
                    message_history.append(ModelResponse(parts=[TextPart(content=turn.content)], model_name='gpt-4', timestamp=datetime.now(), kind='response'))
            result = await agent.run(input, message_history=message_history)
            return Turn(role="assistant", content=result.output)
        ```
      </Tab>
    </Tabs>

    <Callout type="info">
      Your model callback should accept an `input`, and optionally `turns` and `thread_id`. It should return a `Turn` object.
    </Callout>
  </Step>

  <Step>
    ### Load your dataset [#load-your-dataset-1]

    `deepeval` offers support for loading datasets stored in JSON files, CSV files, and hugging face datasets into an `EvaluationDataset` as either test cases or goldens.

    <Tabs items="[&#x22;Confident AI&#x22;, &#x22;From CSV&#x22;, &#x22;From JSON&#x22;]">
      <Tab value="Confident AI">
        ```python
        from deepeval.dataset import EvaluationDataset

        dataset = EvaluationDataset()
        dataset.pull(alias="My Evals Dataset")
        ```
      </Tab>

      <Tab value="From CSV">
        ```python
        from deepeval.dataset import EvaluationDataset

        dataset = EvaluationDataset()

        dataset.add_goldens_from_csv_file(
            # file_path is the absolute path to you .csv file
            file_path="example.csv",
            input_col_name="query"
        )
        ```
      </Tab>

      <Tab value="From JSON">
        ```python
        from deepeval.dataset import EvaluationDataset

        dataset = EvaluationDataset()

        dataset.add_goldens_from_json_file(
            # file_path is the absolute path to you .json file
            file_path="example.json",
            input_key_name="query"
        )
        ```
      </Tab>
    </Tabs>

    You can [learn more about loading datasets here](/docs/evaluation-datasets#load-dataset).
  </Step>

  <Step>
    ### Assert your tests [#assert-your-tests-1]

    You can use `deepeval`'s `assert_test` function to write test files.

    ```python title="test_llm_app.py" showLineNumbers {14}
    from main import chatbot_callback # Replace with your LLM callback
    import pytest

    from deepeval.dataset import Golden
    from deepeval.test_case import ConversationalTestCase
    from deepeval import assert_test
    from deepeval.conversation_simulator import ConversationSimulator

    # Loop through goldens using pytest

    simulator = ConversationSimulator(model_callback=chatbot_callback)
    conversational_test_cases = simulator.simulate(goldens=dataset.goldens, max_turns=10)

    @pytest.mark.parametrize("test_case", conversational_test_cases)
    def test_llm_app(test_case: ConversationalTestCase):
        assert_test(test_case=test_case, metrics=[AnswerRelevancyMetric()])

    @deepeval.log_hyperparameters(model="gpt-4", prompt_template="...")
    def hyperparameters():
        return {"model": "gpt-4.1", "system prompt": "..."}
    ```

    Then, run the following command in your CLI:

    ```bash
    deepeval test run test_llm_app.py
    ```

    There are **TWO** mandatory and **ONE** optional parameter when calling the `assert_test()` function for **END-TO-END** evaluation:

    * `test_case`: an `LLMTestCase`.
    * `metrics`: a list of metrics of type `BaseMetric`.
    * \[Optional] `run_async`: a boolean which when set to `True`, enables concurrent evaluation of all metrics in `@observe`. Defaulted to `True`.

    Create a YAML file to execute your test file automatically in CI/CD pipelines. [Click here for an example YAML file](#yaml-file-for-cicd-evals).
  </Step>
</Steps>

<Callout type="caution">
  The usual `pytest` command would still work but is highly not recommended. `deepeval test run` adds a range of functionalities on top of Pytest for unit-testing LLMs, which is enabled by [8+ optional flags](/docs/evaluation-flags-and-configs#flags-for-deepeval-test-run). Users typically include `deepeval test run` as a command in their `.yaml` files for pre-deployment checks in CI/CD pipelines ([example here](https://www.confident-ai.com/docs/llm-evaluation/unit-testing-cicd)).
</Callout>

[Click here](/docs/evaluation-flags-and-configs#flags-for-deepeval-test-run) to learn about different optional flags available to `deepeval test run` to customize asynchronous behaviors, error handling, etc.

## Component-Level Evals in CI/CD [#component-level-evals-in-cicd]

Test individual parts of your LLM pipeline like prompt templates or retrieval logic in isolation. Component-level evals offer fast, targeted feedback and integrate seamlessly into your CI/CD workflows.

<Steps>
  <Step>
    ### Load your dataset [#load-your-dataset-2]

    `deepeval` offers support for loading datasets stored in JSON files, CSV files, and hugging face datasets into an `EvaluationDataset` as either test cases or goldens.

    <Tabs items="[&#x22;Confident AI&#x22;, &#x22;From CSV&#x22;, &#x22;From JSON&#x22;]">
      <Tab value="Confident AI">
        ```python
        from deepeval.dataset import EvaluationDataset

        dataset = EvaluationDataset()
        dataset.pull(alias="My Evals Dataset")
        ```
      </Tab>

      <Tab value="From CSV">
        ```python
        from deepeval.dataset import EvaluationDataset

        dataset = EvaluationDataset()

        dataset.add_goldens_from_csv_file(
            # file_path is the absolute path to you .csv file
            file_path="example.csv",
            input_col_name="query"
        )
        ```
      </Tab>

      <Tab value="From JSON">
        ```python
        from deepeval.dataset import EvaluationDataset

        dataset = EvaluationDataset()

        dataset.add_goldens_from_json_file(
            # file_path is the absolute path to you .json file
            file_path="example.json",
            input_key_name="query"
        )
        ```
      </Tab>
    </Tabs>

    You can [learn more about loading datasets here](/docs/evaluation-datasets#load-dataset).
  </Step>

  <Step>
    ### Assert your tests [#assert-your-tests-2]

    You can use `deepeval`'s `assert_test` function to write test files.

    ```python title="test_my_ai_agent.py" {10-11}
    import pytest

    from your_agent import my_ai_agent # Replace with your @observe-instrumented AI agent

    from deepeval import assert_test
    from deepeval.dataset import Golden

    # Loop through goldens in our dataset using pytest
    @pytest.mark.parametrize("golden", dataset.goldens)
    def test_my_ai_agent(golden: Golden):
        my_ai_agent(golden.input)  # captures trace
        assert_test(golden=golden)  # evaluates spans

    @deepeval.log_hyperparameters(model="gpt-4", prompt_template="...")
    def hyperparameters():
        return {"model": "gpt-4.1", "system prompt": "..."}
    ```

    Finally, don't forget to run the test file in the CLI:

    ```bash
    deepeval test run test_my_ai_agent.py
    ```

    There is **ONE** mandatory parameter when calling the `assert_test()` function for **COMPONENT-LEVEL** evaluation:

    * `golden`: the `Golden` used to identify the active trace captured during the test.

    Create a YAML file to execute your test file automatically in CI/CD pipelines. [Click here for an example YAML file](#yaml-file-for-cicd-evals).
  </Step>
</Steps>

<Callout type="info">
  Similar to the `evaluate()` function, `assert_test()` for component-level evaluation does not need:

  * Declaration of `metrics` because component-level metrics are defined on spans with `@observe(metrics=[...])`.
  * Creation of `LLMTestCase`s because it is handled at runtime by `update_current_span` in your AI agent.
</Callout>

## YAML File For CI/CD Evals [#yaml-file-for-cicd-evals]

To run your unit tests on all changes in prod, you can use the following `YAML` file in your **github actions** or any other similar CI/CD pipelines. This example uses `poetry` for installation, `OPENAI_API_KEY` as your LLM judge to run evals locally. You can also optionally add `CONFIDENT_API_KEY` to send results to Confident AI.

```yaml {32-33}
name: LLM App `deepeval` Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.10"

      - name: Install Poetry
        run: |
          curl -sSL https://install.python-poetry.org | python3 -
          echo "$HOME/.local/bin" >> $GITHUB_PATH

      - name: Install Dependencies
        run: poetry install --no-root

      - name: Run `deepeval` Unit Tests
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          CONFIDENT_API_KEY: ${{ secrets.CONFIDENT_API_KEY }}
        run: poetry run deepeval test run test_llm_app.py
```

[Click here](/docs/evaluation-flags-and-configs#flags-for-deepeval-test-run) to learn about different optional flags available to `deepeval test run` to customize asynchronous behaviors, error handling, etc.

<Callout type="tip">
  We highly recommend setting up [Confident AI](https://app.confident-ai.com) with your `deepeval` evaluations to get professional test reports and observe trends of your LLM application's performance overtime like this:

  <VideoDisplayer src="ASSETS.tracingSpans" confidentUrl="/docs/llm-tracing/introduction" label="Span-Level Evals in Production" />
</Callout>

# Flags and Configs (/docs/evaluation-flags-and-configs)



Sometimes you might want to customize the behavior of different settings for `evaluate()` and `assert_test()`, and this can be done using "configs" (short for configurations) and "flags".

<Callout type="note">
  For example, if you're using a [custom LLM judge for evaluation](/guides/guides-using-custom-llms), you may wish to `ignore_errors` to not interrupt evaluations whenever your model fails to produce a valid JSON, or avoid rate limit errors entirely by lowering the `max_concurrent` value.
</Callout>

## Configs for `evaluate()` [#configs-for-evaluate]

### Async Configs [#async-configs]

The `AsyncConfig` controls how concurrently `metrics`, `observed_callback`, and `test_cases` will be evaluated during `evaluate()`.

```python
from deepeval.evaluate import AsyncConfig
from deepeval import evaluate

evaluate(async_config=AsyncConfig(), ...)
```

There are **THREE** optional parameters when creating an `AsyncConfig`:

* \[Optional] `run_async`: a boolean which when set to `True`, enables concurrent evaluation of test cases **AND** metrics. Defaulted to `True`.
* \[Optional] `throttle_value`: an integer that determines how long (in seconds) to throttle the evaluation of each test case. You can increase this value if your evaluation model is running into rate limit errors. Defaulted to 0.
* \[Optional] `max_concurrent`: an integer that determines the maximum number of test cases that can be ran in parallel at any point in time. You can decrease this value if your evaluation model is running into rate limit errors. Defaulted to `20`.

The `throttle_value` and `max_concurrent` parameter is only used when `run_async` is set to `True`. A combination of a `throttle_value` and `max_concurrent` is the best way to handle rate limiting errors, either in your LLM judge or LLM application, when running evaluations.

### Display Configs [#display-configs]

The `DisplayConfig` controls how results and intermediate execution steps are displayed during `evaluate()`.

```python
from deepeval.evaluate import DisplayConfig
from deepeval import evaluate

evaluate(display_config=DisplayConfig(), ...)
```

There are **SIX** optional parameters when creating a `DisplayConfig`:

* \[Optional] `verbose_mode`: a optional boolean which when **IS NOT** `None`, overrides each [metric's `verbose_mode` value](/docs/metrics-introduction#debugging-a-metric). Defaulted to `None`.
* \[Optional] `display`: a str of either `"all"`, `"failing"` or `"passing"`, which allows you to selectively decide which type of test cases to display as the final result. Defaulted to `"all"`.
* \[Optional] `show_indicator`: a boolean which when set to `True`, shows the evaluation progress indicator for each individual metric. Defaulted to `True`.
* \[Optional] `print_results`: a boolean which when set to `True`, prints the result of each evaluation. Defaulted to `True`.
* \[Optional] `results_folder`: a string path to a directory where each call to `evaluate()` (or `evals_iterator()`) will be persisted as a `test_run_<YYYYMMDD_HHMMSS>.json` file. Defaulted to `None` (no local save). See [Saving test runs locally](#saving-test-runs-locally) below.
* \[Optional] `results_subfolder`: an optional string that, when set together with `results_folder`, nests the `test_run_*.json` files under `results_folder/results_subfolder/`. Defaulted to `None` (flat layout).
* \[Optional, deprecated] `file_output_dir`: a string which when set, writes a legacy `.log` per test result to the specified directory. Prefer `results_folder`, which saves the full `TestRun` as a single structured JSON file that AI tools can read directly.

#### Saving test runs locally [#saving-test-runs-locally]

Set `results_folder` to persist each `evaluate()` call to disk as a structured `TestRun` JSON. Hyperparameters, per-test-case scores, and metric reasons are all serialized into each file via the same schema that Confident AI uses — no extra setup required.

```python
from deepeval import evaluate
from deepeval.evaluate import DisplayConfig

for temp in [0.0, 0.4, 0.8]:
    evaluate(
        test_cases=test_cases,
        metrics=metrics,
        hyperparameters={"model": "gpt-4o-mini", "temperature": temp},
        display_config=DisplayConfig(results_folder="./evals/prompt-v3"),
    )
```

After the loop, the folder is flat — just the raw test runs:

```
./evals/prompt-v3/
  test_run_20260421_140114.json
  test_run_20260421_140132.json
  test_run_20260421_140151.json
```

The timestamp prefix makes `ls` order match chronological order, so an AI agent (Cursor, Claude Code) can iterate over the folder in the order runs happened. If two runs finish within the same second, the writer appends `_2`, `_3`, … to the filename so nothing is ever overwritten.

Set `results_subfolder` to nest the runs under an extra directory — useful when the parent folder already holds other artifacts:

```python
DisplayConfig(results_folder="./evals/prompt-v3", results_subfolder="test_runs")
```

```
./evals/prompt-v3/
  test_runs/
    test_run_20260421_140114.json
    test_run_20260421_140132.json
```

<Callout type="info" title="Reading results with Cursor / Claude Code">
  Point the agent at the folder and ask it to `ls` and open the `test_run_*.json` files directly. Everything an agent needs — hyperparameters, prompts, metric scores, and failure reasons — is inside each file, so no extra index or summary is required.

  Note that a **test run** is a single `evaluate()` call. An [Experiment](/docs/evaluation-introduction) is formed later by *comparing* multiple test runs, e.g. across different prompts or models.
</Callout>

If `results_folder` is unset but the `DEEPEVAL_RESULTS_FOLDER` environment variable is present, `deepeval` falls back to that path for backwards compatibility.

### Error Configs [#error-configs]

The `ErrorConfig` controls how error is handled in `evaluate()`.

```python
from deepeval.evaluate import ErrorConfig
from deepeval import evaluate

evaluate(error_config=ErrorConfig(), ...)
```

There are **TWO** optional parameters when creating an `ErrorConfig`:

* \[Optional] `skip_on_missing_params`: a boolean which when set to `True`, skips all metric executions for test cases with missing parameters. Defaulted to `False`.
* \[Optional] `ignore_errors`: a boolean which when set to `True`, ignores all exceptions raised during metrics execution for each test case. Defaulted to `False`.

If both `skip_on_missing_params` and `ignore_errors` are set to `True`, `skip_on_missing_params` takes precedence. This means that if a metric is missing required test case parameters, it will be skipped (and the result will be missing) rather than appearing as an ignored error in the final test run.

### Cache Configs [#cache-configs]

The `CacheConfig` controls the caching behavior of `evaluate()`.

```python
from deepeval.evaluate import CacheConfig
from deepeval import evaluate

evaluate(cache_config=CacheConfig(), ...)
```

There are **TWO** optional parameters when creating an `CacheConfig`:

* \[Optional] `use_cache`: a boolean which when set to `True`, uses cached test run results instead. Defaulted to `False`.
* \[Optional] `write_cache`: a boolean which when set to `True`, uses writes test run results to **DISK**. Defaulted to `True`.

The `write_cache` parameter writes to disk and so you should disable it if that is causing any errors in your environment.

## Flags for `deepeval test run`: [#flags-for-deepeval-test-run]

### Parallelization [#parallelization]

Evaluate each test case in parallel by providing a number to the `-n` flag to specify how many processes to use.

```
deepeval test run test_example.py -n 4
```

### Cache [#cache]

Provide the `-c` flag (with no arguments) to read from the local `deepeval` cache instead of re-evaluating test cases on the same metrics.

```
deepeval test run test_example.py -c
```

<Callout type="info">
  This is extremely useful if you're running large amounts of test cases. For example, lets say you're running 1000 test cases using `deepeval test run`, but you encounter an error on the 999th test case. The cache functionality would allow you to skip all the previously evaluated 999 test cases, and just evaluate the remaining one.
</Callout>

### Ignore Errors [#ignore-errors]

The `-i` flag (with no arguments) allows you to ignore errors for metrics executions during a test run. An example of where this is helpful is if you're using a custom LLM and often find it generating invalid JSONs that will stop the execution of the entire test run.

```
deepeval test run test_example.py -i
```

<Callout type="tip">
  You can combine different flags, such as the `-i`, `-c`, and `-n` flag to execute any uncached test cases in parallel while ignoring any errors along the way:

  ```python
  deepeval test run test_example.py -i -c -n 2
  ```
</Callout>

### Verbose Mode [#verbose-mode]

The `-v` flag (with no arguments) allows you to turn on [`verbose_mode` for all metrics](/docs/metrics-introduction#debugging-a-metric) ran using `deepeval test run`. Not supplying the `-v` flag will default each metric's `verbose_mode` to its value at instantiation.

```python
deepeval test run test_example.py -v
```

<Callout type="note">
  When a metric's `verbose_mode` is `True`, it prints the intermediate steps used to calculate said metric to the console during evaluation.
</Callout>

### Skip Test Cases [#skip-test-cases]

The `-s` flag (with no arguments) allows you to skip metric executions where the test case has missing//insufficient parameters (such as `retrieval_context`) that is required for evaluation. An example of where this is helpful is if you're using a metric such as the `ContextualPrecisionMetric` but don't want to apply it when the `retrieval_context` is `None`.

```
deepeval test run test_example.py -s
```

### Identifier [#identifier]

The `-id` flag followed by a string allows you to name test runs and better identify them on [Confident AI](https://confident-ai.com). An example of where this is helpful is if you're running automated deployment pipelines, have deployment IDs, or just want a way to identify which test run is which for comparison purposes.

```
deepeval test run test_example.py -id "My Latest Test Run"
```

### Display Mode [#display-mode]

The `-d` flag followed by a string of "all", "passing", or "failing" allows you to display only certain test cases in the terminal. For example, you can display "failing" only if you only care about the failing test cases.

```
deepeval test run test_example.py -d "failing"
```

### Repeats [#repeats]

Repeat each test case by providing a number to the `-r` flag to specify how many times to rerun each test case.

```
deepeval test run test_example.py -r 2
```

### Hooks [#hooks]

`deepeval`'s Pytest integration allows you to run custom code at the end of each evaluation via the `@deepeval.on_test_run_end` decorator:

```python title="test_example.py"
...

@deepeval.on_test_run_end
def function_to_be_called_after_test_run():
    print("Test finished!")
```

## Eval Metrics:

# Answer Relevancy (/docs/metrics-answer-relevancy)



<MetricTagsDisplayer singleTurn="true" referenceless="true" rag="true" />

The answer relevancy metric uses LLM-as-a-judge to measure the quality of your RAG pipeline's generator by evaluating how relevant the `actual_output` of your LLM application is compared to the provided `input`. `deepeval`'s answer relevancy metric is a self-explaining LLM-Eval, meaning it outputs a reason for its metric score.

<Callout type="tip">
  Here is a detailed guide on [RAG evaluation](/guides/guides-rag-evaluation), which we highly recommend as it explains everything about `deepeval`'s RAG metrics.
</Callout>

## Required Arguments [#required-arguments]

To use the `AnswerRelevancyMetric`, you'll have to provide the following arguments when creating an [`LLMTestCase`](/docs/evaluation-test-cases#llm-test-case):

* `input`
* `actual_output`

Read the [How Is It Calculated](#how-is-it-calculated) section below to learn how test case parameters are used for metric calculation.

## Usage [#usage]

The `AnswerRelevancyMetric()` can be used for [end-to-end](/docs/evaluation-end-to-end-llm-evals) evaluation of text-based and multimodal test cases:

<Tabs items="[&#x22;Text Based&#x22;, &#x22;Multimodal&#x22;]">
  <Tab value="Text Based">
    ```python
    from deepeval import evaluate
    from deepeval.metrics import AnswerRelevancyMetric
    from deepeval.test_case import LLMTestCase

    metric = AnswerRelevancyMetric(
        threshold=0.7,
        model="gpt-4.1",
        include_reason=True
    )
    test_case = LLMTestCase(
        input="What if these shoes don't fit?",
        # Replace this with the output from your LLM app
        actual_output="We offer a 30-day full refund at no extra cost."
    )

    # To run metric as a standalone
    # metric.measure(test_case)
    # print(metric.score, metric.reason)

    evaluate(test_cases=[test_case], metrics=[metric])
    ```
  </Tab>

  <Tab value="Multimodal">
    ```python
    from deepeval import evaluate
    from deepeval.metrics import AnswerRelevancyMetric
    from deepeval.test_case import LLMTestCase, MLLMImage

    metric = AnswerRelevancyMetric(
        threshold=0.7,
        model="gpt-4.1",
        include_reason=True
    )
    test_case = LLMTestCase(
        input=f"Tell me about this landmark in France: {MLLMImage(...)}",
        # Replace this with the output from your LLM app
        actual_output=f"This appears to be Eiffel Tower, which is a famous landmark in France"
    )

    # To run metric as a standalone
    # metric.measure(test_case)
    # print(metric.score, metric.reason)

    evaluate(test_cases=[test_case], metrics=[metric])
    ```
  </Tab>
</Tabs>

There are **SEVEN** optional parameters when creating an `AnswerRelevancyMetric`:

* \[Optional] `threshold`: a float representing the minimum passing threshold, defaulted to 0.5.
* \[Optional] `model`: a string specifying which of OpenAI's GPT models to use, **OR** [any custom LLM model](/docs/metrics-introduction#using-a-custom-llm) of type `DeepEvalBaseLLM`. Defaulted to <DefaultLLMModel />.
* \[Optional] `include_reason`: a boolean which when set to `True`, will include a reason for its evaluation score. Defaulted to `True`.
* \[Optional] `strict_mode`: a boolean which when set to `True`, enforces a binary metric score: 1 for perfection, 0 otherwise. It also overrides the current threshold and sets it to 1. Defaulted to `False`.
* \[Optional] `async_mode`: a boolean which when set to `True`, enables [concurrent execution within the `measure()` method.](/docs/metrics-introduction#measuring-a-metric-in-async) Defaulted to `True`.
* \[Optional] `verbose_mode`: a boolean which when set to `True`, prints the intermediate steps used to calculate said metric to the console, as outlined in the [How Is It Calculated](#how-is-it-calculated) section. Defaulted to `False`.
* \[Optional] `evaluation_template`: a class of type `AnswerRelevancyTemplate`, which allows you to [override the default prompts](#customize-your-template) used to compute the `AnswerRelevancyMetric` score. Defaulted to `deepeval`'s `AnswerRelevancyTemplate`.

### Within components [#within-components]

You can also run the `AnswerRelevancyMetric` within nested components for [component-level](/docs/evaluation-component-level-llm-evals) evaluation.

```python
from deepeval.dataset import Golden
from deepeval.tracing import observe, update_current_span
...

@observe(metrics=[metric])
def inner_component():
    # Set test case at runtime
    test_case = LLMTestCase(input="...", actual_output="...")
    update_current_span(test_case=test_case)
    return

@observe
def llm_app(input: str):
    # Component can be anything from an LLM call, retrieval, agent, tool use, etc.
    inner_component()
    return

evaluate(observed_callback=llm_app, goldens=[Golden(input="Hi!")])
```

### As a standalone [#as-a-standalone]

You can also run the `AnswerRelevancyMetric` on a single test case as a standalone, one-off execution.

```python
...

metric.measure(test_case)
print(metric.score, metric.reason)
```

<Callout type="caution">
  This is great for debugging or if you wish to build your own evaluation pipeline, but you will **NOT** get the benefits (testing reports, Confident AI platform) and all the optimizations (speed, caching, computation) the `evaluate()` function or `deepeval test run` offers.
</Callout>

## How Is It Calculated? [#how-is-it-calculated]

The `AnswerRelevancyMetric` score is calculated according to the following equation:

<Equation formula="\text{Answer Relevancy} = \frac{\text{Number of Relevant Statements}}{\text{Total Number of Statements}}" />

The `AnswerRelevancyMetric` first uses an LLM to extract all statements made in the `actual_output`, before using the same LLM to classify whether each statement is relevant to the `input`.

<Callout type="note">
  You can set the `verbose_mode` of **ANY** `deepeval` metric to `True` to debug the `measure()` method:

  ```python
  ...

  metric = AnswerRelevancyMetric(verbose_mode=True)
  metric.measure(test_case)
  ```
</Callout>

## Customize Your Template [#customize-your-template]

Since `deepeval`'s `AnswerRelevancyMetric` is evaluated by LLM-as-a-judge, you can likely improve your metric accuracy by [overriding `deepeval`'s default prompt templates](/docs/metrics-introduction#customizing-metric-prompts). This is especially helpful if:

* You're using a [custom evaluation LLM](/guides/guides-using-custom-llms), especially for smaller models that have weaker instruction following capabilities.
* You want to customize the examples used in the default `AnswerRelevancyTemplate` to better align with your expectations.

<Callout type="tip">
  You can learn what the default `AnswerRelevancyTemplate` looks like [here on GitHub](https://github.com/confident-ai/deepeval/blob/main/deepeval/metrics/answer_relevancy/template.py), and should read the [How Is It Calculated](#how-is-it-calculated) section above to understand how you can tailor it to your needs.
</Callout>

Here's a quick example of how you can override the statement generation step of the `AnswerRelevancyMetric` algorithm:

```python
from deepeval.metrics import AnswerRelevancyMetric
from deepeval.metrics.answer_relevancy import AnswerRelevancyTemplate

# Define custom template
class CustomTemplate(AnswerRelevancyTemplate):
    @staticmethod
    def generate_statements(actual_output: str):
        return f"""Given the text, breakdown and generate a list of statements presented.

Example:
Our new laptop model features a high-resolution Retina display for crystal-clear visuals.

{{
    "statements": [
        "The new laptop model has a high-resolution Retina display."
    ]
}}
===== END OF EXAMPLE ======

Text:
{actual_output}

JSON:
"""

# Inject custom template to metric
metric = AnswerRelevancyMetric(evaluation_template=CustomTemplate)
metric.measure(...)
```
# Contextual Relevancy (/docs/metrics-contextual-relevancy)



<MetricTagsDisplayer singleTurn="true" rag="true" referenceless="true" />

The contextual relevancy metric uses LLM-as-a-judge to measure the quality of your RAG pipeline's retriever by evaluating the overall relevance of the information presented in your `retrieval_context` for a given `input`. `deepeval`'s contextual relevancy metric is a self-explaining LLM-Eval, meaning it outputs a reason for its metric score.

<Callout type="info">
  Not sure if the `ContextualRelevancyMetric` is suitable for your use case? Run the follow command to find out:

  ```bash
  deepeval recommend metrics
  ```
</Callout>

## Required Arguments [#required-arguments]

To use the `ContextualRelevancyMetric`, you'll have to provide the following arguments when creating an [`LLMTestCase`](/docs/evaluation-test-cases#llm-test-case):

* `input`
* `actual_output`
* `retrieval_context`

<Callout type="note">
  Similar to `ContextualPrecisionMetric`, the `ContextualRelevancyMetric` uses `retrieval_context` from your RAG pipeline for evaluation.
</Callout>

Read the [How Is It Calculated](#how-is-it-calculated) section below to learn how test case parameters are used for metric calculation.

## Usage [#usage]

The `ContextualRelevancyMetric()` can be used for [end-to-end](/docs/evaluation-end-to-end-llm-evals) evaluation of text-based and multimodal test cases:

<Tabs items="[&#x22;Text Based&#x22;, &#x22;Multimodal&#x22;]">
  <Tab value="Text Based">
    ```python
    from deepeval import evaluate
    from deepeval.test_case import LLMTestCase
    from deepeval.metrics import ContextualRelevancyMetric

    # Replace this with the actual output from your LLM application
    actual_output = "We offer a 30-day full refund at no extra cost."

    # Replace this with the actual retrieved context from your RAG pipeline
    retrieval_context = ["All customers are eligible for a 30 day full refund at no extra cost."]

    metric = ContextualRelevancyMetric(
        threshold=0.7,
        model="gpt-4.1",
        include_reason=True
    )
    test_case = LLMTestCase(
        input="What if these shoes don't fit?",
        actual_output=actual_output,
        retrieval_context=retrieval_context
    )

    # To run metric as a standalone
    # metric.measure(test_case)
    # print(metric.score, metric.reason)

    evaluate(test_cases=[test_case], metrics=[metric])
    ```
  </Tab>

  <Tab value="Multimodal">
    ```python
    from deepeval import evaluate
    from deepeval.test_case import LLMTestCase, MLLMImage
    from deepeval.metrics import ContextualRelevancyMetric

    # Replace this with the actual retrieved context from your RAG pipeline
    retrieval_context = [
        f"The Eiffel Tower {MLLMImage(...)} is a wrought-iron lattice tower built in the late 19th century.",
        f"...",
    ]

    metric = ContextualRelevancyMetric(
        threshold=0.7,
        model="gpt-4.1",
        include_reason=True
    )
    test_case = LLMTestCase(
        input=f"Tell me about this landmark in France: {MLLMImage(...)}",
        actual_output=f"This appears to be Eiffel Tower, which is a famous landmark in France"
        retrieval_context=retrieval_context
    )

    # To run metric as a standalone
    # metric.measure(test_case)
    # print(metric.score, metric.reason)

    evaluate(test_cases=[test_case], metrics=[metric])
    ```
  </Tab>
</Tabs>

There are **SEVEN** optional parameters when creating a `ContextualRelevancyMetricMetric`:

* \[Optional] `threshold`: a float representing the minimum passing threshold, defaulted to 0.5.
* \[Optional] `model`: a string specifying which of OpenAI's GPT models to use, **OR** [any custom LLM model](/docs/metrics-introduction#using-a-custom-llm) of type `DeepEvalBaseLLM`. Defaulted to <DefaultLLMModel />.
* \[Optional] `include_reason`: a boolean which when set to `True`, will include a reason for its evaluation score. Defaulted to `True`.
* \[Optional] `strict_mode`: a boolean which when set to `True`, enforces a binary metric score: 1 for perfection, 0 otherwise. It also overrides the current threshold and sets it to 1. Defaulted to `False`.
* \[Optional] `async_mode`: a boolean which when set to `True`, enables [concurrent execution within the `measure()` method.](/docs/metrics-introduction#measuring-metrics-in-async) Defaulted to `True`.
* \[Optional] `verbose_mode`: a boolean which when set to `True`, prints the intermediate steps used to calculate said metric to the console, as outlined in the [How Is It Calculated](#how-is-it-calculated) section. Defaulted to `False`.
* \[Optional] `evaluation_template`: a class of type `ContextualRelevancyTemplate`, which allows you to override the default prompt templates used to compute the `ContextualRelevancyMetric` score. You can learn what the default prompts looks like [here](https://github.com/confident-ai/deepeval/blob/main/deepeval/metrics/contextual_relevancy/template.py), and should read the [How Is It Calculated](#how-is-it-calculated) section below to understand how you can tailor it to your needs. Defaulted to `deepeval`'s `ContextualRelevancyTemplate`.

### Within components [#within-components]

You can also run the `ContextualRelevancyMetric` within nested components for [component-level](/docs/evaluation-component-level-llm-evals) evaluation.

```python
from deepeval.dataset import Golden
from deepeval.tracing import observe, update_current_span
...

@observe(metrics=[metric])
def inner_component():
    # Set test case at runtime
    test_case = LLMTestCase(input="...", actual_output="...")
    update_current_span(test_case=test_case)
    return

@observe
def llm_app(input: str):
    # Component can be anything from an LLM call, retrieval, agent, tool use, etc.
    inner_component()
    return

evaluate(observed_callback=llm_app, goldens=[Golden(input="Hi!")])
```

### As a standalone [#as-a-standalone]

You can also run the `ContextualRelevancyMetric` on a single test case as a standalone, one-off execution.

```python
...

metric.measure(test_case)
print(metric.score, metric.reason)
```

<Callout type="caution">
  This is great for debugging or if you wish to build your own evaluation pipeline, but you will **NOT** get the benefits (testing reports, Confident AI platform) and all the optimizations (speed, caching, computation) the `evaluate()` function or `deepeval test run` offers.
</Callout>

## How Is It Calculated? [#how-is-it-calculated]

The `ContextualRelevancyMetric` score is calculated according to the following equation:

<Equation formula="\text{Contextual Relevancy} = \frac{\text{Number of Relevant Statements}}{\text{Total Number of Statements}}" />

Although similar to how the `AnswerRelevancyMetric` is calculated, the `ContextualRelevancyMetric` first uses an LLM to extract all statements made in the `retrieval_context` instead, before using the same LLM to classify whether each statement is relevant to the `input`.

## Customize Your Template [#customize-your-template]

Since `deepeval`'s `ContextualRelevancyMetric` is evaluated by LLM-as-a-judge, you can likely improve your metric accuracy by [overriding `deepeval`'s default prompt templates](/docs/metrics-introduction#customizing-metric-prompts). This is especially helpful if:

* You're using a [custom evaluation LLM](/guides/guides-using-custom-llms), especially for smaller models that have weaker instruction following capabilities.
* You want to customize the examples used in the default `ContextualRelevancyTemplate` to better align with your expectations.

<Callout type="tip">
  You can learn what the default `ContextualRelevancyTemplate` looks like [here on GitHub](https://github.com/confident-ai/deepeval/blob/main/deepeval/metrics/contextual_relevancy/template.py), and should read the [How Is It Calculated](#how-is-it-calculated) section above to understand how you can tailor it to your needs.
</Callout>

Here's a quick example of how you can override the relevancy classification step of the `ContextualRelevancyMetric` algorithm:

```python
from deepeval.metrics import ContextualRelevancyMetric
from deepeval.metrics.contextual_relevancy import ContextualRelevancyTemplate

# Define custom template
class CustomTemplate(ContextualRelevancyTemplate):
    @staticmethod
    def generate_verdicts(input: str, context: str):
        return f"""Based on the input and context, please generate a JSON object to indicate whether each statement found in the context is relevant to the provided input.

Example JSON:
{{
    "verdicts": [
        {{
            "verdict": "yes",
            "statement": "...",
        }}
    ]
}}
**

Input:
{input}

Context:
{context}

JSON:
"""

# Inject custom template to metric
metric = ContextualRelevancyMetric(evaluation_template=CustomTemplate)
metric.measure(...)
```

# Tool Correctness (/docs/metrics-tool-correctness)



<MetricTagsDisplayer singleTurn="true" usesLLMs="true" agent="true" referenceless="true" />

The tool correctness metric is an agentic LLM metric that assesses your LLM agent's function/tool calling ability. It is calculated by comparing whether every tool that is expected to be used was indeed called and if the selection of the tools made by the LLM agent were the most optimal.

<Callout type="note">
  The `ToolCorrectnessMetric` allows you to define the **strictness** of correctness. By default, it considers matching tool names to be correct, but you can also require input parameters and output to match.
</Callout>

## Required Arguments [#required-arguments]

To use the `ToolCorrectnessMetric`, you'll have to provide the following arguments when creating an [`LLMTestCase`](/docs/evaluation-test-cases#llm-test-case):

* `input`
* `actual_output`
* `tools_called`
* `expected_tools`

Read the [How Is It Calculated](#how-is-it-calculated) section below to learn how test case parameters are used for metric calculation.

## Usage [#usage]

The `ToolCorrectnessMetric()` can be used for [end-to-end](/docs/evaluation-end-to-end-llm-evals) evaluation of text-based and multimodal test cases:

<Tabs items="[&#x22;Text Based&#x22;, &#x22;Multimodal&#x22;]">
  <Tab value="Text Based">
    ```python
    from deepeval import evaluate
    from deepeval.test_case import LLMTestCase, ToolCall
    from deepeval.metrics import ToolCorrectnessMetric

    test_case = LLMTestCase(
        input="What if these shoes don't fit?",
        actual_output="We offer a 30-day full refund at no extra cost.",
        # Replace this with the tools that was actually used by your LLM agent
        tools_called=[ToolCall(name="WebSearch"), ToolCall(name="ToolQuery")],
        expected_tools=[ToolCall(name="WebSearch")],
    )
    metric = ToolCorrectnessMetric()

    # To run metric as a standalone
    # metric.measure(test_case)
    # print(metric.score, metric.reason)

    evaluate(test_cases=[test_case], metrics=[metric])
    ```
  </Tab>

  <Tab value="Multimodal">
    ```python
    from deepeval import evaluate
    from deepeval.test_case import LLMTestCase, MLLMImage
    from deepeval.metrics import ToolCorrectnessMetric

    metric = ToolCorrectnessMetric(
        threshold=0.7,
        model="gpt-4.1",
        include_reason=True
    )
    test_case = LLMTestCase(
        input=f"What's in this image? {MLLMImage(...)}",
        actual_output=f"The image shows a pair of running shoes."
        tools_called=[ToolCall(name="ImageAnalysis"), ToolCall(name="ToolQuery")],
        expected_tools=[ToolCall(name="ImageAnalysis")],
    )

    # To run metric as a standalone
    # metric.measure(test_case)
    # print(metric.score, metric.reason)

    evaluate(test_cases=[test_case], metrics=[metric])
    ```
  </Tab>
</Tabs>

There are **EIGHT** optional parameters when creating a `ToolCorrectnessMetric`:

* \[Optional] `available_tools`: a list of `ToolCall`s that give context on all the tools that were available to your LLM agent. This list is used to evaluate your agent's tool selection capability.
* \[Optional] `threshold`: a float representing the minimum passing threshold, defaulted to 0.5.
* \[Optional] `evaluation_params`: A list of `ToolCallParams` indicating the strictness of the correctness criteria, available options are `ToolCallParams.INPUT_PARAMETERS` and `ToolCallParams.OUTPUT`. For example, supplying a list containing `ToolCallParams.INPUT_PARAMETERS` but excluding `ToolCallParams.OUTPUT`, will deem a tool correct if the tool name and input parameters match, even if the output does not. Defaults to a an empty list.
* \[Optional] `include_reason`: a boolean which when set to `True`, will include a reason for its evaluation score. Defaulted to `True`.
* \[Optional] `strict_mode`: a boolean which when set to `True`, enforces a binary metric score: 1 for perfection, 0 otherwise. It also overrides the current threshold and sets it to 1. Defaulted to `False`.
* \[Optional] `verbose_mode`: a boolean which when set to `True`, prints the intermediate steps used to calculate said metric to the console, as outlined in the [How Is It Calculated](#how-is-it-calculated) section. Defaulted to `False`.
* \[Optional] `should_consider_ordering`: a boolean which when set to `True`, will consider the ordering in which the tools were called in. For example, if `expected_tools=[ToolCall(name="WebSearch"), ToolCall(name="ToolQuery"), ToolCall(name="WebSearch")]` and `tools_called=[ToolCall(name="WebSearch"), ToolCall(name="WebSearch"),  ToolCall(name="ToolQuery")]`, the metric will consider the tool calling to be correct. Only available for `ToolCallParams.TOOL` and defaulted to `False`.
* \[Optional] `should_exact_match`: a boolean which when set to `True`, will required the `tools_called` and `expected_tools` to be exactly the same. Available for `ToolCallParams.TOOL` and `ToolCallParams.INPUT_PARAMETERS` and Defaulted to `False`.

<Callout type="info">
  Since `should_exact_match` is a stricter criteria than `should_consider_ordering`, setting `should_consider_ordering` will have no effect when `should_exact_match` is set to `True`.
</Callout>

### Within components [#within-components]

You can also run the `ToolCorrectnessMetric` within nested components for [component-level](/docs/evaluation-component-level-llm-evals) evaluation.

```python
from deepeval.dataset import Golden
from deepeval.tracing import observe, update_current_span
...

@observe(metrics=[metric])
def inner_component():
    # Set test case at runtime
    test_case = LLMTestCase(input="...", actual_output="...")
    update_current_span(test_case=test_case)
    return

@observe
def llm_app(input: str):
    # Component can be anything from an LLM call, retrieval, agent, tool use, etc.
    inner_component()
    return

evaluate(observed_callback=llm_app, goldens=[Golden(input="Hi!")])
```

### As a standalone [#as-a-standalone]

You can also run the `ToolCorrectnessMetric` on a single test case as a standalone, one-off execution.

```python
...

metric.measure(test_case)
print(metric.score, metric.reason)
```

<Callout type="caution">
  This is great for debugging or if you wish to build your own evaluation pipeline, but you will **NOT** get the benefits (testing reports, Confident AI platform) and all the optimizations (speed, caching, computation) the `evaluate()` function or `deepeval test run` offers.
</Callout>

## How Is It Calculated? [#how-is-it-calculated]

<Callout type="note">
  The `ToolCorrectnessMetric`, unlike all other `deepeval` metrics, uses both deterministic and non-deterministic evaluation to give a final score. It uses `tools_called`, `expected_tools` and `available_tools` to find the final score.
</Callout>

The **tool correctness metric** score is calculated using the following steps:

1. Find the deterministic score for `tools_called` using the `expected_tools` using the following equation:

<Equation
  formula="\text{Tool Correctness} = \frac{\text{Number of Correctly Used Tools (or Correct Input Parameters/Outputs)}}{\text{Total Number of Tools Called}}
"
/>

* This metric assesses the accuracy of your agent's tool usage by comparing the `tools_called` by your LLM agent to the list of `expected_tools`. A score of 1 indicates that every tool utilized by your LLM agent were called correctly according to the list of `expected_tools`, `should_consider_ordering`, and `should_exact_match`, while a score of 0 signifies that none of the `tools_called` were called correctly.

<Callout type="info">
  If `exact_match` is not specified and `ToolCall.INPUT_PARAMETERS` is included in `evaluation_params`, correctness may be a percentage score based on the proportion of correct input parameters (assuming the name and output are correct, if applicable).
</Callout>

2. If the `available_tools` are provided, the `ToolCorrectnessMetric` also uses an LLM to find whether the `tools_called` were the most optimal for the given task using the `available_tools` as reference. The final score is the **minimum of both scores**. If `available_tools` is not provided, the LLM-based evaluation does not take place.

# Argument Correctness (/docs/metrics-argument-correctness)



<MetricTagsDisplayer singleTurn="true" usesLLMs="true" agent="true" referenceless="true" />

The argument correctness metric is an agentic LLM metric that assesses your LLM agent's ability to generate the correct arguments for the tools it calls. It is calculated by determining whether the arguments for each tool call is correct based on the input.

<Callout type="info">
  The `ArgumentCorrectnessMetric` uses an LLM to determine argument correctness, and is also referenceless. If you're looking to determistically evaluate argument correctness, refer to the [tool correctness metric](/docs/metrics-tool-correctness) instead.
</Callout>

## Required Arguments [#required-arguments]

To use the `ArgumentCorrectnessMetric`, you'll have to provide the following arguments when creating an [`LLMTestCase`](/docs/evaluation-test-cases#llm-test-case):

* `input`
* `actual_output`
* `tools_called`

Read the [How Is It Calculated](#how-is-it-calculated) section below to learn how test case parameters are used for metric calculation.

## Usage [#usage]

The `ArgumentCorrectnessMetric()` can be used for [end-to-end](/docs/evaluation-end-to-end-llm-evals) evaluation:

```python
from deepeval import evaluate
from deepeval.metrics import ArgumentCorrectnessMetric
from deepeval.test_case import LLMTestCase, ToolCall

metric = ArgumentCorrectnessMetric(
    threshold=0.7,
    model="gpt-4",
    include_reason=True
)
test_case = LLMTestCase(
    input="When did Trump first raise tariffs?",
    actual_output="Trump first raised tariffs in 2018 during the U.S.-China trade war.",
    tools_called=[
        ToolCall(
            name="WebSearch Tool",
            description="Tool to search for information on the web.",
            input={"search_query": "Trump first raised tariffs year"}
        ),
        ToolCall(
            name="History FunFact Tool",
            description="Tool to provide a fun fact about the topic.",
            input={"topic": "Trump tariffs"}
        )
    ]
)

# To run metric as a standalone
# metric.measure(test_case)
# print(metric.score, metric.reason)

evaluate(test_cases=[test_case], metrics=[metric])
```

There are **SIX** optional parameters when creating an `ArgumentCorrectnessMetric`:

* \[Optional] `threshold`: a float representing the minimum passing threshold, defaulted to 0.5.
* \[Optional] `model`: a string specifying which of OpenAI's GPT models to use, **OR** [any custom LLM model](/docs/metrics-introduction#using-a-custom-llm) of type `DeepEvalBaseLLM`. Defaulted to <DefaultLLMModel />.
* \[Optional] `include_reason`: a boolean which when set to `True`, will include a reason for its evaluation score. Defaulted to `True`.
* \[Optional] `strict_mode`: a boolean which when set to `True`, enforces a binary metric score: 1 for perfection, 0 otherwise. It also overrides the current threshold and sets it to 1. Defaulted to `False`.
* \[Optional] `async_mode`: a boolean which when set to `True`, enables [concurrent execution within the `measure()` method.](/docs/metrics-introduction#measuring-a-metric-in-async) Defaulted to `True`.
* \[Optional] `verbose_mode`: a boolean which when set to `True`, prints the intermediate steps used to calculate said metric to the console, as outlined in the [How Is It Calculated](#how-is-it-calculated) section. Defaulted to `False`.

### Within components [#within-components]

You can also run the `ArgumentCorrectnessMetric` within nested components for [component-level](/docs/evaluation-component-level-llm-evals) evaluation.

```python
from deepeval.dataset import Golden
from deepeval.tracing import observe, update_current_span
...

@observe(metrics=[metric])
def inner_component():
    # Set test case at runtime
    test_case = LLMTestCase(input="...", actual_output="...", tools_called=[...])
    update_current_span(test_case=test_case)
    return

@observe
def llm_app(input: str):
    # Component can be anything from an LLM call, retrieval, agent, tool use, etc.
    inner_component()
    return

evaluate(observed_callback=llm_app, goldens=[Golden(input="Hi!")])
```

### As a standalone [#as-a-standalone]

You can also run the `ArgumentCorrectnessMetric` on a single test case as a standalone, one-off execution.

```python
...

metric.measure(test_case)
print(metric.score, metric.reason)
```

<Callout type="caution">
  This is great for debugging or if you wish to build your own evaluation pipeline, but you will **NOT** get the benefits (testing reports, Confident AI platform) and all the optimizations (speed, caching, computation) the `evaluate()` function or `deepeval test run` offers.
</Callout>

## How Is It Calculated? [#how-is-it-calculated]

The `ArgumentCorrectnessMetric` score is calculated according to the following equation:

<Equation formula="\text{Argument Correctness} = \frac{\text{Number of Correctly Generated Input Parameters}}{\text{Total Number of Tool Calls}}" />

The `ArgumentCorrectnessMetric` assesses the correctness of the arguments (input parameters) for each tool call, based on the task outlined in the input.

<Callout type="note">
  You can set the `verbose_mode` of **ANY** `deepeval` metric to `True` to debug the `measure()` method:

  ```python
  ...

  metric = ArgumentCorrectnessMetric(verbose_mode=True)
  metric.measure(test_case)
  ```
</Callout>

# Exact Match (/docs/metrics-exact-match)



<MetricTagsDisplayer singleTurn="true" usesLLMs="false" referenceless="false" />

The Exact Match metric measures whether your LLM application's `actual_output` matches the `expected_output` exactly.

<Callout type="note">
  The `ExactMatchMetric` does **not** rely on an LLM for evaluation. It purely performs a **string-level equality check** between the outputs.
</Callout>

## Required Arguments [#required-arguments]

To use the `ExactMatchMetric`, you'll have to provide the following arguments when creating an [`LLMTestCase`](/docs/evaluation-test-cases#llm-test-case):

* `input`
* `actual_output`
* `expected_output`

Read the [How Is It Calculated](#how-is-it-calculated) section below to learn how test case parameters are used for metric calculation.

## Usage [#usage]

```python
from deepeval import evaluate
from deepeval.metrics import ExactMatchMetric
from deepeval.test_case import LLMTestCase

metric = ExactMatchMetric(
    threshold=1.0,
    verbose_mode=True,
)

test_case = LLMTestCase(
    input="Translate 'Hello, how are you?' in french",
    actual_output="Bonjour, comment ça va ?",
    expected_output="Bonjour, comment allez-vous ?"
)

# To run metric as a standalone
# metric.measure(test_case)
# print(metric.score, metric.reason)

evaluate(test_cases=[test_case], metrics=[metric])
```

There are **TWO** optional parameters when creating an `ExactMatchMetric`:

* \[Optional] `threshold`: a float representing the minimum passing threshold, defaulted to 1.0.
* \[Optional] `verbose_mode`: a boolean which when set to `True`, prints the intermediate steps used to calculate said metric to the console, as outlined in the [How Is It Calculated](#how-is-it-calculated) section. Defaulted to `False`.

### As a Standalone [#as-a-standalone]

You can also run the `ExactMatchMetric` on a single test case as a standalone, one-off execution.

```python
...

metric.measure(test_case)
print(metric.score, metric.reason)
```

## How Is It Calculated? [#how-is-it-calculated]

The `ExactMatchMetric` score is calculated according to the following equation:

<Equation
  formula="\text{Exact Match Score} =
\begin{cases}
1 & \text{if actual\_output = expected\_output}, \\
0 & \text{otherwise}
\end{cases}"
/>

The `ExactMatchMetric` performs a strict equality check to determine if the `actual_output` matches the `expected_output`.

# CLI Settings (/docs/command-line-interface)



## Quick Summary [#quick-summary]

`deepeval` provides a CLI for managing common tasks directly from the terminal. You can use it for:

* Logging in/out and viewing test runs
* Running evaluations from test files
* Generating synthetic goldens from docs, contexts, scratch, or existing goldens
* Enabling/disabling debug
* Selecting an LLM/embeddings provider (OpenAI, Azure OpenAI, Gemini, Grok, DeepSeek, LiteLLM, local/Ollama)
* Setting/unsetting provider-specific options (model, endpoint, deployment, etc.)
* Listing and updating any deepeval setting (`deepeval settings -l`, `deepeval settings --set KEY=VALUE`)
* Saving settings and secrets persistently to `.env` files

<Callout type="tip">
  For the full and most up-to-date list of flags for any command, run `deepeval <command> --help`.
</Callout>

## Install & Update [#install--update]

```bash
pip install -U deepeval
```

To review available commands consult the CLI built in help:

```bash
deepeval --help
```

## Read & Write Settings [#read--write-settings]

deepeval reads settings from dotenv files in the current working directory (or `ENV_DIR_PATH=/path/to/project`), without overriding existing process environment variables. Dotenv precedence (lowest → highest) is: `.env` → `.env.<APP_ENV>` → `.env.local`.

deepeval also uses a legacy JSON keystore at `.deepeval/.deepeval` for **non-secret** keys. This keystore is treated as a fallback (dotenv/process env take precedence). Secrets are never written to the JSON keystore.

<Callout type="tip">
  To disable dotenv autoloading (useful in pytest/CI to avoid loading local `.env*` files on import), set `DEEPEVAL_DISABLE_DOTENV=1`.
</Callout>

## Core Commands [#core-commands]

### `generate` [#generate]

Use `deepeval generate` to generate synthetic goldens from the terminal with the Golden Synthesizer. The command requires two selectors:

* `--method`: where goldens come from: `docs`, `contexts`, `scratch`, or `goldens`
* `--variation`: what to generate: `single-turn` or `multi-turn`

Generate single-turn goldens from documents:

```bash
deepeval generate \
  --method docs \
  --variation single-turn \
  --documents example.txt \
  --documents another.pdf \
  --output-dir ./synthetic_data
```

Generate multi-turn goldens from scratch:

```bash
deepeval generate \
  --method scratch \
  --variation multi-turn \
  --num-goldens 25 \
  --scenario-context "Users asking support questions" \
  --conversational-task "Help users solve product issues" \
  --participant-roles "User and assistant"
```

Common options:

| Option                                       | Description                                                                  |
| -------------------------------------------- | ---------------------------------------------------------------------------- |
| `--method docs\|contexts\|scratch\|goldens`  | Select the generation method.                                                |
| `--variation single-turn\|multi-turn`        | Select whether to generate `Golden`s or `ConversationalGolden`s.             |
| `--output-dir`                               | Directory where generated goldens are saved. Defaults to `./synthetic_data`. |
| `--file-type json\|csv\|jsonl`               | Output file type. Defaults to `json`.                                        |
| `--file-name`                                | Optional output filename without extension.                                  |
| `--model`                                    | Model to use for generation.                                                 |
| `--async-mode / --sync-mode`                 | Enable or disable concurrent generation.                                     |
| `--max-concurrent`                           | Maximum number of concurrent generation tasks.                               |
| `--include-expected / --no-include-expected` | Generate or skip expected outputs/outcomes.                                  |
| `--cost-tracking`                            | Print generation cost when supported by the model.                           |

Method-specific options:

| Method     | Required Options                     | Useful Optional Options                                                                                                                                                                                               |
| ---------- | ------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `docs`     | `--documents`                        | `--max-goldens-per-context`, `--max-contexts-per-document`, `--min-contexts-per-document`, `--chunk-size`, `--chunk-overlap`, `--context-quality-threshold`, `--context-similarity-threshold`, `--max-retries`        |
| `contexts` | `--contexts-file`                    | `--max-goldens-per-context`                                                                                                                                                                                           |
| `scratch`  | `--num-goldens` plus styling options | Single-turn: `--scenario`, `--task`, `--input-format`, `--expected-output-format`. Multi-turn: `--scenario-context`, `--conversational-task`, `--participant-roles`, `--scenario-format`, `--expected-outcome-format` |
| `goldens`  | `--goldens-file`                     | `--max-goldens-per-golden`                                                                                                                                                                                            |

For a deeper walkthrough, see the [Golden Synthesizer](/docs/golden-synthesizer#generate-goldens-from-the-cli) docs.

### `test` [#test]

Use `deepeval test run` to run evaluation test files through `pytest` with the `deepeval` pytest plugin enabled.

```bash
deepeval test --help
deepeval test run --help
```

Run a single test file:

```bash
deepeval test run test_chatbot.py
```

Run a test directory:

```bash
deepeval test run tests/evals
```

Run a specific test:

```bash
deepeval test run test_chatbot.py::test_answer_relevancy
```

Useful options:

| Option                           | Description                                                    |
| -------------------------------- | -------------------------------------------------------------- |
| `--verbose`, `-v`                | Show verbose pytest output and turn on deepeval verbose mode.  |
| `--exit-on-first-failure`, `-x`  | Stop after the first failed test.                              |
| `--show-warnings`, `-w`          | Show pytest warnings instead of disabling them.                |
| `--identifier`, `-id`            | Attach an identifier to the test run.                          |
| `--num-processes`, `-n`          | Run tests with multiple pytest-xdist processes.                |
| `--repeat`, `-r`                 | Rerun each test case the specified number of times.            |
| `--use-cache`, `-c`              | Use cached evaluation results when `--repeat` is not set.      |
| `--ignore-errors`, `-i`          | Continue when deepeval evaluation errors occur.                |
| `--skip-on-missing-params`, `-s` | Skip test cases with missing metric parameters.                |
| `--display`, `-d`                | Control final result display. Defaults to showing all results. |
| `--mark`, `-m`                   | Run tests matching a pytest marker expression.                 |

You can pass additional pytest flags after the `deepeval` options. For example:

```bash
deepeval test run tests/evals \
  --mark "not slow" \
  --exit-on-first-failure \
  -- --tb=short
```

## Confident AI Commands [#confident-ai-commands]

Use these commands to connect `deepeval` to **Confident AI** (`deepeval` Cloud) so your local evaluations can be uploaded, organized, and viewed as rich test run reports on the cloud. If you don’t have an account yet, [sign up here](https://app.confident-ai.com).

### `login` & `logout` [#login--logout]

* `deepeval login [--confident-api-key ...] [--save=dotenv[:path]]`: Log in to Confident AI by saving your `CONFIDENT_API_KEY`. Once logged in, `deepeval` can automatically upload test runs so you can browse results, share reports, and track evaluation performance over time on Confident AI.
* `deepeval logout [--save=dotenv[:path]]`: Remove your Confident AI credentials from local persistence (JSON keystore and the chosen dotenv file).

### `view` [#view]

* `deepeval view`: Opens the latest test run on Confident AI in your browser. If needed, it uploads the cached run artifacts first.

## Persistence & Secrets [#persistence--secrets]

All `set-*` / `unset-*` commands follow the same rules:

* Non-secrets (model name, endpoint, deployment, etc.) may be mirrored into `.deepeval/.deepeval`.
* Secrets (API keys) are never written to `.deepeval/.deepeval`.
* Pass `--save=dotenv[:path]` to write settings (including secrets) to a dotenv file (default: `.env.local`).
* If `--save` is omitted, deepeval will use `DEEPEVAL_DEFAULT_SAVE` if set; otherwise it won’t write a dotenv file (some commands like `login` still default to `.env.local`).
* Unsetting one provider only removes that provider’s keys. If other provider credentials remain (e.g. `OPENAI_API_KEY`), they may still be selected by default.

<Callout type="tip">
  You can set a default save target via `DEEPEVAL_DEFAULT_SAVE=dotenv:.env.local` so you don’t have to pass `--save` each time.
</Callout>

<Callout type="info">
  Token costs are expressed in **USD per token*&#x2A;. If you're using published pricing in **\$/MTok** (million tokens), divide by **1,000,000*&#x2A;.
  For example, **\$3 / MTok = 0.000003**.
</Callout>

To set the model and token cost for Anthropic you would run:

```bash
deepeval set-anthropic -m claude-3-7-sonnet-latest -i 0.000003 -o 0.000015 --save=dotenv
Saved environment variables to .env.local (ensure it's git-ignored).
🙌 Congratulations! You're now using Anthropic `claude-3-7-sonnet-latest` for all evals that require an LLM.
```

To view your settings for Anthropic you would run:

```bash
deepeval settings -l anthropic
                                                                                Settings
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name                            ┃ Value                    ┃ Description                                                                                      ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ ANTHROPIC_API_KEY               │ ********                 │ Anthropic API key.                                                                               │
│ ANTHROPIC_COST_PER_INPUT_TOKEN  │ 3e-06                    │ Anthropic input token cost (used for cost reporting).                                            │
│ ANTHROPIC_COST_PER_OUTPUT_TOKEN │ 1.5e-05                  │ Anthropic output token cost (used for cost reporting).                                           │
│ ANTHROPIC_MODEL_NAME            │ claude-3-7-sonnet-latest │ Anthropic model name (e.g. 'claude-3-...').                                                      │
│ USE_ANTHROPIC_MODEL             │ True                     │ Select Anthropic as the active LLM provider (USE_* flags are mutually exclusive in CLI helpers). │
└─────────────────────────────────┴──────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Debug Controls [#debug-controls]

Use these to turn on structured logs, gRPC wire tracing, and Confident tracing (all optional).

```bash
deepeval set-debug \
  --log-level DEBUG \
  --debug-async \
  --retry-before-level INFO \
  --retry-after-level ERROR \
  --grpc --grpc-verbosity DEBUG --grpc-trace list_tracers \
  --trace-verbose --trace-env staging --trace-flush \
  --save=dotenv
```

* **Immediate effect** in the current process
* **Optional persistence** via `--save=dotenv[:path]`
* **No-op guard**: If nothing would change, you’ll see &#x2A;*No changes to save …** (and nothing is written).

<Callout type="info">
  To see all available debug flags, run `deepeval set-debug --help`.
</Callout>

<Callout type="tip">
  To filter (substring match) settings by name displaying each setting's current value and description run:

  ```bash
  deepeval settings -l log-level
                                                              Settings
  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
  ┃ Name                            ┃ Value ┃ Description                                                                  ┃
  ┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
  │ DEEPEVAL_RETRY_AFTER_LOG_LEVEL  │ 20    │ Log level for 'after retry' logs (defaults to ERROR).                        │
  │ DEEPEVAL_RETRY_BEFORE_LOG_LEVEL │ 20    │ Log level for 'before retry' logs (defaults to LOG_LEVEL if set, else INFO). │
  │ LOG_LEVEL                       │ 40    │ Global logging level (e.g. DEBUG/INFO/WARNING/ERROR/CRITICAL or numeric).    │
  └─────────────────────────────────┴───────┴──────────────────────────────────────────────────────────────────────────────┘
  ```
</Callout>

To restore defaults and clean persisted values:

```bash
deepeval unset-debug --save=dotenv
```

## Model Provider Configs [#model-provider-configs]

All provider commands come in pairs:

* `deepeval set-<provider> [provider-specific flags] [--save=dotenv[:path]] [--quiet]`
* `deepeval unset-<provider> [--save=dotenv[:path]] [--quiet]`

This switches the active provider:

* It sets `USE_<PROVIDER>_MODEL = True` for the chosen provider, and
* Turns all other `USE_*` flags off so that only one provider is enabled at a time.

When you **set** a provider, the CLI enables that provider’s `USE_<PROVIDER>_MODEL` flag and disables all other `USE_*` flags. When you **unset** a provider, it disables only that provider’s `USE_*` flag and leaves all others untouched. If you manually set env vars (or edit dotenv files) it’s possible to end up with multiple `USE_*` flags enabled.

<Callout type="caution">
  Because of how `deepeval` manages your model related environment variables, &#x2A;*using the CLI is 100% the recommended way to configure evaluation models in `deepeval`.** It handles all the necessary environment variables for you, ensuring consistent and correct setup across different providers.

  If you want to see what environment variables `deepeval` manages under the hood, refer to the [Model Settings](/docs/environment-variables#model-settings) documentation.
</Callout>

### Full model list [#full-model-list]

| Provider (LLM)   | Set                | Unset                |
| ---------------- | ------------------ | -------------------- |
| OpenAI           | `set-openai`       | `unset-openai`       |
| Azure OpenAI     | `set-azure-openai` | `unset-azure-openai` |
| Anthropic        | `set-anthropic`    | `unset-anthropic`    |
| AWS Bedrock      | `set-bedrock`      | `unset-bedrock`      |
| Ollama (local)   | `set-ollama`       | `unset-ollama`       |
| Local HTTP model | `set-local-model`  | `unset-local-model`  |
| Grok             | `set-grok`         | `unset-grok`         |
| Moonshot (Kimi)  | `set-moonshot`     | `unset-moonshot`     |
| DeepSeek         | `set-deepseek`     | `unset-deepseek`     |
| Gemini           | `set-gemini`       | `unset-gemini`       |
| LiteLLM          | `set-litellm`      | `unset-litellm`      |
| Portkey          | `set-portkey`      | `unset-portkey`      |

**Embeddings:**

| Provider (Embeddings) | Set                          | Unset                          |
| --------------------- | ---------------------------- | ------------------------------ |
| Azure OpenAI          | `set-azure-openai-embedding` | `unset-azure-openai-embedding` |
| Local (HTTP)          | `set-local-embeddings`       | `unset-local-embeddings`       |
| Ollama                | `set-ollama-embeddings`      | `unset-ollama-embeddings`      |

<Callout type="tip">
  For provider-specific flags, run `deepeval set-<provider> --help`.
</Callout>

## Common Issues [#common-issues]

* **Nothing printed?** For `set-*` / `unset-*` / `set-debug`, a clean exit with no output often means you are passing the `--quiet` / `-q` flag.
* **Provider still active after unsetting?** Unsetting turns off target provider `USE_*` flags; if a provider remains enabled and properly configured it will become the active provider. If no provider is enabled, but OpenAI credentials are present, OpenAI may be used as a fallback. To force a provider, run the corresponding `set-<provider>` command.
* **Dotenv edits not picked up?** deepeval loads dotenv files from the current working directory by default, or `ENV_DIR_PATH` if set. Ensure your Python process runs in that context.

If you’re still stuck, the dedicated [Troubleshooting](/docs/troubleshooting) page covers deeper debugging (TLS errors, logging, timeouts, dotenv loading, and config caching).

# Environment Variables (/docs/environment-variables)



`deepeval` automatically loads environment variables from dotenv files in this order: `.env` → `.env.{APP_ENV}` → `.env.local` (highest precedence). Existing process environment variables are never overwritten—process env always wins.

## Boolean flags [#boolean-flags]

Boolean environment variables in `deepeval` are parsed using env-style boolean semantics. Tokens are case-insensitive and any surrounding quotes or whitespace is ignored.

* **Truthy tokens**:
  `1`, `true`, `t`, `yes`, `y`, `on`, `enable`, `enabled`
* **Falsy tokens**:
  `0`, `false`, `f`, `no`, `n`, `off`, `disable`, `disabled`

Rules:

* `bool` values are used as-is.
* Numeric values are `False` when `0`, otherwise `True`.
* Strings are matched against the tokens above.
* If a value is **unset** (or doesn't match any token), `deepeval` falls back to the setting's default.

In the tables below, boolean variables are shown as `1` / `0` / `unset`, but all of the tokens above are accepted.

## General Settings [#general-settings]

These are the core settings for controlling `deepeval`'s behavior, file paths, and run identifiers.

| Variable                          | Values                  | Effect                                                                                                                             |
| --------------------------------- | ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `CONFIDENT_API_KEY`               | `string` / unset        | Logs in to Confident AI. Enables tracing observability, and automatically upload test results to the cloud on evaluation complete. |
| `DEEPEVAL_DISABLE_DOTENV`         | `1` / `0` / `unset`     | Disable dotenv autoload at import.                                                                                                 |
| `ENV_DIR_PATH`                    | `path` / unset          | Directory containing `.env` files (defaults to CWD when unset).                                                                    |
| `APP_ENV`                         | `string` / unset        | When set, loads `.env.{APP_ENV}` between `.env` and `.env.local`.                                                                  |
| `DEEPEVAL_DISABLE_LEGACY_KEYFILE` | `1` / `0` / `unset`     | Disable reading legacy `.deepeval/.deepeval` JSON keystore into env.                                                               |
| `DEEPEVAL_DEFAULT_SAVE`           | `dotenv[:path]` / unset | Default persistence target for `deepeval set-* --save` when `--save` is omitted.                                                   |
| `DEEPEVAL_FILE_SYSTEM`            | `READ_ONLY` / unset     | Restrict file writes in constrained environments.                                                                                  |
| `DEEPEVAL_RESULTS_FOLDER`         | `path` / unset          | Export a timestamped JSON of the latest test run into this directory (created if needed).                                          |
| `DEEPEVAL_IDENTIFIER`             | `string` / unset        | Default identifier for runs (same idea as `deepeval test run -id ...`).                                                            |

## Display / Truncation [#display--truncation]

These settings control output verbosity and text truncation in logs and displays.

| Variable                          | Values              | Effect                                                                                                     |
| --------------------------------- | ------------------- | ---------------------------------------------------------------------------------------------------------- |
| `DEEPEVAL_MAXLEN_TINY`            | `int`               | Max length used for "tiny" shorteners (default: 40).                                                       |
| `DEEPEVAL_MAXLEN_SHORT`           | `int`               | Max length used for "short" shorteners (default: 60).                                                      |
| `DEEPEVAL_MAXLEN_MEDIUM`          | `int`               | Max length used for "medium" shorteners (default: 120).                                                    |
| `DEEPEVAL_MAXLEN_LONG`            | `int`               | Max length used for "long" shorteners (default: 240).                                                      |
| `DEEPEVAL_SHORTEN_DEFAULT_MAXLEN` | `int` / unset       | Overrides the default max length used by `shorten(...)` (falls back to `DEEPEVAL_MAXLEN_LONG` when unset). |
| `DEEPEVAL_SHORTEN_SUFFIX`         | `string`            | Suffix used by `shorten(...)` (default: `...`).                                                            |
| `DEEPEVAL_VERBOSE_MODE`           | `1` / `0` / `unset` | Enable verbose mode globally (where supported).                                                            |
| `DEEPEVAL_LOG_STACK_TRACES`       | `1` / `0` / `unset` | Log stack traces for errors (where supported).                                                             |

## Retry / Backoff Tuning [#retry--backoff-tuning]

These settings control retry and backoff behavior for API calls.

| Variable                          | Type           | Default                                                                             | Notes                         |
| --------------------------------- | -------------- | ----------------------------------------------------------------------------------- | ----------------------------- |
| `DEEPEVAL_RETRY_MAX_ATTEMPTS`     | `int`          | `2`                                                                                 | Total attempts (1 retry)      |
| `DEEPEVAL_RETRY_INITIAL_SECONDS`  | `float`        | `1.0`                                                                               | Initial backoff               |
| `DEEPEVAL_RETRY_EXP_BASE`         | `float`        | `2.0`                                                                               | Exponential base (≥ 1)        |
| `DEEPEVAL_RETRY_JITTER`           | `float`        | `2.0`                                                                               | Random jitter added per retry |
| `DEEPEVAL_RETRY_CAP_SECONDS`      | `float`        | `5.0`                                                                               | Max sleep between retries     |
| `DEEPEVAL_SDK_RETRY_PROVIDERS`    | `list` / unset | Provider slugs for which retries are delegated to provider SDKs (supports `["*"]`). |                               |
| `DEEPEVAL_RETRY_BEFORE_LOG_LEVEL` | `int` / unset  | Log level for "before retry" logs (defaults to `LOG_LEVEL` if set, else INFO).      |                               |
| `DEEPEVAL_RETRY_AFTER_LOG_LEVEL`  | `int` / unset  | Log level for "after retry" logs (defaults to ERROR).                               |                               |

## Timeouts / Concurrency [#timeouts--concurrency]

These options let you tune timeout limits and concurrency for parallel execution and provider calls.

| Variable                                        | Values             | Effect                                                                                      |
| ----------------------------------------------- | ------------------ | ------------------------------------------------------------------------------------------- |
| `DEEPEVAL_MAX_CONCURRENT_DOC_PROCESSING`        | `int`              | Max concurrent document processing tasks (default: 2).                                      |
| `DEEPEVAL_TIMEOUT_THREAD_LIMIT`                 | `int`              | Max threads used by timeout machinery (default: 128).                                       |
| `DEEPEVAL_TIMEOUT_SEMAPHORE_WARN_AFTER_SECONDS` | `float`            | Warn if acquiring timeout semaphore takes too long (default: 5.0).                          |
| `DEEPEVAL_PER_ATTEMPT_TIMEOUT_SECONDS_OVERRIDE` | `float` / unset    | Per-attempt timeout override for provider calls (preferred override key).                   |
| `DEEPEVAL_PER_TASK_TIMEOUT_SECONDS_OVERRIDE`    | `float` / unset    | Outer timeout budget override for a metric/test-case (preferred override key).              |
| `DEEPEVAL_TASK_GATHER_BUFFER_SECONDS_OVERRIDE`  | `float` / unset    | Override extra buffer time added to gather/drain after tasks complete.                      |
| `DEEPEVAL_DISABLE_TIMEOUTS`                     | `1` / `0` / unset  | Disable `deepeval` enforced timeouts (per-attempt, per-task, gather).                       |
| `DEEPEVAL_PER_ATTEMPT_TIMEOUT_SECONDS`          | `float` (computed) | Read-only computed value. To override, set `DEEPEVAL_PER_ATTEMPT_TIMEOUT_SECONDS_OVERRIDE`. |
| `DEEPEVAL_PER_TASK_TIMEOUT_SECONDS`             | `float` (computed) | Read-only computed value. To override, set `DEEPEVAL_PER_TASK_TIMEOUT_SECONDS_OVERRIDE`.    |
| `DEEPEVAL_TASK_GATHER_BUFFER_SECONDS`           | `float` (computed) | Read-only computed value. To override, set `DEEPEVAL_TASK_GATHER_BUFFER_SECONDS_OVERRIDE`.  |

## Telemetry / Debug [#telemetry--debug]

These flags let you enable debug mode, opt out of telemetry, and control diagnostic logging.

| Variable                         | Values              | Effect                                                      |
| -------------------------------- | ------------------- | ----------------------------------------------------------- |
| `DEEPEVAL_DEBUG_ASYNC`           | `1` / `0` / `unset` | Enable extra async debugging (where supported).             |
| `DEEPEVAL_TELEMETRY_OPT_OUT`     | `1` / `0` / `unset` | Opt out of telemetry (unset defaults to telemetry enabled). |
| `DEEPEVAL_UPDATE_WARNING_OPT_IN` | `1` / `0` / `unset` | Opt in to update warnings (where supported).                |
| `DEEPEVAL_GRPC_LOGGING`          | `1` / `0` / `unset` | Enable extra gRPC logging.                                  |

## Model Settings [#model-settings]

You can configure model providers by setting a combination of environment variables (API keys, model names, provider flags, etc.). However, we recommend using the [CLI commands](/docs/command-line-interface#model-provider-configs) instead, which will set these variables for you.

<Callout type="info">
  For example, running:

  ```bash
  deepeval set-openai --model=gpt-4o
  ```

  automatically sets `OPENAI_API_KEY`, `OPENAI_MODEL_NAME`, and `USE_OPENAI_MODEL=1`.
</Callout>

Explicit constructor arguments (e.g. `OpenAIModel(api_key=...)`) always take precedence over environment variables. You can also set `TEMPERATURE` to provide a default temperature for all model instances.

### Variable Options [#variable-options]

When set to `1`, `USE_{PROVIDER}_MODEL` (e.g. `USE_OPENAI_MODEL`) tells `deepeval` which provider to use for LLM-as-a-judge metrics when no model is explicitly passed.

Each provider also has its own set of variables for API keys, model names, and other provider-specific options. Expand the sections below to see the full list for each provider.

<Callout type="caution">
  **Remember**, please do not play around with these variables manually, it should soley be for debugging purposes. Instead, use the CLI instead as `deepeval` takes care of managing these variables for you.
</Callout>

# Regression Testing LLM Systems in CI/CD (/guides/guides-regression-testing-in-cicd)



Regression testing ensures your LLM systems doesn't degrade in performance over time, and there is no better place to do it than in CI/CD environments. `deepeval` allows anyone to easily regression test outputs of LLM systems (which can be RAG pipelines, or even just an LLM itself) in the CLI through its deep integration with Pytest via the `deepeval test run` command.

<Callout type="info">
  This guide will show how you can include `deepeval` in your CI/CD pipelines, using GitHub Actions as an example.
</Callout>

## Creating Your Test File [#creating-your-test-file]

`deepeval` treats rows in an evaluation dataset as unit test cases, and a wide range of research backed LLM evaluation metrics, which you can define in a `test_<name>.py` file to implement your regression test.

```python title="test_file.py"
import pytest

from deepeval import assert_test
from deepeval.metrics import HallucinationMetric, AnswerRelevancyMetric
from deepeval.test_case import LLMTestCase
from deepeval.dataset import EvaluationDataset

first_test_case = LLMTestCase(input="...", actual_output="...")
second_test_case = LLMTestCase(input="...", actual_output="...")
dataset = EvaluationDataset(
    test_cases=[first_test_case, second_test_case]
)

@pytest.mark.parametrize(
    "test_case",
    dataset.test_cases,
)
def test_example(test_case: LLMTestCase):
    metric = AnswerRelevancyMetric(threshold=0.5)
    assert_test(test_case, [metric])
```

<Callout type="tip">
  In the example shown above, the `LLMTestCase`s are hardcoded for demonstration purposes only. Instead, you should aim to choose one of the [three ways `deepeval` offers to load a dataset](/docs/evaluation-datasets#load-an-existing-dataset) in a more scalable way.
</Callout>

To check that your test file is working, run `deepeval test run`:

```bash
deepeval test run test_file.py
```

## Setting Up Your YAML File [#setting-up-your-yaml-file]

To set up a GitHub workflow that triggers `deepeval test run` on every pull or push request, define a `.yaml` file:

```yaml title=".github/workflows/regression.yml"
name: LLM Regression Test

on:
  push:
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.10"

      - name: Install Poetry
        run: |
          curl -sSL https://install.python-poetry.org | python3 -
          echo "$HOME/.local/bin" >> $GITHUB_PATH

      - name: Install Dependencies
        run: poetry install --no-root

      - name: Run DeepEval Unit Tests
        run: poetry run deepeval test run test_file.py
```

**Congratulations 🎉!** You've now setup an automated regression testing suite in under 30 lines of code.

<Callout type="note">
  Although we only showed GitHub workflows in this guide, it will be extremely similar even if you're using another CI/CD environment such as Travis CI or CircleCI.

  You should also note that you don't have to strictly use poetry (as shown in the example above) to install dependencies, and you may need to configure additional environment variables such as an `OPENAI_API_KEY` if you're using GPT models for evaluation and a `CONFIDENT_API_KEY` if you're using Confident AI to keep track of testing results.
</Callout>
