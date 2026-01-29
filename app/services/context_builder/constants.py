"""Constants for context building.

Contains hierarchy weights and Italian labels for legal document types.
"""

# Maximum number of KB documents to preserve (performance cap)
MAX_KB_DOCUMENTS = 20

# DEV-244: Minimum RRF score to display in Fonti dropdown
MIN_FONTI_RELEVANCE_SCORE = 0.008

# Italian legal document hierarchy weights for source prioritization
HIERARCHY_WEIGHTS: dict[str, float] = {
    "legge": 1.0,
    "decreto_legislativo": 1.0,
    "dpr": 1.0,
    "decreto_ministeriale": 0.8,
    "regolamento_ue": 0.8,
    "circolare": 0.6,
    "risoluzione": 0.6,
    "interpello": 0.4,
    "faq": 0.4,
    "cassazione": 0.9,
    "corte_costituzionale": 1.0,
}

# DEV-245: Category labels in Italian for Fonti section display
CATEGORY_LABELS_IT: dict[str, str] = {
    "regulatory_documents": "normativa",
    "legge": "legge",
    "decreto_legislativo": "decreto legislativo",
    "decreto": "decreto",
    "dpr": "DPR",
    "decreto_ministeriale": "decreto ministeriale",
    "regolamento_ue": "regolamento UE",
    "circolare": "circolare",
    "risoluzione": "risoluzione",
    "interpello": "interpello",
    "faq": "FAQ",
    "cassazione": "Cassazione",
    "corte_costituzionale": "Corte Costituzionale",
    "prassi": "prassi",
    "guida": "guida",
    "web": "web",
}
