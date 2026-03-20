import re
from typing import Optional


def parse_constraints(text: str) -> dict:
    constraints = {
        "max_words": None,
        "max_lines": None,
        "sentence_count": None,
        "words_per_sentence": None,
        "forbidden_chars": None,
        "format": None
    }

    text_lower = text.lower()

    lines_match = re.search(r'(\d+)\s*(?:line|lines)\b', text_lower)
    if lines_match:
        constraints["max_lines"] = int(lines_match.group(1))

    wps_match = re.search(r'(\d+)\s*words?\s+each\b', text_lower)
    if wps_match:
        constraints["words_per_sentence"] = int(wps_match.group(1))

    wps_match2 = re.search(r'(\d+)\s*words?\s+per\s+(?:sentence|line)\b', text_lower)
    if wps_match2:
        constraints["words_per_sentence"] = int(wps_match2.group(1))

    sentence_match = re.search(r'(\d+)\s*(?:sentence|sentences)\b', text_lower)
    if sentence_match:
        constraints["sentence_count"] = int(sentence_match.group(1))

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
    else:
        if not constraints["words_per_sentence"]:
            words_match = re.search(r'(\d+)\s*words?', text_lower)
            if words_match and not re.search(r'\b(one|two|three)\s*words?\b', text_lower):
                constraints["max_words"] = int(words_match.group(1))

    forbidden_pattern = re.findall(r"['\"](\w)['\"]", text)
    if forbidden_pattern:
        constraints["forbidden_chars"] = list(set(forbidden_pattern))

    if re.search(r'\b(?:yes|no|true|false)\s*(?:or|,)\s*(?:yes|no|true|false)\s*only\b', text_lower):
        constraints["format"] = "yes_no_only"

    return constraints


def detect_contradictions(constraints: dict, raw_input: str) -> dict:
    contradiction_detected = False
    contradiction_reason = None
    input_lower = raw_input.lower()

    max_words = constraints.get("max_words") or 0
    max_lines = constraints.get("max_lines") or 0
    sentence_count = constraints.get("sentence_count") or 0

    if max_words == 1 and max_lines > 1:
        contradiction_detected = True
        contradiction_reason = "Single word constraint conflicts with multi-line requirement"

    if max_words == 1 and sentence_count > 1:
        contradiction_detected = True
        contradiction_reason = "Single word constraint conflicts with multi-sentence requirement"

    if constraints.get("format") == "yes_no_only":
        if max_words > 3:
            contradiction_detected = True
            contradiction_reason = "YES/NO format constraint conflicts with explanation requirement"

    if sentence_count and max_words:
        if max_words < sentence_count:
            contradiction_detected = True
            contradiction_reason = f"Cannot have {sentence_count} sentences with only {max_words} words"

    if re.search(r'\b(one|1)\s*word\b', input_lower) and 'explain' in input_lower:
        contradiction_detected = True
        contradiction_reason = "Single-word constraint conflicts with explanation requirement"

    if re.search(r'\b(one|1)\s*word\b', input_lower) and 'justify' in input_lower:
        contradiction_detected = True
        contradiction_reason = "Single-word constraint conflicts with justification requirement"

    if 'only' in input_lower and ('explain' in input_lower or 'justify' in input_lower):
        contradiction_detected = True
        contradiction_reason = "Exclusive format conflicts with explanation requirement"

    if 'brief' in input_lower and re.search(r'\bat least\b.*\d+\s*words', input_lower):
        contradiction_detected = True
        contradiction_reason = "Brief constraint conflicts with minimum word requirement"

    if re.search(r'\bsingle\s*word\b', input_lower) and ('explain' in input_lower or 'justify' in input_lower):
        contradiction_detected = True
        contradiction_reason = "Single-word constraint conflicts with explanation requirement"

    return {
        "contradiction_detected": contradiction_detected,
        "contradiction_reason": contradiction_reason
    }


def _split_sentences(text: str) -> list[str]:
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]


def validate_output(output: str, constraints: dict) -> list[str]:
    violations = []

    if constraints.get("format") == "yes_no_only":
        cleaned = output.strip().upper()
        if cleaned not in ["YES", "NO"]:
            violations.append(f"Format violation: expected YES or NO only, got '{output.strip()}'")
        return violations

    lines = output.strip().split('\n')
    line_count = len([l for l in lines if l.strip()])

    if constraints.get("max_lines") and line_count > constraints["max_lines"]:
        violations.append(f"Exceeded line limit: {line_count} lines > {constraints['max_lines']} allowed")

    words = output.split()
    word_count = len(words)

    if constraints.get("max_words") and word_count > constraints["max_words"]:
        violations.append(f"Exceeded word limit: {word_count} words > {constraints['max_words']} allowed")

    sentences = _split_sentences(output)

    if constraints.get("sentence_count"):
        expected = constraints["sentence_count"]
        actual = len(sentences)
        if actual != expected:
            violations.append(f"Sentence count mismatch: expected {expected}, got {actual}")

    if constraints.get("words_per_sentence"):
        expected_words = constraints["words_per_sentence"]
        for i, sentence in enumerate(sentences, 1):
            actual_words = len(sentence.split())
            if actual_words != expected_words:
                violations.append(f"Sentence {i}: expected {expected_words} words, got {actual_words}")

    if constraints.get("forbidden_chars"):
        output_lower = output.lower()
        for char in constraints["forbidden_chars"]:
            if char.lower() in output_lower:
                violations.append(f"Forbidden character '{char}' found in output")

    return violations


def calculate_trust_score(
    violations: list[str],
    contradiction_detected: bool,
    latency_ms: float
) -> tuple[float, str]:
    score = 1.0
    deductions = []

    format_violations = sum(1 for v in violations if "format" in v.lower())
    structural_violations = sum(1 for v in violations if "mismatch" in v.lower() or "exceeded" in v.lower() or "sentence" in v.lower())
    minor_violations = sum(1 for v in violations if v not in [v for v in violations if "format" in v.lower() or "mismatch" in v.lower() or "exceeded" in v.lower() or "sentence" in v.lower()])

    if contradiction_detected:
        score -= 0.5
        deductions.append("contradiction (-0.5)")

    if format_violations > 0:
        penalty = min(format_violations * 0.3, 0.6)
        score -= penalty
        deductions.append(f"format violations (-{penalty:.1f})")

    if structural_violations > 0:
        penalty = min(structural_violations * 0.2, 0.4)
        score -= penalty
        deductions.append(f"structural violations (-{penalty:.1f})")

    if minor_violations > 0:
        penalty = min(minor_violations * 0.1, 0.3)
        score -= penalty
        deductions.append(f"minor violations (-{penalty:.1f})")

    if latency_ms > 10000:
        score -= 0.2
        deductions.append("high latency >10s (-0.2)")

    score = max(0.0, min(1.0, score))

    if deductions:
        explanation = f"Base 1.0, deductions: {'; '.join(deductions)}"
    else:
        explanation = "Full trust: all constraints met, latency optimal"

    return score, explanation
