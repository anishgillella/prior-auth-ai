# System Architecture

## High-Level Overview

This is a **FastAPI-based Prior Authorization Answer Generation System** that uses LLMs to generate answers to pharmacy prior authorization questions based on patient data, with human-in-the-loop validation through clinical staff annotations.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER (Browser)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────┬──────────────────────────────────┐ │
│  │   Main Application (index.html)      │   Annotation UI (annotate.html)  │ │
│  │  - Submit patient & questions        │  - Review AI answers             │ │
│  │  - Display generated answers         │  - Approve/Reject/Correct       │ │
│  │  - View confidence & reasoning       │  - Clinical staff feedback       │ │
│  └──────────────────────────────────────┴──────────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │ HTTP/REST
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FASTAPI APPLICATION LAYER (main.py)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  ENDPOINTS:                                                                 │
│  • GET  /              → Serve main frontend                               │
│  • GET  /annotate      → Serve annotation UI                              │
│  • GET  /health        → Health check                                      │
│  • POST /answers       → Generate answers (Main workflow)                 │
│  • POST /annotations   → Create clinical annotation                        │
│  • GET  /annotations   → Retrieve annotations (with filtering)             │
│                                                                             │
│  Middleware:                                                                │
│  • CORS enabled (all origins)                                              │
│  • Logfire instrumentation for observability                               │
│  • Static file serving for sample data                                     │
└────────┬────────────────────────────────────────┬──────────────────────────┘
         │                                        │
         │ Process Answer Request                 │ Save Annotation Data
         ▼                                        ▼
┌────────────────────────────────┐    ┌──────────────────────────────────┐
│  ANSWER SERVICE LAYER          │    │  ANNOTATION SERVICE             │
│  (answer_service.py)           │    │  (annotations.py)               │
├────────────────────────────────┤    ├──────────────────────────────────┤
│ • build_patient_context()      │    │ • create_annotation()           │
│   - Formats patient data       │    │ • get_annotations()             │
│   - Structures demographics    │    │ • Filter by reviewer_id/status   │
│                                │    │ • JSON persistence              │
│ • answer_question()            │    │                                  │
│   - Main question answering    │    │ Stores:                         │
│   - Calls LLM with few-shot    │    │ • Reviewer feedback              │
│   - Returns answer + confidence│    │ • Corrected answers              │
│   - Triggers actor-critic if   │    │ • Approval status                │
│     confidence < 0.7           │    │ • Timestamps & notes             │
└────────┬─────────────────────┘    └──────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                ACTOR-CRITIC REFINEMENT LAYER                               │
│                (actor_critic.py)                                           │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  WORKFLOW:                                                                  │
│  ┌──────────────────────┐                                                  │
│  │ Actor (Initial)      │ ← Generates first answer with few-shot examples │
│  │ answer_question()    │   Uses Pydantic structured output                │
│  └──────────┬───────────┘                                                  │
│             │                                                              │
│             ▼                                                              │
│  ┌──────────────────────┐                                                  │
│  │ Confidence Check     │ ← Is confidence < 0.7?                          │
│  │ confidence < 0.7?    │   If YES → proceed to Critic                     │
│  └──────────┬───────────┘   If NO  → return answer                         │
│             │                                                              │
│             ▼                                                              │
│  ┌──────────────────────────┐                                              │
│  │ Critic (Evaluation)      │ ← Analyzes answer for issues                 │
│  │ critique_answer()        │ • Missing information?                       │
│  │                          │ • Wrong assumptions?                         │
│  │                          │ • Suggests improvements                       │
│  └──────────┬───────────────┘                                              │
│             │                                                              │
│             ▼                                                              │
│  ┌──────────────────────────┐                                              │
│  │ Actor (Refined)          │ ← Regenerates answer considering criticism   │
│  │ answer_question_refined()│   Integrates feedback                        │
│  │                          │   Returns improved answer                     │
│  └──────────────────────────┘                                              │
│                                                                             │
│  RESULT: High confidence answers even for ambiguous data                   │
│  Example: 0.0 → 0.9 confidence on missing information                     │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                        FEW-SHOT EXAMPLES LAYER                              │
│                        (examples.py)                                        │
├──────────────────────────────────────────────────────────────────────────────┤
│  Demonstrates expected behavior with 4 focused examples:                    │
│                                                                              │
│  • Example 1 (Text): High confidence (1.0) - Explicit information           │
│    └─ "Medication explicitly stated: Saxenda 0.6mg"                         │
│                                                                              │
│  • Example 2 (Text): Low confidence (0.0) - Missing information             │
│    └─ "Information not available in patient records"                        │
│                                                                              │
│  • Example 3 (Boolean): Medium confidence (0.6) - Ambiguous information     │
│    └─ "Inferred from context but not explicitly stated"                     │
│                                                                              │
│  • Example 4 (Boolean): High confidence (0.9) - Strong inference            │
│    └─ "Clear evidence from visit notes"                                     │
│                                                                              │
│  Format: format_few_shot_examples() - returns few-shot prompt               │
│  Cost: ~20% more tokens, Benefit: Consistent, reliable answers              │
└──────────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                    PYDANTIC DATA MODELS LAYER (models.py)                    │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  REQUEST/RESPONSE:                                                          │
│  • Patient: Demographics + prescription + visit notes                       │
│  • Question/QuestionSet: Text or boolean prior auth questions               │
│  • AnswerInput: Patient + questions                                         │
│  • AnswerOutput: List of Answer objects                                     │
│                                                                              │
│  LLM STRUCTURED OUTPUTS:                                                    │
│  • TextAnswerResponse: answer (str) + confidence + reasoning                │
│  • BooleanAnswerResponse: answer (bool) + confidence + reasoning            │
│                                                                              │
│  CLINICAL FEEDBACK:                                                         │
│  • Annotation: Complete review record with id, timestamp, status            │
│  • AnnotationInput: Input from clinical staff                               │
│  • Status: approved | rejected | corrected                                  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                       EXTERNAL LLM SERVICE                                   │
│                     (OpenRouter + gpt-4o-mini)                              │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Provider: OpenRouter (flexible, cost-effective)                            │
│  Model: gpt-4o-mini (optimized for token budget)                            │
│  API: AsyncOpenAI client                                                    │
│                                                                              │
│  REQUEST FLOW:                                                              │
│  1. Patient context formatted                                               │
│  2. Few-shot examples included                                              │
│  3. Question sent to LLM                                                    │
│  4. Structured output (Pydantic) requested via .parse()                     │
│  5. Response parsed and validated (zero parsing errors)                     │
│                                                                              │
│  COST PROFILE:                                                              │
│  • ~$0.004-0.008 per 40-question form                                       │
│  • Few-shot overhead: ~20% additional tokens                                │
│  • Actor-critic only for low-confidence: Smart optimization                 │
│                                                                              │
│  SECURITY:                                                                  │
│  • Tested for prompt injection vulnerabilities                              │
│  • Found: Partial vulnerability (follows system instructions in reasoning)  │
│  • Mitigation: Input validation at application layer                        │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

