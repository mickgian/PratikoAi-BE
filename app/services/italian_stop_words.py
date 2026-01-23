"""Italian stop words for fiscal/legal domain keyword extraction.

DEV-245 Phase 5.14: Centralized stop word module.
Single source of truth - all services import from here.

Usage:
    from app.services.italian_stop_words import STOP_WORDS, STOP_WORDS_MINIMAL

    # Full list (~200 words) - for search keyword extraction
    if word in STOP_WORDS:
        skip_word()

    # Minimal list (~50 words) - for topic extraction
    if word in STOP_WORDS_MINIMAL:
        skip_word()

Previous locations (now deprecated - use this module instead):
- parallel_retrieval.py _extract_search_keywords() - ~150 words
- step_040__build_context.py _extract_filter_keywords_from_query() - ~150 words
- step_034a__llm_router.py _TOPIC_STOP_WORDS - ~40 words
- italian_query_normalizer.py self.stop_words - ~60 words
- action_validator.py _extract_significant_words() - ~80 words
"""

# ============================================================================
# ARTICLES & PREPOSITIONS (~45 words)
# ============================================================================
_ARTICLES = {
    "il",
    "lo",
    "la",
    "i",
    "gli",
    "le",
    "un",
    "uno",
    "una",
}

_PREPOSITIONS = {
    "di",
    "a",
    "da",
    "in",
    "con",
    "su",
    "per",
    "tra",
    "fra",
}

_PREPOSITION_CONTRACTIONS = {
    # di + article
    "del",
    "dello",
    "della",
    "dei",
    "degli",
    "delle",
    # a + article
    "al",
    "allo",
    "alla",
    "ai",
    "agli",
    "alle",
    # da + article
    "dal",
    "dallo",
    "dalla",
    "dai",
    "dagli",
    "dalle",
    # in + article
    "nel",
    "nello",
    "nella",
    "nei",
    "negli",
    "nelle",
    # su + article
    "sul",
    "sullo",
    "sulla",
    "sui",
    "sugli",
    "sulle",
    # Apostrophe stems (after splitting "dell'irap" → "dell")
    "dell",
    "all",
    "nell",
    "sull",
    "dall",
}

# ============================================================================
# CONJUNCTIONS & CONNECTORS (~25 words)
# ============================================================================
_CONJUNCTIONS = {
    "e",
    "ed",
    "o",
    "ma",
    "però",
    "quindi",
    "dunque",
    "perché",
    "che",
    "se",
    "quando",
    "come",
    "dove",
    "chi",
    "cui",
    "oppure",
    "ovvero",
    "infatti",
    "inoltre",
    "comunque",
    "tuttavia",
    "pertanto",
    "allora",
    "mentre",
}

# ============================================================================
# PRONOUNS (~25 words)
# ============================================================================
_PRONOUNS = {
    "io",
    "tu",
    "lui",
    "lei",
    "noi",
    "voi",
    "loro",
    "mi",
    "ti",
    "ci",
    "vi",
    "si",
    "li",
    "ne",
    "me",
    "te",
    "sé",
    "questo",
    "quello",
    "quale",
    "quali",
    "questa",
    "questi",
    "queste",
    "quella",
    "quelli",
    "quelle",
}

# ============================================================================
# VERBS - COMPREHENSIVE (~100 words)
# DEV-245 Phase 5.14: Added future/conditional/imperative forms
# ============================================================================

# Essere (to be) - all common forms
_VERB_ESSERE = {
    "essere",
    "è",
    "sono",
    "sei",
    "siamo",
    "siete",
    "era",
    "erano",
    "sarà",
    "saranno",
    "sarebbe",
    "sarebbero",  # Future/conditional
    "sia",
    "siano",
    "fosse",
    "fossero",  # Subjunctive
    "stato",
    "stata",
    "stati",
    "state",  # Past participle
}

