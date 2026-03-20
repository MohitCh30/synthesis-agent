import re
from typing import Optional, Tuple


def extract_constraints(text: str) -> dict:
    constraints = {
        "max_lines": None,
        "max_words": None
    }

    text_lower = text.lower()

    lines_match = re.search(r'(\d+)\s*(?:line|lines)\b', text_lower)
    if lines_match:
        constraints["max_lines"] = int(lines_match.group(1))

    if re.search(r'\b(one|1)\s*word\b', text_lower):
        constraints["max_words"] = 1
    elif re.search(r'\b(two|2)\s*words?\b', text_lower):
        constraints["max_words"] = 2
    elif re.search(r'\b(three|3)\s*words?\b', text_lower):
        constraints["max_words"] = 3
    elif re.search(r'\b(short answer)\b', text_lower):
        constraints["max_words"] = 50
    elif re.search(r'\b(single|brief)\s*(sentence|answer)\b', text_lower):
        constraints["max_words"] = 20

    words_match = re.search(r'(\d+)\s*words?', text_lower)
    if words_match and not re.search(r'\b(one|two|three)\s*words?\b', text_lower):
        constraints["max_words"] = int(words_match.group(1))

    return constraints


def validate_output(output: str, constraints: dict) -> Tuple[bool, str]:
    if not constraints["max_lines"] and not constraints["max_words"]:
        return True, ""

    lines = output.strip().split('\n')
    line_count = len([l for l in lines if l.strip()])

    if constraints["max_lines"] and line_count > constraints["max_lines"]:
        return False, f"Exceeded line limit: {line_count} lines > {constraints['max_lines']} allowed"

    words = output.split()
    word_count = len(words)

    if constraints["max_words"] and word_count > constraints["max_words"]:
        return False, f"Exceeded word limit: {word_count} words > {constraints['max_words']} allowed"

    return True, ""


def calculate_trust_score(
    constraints_valid: bool,
    latency_ms: float
) -> Tuple[float, str]:
    score = 1.0
    reasons = []

    if not constraints_valid:
        score -= 0.5
        reasons.append("constraints violated (-0.5)")

    if latency_ms > 10000:
        score -= 0.2
        reasons.append("high latency >10s (-0.2)")

    score = max(0.0, min(1.0, score))

    if reasons:
        explanation = f"Base score 1.0, deductions: {'; '.join(reasons)}"
    else:
        explanation = "Full trust: all constraints met, latency optimal"

    return score, explanation
