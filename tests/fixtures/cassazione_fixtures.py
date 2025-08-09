"""
HTML fixtures for testing Cassazione web scraping.

This module provides sample HTML pages that represent the structure
of actual Cassazione court decision pages for testing purposes.
"""

from typing import Dict, Any


# Sample decision page HTML structure
SAMPLE_CIVIL_DECISION_HTML = """
<!DOCTYPE html>
<html lang="it">
<head>
    <title>Cassazione Civile - Sentenza n. 15234 del 15/03/2024</title>
    <meta charset="UTF-8">
</head>
<body>
    <div id="main-content">
        <header class="court-header">
            <h1>CORTE SUPREMA DI CASSAZIONE</h1>
            <h2>SEZIONE CIVILE TERZA</h2>
        </header>
        
        <div class="decision-metadata">
            <div class="decision-title">
                <h3>Sentenza 15 marzo 2024, n. 15234</h3>
                <p class="decision-type">SENTENZA</p>
            </div>
            
            <div class="case-info">
                <p><strong>N. di ruolo:</strong> 12345/2023</p>
                <p><strong>Data udienza:</strong> 28 febbraio 2024</p>
            </div>
        </div>
        
        <div class="parties-section">
            <h4>PARTI IN CAUSA</h4>
            <div class="party-info">
                <p><strong>Ricorrente:</strong> ALFA S.P.A., in persona del legale rappresentante pro tempore, rappresentata e difesa dall'Avv. Mario Rossi</p>
                <p><strong>Convenuta:</strong> BETA S.R.L., in persona del legale rappresentante pro tempore, rappresentata e difesa dall'Avv. Luigi Verdi</p>
            </div>
        </div>
        
        <div class="judges-section">
            <h4>COMPOSIZIONE DEL COLLEGIO</h4>
            <ul class="judges-list">
                <li><strong>Presidente:</strong> Dott. Marco Bianchi</li>
                <li><strong>Relatore:</strong> Dott.ssa Anna Neri</li>
                <li><strong>Consigliere:</strong> Dott. Giuseppe Rossi</li>
            </ul>
        </div>
        
        <div class="decision-subject">
            <h4>MATERIA</h4>
            <p>Diritto societario - Responsabilità dell'amministratore di S.R.L. per le obbligazioni sociali - Limiti e presupposti</p>
        </div>
        
        <div class="decision-content">
            <h4>FATTO E DIRITTO</h4>
            
            <h5>Svolgimento del processo</h5>
            <p>
                La società Alfa S.p.A. conveniva in giudizio la Beta S.r.l. e il suo amministratore unico, 
                chiedendo il pagamento di Euro 500.000,00 a titolo di risarcimento danni per inadempimento 
                contrattuale. Il Tribunale rigettava la domanda. La Corte di Appello confermava la sentenza 
                di primo grado.
            </p>
            
            <h5>Motivi della decisione</h5>
            <p>
                Il ricorso è fondato. La Corte di merito ha erroneamente applicato i principi in tema di 
                responsabilità dell'amministratore di società a responsabilità limitata.
            </p>
            
            <h5>PRINCIPI DI DIRITTO</h5>
            <div class="legal-principles">
                <ol>
                    <li>
                        In tema di società a responsabilità limitata, l'amministratore risponde verso i 
                        creditori sociali per le obbligazioni sociali quando abbia compiuto atti in violazione 
                        della legge o dello statuto, sempre che sussista un nesso causale tra la condotta 
                        dell'amministratore e l'evento dannoso.
                    </li>
                    <li>
                        È necessario provare non solo l'inadempimento della società debitrice, ma anche la 
                        colpa grave dell'amministratore nel compimento dell'atto gestorio.
                    </li>
                    <li>
                        La responsabilità dell'amministratore sussiste solo quando la condotta omissiva o 
                        commissiva sia stata determinante nel causare o aggravare l'insolvenza sociale.
                    </li>
                </ol>
            </div>
            
            <h5>RIFERIMENTI NORMATIVI</h5>
            <div class="law-references">
                <ul>
                    <li>Art. 2476 Codice Civile (Responsabilità verso i creditori)</li>
                    <li>Art. 2381 Codice Civile (Responsabilità degli amministratori verso la società)</li>
                    <li>Art. 1218 Codice Civile (Responsabilità per inadempimento)</li>
                </ul>
            </div>
            
            <h5>PRECEDENTI GIURISPRUDENZIALI</h5>
            <div class="case-references">
                <ul>
                    <li>Cass. Civ. Sez. I, 15 gennaio 2023, n. 98765</li>
                    <li>Cass. Civ. Sez. II, 22 novembre 2022, n. 54321</li>
                    <li>Cass. Civ. SS. UU., 10 maggio 2021, n. 13579</li>
                </ul>
            </div>
            
            <h5>DISPOSITIVO</h5>
            <p>
                La Corte, definitivamente pronunciando sul ricorso, lo accoglie, cassa la sentenza impugnata 
                e rinvia la causa ad altra Sezione della Corte di Appello di Roma per nuovo giudizio, anche 
                in ordine alle spese del presente giudizio.
            </p>
        </div>
        
        <footer class="decision-footer">
            <p class="publication-info">
                Pubblicata in data: 20 marzo 2024<br>
                Depositata in Cancelleria il: 18 marzo 2024
            </p>
        </footer>
    </div>
</body>
</html>
"""