# Avere (to have) - all common forms
_VERB_AVERE = {
    "avere",
    "ha",
    "ho",
    "hai",
    "abbiamo",
    "avete",
    "hanno",
    "aveva",
    "avevano",
    "avrà",
    "avranno",
    "avrebbe",
    "avrebbero",  # Future/conditional
    "abbia",
    "abbiano",
    "avesse",
    "avessero",  # Subjunctive
    "avuto",  # Past participle
}

# Modal verbs (potere, dovere, volere)
_VERB_MODALS = {
    # Potere (can/may)
    "potere",
    "può",
    "posso",
    "puoi",
    "possiamo",
    "possono",
    "potrebbe",
    "potrebbero",
    "potrà",
    "potranno",
    "potrei",
    "potresti",
    "potremmo",
    "potreste",
    "possa",
    "possano",  # Subjunctive
    # Dovere (must/have to)
    "dovere",
    "deve",
    "devo",
    "devi",
    "dobbiamo",
    "devono",
    "dovrebbe",
    "dovrebbero",
    "dovrà",
    "dovranno",
    "dovrei",
    "dovresti",
    "dovremmo",
    "dovreste",
    "debba",
    "debbano",  # Subjunctive
    # Volere (want)
    "volere",
    "vuole",
    "voglio",
    "vuoi",
    "vogliamo",
    "vogliono",
    "vorrebbe",
    "vorrebbero",
    "vorrà",
    "vorranno",
    "vorrei",
    "vorresti",
    "vorremmo",
    "vorreste",
    "voglia",
    "vogliano",  # Subjunctive
}

# Common action verbs
_VERB_COMMON = {
    # Fare (to do/make)
    "fare",
    "fa",
    "fai",
    "fanno",
    "fatto",
    "farà",
    "faranno",
    "farebbe",
    "farebbero",
    # Dire (to say)
    "dire",
    "dice",
    "dico",
    "dicono",
    "detto",
    # Sapere (to know)
    "sapere",
    "sa",
    "so",
    "sai",
    "sanno",
    # Vedere (to see)
    "vedere",
    "vedo",
    "vedi",
    "vede",
    "vediamo",
    "vedono",
    # Venire (to come) - important for passive constructions
    "venire",
    "viene",
    "vengono",
    "veniva",
    "venivano",
    # Andare (to go)
    "andare",
    "va",
    "vai",
    "vanno",
    "andato",
    # Stare (to stay/be)
    "stare",
    "sta",
    "sto",
    "stai",
    "stanno",
}

# Conversational/request verbs
_VERB_CONVERSATIONAL = {
    "parlare",
    "parlami",
    "parla",
    "spiegare",
    "spiegami",
    "spiega",
    "raccontare",
    "raccontami",
    "racconta",
    "dimmi",
    "dammi",
    "fammi",  # Imperatives
    "indicami",
    "mostrami",
    "elencami",
    "capire",
    "capisco",
    "capisci",
    "trovare",
    "trovo",
    "trova",
    "cercare",
    "cerco",
    "cerca",
}

# DEV-245 Phase 5.14: Problematic verbs that caused issues
_VERB_PROBLEMATIC = {
    # Future tense verbs that slip through (the "recepira" problem)
    # Include BOTH accented and non-accented forms because users often type
    # "recepira'" (apostrophe) instead of "recepirà" (proper accent)
    "recepire",
    "recepisce",
    "recepiscono",
    "recepirà",
    "recepiranno",
    "recepirebbe",  # Accented forms
    "recepira",  # Non-accented form (THE FIX for the "recepira" problem!)
    # Other -ire verbs that might cause issues (both accented and non-accented)
    "includere",
    "include",
    "includono",
    "includerà",
    "includera",
    "applicare",
    "applica",
    "applicano",
    "applicherà",
    "applichera",
    "riguardare",
    "riguarda",
    "riguardano",
    "riguarderà",
    "riguardera",
    "esistere",
    "esiste",
    "esistono",
    "esisterà",
    "esistera",
    "funzionare",
    "funziona",
    "funzionano",
    "funzionerà",
    "funzionera",
    # Additional common verbs (both accented and non-accented)
    "prevedere",
    "prevede",
    "prevedono",
    "prevederà",
    "prevedera",
    "contenere",
    "contiene",
    "contengono",
    "comprendere",
    "comprende",
    "comprendono",
}

