"""
Few-shot examples for prompt optimization.

These examples demonstrate high-quality answers covering different scenarios:
- Explicit information (high confidence)
- Missing information (low confidence)
- Ambiguous information (medium confidence)
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
        "question": "Has the patient tried lifestyle modifications?",
        "patient_context": """Patient Information:
- Name: Jane Smith

Visit Notes:
1. Patient mentions trying to eat better over the past few weeks.""",
        "expected_output": {
            "answer": True,
            "confidence": 0.6,
            "reasoning": "Patient mentions attempting to eat better, which suggests lifestyle modification. However, the information is vague without specific details about the extent or consistency of changes, resulting in moderate confidence.",
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