### Primary Flow: Answer Generation

```
User Input (Patient + Questions)
          │
          ▼
   ┌─────────────────┐
   │ FastAPI /answers│
   │ (main.py)       │
   └────────┬────────┘
            │
            ▼
   ┌─────────────────────────────────────┐
   │ build_patient_context()             │
   │ (answer_service.py)                 │
   │ Formats: demographics + notes       │
   └────────┬────────────────────────────┘
            │
            ▼
   ┌──────────────────────────────────────┐
   │ For each Question:                   │
   │ answer_question()                    │
   │ (answer_service.py)                  │
   └────────┬─────────────────────────────┘
            │
            ├─ Build prompt with:
            │  • Patient context
            │  • Few-shot examples (4 examples)
            │  • Current question
            │  └─ Send to OpenRouter API
            │
            ▼
   ┌─────────────────────────────────────┐
   │ OpenRouter LLM Response             │
   │ (TextAnswerResponse or              │
   │  BooleanAnswerResponse)             │
   └────────┬────────────────────────────┘
            │
            ▼
   ┌──────────────────────────────────────┐
   │ Check Confidence                     │
   │ if confidence < 0.7:                 │
   │   → refine_answer_with_critic()      │
   │   else: return answer                │
   └────────┬─────────────────────────────┘
            │
            ├─ CRITIC PATH (low confidence)
            │  ├─ critique_answer() evaluates
            │  ├─ Identifies issues
            │  └─ answer_question_refined()
            │      regenerates improved answer
            │
            ▼
   ┌─────────────────────────────────────┐
   │ AnswerOutput                        │
   │ List of Answer objects:             │
   │ • question                          │
   │ • value (answer)                    │
   │ • confidence (0.0-1.0)              │
   │ • reasoning (evidence)              │
   └────────┬────────────────────────────┘
            │
            ▼
   Response to Client (JSON)
```

