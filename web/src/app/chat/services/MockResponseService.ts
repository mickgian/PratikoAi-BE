interface MockResponse {
  patterns: string[]
  response: string
}

/**
 * Mock response service with predefined HTML responses
 * Provides realistic fiscal consulting responses for testing
 */
export class MockResponseService {
  private responses: MockResponse[] = [
    // Regime forfettario question
    {
      patterns: [
        'come funziona il regime forfettario',
        'regime forfettario',
        'forfettario',
        'forfetario',
        'come funziona forfettario'
      ],
      response: `
        <h3>Il Regime Forfettario</h3>
        <p>Il regime forfettario è un regime fiscale agevolato per le partite IVA con ricavi limitati.</p>
        
        <div class="calculation">
          <div class="calculation-step">
            <span class="label">Aliquota fiscale:</span>
            <span class="percentage">15%</span>
          </div>
          <div class="calculation-step">
            <span class="label">Per i primi 5 anni (under 35):</span>
            <span class="percentage">5%</span>
          </div>
        </div>

        <p><strong>Vantaggi principali:</strong></p>
        <ul>
          <li>Aliquota ridotta al 15% (o 5% per i giovani)</li>
          <li>Esenzione IVA</li>
          <li>Contabilità semplificata</li>
          <li>Niente versamenti trimestrali IVA</li>
        </ul>

        <p class="legal-ref">Art. 1, commi 54-89, Legge 190/2014</p>
      `
    },

    // IRPEF calculation
    {
      patterns: [
        'calcola irpef',
        'calcolo irpef',
        'irpef',
        'imposta sul reddito',
        'calcolo imposte',
        'tasse reddito'
      ],
      response: `
        <h3>Calcolo IRPEF</h3>
        <p>L'IRPEF (Imposta sul Reddito delle Persone Fisiche) si calcola per scaglioni progressivi.</p>

        <div class="calculation">
          <h4>Scaglioni IRPEF 2024:</h4>
          <div class="calculation-step">
            <span class="label">Fino a € 28.000:</span>
            <span class="percentage">23%</span>
          </div>
          <div class="calculation-step">
            <span class="label">Da € 28.001 a € 50.000:</span>
            <span class="percentage">35%</span>
          </div>
          <div class="calculation-step">
            <span class="label">Oltre € 50.000:</span>
            <span class="percentage">43%</span>
          </div>
        </div>

        <div class="calculation">
          <h4>Esempio pratico - Reddito € 45.000:</h4>
          <div class="calculation-step">
            <span class="formula">€ 28.000 × 23%</span>
            <span class="amount">€ 6.440</span>
          </div>
          <div class="calculation-step">
            <span class="formula">€ 17.000 × 35%</span>
            <span class="amount">€ 5.950</span>
          </div>
          <div class="calculation-total">
            <span class="label">IRPEF totale:</span>
            <strong class="amount">€ 12.390</strong>
          </div>
        </div>

        <p><em>Nota: Il calcolo non include detrazioni e deduzioni applicabili.</em></p>
      `
    },

    // Limits and thresholds
    {
      patterns: [
        'quali sono i limiti',
        'limiti',
        'soglie',
        'requisiti',
        'massimali',
        'limite fatturato',
        'limite ricavi'
      ],
      response: `
        <h3>Limiti e Soglie Fiscali 2024</h3>
        
        <div class="calculation">
          <h4>Regime Forfettario:</h4>
          <div class="calculation-step">
            <span class="label">Ricavi massimi:</span>
            <span class="amount">€ 85.000</span>
          </div>
          <div class="calculation-step">
            <span class="label">Spese per lavoro dipendente:</span>
            <span class="amount">max € 20.000</span>
          </div>
          <div class="calculation-step">
            <span class="label">Beni strumentali:</span>
            <span class="amount">max € 20.000</span>
          </div>
        </div>

        <div class="calculation">
          <h4>Altri Limiti Importanti:</h4>
          <div class="calculation-step">
            <span class="label">Compensi professionali (Ritenuta d'acconto):</span>
            <span class="amount">€ 5.000</span>
          </div>
          <div class="calculation-step">
            <span class="label">Soglia per fatturazione elettronica:</span>
            <span class="amount">€ 400</span>
          </div>
          <div class="calculation-step">
            <span class="label">Limite contanti:</span>
            <span class="amount">€ 5.000</span>
          </div>
        </div>

        <p><strong>Requisiti per mantenere il forfettario:</strong></p>
        <ul>
          <li>Non superare i ricavi massimi dell'anno precedente</li>
          <li>Non avere dipendenti o collaboratori oltre i limiti</li>
          <li>Non partecipare contemporaneamente ad altri regimi agevolati</li>
          <li>Non esercitare attività prevalentemente commerciali</li>
        </ul>

        <p class="legal-ref">Legge di Bilancio 2024 - Art. 1, c. 54-89, L. 190/2014</p>
      `
    },

    // Default response for unmatched questions
    {
      patterns: [''],
      response: `
        <h3>Assistenza Fiscale PratikoAI</h3>
        <p>Ciao! Sono qui per aiutarti con le tue domande fiscali.</p>
        
        <p><strong>Posso assisterti su:</strong></p>
        <ul>
          <li>Regime forfettario e agevolazioni fiscali</li>
          <li>Calcoli IRPEF e imposte</li>
          <li>Limiti e soglie fiscali</li>
          <li>Detrazioni e deduzioni</li>
          <li>Adempimenti fiscali e scadenze</li>
        </ul>

        <p>Prova a chiedermi qualcosa come:</p>
        <ul>
          <li><em>"Come funziona il regime forfettario?"</em></li>
          <li><em>"Calcola IRPEF per un reddito di 50.000€"</em></li>
          <li><em>"Quali sono i limiti del forfettario?"</em></li>
        </ul>

        <p>Come posso aiutarti oggi?</p>
      `
    }
  ]

  /**
   * Find the best matching response for a user message
   */
  getResponse(userMessage: string): string {
    const normalizedMessage = userMessage.toLowerCase().trim()
    
    // Find the first response that matches any pattern
    for (const mockResponse of this.responses) {
      for (const pattern of mockResponse.patterns) {
        if (pattern && normalizedMessage.includes(pattern.toLowerCase())) {
          return mockResponse.response.trim()
        }
      }
    }
    
    // Return default response if no match found
    return this.responses[this.responses.length - 1].response.trim()
  }

  /**
   * Check if a message matches any specific pattern (for testing)
   */
  hasResponseFor(userMessage: string): boolean {
    const normalizedMessage = userMessage.toLowerCase().trim()
    
    // Check all responses except the default (last one)
    for (let i = 0; i < this.responses.length - 1; i++) {
      const mockResponse = this.responses[i]
      for (const pattern of mockResponse.patterns) {
        if (pattern && normalizedMessage.includes(pattern.toLowerCase())) {
          return true
        }
      }
    }
    
    return false
  }
}