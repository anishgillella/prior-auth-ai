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

## Next Steps: Deep Extras

Once core is working, here are the recommended deep extras to implement:

1. **Prompt Optimization**
   - Few-shot examples with medical prior auth answers
   - Actor-critic: Have LLM evaluate its own answers
   - Compare Gemini Flash vs reasoning models (o1-mini)

2. **Evaluation Pipeline**
   - Use Pydantic AI for structured evals
   - Test against known good answers
   - Measure accuracy, completeness

3. **Confidence Scores**
   - Add confidence field to Answer model
   - Use LLM to assess certainty
   - Flag low-confidence answers for human review

