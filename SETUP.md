# Setup & Usage Guide

Complete guide for setting up and running the Prior Authorization API.

---

## Prerequisites

- Python 3.12+
- `uv` package manager
- OpenRouter API key (get from https://openrouter.ai)
- Logfire account (optional, for observability)

---

## Quick Start

### 1. Install Dependencies

```bash
uv sync
uv run pre-commit install
```

### 2. Configure Environment

Create `.env` file:

```bash
# Required
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=openai/gpt-4o-mini

# Optional - for observability
LOGFIRE_TOKEN=your_token_here
```

Get your keys:
- **OpenRouter:** https://openrouter.ai/keys
- **Logfire:** https://logfire.pydantic.dev (free tier available)

### 3. Run the Server

```bash
uv run uvicorn app.main:app --reload
```

Server runs at: **http://localhost:8000**

---

## Testing

### Run Integration Tests
```bash
uv run pytest tests/test_answers.py -v -s
```

### Run Evaluation Pipeline
```bash
uv run python tests/eval_pydantic_ai.py
```

**What it tests:**
- 9 test cases including adversarial attacks
- Pydantic AI evaluates accuracy, confidence, reasoning
- Results: ~77% pass rate with detailed feedback

---

## Using the Application

### 1. Main UI (Answer Generation)

**URL:** http://localhost:8000

**Features:**
- **📝 Simple Example** - Basic patient data and questions
- **📋 Detailed Example** - Comprehensive patient record
- **🎭 Actor-Critic Demo** - Ambiguous data that triggers automatic refinement
- Click "Generate Answers" to see AI-generated responses
- View confidence scores and reasoning for each answer
- Refined answers show a purple **🎭 Actor-Critic** badge

### 2. Annotation UI (Clinical Review)

**URL:** http://localhost:8000/annotate

**Features:**
- Clinical staff can review AI-generated answers
- Three actions: Approve ✓ / Reject ✗ / Correct ✎
- Annotations saved to `sample_data/annotations.json`
- View recent annotation history

**Use Case:** Quality assurance and human feedback loop

### 3. API Documentation

**Swagger UI:** http://localhost:8000/docs  
**ReDoc:** http://localhost:8000/redoc

---

## API Endpoints

### POST /answers
Generate answers to prior authorization questions.

**Request:**
```json
{
  "patient": {
    "first_name": "John",
    "last_name": "Doe",
    "date_of_birth": "1970-01-01",
    "gender": "Male",
    "prescription": {
      "medication": "Zepbound",
      "dosage": "5 mg",
      "frequency": "once weekly",
      "duration": "ongoing"
    },
    "visit_notes": ["Patient has BMI of 37.4..."]
  },
  "question_set": {
    "name": "Prior Auth",
    "questions": [
      {
        "type": "text",
        "key": "patient_bmi",
        "content": "What is the patient's BMI?"
      }
    ]
  }
}
```

**Response:**
```json
{
  "answers": [
    {
      "question": {...},
      "value": "37.4 kg/m²",
      "confidence": 1.0,
      "reasoning": "BMI is explicitly stated in visit notes..."
    }
  ]
}
```

### POST /annotations
Submit clinical staff review.

### GET /annotations
Retrieve annotations (filterable by reviewer/status).

---

## Architecture Overview

```
HTTP Request → FastAPI Endpoint
                    ↓
            Answer Service
                    ↓
         Few-Shot Prompting → LLM
                    ↓
         Initial Answer Generated
                    ↓
    Confidence < 0.7? → Actor-Critic Refinement
                    ↓
         Return Final Answer
                    ↓
       Frontend Displays Results
                    ↓
  Clinical Staff Reviews (Annotation UI)
                    ↓
    Feedback Stored for Improvement
```

---

## Features Implemented

### Core Requirements ✅
- `/answers` endpoint with LLM integration
- Pydantic structured outputs (type-safe)
- Patient context extraction
- Efficient modular architecture

### AI Engineer Extras ✅
1. **Few-Shot Prompting** - 6 examples for consistency
2. **Actor-Critic System** - Auto-refines low-confidence answers (< 0.7)
3. **Eval Pipeline** - Pydantic AI with 9 test cases
4. **Confidence Scores** - With reasoning for every answer
5. **Annotation UI** - Clinical staff review system

### Additional Features ✅
- Frontend demo UI
- Logfire observability
- Security testing (adversarial)
- Comprehensive documentation

---

## AI Engineer Extras Details

### 1. Few-Shot Prompting
**Location:** `app/examples.py`

Provides 4 focused examples (2 text, 2 boolean) covering:
- High confidence (1.0) - Explicit information
- Low confidence (0.0) - Missing information  
- Medium confidence (0.6) - Ambiguous information
- Evidence citation format

### 2. Actor-Critic System  
**Location:** `app/actor_critic.py`

**How it works:**
- Triggers automatically when confidence < 0.7
- Critic evaluates initial answer and provides feedback
- Actor regenerates improved answer
- Tracks improvement in Logfire

**Try it yourself (Frontend - Easiest!):**
1. Start server: `uv run fastapi dev`
2. Open http://localhost:8000
3. Click the purple **🎭 Actor-Critic Demo** button
4. Click **Generate Answers**
5. Look for the purple **🎭 Actor-Critic** badge in refined answers!

**Or via CLI:**
```bash
curl -X POST "http://localhost:8000/answers" \
  -H "Content-Type: application/json" \
  -d @sample_data/actor_critic_example.json
```

**What you'll see:**
1. **Initial Answer:** Low confidence (e.g., 0.5-0.6) due to vague information
2. **Actor-Critic Triggered:** System detects low confidence
3. **Critic Feedback:** "Information is vague, lacks specific details..."
4. **Refined Answer:** Improved confidence and reasoning

**Check Logfire for:**
- `invoking_actor_critic` span
- `critique_answer` with feedback
- `answer_refined` with improvement metrics

**Example output:**
```json
{
  "question": "Has patient completed structured lifestyle program?",
  "value": false,
  "confidence": 0.65,
  "reasoning": "[Refined via Actor-Critic] Patient mentions trying to eat better and occasional walks, but there is no documentation of a structured program with at least 6 months of consistent effort..."
}
```

**In the frontend UI**, refined answers display with a purple gradient badge:
```
🎭 Actor-Critic
Patient mentions trying to eat better and occasional walks, but there 
is no documentation of a structured program...
```

The `[Refined via Actor-Critic]` prefix is automatically converted to a styled badge!

### 3. Evaluation Pipeline
**Location:** `tests/eval_pydantic_ai.py`

Uses Pydantic AI to evaluate:
- Accuracy (is answer correct?)
- Confidence calibration (is confidence appropriate?)
- Reasoning quality (cites evidence?)

**Test cases include:**
- Explicit information
- Missing data
- Multi-step calculations
- Contradictory info
- Adversarial jailbreak attempts

### 4. Annotation UI
**Location:** `frontend/annotate.html`, `app/annotations.py`

Clinical staff can:
- Review AI answers
- Approve/Reject/Correct
- Add review notes
- Track annotation history

Stored in: `sample_data/annotations.json`

---

## Project Structure

```
app/
├── main.py              # API endpoints (clean, focused)
├── answer_service.py    # Answer generation logic
├── actor_critic.py      # Critic & refinement system
├── annotations.py       # Clinical review handling
├── models.py            # Pydantic data models
├── examples.py          # Few-shot examples
└── env.py              # Configuration

frontend/
├── index.html          # Main demo UI
└── annotate.html       # Annotation UI

tests/
├── test_answers.py     # Integration tests
└── eval_pydantic_ai.py # Evaluation pipeline

sample_data/
├── patient_data.json
├── zepbound_question_set.json
├── eval_test_cases.json
└── annotations.json    # Generated at runtime
```

---

## Monitoring with Logfire

View real-time metrics:
- Request traces
- LLM call performance
- Confidence score distributions
- Actor-critic invocations
- Error rates

**Dashboard:** https://logfire-us.pydantic.dev/

---

## Common Issues

### Server won't start
```bash
# Check if port 8000 is in use
lsof -i :8000

# Use different port
uv run uvicorn app.main:app --port 8001
```

### API Key not working
```bash
# Verify .env file exists
cat .env

# Check key is loaded
uv run python -c "from app.env import get_openrouter_api_key; print(get_openrouter_api_key())"
```

### Tests failing
```bash
# Ensure dependencies are installed
uv sync

# Check API key is set
grep OPENROUTER_API_KEY .env
```

---

## Development

### Run with hot reload
```bash
uv run uvicorn app.main:app --reload
```

### Format code
```bash
uv run ruff format .
```

### Lint code
```bash
uv run pre-commit run --all-files
```

---

## Performance

- **Avg response time:** 2-3 seconds per question
- **Simple case (3 questions):** ~5 seconds total
- **Complex case (40 questions):** ~60-80 seconds
- **Actor-critic overhead:** +2-3 seconds when triggered

**Optimization opportunities:**
- Parallel question processing (currently sequential)
- Caching for repeated questions
- Streaming responses

---

## Security Considerations

- **Jailbreak Testing:** Included in evaluation
- **Finding:** Model partially vulnerable to prompt injection
- **Mitigation:** Input validation, system prompt hardening (future work)
- **API Keys:** Never commit to git (.env in .gitignore)

---

## Cost Estimation

Using `gpt-4o-mini` via OpenRouter:
- **Simple form (3 questions):** ~$0.001-0.002
- **Full form (40 questions):** ~$0.004-0.008
- **With actor-critic:** +20% cost when triggered

**Monthly estimate (1000 forms):** ~$4-8

---

For questions or issues, refer to `CHALLENGES.md` for detailed technical decisions and problem-solving approaches.
