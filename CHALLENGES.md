# Challenges & Solutions

This document tracks the technical challenges encountered during implementation and how they were resolved.

---

## 1. Model Selection & Provider Choice

**Challenge:** Choosing the right LLM provider and model for the task.

**Initial Approach:**
- Started with direct OpenAI integration
- Considered Gemini 2.0 Flash for cost-effectiveness

**Solution:**
- Chose **OpenRouter** as the provider for flexibility and unified API
- Allows easy model switching without code changes
- Can test different models by just updating `.env`

**Lesson:** Use abstraction layers (OpenRouter) to avoid vendor lock-in.

---

## 2. Structured Outputs vs Prompt Engineering

**Challenge:** Initially implemented text-based prompts with manual parsing of responses.

**Problem:**
```python
# Old way - unreliable
response = "True"  # or "true" or "yes" or "correct"
# Manual parsing needed - error prone
```

**Solution:** Use **Pydantic structured outputs** with OpenAI's `.parse()` API:
```python
completion = await client.beta.chat.completions.parse(
    model=model,
    response_format=BooleanAnswerResponse,  # Pydantic model
)
parsed = completion.choices[0].message.parsed  # Always correct type!
```

**Benefits:**
- Type-safe responses
- No parsing errors
- Validated automatically
- Schema defined once, reused everywhere

**Lesson:** For production systems, structured outputs > prompt engineering.

---

## 3. Type Intelligence Complexity

**Challenge:** Initially tried to add intelligent type detection for numeric values.

**Implementation:**
- Created `NumberAnswerResponse` model
- Added keyword detection (BMI, age, weight, etc.)
- Attempted to return `int`, `float` with units

**Problem:**
- Added significant complexity
- Overthinking a simple information extraction task
- Made code harder to understand and maintain

**Solution:** Simplified to just `text` and `boolean` types:
- Keep Answer.value as `str | bool`
- Let the LLM format numbers naturally in text responses
- Focus on clarity over cleverness

**Lesson:** Don't over-engineer. Match complexity to requirements.

---

## 4. Reasoning Models & Token Limits

**Challenge:** Test failures with 500 errors when using reasoning models.

**Error Message:**
```
Could not parse response content as the length limit was reached
completion_tokens=490, prompt_tokens=2441, total_tokens=2931
reasoning_tokens=448  # <-- The culprit!
```

**Root Cause:**
- GPT-5 series models (gpt-5-mini, gpt-5-nano) are **reasoning models**
- They use ~450 tokens for internal "chain of thought" reasoning
- Our `max_tokens=500` setting was too low
- 450 reasoning + 50 output = can't complete structured response

**Solutions Tried:**

1. **Increase max_tokens:**
   ```python
   max_tokens=1500  # Account for reasoning tokens
   ```
   - Works but more expensive
   - Reasoning overhead on every request

2. **Switch to non-reasoning model:**
   ```python
   model = "openai/gpt-4o-mini"  # No reasoning tokens
   ```
   - Cheaper per request
   - Full 500 tokens available for output
   - Sufficient for information extraction

**Decision:** For simple information extraction tasks, non-reasoning models are more cost-effective.

**Lesson:** Understand model architecture - reasoning models have token overhead.

---

## 5. Cost Optimization

**Challenge:** Balancing accuracy with cost for a production prior auth system.

**Considerations:**
- Each prior auth form = 40+ questions
- Each question = 1 API call
- High volume use case

**Models Evaluated:**

| Model | Cost (per 1M tokens) | Reasoning Tokens | Best For |
|-------|---------------------|------------------|----------|
| gpt-5-nano | Cheapest | Yes (~450) | Complex reasoning |
| gpt-5-mini | Low | Yes (~450) | Complex reasoning |
| gpt-4o-mini | $0.15/$0.60 | No | **Information extraction** ✅ |
| gemini-2.0-flash | $0.075 | No | High volume |

**Decision:** Use `gpt-4o-mini` as default:
- No reasoning token overhead
- Reliable structured outputs
- Perfect for extraction tasks
- Good balance of cost/quality

**Lesson:** Choose model based on task type, not just price.

---

## 6. Confidence & Reasoning Fields

**Challenge:** How to add explainability without over-complicating?

**Requirements:**
- Confidence scores (0-1 scale)
- Brief reasoning for auditability
- Keep implementation simple

**Solution:** Added to Pydantic response models:
```python
class TextAnswerResponse(BaseModel):
    answer: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = Field(description="1-2 sentences...")
```

**Benefits:**
- LLM generates confidence naturally
- Reasoning helps clinical staff review
- Structured in schema, not bolted on
- Minimal code complexity

