"""PII restoration for LLM responses.

Handles de-anonymization of PII placeholders in responses.
"""


def deanonymize_response(content: str, deanonymization_map: dict[str, str]) -> str:
    """Restore original PII values in LLM response.

    DEV-007 PII: Reverse the anonymization applied to document content.
    Sorts placeholders by length descending to avoid partial replacements.

    Args:
        content: LLM response text with PII placeholders
        deanonymization_map: Dict mapping placeholder -> original value

    Returns:
        Response text with original PII values restored
    """
    if not deanonymization_map or not content:
        return content

    result = content
    # Sort by length descending to avoid partial replacements
    # e.g., [NOME_ABC123] should be replaced before [NOME_ABC]
    for placeholder, original in sorted(
        deanonymization_map.items(),
        key=lambda x: len(x[0]),
        reverse=True,
    ):
        result = result.replace(placeholder, original)

    return result