### Secondary Flow: Clinical Annotation

```
Annotation UI (annotate.html)
          │
          ▼
   ┌──────────────────────┐
   │ Clinical Staff       │
   │ Review & Feedback    │
   │ • Approve            │
   │ • Reject             │
   │ • Correct            │
   └────────┬─────────────┘
            │
            ▼
   ┌──────────────────────────────────────┐
   │ POST /annotations                    │
   │ (main.py)                            │
   └────────┬─────────────────────────────┘
            │
            ▼
   ┌──────────────────────────────────────┐
   │ create_annotation()                  │
   │ (annotations.py)                     │
   │ • Generate unique ID                 │
   │ • Timestamp (ISO format)             │
   │ • Store reviewer metadata            │
   │ • Persist to JSON                    │
   └────────┬─────────────────────────────┘
            │
            ▼
   ┌──────────────────────────────────────┐
   │ annotations.json                     │
   │ (JSON persistence)                   │
   │ • Append new annotation              │
   │ • Preserve history                   │
   └──────────────────────────────────────┘
```

---

## Module Structure

```
app/
├── main.py ........................... FastAPI endpoints (213 lines)
│   ├── GET /
│   ├── GET /health
│   ├── POST /answers ........... Answer generation endpoint
│   ├── POST /annotations
│   └── GET /annotations
│
├── answer_service.py ................ Core answer generation (174 lines)
│   ├── build_patient_context()
│   └── answer_question()
│
├── actor_critic.py .................. Refinement system (162 lines)
│   ├── critique_answer()
│   └── answer_question_refined()
│
├── annotations.py ................... Clinical feedback storage (132 lines)
│   ├── create_annotation()
│   └── get_annotations()
│
├── models.py ........................ Pydantic data models (129 lines)
│   ├── Question/QuestionSet
│   ├── Patient/Prescription
│   ├── Answer/AnswerOutput
│   ├── TextAnswerResponse
│   ├── BooleanAnswerResponse
│   └── Annotation/AnnotationInput
│
├── examples.py ...................... Few-shot examples (135 lines)
│   └── format_few_shot_examples()
│
└── env.py ........................... Configuration (25 lines)
    ├── setup_env()
    ├── get_openrouter_api_key()
    └── get_openrouter_model()
```

---

## Key Design Decisions

### 1. **Few-Shot Prompting**
- **Why**: Improves consistency without excessive overhead
- **Implementation**: 4 focused examples (2 text, 2 boolean)
- **Cost**: ~20% more tokens
- **Benefit**: Teaches confidence calibration

### 2. **Actor-Critic Pattern**
- **Why**: Handle ambiguous cases intelligently
- **Trigger**: Only when confidence < 0.7 (cost-optimized)
- **Result**: Improves low-confidence answers from 0.0 → 0.9
- **Smart**: Only 1-2 additional LLM calls when needed

### 3. **Pydantic Structured Outputs**
- **Why**: Zero parsing errors, type safety
- **Method**: OpenAI `.parse()` API with structured output
- **Benefit**: Production-ready reliability
- **Alternative Rejected**: Fragile text parsing

### 4. **OpenRouter with gpt-4o-mini**
- **Why**: Cost-effective, flexible model switching
- **Cost**: $0.004-0.008 per 40-question form
- **Rejected Alternative**: Reasoning models have token overhead
- **Config**: Via `.env` variable (OPENROUTER_MODEL)

### 5. **Modular Architecture**
- **Principle**: Single Responsibility, <200 lines per module
- **Benefit**: Easy testing, maintenance, feature extension
- **Separation**: Concerns clearly divided across files

### 6. **JSON Persistence for Annotations**
- **Why**: Simple, no external database required
- **Benefit**: Self-contained, portable
- **Future**: Can be swapped for database

### 7. **Human-in-the-Loop Validation**
- **Why**: Clinical staff verify and correct AI answers
- **Feedback Types**: Approve / Reject / Correct
- **Storage**: Reviewer ID, timestamp, notes
- **Future Use**: Training data or improved few-shot examples

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | HTML5 (static files: index.html, annotate.html) |
| **Framework** | FastAPI 0.115+ |
| **Server** | Uvicorn (async ASGI) |
| **Data Models** | Pydantic v2 |
| **LLM Integration** | OpenAI Python client, OpenRouter API |
| **Observability** | Logfire + OpenTelemetry |
| **Configuration** | python-dotenv |
| **Testing** | pytest, httpx |
| **Code Quality** | Ruff (lint + format) |
| **Async Runtime** | asyncpg, asyncio |
| **Tokenization** | tiktoken |

