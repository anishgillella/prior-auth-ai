# 🎭 Actor-Critic System Demo

## Overview
This demo showcases how the Actor-Critic system automatically refines low-confidence answers using a two-stage LLM approach.

---

## 🚀 How to Run

### Option 1: Frontend (Recommended)
1. Start the server: `uv run fastapi dev`
2. Open http://localhost:8000
3. Click **🎭 Actor-Critic Demo** button
4. Click **Generate Answers**
5. Look for the purple **🎭 Actor-Critic** badge in refined answers

### Option 2: CLI
```bash
curl -X POST "http://localhost:8000/answers" \
  -H "Content-Type: application/json" \
  -d @sample_data/actor_critic_example.json
```

---

## 📋 Demo Scenario

### Patient Data (Ambiguous)
```json
{
  "first_name": "Sarah",
  "last_name": "Martinez",
  "visit_notes": [
    "Patient mentions trying to eat better over the past few weeks.",
    "Patient reports occasional walks in the neighborhood.",
    "Interested in weight management options."
  ]
}
```

### Questions
1. **Has the patient completed a structured lifestyle modification program with documented attempts at diet and exercise for at least 6 months?**
   - Type: Boolean

2. **What percentage of body weight has the patient lost through lifestyle modifications?**
   - Type: Text

---

## 🎬 What Happens

### Stage 1: Initial Answer (Actor)
The LLM generates an initial answer:

```json
{
  "answer": false,
  "confidence": 0.55,  // ⚠️ Low confidence triggers Actor-Critic!
  "reasoning": "Patient mentions trying to eat better and occasional walks, but no structured program documented."
}
```

**Trigger**: Confidence < 0.7 → Actor-Critic activates

---

### Stage 2: Critique (Critic)
A separate LLM evaluates the answer:

```
Critical Analysis:
- The reasoning correctly identifies lack of documentation
- However, it should more clearly differentiate between:
  * Informal attempts (what patient has)
  * Structured program (what question asks)
- Should emphasize the 6-month requirement explicitly
- Confidence seems appropriate given the ambiguity
```

---

### Stage 3: Refined Answer (Actor v2)
The Actor regenerates the answer using the critique:

```json
{
  "answer": false,
  "confidence": 0.65,  // Improved clarity
  "reasoning": "[Refined via Actor-Critic] Patient mentions trying to eat better and occasional walks, but there is no documentation of a structured program with at least 6 months of consistent effort. The information provided suggests informal attempts rather than a formal lifestyle modification program with documented diet and exercise plans."
}
```

**Improvements:**
- ✅ More explicit about "structured program" vs "informal attempts"
- ✅ Emphasizes "6 months" requirement
- ✅ Clearer reasoning even if confidence stays similar
- ✅ Badge appears in UI: **🎭 Actor-Critic**

---

## 📊 Logfire Observability

Check your Logfire dashboard for detailed traces:

### Trace Structure
```
POST /answers
├── build_patient_context
├── answer_question (Initial)
│   ├── openai.chat.completions.create
│   └── confidence=0.55 → Trigger!
├── invoking_actor_critic
│   ├── critique_answer
│   │   └── openai.chat.completions.create
│   └── answer_refined
│       └── openai.chat.completions.create
└── Response: [Refined via Actor-Critic] ...
```

### Key Metrics to Watch
- **Initial Confidence**: Should be < 0.7
- **Critique Quality**: Check feedback specificity
- **Refinement Impact**: Compare initial vs refined reasoning
- **Token Usage**: Actor-Critic adds ~500-800 tokens per refinement

---

## 🔍 Visual Example

### Frontend Display

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Has the patient completed a structured lifestyle...      │
│    Boolean                                                   │
├─────────────────────────────────────────────────────────────┤
│ ❌ No                                                        │
├─────────────────────────────────────────────────────────────┤
│ Confidence: 65%                                              │
│ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░                      │
├─────────────────────────────────────────────────────────────┤
│ 💡 Reasoning:                                                │
│ ┌───────────────────┐                                       │
│ │ 🎭 Actor-Critic  │ Patient mentions trying to eat        │
│ └───────────────────┘ better and occasional walks, but     │
│ there is no documentation of a structured program with      │
│ at least 6 months of consistent effort...                   │
└─────────────────────────────────────────────────────────────┘
```

The purple **🎭 Actor-Critic** badge indicates this answer was refined!

---

## 🎯 When Actor-Critic Activates

✅ **Triggers on:**
- Confidence < 0.7
- Ambiguous patient information
- Weak initial reasoning
- Missing explicit evidence

❌ **Doesn't trigger on:**
- Confidence ≥ 0.7 (already high quality)
- Explicit information in records
- Clear yes/no answers

---

## 💰 Cost & Performance

### Token Usage (per refined answer)
- Initial generation: ~300 tokens
- Critique: ~200 tokens
- Refinement: ~400 tokens
- **Total overhead**: ~600 extra tokens (2x the base cost)

### When to Use
- ✅ **Production**: High-stakes medical decisions
- ✅ **Pilot**: Review edge cases and ambiguous data
- ⚠️ **High Volume**: Consider cost vs quality tradeoff

### Performance
- Base latency: ~1-2 seconds
- With Actor-Critic: ~3-5 seconds
- **2-3x slower** but significantly better quality

---

## 🧪 Try Different Scenarios

Modify `sample_data/actor_critic_example.json` to test:

### More Ambiguous (Lower Initial Confidence)
```json
"visit_notes": ["Patient mentions wanting to lose weight."]
```
Expected: Very low confidence → Strong critique → Major refinement

### Less Ambiguous (Higher Initial Confidence)
```json
"visit_notes": [
  "Patient completed 8-month program with dietitian.",
  "Lost 15 lbs through documented meal plans and exercise."
]
```
Expected: High confidence → **No Actor-Critic triggered!**

### Contradictory Info (Stress Test)
```json
"visit_notes": [
  "Patient tried diets but gave up after 2 weeks.",
  "Patient mentions 6-month gym membership."
]
```
Expected: Medium confidence → Critique should flag contradiction

---

## 🎓 Key Takeaways

1. **Automatic Quality Control**: No manual intervention needed
2. **Transparent**: Badge shows when refinement occurred
3. **Cost-Effective**: Only refines when needed (confidence < 0.7)
4. **Observable**: Full trace in Logfire
5. **Explainable**: Reasoning shows improvement rationale

---

## 📚 Related Documentation

- [SETUP.md](../SETUP.md#2-actor-critic-system) - Full setup guide
- [CHALLENGES.md](../CHALLENGES.md#4-actor-critic-system-design) - Implementation challenges
- [app/actor_critic.py](../app/actor_critic.py) - Source code

---

**Questions?** Check the reasoning in your results for the `[Refined via Actor-Critic]` prefix!

