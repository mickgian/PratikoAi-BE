"""Constants for LLM response processing.

Contains source hierarchy rankings for Italian legal documents.
"""

# DEV-214: Italian legal source hierarchy (highest to lowest authority)
# Lower number = higher authority
SOURCE_HIERARCHY = {
    "legge": 1,  # Legge (Law)
    "decreto": 2,  # Decreto Legislativo / DPR / D.Lgs
    "circolare": 3,  # Circolare AdE
    "interpello": 4,  # Interpello / Risposta
    "prassi": 5,  # Other prassi
    "unknown": 99,
}