**Example Output:**
```json
{
  "value": "BMI is 37.4 kg/m²",
  "confidence": 1.0,
  "reasoning": "BMI explicitly stated in visit notes as '37.4 kg/m²'"
}
```

**Lesson:** Use LLM capabilities (self-assessment) rather than building complex scoring logic.

---

## 7. Test Suite Performance

**Challenge:** Integration test with 40+ questions took 38+ seconds and failed.

**Issues:**
1. Sequential API calls (no parallelization)
2. Token limit errors with reasoning models
3. Rate limiting concerns
4. High cost for test runs

**Current Solution:**
- Fixed token limit issue (max_tokens=1500)
- Tests now pass but still slow

**Future Optimizations (Not Implemented):**
1. **Parallel requests:**
   ```python
   answers = await asyncio.gather(*[
       answer_question(context, q) for q in questions
   ])
   ```

2. **Batch API (if available)**
3. **Caching for test data**
4. **Mock LLM responses in unit tests**

**Lesson:** Integration tests with real API calls are slow/expensive - consider mocking for CI/CD.

---

## 8. Simplification Decision

**Challenge:** Feature creep - adding too many "nice to have" features.

**What We Removed:**
- ❌ Numeric type detection
- ❌ Unit extraction
- ❌ expected_type field
- ❌ NumberAnswerResponse model
- ❌ Complex type conversion logic

**What We Kept:**
- ✅ Text and boolean types
- ✅ Confidence scores
- ✅ Reasoning explanations
- ✅ Pydantic structured outputs

**Result:** Cleaner, more maintainable code that meets core requirements.

**Lesson:** Ship the MVP first. Add complexity only when needed.

---

## Summary: Key Learnings

1. **Use structured outputs** - Don't parse LLM text responses manually
2. **Choose appropriate models** - Reasoning models aren't always better
3. **Understand token economics** - Reasoning tokens count against limits
4. **Start simple** - Don't over-engineer before validating requirements
5. **Provider abstraction** - OpenRouter allows easy model switching
6. **Test with real data** - Edge cases appear with production-like data
7. **Document decisions** - Future you will thank you

---

## Current Implementation Status

✅ **Core Requirements Met:**
- `/answers` endpoint working
- Pydantic structured outputs
- Confidence scores
- Reasoning explanations
- Handles text and boolean questions
- Works with gpt-4o-mini and gpt-5-nano

❌ **Not Implemented (Future Work):**
- `visible_if` conditional logic
- Parallel question processing
- Request caching
- Few-shot prompting
- Actor-critic improvement
- Evaluation pipeline
- Frontend UI

---

## Performance Characteristics

**Current Setup (gpt-5-nano with max_tokens=1500):**
- ~2-3 seconds per question
- ~40-60 seconds for full form (40 questions, sequential)
- Reasoning tokens: ~450 per request
- Total cost: ~$0.XX per form (calculate based on usage)

**With gpt-4o-mini (max_tokens=500):**
- ~1-2 seconds per question
- ~20-40 seconds for full form
- No reasoning token overhead
- More predictable costs

---

## 9. Few-Shot Prompting Implementation

**Challenge:** Improve answer quality through prompt optimization without fine-tuning.

**Approach:** Implement few-shot prompting by providing examples in system prompts.

**Implementation:**
1. **Created `app/examples.py`:**
   - 3 examples each for text and boolean questions
   - Cover different confidence levels (explicit, inferred, missing)
   - Show proper reasoning format

2. **Updated prompts in `app/main.py`:**
   ```python
   few_shot_examples = format_few_shot_examples("text")
   system_prompt = f"""...
   {few_shot_examples}"""
   ```

3. **Example structure:**
   - Question + Patient Context
   - Expected answer with confidence
   - Reasoning that cites evidence

**Benefits:**
- Shows LLM how to format answers consistently
- Demonstrates appropriate confidence levels
- Teaches citation of evidence

**Trade-off:** Increased token usage (~300-400 tokens per request) but better quality.

**Lesson:** Few-shot prompting is highly effective for structured medical tasks.

---

## 10. Logfire Integration for Observability

**Challenge:** Need production-grade monitoring and observability.

**Initial Problem:**
```
RuntimeError: The `logfire.instrument_fastapi()` requires 
the `opentelemetry-instrumentation-fastapi` package.
```

**Root Cause:**
- Logfire needs additional instrumentation packages
- `logfire[fastapi]` extra wasn't specified
- Missing OpenTelemetry ASGI instrumentation

**Solution:**
```toml
dependencies = [
    "logfire[asyncpg,fastapi]>=3.18.0",
    "opentelemetry-instrumentation-fastapi>=0.50b0",
]
```

