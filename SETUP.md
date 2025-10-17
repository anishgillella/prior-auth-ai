# Core Implementation Setup Guide

## What's Been Implemented

✅ **Core `/answers` endpoint** using OpenRouter with GPT-4o-mini
- Extracts patient context from visit notes and prescription data
- Answers both `text` and `boolean` type questions
- **Uses Pydantic structured outputs** for type-safe, reliable responses
- Handles errors gracefully with detailed error messages

## Quick Start

### 1. Install Dependencies

```bash
uv sync
```

### 2. Configure Environment

Create a `.env` file in the project root:

```bash
# Required
OPENROUTER_API_KEY=your_actual_openrouter_key_here

# Optional (defaults to openai/gpt-4o-mini)
OPENROUTER_MODEL=openai/gpt-5-mini

# Optional: For observability
LOGFIRE_TOKEN=your_logfire_token_here
```

**Get your OpenRouter API key:** https://openrouter.ai/keys

### 3. Run the Server

```bash
uv run uvicorn app.main:app --reload
```

The API will be available at http://localhost:8000

### 4. Test the Endpoint

```bash
curl -X POST "http://localhost:8000/answers" \
  -H "Content-Type: application/json" \
  -d @sample_data/example_request.json
```

Or visit the interactive docs at http://localhost:8000/docs

### 5. Run Tests

```bash
uv run pytest
```

## Implementation Details

### Architecture

```
POST /answers
├── Validates API key
├── Builds patient context string
│   ├── Demographics
│   ├── Prescription details
│   └── Visit notes
└── For each question:
    ├── Builds type-specific prompt
    ├── Calls OpenRouter (GPT-4o-mini) with Pydantic response_format
    │   ├── TextAnswerResponse for text questions
    │   └── BooleanAnswerResponse for boolean questions
    └── Returns typed, validated response
```

### Why GPT-4o-mini with Pydantic Structured Outputs?

- **Type-safe**: Pydantic models ensure responses always match expected schema
- **Reliable**: No parsing errors or format inconsistencies
- **Cost-effective**: GPT-4o-mini is affordable at ~$0.15/1M input tokens
- **Fast**: Low latency for better UX
- **Developer-friendly**: Models are defined once and reused for validation

### Current Limitations (TODOs for Extras)

- ❌ No `visible_if` condition handling
- ❌ No confidence scores
- ❌ No prompt optimization (few-shot, actor-critic)
- ❌ No evaluation pipeline

## Extras Implemented

### 1. Few-Shot Prompting ✅

Improved answer quality by providing examples in prompts.

**Files:**
- `app/examples.py` - Few-shot example library
- `app/main.py` - Updated to use examples

**How it works:**
- 3 examples each for text and boolean questions
- Examples show appropriate confidence levels
- Demonstrates proper reasoning format

**Result:** Better consistency and citation of evidence.

### 2. Evaluation Pipeline ✅

Automated testing using **Pydantic AI** to measure answer quality.

**Files:**
- `tests/eval_pydantic_ai.py` - Pydantic AI evaluation framework
- `tests/fixtures/eval_test_cases.json` - Test cases with expected answers

**Run evaluation:**
```bash
uv run python tests/eval_pydantic_ai.py
```

**What Pydantic AI evaluates:**
- **Accuracy:** Is the answer correct given patient data?
- **Confidence Calibration:** Is the confidence score appropriate?
- **Reasoning Quality:** Does it cite specific evidence?
- **Overall Score:** Composite metric across all three

**Uses an LLM as the evaluator** - sophisticated assessment of answer quality.

### 3. Logfire Integration ✅

Full observability and monitoring.

**Setup:**
1. Sign up at https://logfire.pydantic.dev/
2. Add token to `.env`:
   ```bash
   LOGFIRE_TOKEN=your_token_here
   ```

3. Logfire automatically instruments:
   - FastAPI requests
   - OpenAI LLM calls
   - Custom spans for each question

**View dashboard:** https://logfire-us.pydantic.dev/

**What you can see:**
- Request traces and latency
- Confidence score distributions
- Token usage per call
- Error tracking

### 4. Confidence Scores ✅

Already implemented in core! Each answer includes:
- `confidence`: 0.0-1.0 score
- `reasoning`: Explanation citing evidence

---

## Running Evaluations

### Quick Evaluation (6 test cases)

```bash
uv run python tests/eval_pydantic_ai.py
```

**Output:**
- Pydantic AI agent evaluates each answer
- Accuracy, confidence calibration, and reasoning quality scores
- Detailed explanations from the evaluator
- Summary statistics and overall grade

**Note:** No server needed - calls API functions directly

### Full Test Suite (40+ questions)

```bash
uv run pytest tests/test_answers.py -v -s
```

Shows detailed output for all Zepbound questions with the full patient data.

---

## Performance Metrics

**Current Performance (with few-shot prompting):**
- ~2-3 seconds per question
- ~60-80 seconds for full 40-question form (sequential)
- 83.3% pass rate on evaluation tests
- Average confidence: 0.80

**Cost Estimate:**
- ~$0.0001-0.0002 per question
- ~$0.004-0.008 per complete prior auth form
- Few-shot overhead: ~30% more tokens but better quality