# Sample tax court decision HTML
SAMPLE_TAX_DECISION_HTML = """
<!DOCTYPE html>
<html lang="it">
<head>
    <title>Cassazione Tributaria - Sentenza n. 8756 del 22/02/2024</title>
    <meta charset="UTF-8">
</head>
<body>
    <div id="main-content">
        <header class="court-header">
            <h1>CORTE SUPREMA DI CASSAZIONE</h1>
            <h2>SEZIONE TRIBUTARIA</h2>
        </header>
        
        <div class="decision-metadata">
            <div class="decision-title">
                <h3>Sentenza 22 febbraio 2024, n. 8756</h3>
                <p class="decision-type">SENTENZA</p>
            </div>
        </div>
        
        <div class="parties-section">
            <h4>PARTI IN CAUSA</h4>
            <div class="party-info">
                <p><strong>Ricorrente:</strong> CONTRIBUENTE S.R.L.</p>
                <p><strong>Convenuta:</strong> AGENZIA DELLE ENTRATE</p>
            </div>
        </div>
        
        <div class="judges-section">
            <h4>COMPOSIZIONE DEL COLLEGIO</h4>
            <ul class="judges-list">
                <li><strong>Presidente:</strong> Dott. Carlo Verdi</li>
                <li><strong>Relatore:</strong> Dott.ssa Maria Blu</li>
            </ul>
        </div>
        
        <div class="decision-subject">
            <h4>MATERIA</h4>
            <p>IVA - Operazioni immobiliari - Applicazione dell'aliquota agevolata - Requisiti soggettivi e oggettivi</p>
        </div>
        
        <div class="decision-content">
            <h5>PRINCIPI DI DIRITTO</h5>
            <div class="legal-principles">
                <ol>
                    <li>
                        In materia di IVA sulle cessioni di fabbricati, l'applicazione dell'aliquota ridotta 
                        del 4% prevista per l'acquisto della prima casa è subordinata alla sussistenza di 
                        specifici requisiti soggettivi e oggettivi.
                    </li>
                    <li>
                        È necessario che l'acquirente non sia titolare, nemmeno in quota, di diritti di 
                        proprietà, usufrutto, uso o abitazione su altra casa di abitazione nel territorio 
                        del comune ove è ubicato l'immobile da acquistare.
                    </li>
                </ol>
            </div>
            
            <h5>RIFERIMENTI NORMATIVI</h5>
            <div class="law-references">
                <ul>
                    <li>DPR 633/1972, Tabella A, parte II, n. 39</li>
                    <li>Art. 7, Nota II-bis, della Tariffa allegata al DPR 131/1986</li>
                </ul>
            </div>
        </div>
    </div>
</body>
</html>
"""