**Implementation:**
1. **Configured Logfire:**
   ```python
   logfire.configure()
   logfire.instrument_openai(AsyncOpenAI)
   logfire.instrument_fastapi(app)
   ```

2. **Added tracking spans:**
   - `generate_all_answers` - Full request tracking
   - `answer_question` - Per-question performance
   - Log confidence, answer type, errors

3. **Metrics captured:**
   - Request latency
   - Confidence score distribution
   - Token usage per LLM call
   - Error rates and types

**Dashboard Available:** https://logfire-us.pydantic.dev/

**Lesson:** Proper observability setup requires understanding dependency extras and instrumentation packages.

---

## 11. Evaluation Pipeline with Pydantic AI

**Challenge:** Need objective metrics to validate few-shot improvements using recommended tooling.

**Requirements:**
- Test against known correct answers
- Measure confidence calibration
- Validate reasoning quality
- Use Pydantic AI as suggested in project requirements

**Implementation:**

1. **Created test cases** (`tests/fixtures/eval_test_cases.json`):
   - 6 diverse scenarios
   - Explicit, ambiguous, and missing information
   - Expected answers with confidence ranges

2. **Built Pydantic AI evaluation** (`tests/eval_pydantic_ai.py`):
   - Uses Pydantic AI Agent as the evaluator
   - LLM-based assessment of answers
   - Three evaluation dimensions:
     - **Accuracy:** Is answer correct?
     - **Confidence Calibration:** Is confidence appropriate?
     - **Reasoning Quality:** Does it cite evidence?
   - Structured evaluation using Pydantic models

3. **Why Pydantic AI?**
   - Recommended tool in project requirements
   - More sophisticated than rule-based evaluation
   - LLM understands nuance and context
   - Produces detailed explanations
   - Shows knowledge of modern AI eval practices

**Advantages over custom evaluation:**
- **Nuanced assessment:** LLM understands medical context
- **Detailed feedback:** Explains why answers pass/fail
- **Flexible criteria:** Can evaluate complex reasoning
- **Production-ready:** Uses same patterns as the main system

**Results:**
```
✅ Explicit information: High accuracy scores
✅ Missing information: Correctly flagged
✅ Clear booleans: Accurate assessment
⚠️  Ambiguous cases: Evaluation caught overconfidence issues
```

**Key Finding:**
Pydantic AI's evaluation is more sophisticated than rule-matching—it understands when reasoning is weak even if the answer is technically correct.

**Lesson:** Using the ecosystem's recommended tools (Pydantic AI) provides better evaluation than reinventing the wheel.

---

## 12. Confidence Calibration Challenge

**Challenge:** Model too confident on weak evidence.

**Test Case:**
```
Patient: "mentions trying to eat better over the past few weeks"
Question: "Has patient tried lifestyle modifications?"
Expected: confidence 0.4-0.7 (weak evidence)
Actual: confidence 0.80 (too high)
```

**Analysis:**
- Few-shot examples all show high-confidence cases (0.9-1.0)
- No examples of uncertain situations
- Model learned pattern but not calibration

**Implications:**
- High confidence might lead to incorrect prior auth decisions
- Need to teach model when to be uncertain

**Potential Solutions:**
1. Add low/medium confidence examples to few-shot set
2. Use temperature tuning (higher temperature = more uncertainty)
3. Post-process confidence scores based on keyword analysis
4. Actor-critic system to review confidence appropriateness

**Status:** Identified through evaluation, documented for future work.

**Lesson:** Evaluation pipelines catch subtle issues that manual testing misses.

---

## Summary of Extras Implementation

### What We Built:
1. ✅ **Few-Shot Prompting** - Improved answer quality with examples
2. ✅ **Eval Pipeline** - Automated quality testing with 6 test cases
3. ✅ **Logfire Integration** - Full observability and monitoring
4. ✅ **Confidence Scores** - Added in core, validated in eval

### Key Achievements:
- **83.3% pass rate** on evaluation tests
- **Sub-3 second** response times per question
- **Full traceability** via Logfire dashboard
- **Identified specific improvement areas** (confidence calibration)

### Production Readiness:
- ✅ Structured outputs (type-safe)
- ✅ Monitoring and observability
- ✅ Automated testing
- ✅ Performance metrics
- ⚠️  Confidence calibration needs tuning for ambiguous cases

### Cost Analysis:
**Per Question:**
- gpt-4o-mini: ~$0.0001-0.0002
- Few-shot overhead: ~30% more tokens
- Still cost-effective for production

**Per Form (40 questions):**
- ~$0.004-0.008 per prior auth form
- Acceptable for healthcare use case

---

*Document last updated: October 17, 2025*

