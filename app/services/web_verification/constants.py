"""Constants for web verification.

Contains keywords and thresholds used for contradiction detection.
"""

# Keywords that indicate potential contradictions
CONTRADICTION_KEYWORDS = {
    # Italian negation/exception words
    "non",
    "esclusi",
    "escluso",
    "esclusa",
    "tranne",
    "eccetto",
    "salvo",
    "ma",
    "però",
    "tuttavia",
    "invece",
    "attenzione",
    "importante",
    "dipende",
    "richiede",
    "necessario",
    "obbligatorio",
    "condizione",
    "requisito",
    "limite",
    "limitato",
    "solo",
    "soltanto",
    "parzialmente",
    "accordo",
    "delibera",
    "ente locale",
    # Date-related (potential updates)
    "prorogato",
    "prorogata",
    "proroga",
    "posticipato",
    "posticipata",
    "rinviato",
    "rinviata",
    "nuova scadenza",
    "aggiornato",
    "aggiornata",
    "modificato",
    "modificata",
}

# Topics that often have nuances requiring caveats
SENSITIVE_TOPICS = {
    "tributi locali",
    "imu",
    "tasi",
    "tasse auto",
    "bollo auto",
    "irap",
    "accertamento",
    "ente locale",
    "comune",
    "regione",
    "provincia",
}

# DEV-245 Phase 5.14: Keywords indicating genuine exclusions in web content
# Used to determine whether to use checkmark/cross format in synthesis prompts
EXCLUSION_KEYWORDS = {
    # Direct exclusions
    "escluso",
    "esclusa",
    "esclusi",
    "escluse",
    "non ammesso",
    "non ammessa",
    "non ammessi",
    "non rientra",
    "non rientrano",
    "non può",
    "non possono",
    # Conditional limitations
    "tranne",
    "eccetto",
    "salvo",
    "a condizione",
    "solo se",
    "dipende da",
    "richiede",
    # Specific to rottamazione/fiscal domain
    "delibera comunale",
    "delibera dell'ente",
    "accordo",
    "adesione dell'ente",
}

# Minimum confidence threshold for generating caveats
MIN_CAVEAT_CONFIDENCE = 0.5