---

## Data Models Summary

```
┌─────────────────────────────────────────────────────────────┐
│ REQUEST: AnswerInput                                        │
├─────────────────────────────────────────────────────────────┤
│ patient: Patient                                            │
│   ├── first_name, last_name                                │
│   ├── date_of_birth, gender                                │
│   ├── prescription: Prescription                            │
│   │   ├── medication, dosage, frequency, duration          │
│   └── visit_notes: List[str]                               │
│                                                             │
│ question_set: QuestionSet                                   │
│   ├── name                                                  │
│   └── questions: List[Question]                            │
│       ├── type: "text" | "boolean"                         │
│       ├── key, content                                      │
│       └── visible_if (conditional)                         │
└─────────────────────────────────────────────────────────────┘
                         ▼
        ┌────────────────────────────────┐
        │ LLM Processing (OpenRouter)    │
        │                                │
        │ TextAnswerResponse OR          │
        │ BooleanAnswerResponse          │
        │ • answer (str/bool)            │
        │ • confidence (0.0-1.0)         │
        │ • reasoning (evidence)         │
        └────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ RESPONSE: AnswerOutput                                      │
├─────────────────────────────────────────────────────────────┤
│ answers: List[Answer]                                       │
│   ├── question: Question                                   │
│   ├── value: str | bool                                    │
│   ├── confidence: float (0.0-1.0)                          │
│   └── reasoning: str                                        │
└─────────────────────────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ CLINICAL FEEDBACK: Annotation                              │
├─────────────────────────────────────────────────────────────┤
│ id: str (unique)                                            │
│ timestamp: str (ISO format)                                 │
│ reviewer_id: str                                            │
│ patient_name: str                                           │
│ question_key, question_content: str                         │
│ original_answer, original_confidence, original_reasoning   │
│ status: "approved" | "rejected" | "corrected"             │
│ corrected_answer: str | bool (if corrected)               │
│ notes: str (reviewer feedback)                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Observability & Monitoring

**Logfire Integration:**
- Instruments FastAPI (request/response tracking)
- Instruments OpenAI client (LLM call visibility)
- Custom spans for key operations:
  - `generate_all_answers` (per request)
  - `answer_question` (per question)
  - `critique_answer` (actor-critic only)
  - `answer_question_refined` (refined answers)

**Metrics Captured:**
- Patient name, question count, medication
- Average confidence score per request
- Question set name and size
- Model used, question type, key
- Initial vs refined confidence (actor-critic)

---

## Security Considerations

### Vulnerabilities Tested
1. **Prompt Injection (SYSTEM OVERRIDE)**
   - Result: Partial vulnerability detected
   - Model acknowledges override in reasoning but gives correct answer
   - Mitigation: Input sanitization, system prompt hardening

### Recommended Protections
1. Input sanitization (block "SYSTEM", "OVERRIDE", etc.)
2. System prompt hardening (ignore embedded instructions)
3. Validation pass to detect suspicious reasoning patterns
4. Rate limiting on API endpoints
5. CORS restrictions (currently open for development)

---

## Performance Characteristics

| Operation | Time | Cost | Notes |
|-----------|------|------|-------|
| Answer 1 question | ~2-5s | $0.0001-0.0002 | Includes few-shot |
| Answer 40 questions | ~80-200s | $0.004-0.008 | Parallel possible |
| Actor-Critic refinement | +2-3s | +$0.0001-0.0002 | Only if confidence < 0.7 |
| Annotation creation | ~100ms | N/A | Local JSON write |
| Annotation retrieval | ~50-100ms | N/A | Depends on filter |

---

## Future Enhancements

1. **Database Migration**: Replace JSON with PostgreSQL
2. **Batch Processing**: Parallel question answering
3. **Fine-tuning**: Use approved annotations as training data
4. **Caching**: Store patient context across requests
5. **Advanced Metrics**: Performance analytics dashboard
6. **Version Control**: Track model/prompt changes
7. **A/B Testing**: Compare different strategies
8. **Confidence Calibration**: Improved through data
9. **Specialized Models**: Domain-specific LLMs
10. **Audit Logging**: Compliance and traceability