# Sample search results page HTML
SAMPLE_SEARCH_RESULTS_HTML = """
<!DOCTYPE html>
<html lang="it">
<head>
    <title>Risultati ricerca - Cassazione</title>
    <meta charset="UTF-8">
</head>
<body>
    <div id="search-container">
        <div class="search-header">
            <h2>Risultati della ricerca</h2>
            <p class="results-count">Trovati 247 risultati per "amministratore società"</p>
        </div>
        
        <div class="search-results">
            <div class="result-item" data-decision-id="15234">
                <h3 class="result-title">
                    <a href="/decision/15234/2024" class="decision-link">
                        Cass. Civ. Sez. III, 15 marzo 2024, n. 15234
                    </a>
                </h3>
                <p class="result-subject">Responsabilità amministratore SRL per obbligazioni sociali</p>
                <p class="result-summary">
                    L'amministratore risponde verso i creditori sociali quando abbia compiuto atti 
                    in violazione della legge o dello statuto...
                </p>
                <div class="result-metadata">
                    <span class="result-date">15 marzo 2024</span>
                    <span class="result-section">Sezione Civile</span>
                    <span class="result-type">Sentenza</span>
                </div>
            </div>
            
            <div class="result-item" data-decision-id="15678">
                <h3 class="result-title">
                    <a href="/decision/15678/2024" class="decision-link">
                        Cass. Civ. Sez. II, 10 marzo 2024, n. 15678
                    </a>
                </h3>
                <p class="result-subject">Doveri dell'amministratore nella gestione sociale</p>
                <p class="result-summary">
                    Gli amministratori devono adempiere i doveri loro imposti dalla legge e dall'atto 
                    costitutivo con la diligenza richiesta...
                </p>
                <div class="result-metadata">
                    <span class="result-date">10 marzo 2024</span>
                    <span class="result-section">Sezione Civile</span>
                    <span class="result-type">Sentenza</span>
                </div>
            </div>
            
            <div class="result-item" data-decision-id="8756">
                <h3 class="result-title">
                    <a href="/decision/8756/2024" class="decision-link">
                        Cass. Trib., 22 febbraio 2024, n. 8756
                    </a>
                </h3>
                <p class="result-subject">IVA su operazioni immobiliari</p>
                <p class="result-summary">
                    Applicazione dell'aliquota agevolata per l'acquisto della prima casa: 
                    requisiti soggettivi e oggettivi...
                </p>
                <div class="result-metadata">
                    <span class="result-date">22 febbraio 2024</span>
                    <span class="result-section">Sezione Tributaria</span>
                    <span class="result-type">Sentenza</span>
                </div>
            </div>
            
            <div class="result-item" data-decision-id="14521">
                <h3 class="result-title">
                    <a href="/decision/14521/2024" class="decision-link">
                        Cass. Lav., 5 marzo 2024, n. 14521
                    </a>
                </h3>
                <p class="result-subject">Licenziamento per giusta causa</p>
                <p class="result-summary">
                    Il licenziamento per giusta causa deve essere sorretto da fatti di particolare 
                    gravità che rendano impossibile la prosecuzione...
                </p>
                <div class="result-metadata">
                    <span class="result-date">5 marzo 2024</span>
                    <span class="result-section">Sezione Lavoro</span>
                    <span class="result-type">Sentenza</span>
                </div>
            </div>
        </div>
        
        <div class="pagination">
            <nav class="page-navigation">
                <span class="page-info">Pagina 1 di 25</span>
                <div class="page-links">
                    <span class="current-page">1</span>
                    <a href="?page=2" class="page-link">2</a>
                    <a href="?page=3" class="page-link">3</a>
                    <a href="?page=4" class="page-link">4</a>
                    <a href="?page=5" class="page-link">5</a>
                    <span class="page-separator">...</span>
                    <a href="?page=25" class="page-link">25</a>
                    <a href="?page=2" class="next-link">Successiva &raquo;</a>
                </div>
            </nav>
        </div>
    </div>
</body>
</html>
"""