# ============================================================================
# QUESTION WORDS (~10 words)
# ============================================================================
_QUESTION_WORDS = {
    "cosa",
    "quanto",
    "quanta",
    "quanti",
    "quante",
    # Note: come, quando, perché, dove, chi, quale, quali are in conjunctions
}

# ============================================================================
# ADVERBS & MODIFIERS (~25 words)
# ============================================================================
_ADVERBS = {
    "non",
    "più",
    "molto",
    "poco",
    "troppo",
    "anche",
    "solo",
    "sempre",
    "mai",
    "già",
    "ancora",
    "ora",
    "poi",
    "prima",
    "dopo",
    "così",
    "bene",
    "male",
    "meglio",
    "peggio",
    "subito",
    "forse",
    "quasi",
    "proprio",
    "davvero",
    "veramente",
}

# ============================================================================
# OTHER COMMON WORDS (~30 words)
# ============================================================================
_COMMON_WORDS = {
    "tutto",
    "tutti",
    "tutte",
    "ogni",
    "altro",
    "altri",
    "altre",
    "stesso",
    "stessa",
    "stessi",
    "stesse",
    "nuovo",
    "nuova",
    "nuovi",
    "nuove",
    "vecchio",
    "vecchia",
    "grande",
    "grandi",
    "piccolo",
    "piccola",
    "primo",
    "prima",
    "ultimo",
    "ultima",
    "anno",
    "anni",
    "mese",
    "mesi",
    "giorno",
    "giorni",
    "modo",
    "caso",
    "casi",
    "volta",
    "volte",
}

# ============================================================================
# DOMAIN-SPECIFIC STOP WORDS (~15 words)
# Words common in fiscal queries but not substantive
# ============================================================================
_DOMAIN_STOP_WORDS = {
    "riguardo",
    "circa",
    "rispetto",
    "secondo",
    "relativo",
    "relativa",
    "relativi",
    "relative",
    "eventuale",
    "eventuali",
    "eventualmente",
    "possibile",
    "possibili",
    "necessario",
    "necessaria",
}

# ============================================================================
# COMBINED SETS
# ============================================================================

# Full stop word list (~200+ words) - for search keyword extraction
STOP_WORDS: frozenset[str] = frozenset(
    _ARTICLES
    | _PREPOSITIONS
    | _PREPOSITION_CONTRACTIONS
    | _CONJUNCTIONS
    | _PRONOUNS
    | _VERB_ESSERE
    | _VERB_AVERE
    | _VERB_MODALS
    | _VERB_COMMON
    | _VERB_CONVERSATIONAL
    | _VERB_PROBLEMATIC
    | _QUESTION_WORDS
    | _ADVERBS
    | _COMMON_WORDS
    | _DOMAIN_STOP_WORDS
)

# Minimal stop word list (~50 words) - for topic extraction
# Only the most common words, keeps more content words
STOP_WORDS_MINIMAL: frozenset[str] = frozenset(
    _ARTICLES
    | _PREPOSITIONS
    | {"e", "o", "ma", "che", "se", "come", "dove", "chi"}  # Basic conjunctions
    | {"mi", "ti", "ci", "vi", "si", "ne", "lo", "li"}  # Clitics
    | {"è", "sono", "ha", "hanno", "può", "deve"}  # Common verbs
    | {"parlami", "dimmi", "spiegami", "cosa"}  # Request words
    | {"del", "della", "dei", "delle", "nel", "nella", "al", "alla"}  # Common contractions
)
