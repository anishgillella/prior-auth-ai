"""
Few-shot examples for prompt optimization.

These examples demonstrate high-quality answers for the LLM to learn from.
"""

# Few-shot examples for text questions
TEXT_EXAMPLES = [
    {
        "question": "What is the patient's BMI?",
        "patient_context": """Patient Information:
- Name: John Doe
- Date of Birth: 1970-01-01
- Gender: Male

Current Prescription:
- Medication: Zepbound
- Dosage: 5 mg
- Frequency: once weekly
- Duration: ongoing

Visit Notes:
1. Patient is a 55-year-old male with BMI of 37.4 kg/m². Weight: 261 lbs. Height: 5 ft 10 in.""",
        "expected_output": {
            "answer": "37.4 kg/m²",
            "confidence": 1.0,
            "reasoning": "BMI is explicitly stated in the visit notes as 37.4 kg/m².",
        },
    },
    {
        "question": "What is the patient's age in years?",
        "patient_context": """Patient Information:
- Name: Sarah Smith
- Date of Birth: 1985-03-15
- Gender: Female

Visit Notes:
1. Patient is a 40-year-old female presenting for follow-up.""",
        "expected_output": {
            "answer": "40 years",
            "confidence": 1.0,
            "reasoning": "Age is explicitly stated in visit notes as 40 years old, which matches the calculated age from DOB (1985-03-15).",
        },
    },
    {
        "question": "What is the patient's current weight?",
        "patient_context": """Patient Information:
- Name: John Doe
- Date of Birth: 1970-01-01

Visit Notes:
1. Patient has been compliant with medication regimen.""",
        "expected_output": {
            "answer": "Information not available in patient records",
            "confidence": 0.0,
            "reasoning": "No weight information is provided in the patient demographics or visit notes.",
        },
    },
]

# Few-shot examples for boolean questions
BOOLEAN_EXAMPLES = [
    {
        "question": "Has the patient tried lifestyle modifications?",
        "patient_context": """Patient Information:
- Name: John Doe

Visit Notes:
1. Patient has tried multiple diets including calorie restriction and low-carbohydrate regimens.
2. Patient worked with a registered dietitian and joined a gym in January 2025.
3. Patient has engaged in lifestyle modifications for over 6 months with minimal sustained results.""",
        "expected_output": {
            "answer": True,
            "confidence": 1.0,
            "reasoning": "Visit notes explicitly document multiple lifestyle modification attempts including diets, working with a dietitian, gym membership, and sustained effort over 6 months.",
        },
    },
    {
        "question": "Does the patient have diabetes?",
        "patient_context": """Patient Information:
- Name: Sarah Smith

Visit Notes:
1. Patient has history of hypertension, well controlled on lisinopril.
2. Patient has dyslipidemia, on atorvastatin.
3. No history of diabetes (last HbA1c 5.7% in May 2025).""",
        "expected_output": {
            "answer": False,
            "confidence": 1.0,
            "reasoning": "Visit notes explicitly state 'No history of diabetes' and recent HbA1c of 5.7% is below the diagnostic threshold for diabetes.",
        },
    },
    {
        "question": "Has the patient been adherent to medication?",
        "patient_context": """Patient Information:
- Name: John Doe

Visit Notes:
1. Patient presents for follow-up regarding weight management therapy.""",
        "expected_output": {
            "answer": False,
            "confidence": 0.5,
            "reasoning": "No explicit information about medication adherence is provided in the visit notes. Cannot determine adherence from the available information.",
        },
    },
]


def format_few_shot_examples(question_type: str) -> str:
    """
    Format few-shot examples for inclusion in prompts.

    Args:
        question_type: Either "text" or "boolean"

    Returns:
        Formatted string with examples
    """
    examples = TEXT_EXAMPLES if question_type == "text" else BOOLEAN_EXAMPLES

    formatted = "\n\nHere are examples of high-quality answers:\n\n"

    for i, example in enumerate(examples, 1):
        formatted += f"Example {i}:\n"
        formatted += f"Question: {example['question']}\n\n"
        formatted += f"Patient Context:\n{example['patient_context']}\n\n"
        formatted += "Expected Answer:\n"
        formatted += f"  answer: {example['expected_output']['answer']}\n"
        formatted += f"  confidence: {example['expected_output']['confidence']}\n"
        formatted += f"  reasoning: {example['expected_output']['reasoning']}\n\n"

    formatted += "Now answer the following question in the same format:\n"

    return formatted