# Sample ordinance (different from sentenza)
SAMPLE_ORDINANCE_HTML = """
<!DOCTYPE html>
<html lang="it">
<head>
    <title>Cassazione Civile - Ordinanza n. 9876 del 12/03/2024</title>
</head>
<body>
    <div id="main-content">
        <header class="court-header">
            <h1>CORTE SUPREMA DI CASSAZIONE</h1>
            <h2>SEZIONE CIVILE PRIMA</h2>
        </header>
        
        <div class="decision-metadata">
            <div class="decision-title">
                <h3>Ordinanza 12 marzo 2024, n. 9876</h3>
                <p class="decision-type">ORDINANZA</p>
            </div>
        </div>
        
        <div class="parties-section">
            <p><strong>Ricorrente:</strong> GAMMA S.R.L.</p>
            <p><strong>Convenuta:</strong> DELTA S.P.A.</p>
        </div>
        
        <div class="decision-subject">
            <h4>MATERIA</h4>
            <p>Contratti - Vendita - Risoluzione per inadempimento</p>
        </div>
        
        <div class="decision-content">
            <h5>DISPOSITIVO</h5>
            <p>
                La Corte dichiara inammissibile il ricorso per difetto dei presupposti 
                di cui all'art. 360 c.p.c.
            </p>
        </div>
    </div>
</body>
</html>
"""

# Sample Sezioni Unite decision (highest authority)
SAMPLE_SEZIONI_UNITE_HTML = """
<!DOCTYPE html>
<html lang="it">
<head>
    <title>Cassazione Sezioni Unite - Sentenza n. 5555 del 01/02/2024</title>
</head>
<body>
    <div id="main-content">
        <header class="court-header">
            <h1>CORTE SUPREMA DI CASSAZIONE</h1>
            <h2>SEZIONI UNITE CIVILI</h2>
        </header>
        
        <div class="decision-metadata">
            <div class="decision-title">
                <h3>Sentenza 1 febbraio 2024, n. 5555</h3>
                <p class="decision-type">SENTENZA</p>
            </div>
        </div>
        
        <div class="decision-subject">
            <h4>MATERIA</h4>
            <p>Contrasto giurisprudenziale - Responsabilità civile - Danno esistenziale</p>
        </div>
        
        <div class="decision-content">
            <h5>PRINCIPI DI DIRITTO</h5>
            <div class="legal-principles">
                <p>
                    <strong>PRINCIPIO DI DIRITTO ENUNCIATO DALLE SEZIONI UNITE:</strong>
                </p>
                <ol>
                    <li>
                        Il danno esistenziale, inteso come compromissione delle attività realizzatrici 
                        della persona umana, è risarcibile solo se costituisce lesione di un interesse 
                        della persona costituzionalmente garantito.
                    </li>
                </ol>
            </div>
        </div>
    </div>
</body>
</html>
"""

# Malformed HTML for testing error handling
MALFORMED_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Broken Page</title>
</head>
<body>
    <div class="content">
        <h1>Some title without closing tag
        <p>Paragraph with unclosed div
    <div>
        <span>Unclosed span
        <!-- Malformed comment
    </body>
<!-- Missing closing html tag
"""

# Empty search results
EMPTY_SEARCH_RESULTS_HTML = """
<!DOCTYPE html>
<html lang="it">
<head>
    <title>Nessun risultato trovato</title>
</head>
<body>
    <div id="search-container">
        <div class="search-header">
            <h2>Nessun risultato trovato</h2>
            <p class="results-count">La ricerca per "termine inesistente" non ha prodotto risultati.</p>
        </div>
        
        <div class="search-results empty">
            <p class="no-results-message">
                Non sono state trovate sentenze corrispondenti ai criteri di ricerca.
            </p>
        </div>
    </div>
