# Test Scripts

Quick reference for running tests and demos.

---

## 🚀 Quick Commands

### Run ALL Tests (Comprehensive)
```bash
./scripts/run_tests.sh
```

Runs:
- ✅ Integration tests (pytest)
- ✅ Evaluation pipeline (Pydantic AI)
- ✅ Live API examples
- ✅ Code quality checks

---

### Run Individual Test Suites

#### 1. Integration Tests (All Scenarios)
```bash
uv run pytest tests/test_answers.py -v -s
```

**Tests included:**
- Detailed patient (full question set)
- Simple explicit info (high confidence)
- Actor-Critic refinement (ambiguous data)
- Missing information (low confidence)
- Boolean questions (mixed answers)
- Health check endpoint

#### 2. Single Test Case
```bash
# Run specific test
uv run pytest tests/test_answers.py::test_actor_critic_refinement -v -s

# Other test functions:
# - test_detailed_patient
# - test_simple_explicit_info
# - test_actor_critic_refinement
# - test_missing_information
# - test_boolean_questions
# - test_health_endpoint
```

#### 3. Evaluation Pipeline
```bash
uv run python tests/eval_pydantic_ai.py
```

Runs 9 test cases with LLM-as-Judge evaluation.

#### 4. Code Quality
```bash
uv run pre-commit run --all-files
```

---

## 📊 Output Examples

### Integration Test Output
```
🧪 TEST: Actor-Critic Refinement Test
📝 Ambiguous patient data that triggers automatic answer refinement
────────────────────────────────────────────────────────────────────────────────
📊 Generated 2 answers
────────────────────────────────────────────────────────────────────────────────

1. [BOOLEAN] Has the patient completed a structured lifestyle program...
   🔑 Key: structured_lifestyle_program
   💬 Answer: False
   🟡 Confidence: 65.00%
   🎭 [ACTOR-CRITIC REFINED]
   🧠 Reasoning: Patient mentions trying to eat better...

🎭 Actor-Critic refinements: 1/2
✅ Actor-Critic system activated as expected!
```

### Evaluation Pipeline Output
```
📊 Test Case 1: Explicit BMI Information
  📋 Question: What is the patient's BMI?
  💬 Answer: 37.4 kg/m²
  🎯 Confidence: 1.00
  🧠 Reasoning: BMI explicitly stated...

Evaluation:
├── Accuracy: 1.0 ✅
├── Confidence Appropriateness: 1.0 ✅
└── Reasoning Quality: 0.9 ✅
```

---

## 🎯 Common Use Cases

### Before Committing
```bash
# Quick check
uv run pytest tests/test_answers.py -v

# Full check
./scripts/run_tests.sh
```

### Testing Specific Features
```bash
# Test Actor-Critic
uv run pytest tests/test_answers.py::test_actor_critic_refinement -v -s

# Test evaluation
uv run python tests/eval_pydantic_ai.py
```

### Debugging
```bash
# Run with full output
uv run pytest tests/test_answers.py -v -s --tb=short

# Run single test with debugging
uv run pytest tests/test_answers.py::test_detailed_patient -v -s -x
```

---

## 📝 Test Data Files

- `sample_data/patient_data.json` - Full patient records
- `sample_data/zepbound_question_set.json` - Complete question set
- `sample_data/actor_critic_example.json` - Ambiguous data for Actor-Critic
- `sample_data/eval_test_cases.json` - Evaluation test cases

---

## 🔧 Troubleshooting

### Tests failing?
1. Check if `.env` file has `OPENROUTER_API_KEY`
2. Ensure server is running for API tests: `uv run fastapi dev`
3. Check Logfire token if using observability

### Evaluation failing?
- Requires API key in `.env`
- Uses LLM calls (may take 2-3 minutes)
- Check network connection

### Server tests skipped?
- Start server in another terminal: `uv run fastapi dev`
- Server must be running on `http://localhost:8000`

---

## 🎓 Understanding Test Results

### Confidence Levels
- 🟢 **High (≥70%)**: Explicit information
- 🟡 **Medium (40-69%)**: Reasonable inference
- 🔴 **Low (<40%)**: Missing or ambiguous data

### Actor-Critic Badge
- 🎭 **[ACTOR-CRITIC REFINED]**: Answer was refined due to low initial confidence

### Evaluation Scores
- **1.0**: Perfect
- **0.7-0.9**: Good
- **0.4-0.6**: Acceptable
- **<0.4**: Needs improvement