</body>
</html>
"""

# HTML fixtures mapping for easy access in tests
HTML_FIXTURES = {
    "civil_decision": SAMPLE_CIVIL_DECISION_HTML,
    "tax_decision": SAMPLE_TAX_DECISION_HTML,
    "search_results": SAMPLE_SEARCH_RESULTS_HTML,
    "ordinance": SAMPLE_ORDINANCE_HTML,
    "sezioni_unite": SAMPLE_SEZIONI_UNITE_HTML,
    "malformed": MALFORMED_HTML,
    "empty_search": EMPTY_SEARCH_RESULTS_HTML
}

# Expected parsing results for validation
EXPECTED_PARSING_RESULTS = {
    "civil_decision": {
        "decision_number": "15234/2024",
        "date": "2024-03-15",
        "section": "civile",
        "subsection": "III",
        "decision_type": "sentenza",
        "subject": "Diritto societario - Responsabilità dell'amministratore di S.R.L.",
        "judge_count": 3,
        "party_count": 2,
        "legal_principles_count": 3,
        "law_references_count": 3,
        "case_references_count": 3
    },
    "tax_decision": {
        "decision_number": "8756/2024",
        "date": "2024-02-22",
        "section": "tributaria",
        "decision_type": "sentenza",
        "subject": "IVA - Operazioni immobiliari",
        "legal_principles_count": 2,
        "law_references_count": 2
    },
    "search_results": {
        "total_results": 4,
        "results_per_page": 4,
        "current_page": 1,
        "total_pages": 25,
        "sections_represented": ["civile", "tributaria", "lavoro"]
    }
}


def get_fixture(fixture_name: str) -> str:
    """Get HTML fixture by name."""
    if fixture_name not in HTML_FIXTURES:
        raise ValueError(f"Fixture '{fixture_name}' not found. Available: {list(HTML_FIXTURES.keys())}")
    return HTML_FIXTURES[fixture_name]


def get_expected_result(fixture_name: str) -> Dict[str, Any]:
    """Get expected parsing result for a fixture."""
    if fixture_name not in EXPECTED_PARSING_RESULTS:
        raise ValueError(f"Expected result for '{fixture_name}' not found")
    return EXPECTED_PARSING_RESULTS[fixture_name]


def create_custom_decision_html(
    decision_number: str,
    date_str: str,
    section: str,
    subject: str,
    judges: list = None,
    parties: list = None
) -> str:
    """Create custom decision HTML for specific test scenarios."""
    judges = judges or ["Mario Rossi"]
    parties = parties or ["Ricorrente A", "Convenuto B"]
    
    judges_html = "\n".join([f"<li><strong>Giudice:</strong> {judge}</li>" for judge in judges])
    parties_html = "\n".join([f"<p><strong>Parte:</strong> {party}</p>" for party in parties])
    
    return f"""
    <!DOCTYPE html>
    <html lang="it">
    <head>
        <title>Cassazione {section.title()} - Sentenza n. {decision_number}</title>
    </head>
    <body>
        <div id="main-content">
            <header class="court-header">
                <h1>CORTE SUPREMA DI CASSAZIONE</h1>
                <h2>SEZIONE {section.upper()}</h2>
            </header>
            
            <div class="decision-metadata">
                <h3>Sentenza {date_str}, n. {decision_number}</h3>
            </div>
            
            <div class="parties-section">
                {parties_html}
            </div>
            
            <div class="judges-section">
                <ul class="judges-list">
                    {judges_html}
                </ul>
            </div>
            
            <div class="decision-subject">
                <h4>MATERIA</h4>
                <p>{subject}</p>
            </div>
            
            <div class="decision-content">
                <h5>PRINCIPI DI DIRITTO</h5>
                <p>Principio di diritto stabilito dalla Corte per il caso {decision_number}.</p>
            </div>
        </div>
    </body>
    </html>
    """