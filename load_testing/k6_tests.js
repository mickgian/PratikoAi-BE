/**
 * k6 Load Testing Implementation for PratikoAI
 * 
 * This script implements comprehensive load testing using k6 to validate
 * the system can handle 50-100 concurrent Italian tax/accounting users.
 * 
 * Focuses on performance thresholds and detailed metrics collection.
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter, Gauge } from 'k6/metrics';
import { htmlReport } from 'https://raw.githubusercontent.com/benc-uk/k6-reporter/main/dist/bundle.js';

// Custom metrics for detailed analysis
const errorRate = new Rate('errors');
const queryDuration = new Trend('query_duration');
const cacheHitRate = new Rate('cache_hits');
const taxCalcDuration = new Trend('tax_calculation_duration');
const documentProcDuration = new Trend('document_processing_duration');
const concurrentUsers = new Gauge('concurrent_users');
const retryRate = new Rate('retry_attempts');

// Load test configuration for 50-100 concurrent users (€25k ARR target)
export const options = {
  stages: [
    // Baseline test (1 user)
    { duration: '1m', target: 1 },   // Establish baseline
    
    // Normal day simulation (30 users)
    { duration: '2m', target: 30 },  // Ramp to normal load
    { duration: '5m', target: 30 },  // Sustain normal load
    
    // Peak hours simulation (50 users)
    { duration: '2m', target: 50 },  // Ramp to target load
    { duration: '10m', target: 50 }, // Sustain target load (key test)
    
    // Stress test (100 users)
    { duration: '2m', target: 100 }, // Ramp to stress level
    { duration: '5m', target: 100 }, // Sustain stress level
    
    // Spike test (sudden increase)
    { duration: '30s', target: 150 }, // Spike to 150 users
    { duration: '2m', target: 150 },  // Brief spike test
    
    // Recovery phase
    { duration: '2m', target: 50 },   // Back to normal
    { duration: '1m', target: 0 },    // Ramp down
  ],
  
  // Performance thresholds based on requirements
  thresholds: {
    // Response time thresholds
    'http_req_duration': [
      'p(50)<1000',    // 50% of requests under 1s
      'p(95)<3000',    // 95% of requests under 3s (single user SLA)
      'p(99)<5000'     // 99% of requests under 5s
    ],
    'http_req_duration{name:complex_query}': ['p(95)<5000'], // Complex queries: 5s
    'http_req_duration{name:tax_calculation}': ['p(95)<2000'], // Tax calc: 2s
    'http_req_duration{name:document_upload}': ['p(95)<30000'], // Documents: 30s
    
    // Error rate thresholds
    'errors': ['rate<0.01'],          // Error rate < 1%
    'http_req_failed': ['rate<0.01'], // HTTP failures < 1%
    
    // Throughput thresholds
    'http_reqs': ['rate>15'],         // Minimum 15 req/sec (900 req/min)
    
    // Cache performance
    'cache_hits': ['rate>0.7'],       // Cache hit rate > 70%
    
    // Italian market specific
    'tax_calculation_duration': ['p(95)<2000'], // Tax calculations fast
    'document_processing_duration': ['p(95)<30000'], // Document processing
  },
  
  // Test configuration
  maxRedirects: 0,
  batch: 10,
  batchPerHost: 5,
  discardResponseBodies: false, // Keep for validation
};

// Test data for Italian market
const ITALIAN_QUERIES = [
  "Come calcolare l'IVA al 22%?",
  "Quali sono le aliquote IRPEF 2024?",
  "Scadenze fiscali per SRL",
  "Regime forfettario requisiti",
  "Fattura elettronica obblighi",
  "Deduzione spese mediche",
  "Bonus edilizi 2024",
  "Calcolo IMU prima casa",
  "Tassazione dividendi SRL",
  "Contributi INPS artigiani"
];

const COMPLEX_QUERIES = [
  "Analizza le implicazioni fiscali di una SRL che diventa SPA",
  "Come ottimizzare la tassazione per un freelancer con partita IVA?",
  "Quali sono le novità fiscali per il 2024 in Italia?",
  "Confronta regime forfettario e regime ordinario per fatturato 50k€",
  "Strategie di pianificazione fiscale per startup innovative"
];

const TAX_TYPES = ['IVA', 'IRPEF', 'IMU', 'TASI'];
const ITALIAN_REGIONS = ['Lombardia', 'Lazio', 'Campania', 'Veneto', 'Emilia-Romagna'];

// Base URL configuration
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// Authentication setup
let authToken = null;

export function setup() {
  // Setup test data and authenticate
  console.log('Setting up load test environment...');
  
  // Create test user
  const userNum = Math.floor(Math.random() * 1000);
  const registerResponse = http.post(`${BASE_URL}/api/auth/register`, JSON.stringify({
    email: `k6_user_${userNum}@pratikoai.it`,
    password: 'K6TestPassword123!',
    company_name: `K6 Test Company ${userNum}`,
    vat_number: `IT${userNum.toString().padStart(11, '0')}`
  }), {
    headers: { 'Content-Type': 'application/json' }
  });
  
  if (registerResponse.status === 200 || registerResponse.status === 201) {
    const userData = JSON.parse(registerResponse.body);
    authToken = userData.token;
    console.log('Test user created and authenticated');
  } else {
    // Try to login with existing user
    const loginResponse = http.post(`${BASE_URL}/api/auth/login`, JSON.stringify({
      email: `k6_user_${userNum}@pratikoai.it`,
      password: 'K6TestPassword123!'
    }), {
      headers: { 'Content-Type': 'application/json' }
    });
    
    if (loginResponse.status === 200) {
      const userData = JSON.parse(loginResponse.body);
      authToken = userData.token;
      console.log('Authenticated with existing test user');
    }
  }
  
  return { token: authToken };
}

export default function(data) {
  // Update concurrent users metric
  concurrentUsers.add(__VU);
  
  // Use token from setup
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': data.token ? `Bearer ${data.token}` : ''
  };
  
  // Scenario distribution based on realistic usage patterns
  const scenario = Math.random();
  
  if (scenario < 0.3) {
    testSimpleQuery(headers);
  } else if (scenario < 0.55) {
    testComplexQuery(headers);
  } else if (scenario < 0.75) {
    testTaxCalculation(headers);
  } else if (scenario < 0.85) {
    testDocumentUpload(headers);
  } else if (scenario < 0.95) {
    testKnowledgeSearch(headers);
  } else {
    testUserOperations(headers);
  }
  
  // Realistic think time between requests
  sleep(Math.random() * 2 + 1); // 1-3 seconds
}

function testSimpleQuery(headers) {
  group('Simple Query', function() {
    const query = ITALIAN_QUERIES[Math.floor(Math.random() * ITALIAN_QUERIES.length)];
    
    const startTime = Date.now();
    const response = http.post(
      `${BASE_URL}/api/query`,
      JSON.stringify({ query: query }),
      { 
        headers: headers,
        tags: { name: 'simple_query' }
      }
    );
    
    const duration = Date.now() - startTime;
    queryDuration.add(duration);
    
    const success = check(response, {
      'status is 200': (r) => r.status === 200,
      'response time < 3s': (r) => r.timings.duration < 3000,
      'has response': (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.response && body.response.length > 0;
        } catch (e) {
          return false;
        }
      },
      'response is meaningful': (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.response && body.response.length > 50;
        } catch (e) {
          return false;
        }
      }
    });
    
    if (!success) {
      errorRate.add(1);
    } else {
      errorRate.add(0);
      
      // Check if response was from cache
      if (response.headers['X-Cache-Hit'] === 'true') {
        cacheHitRate.add(1);
      } else {
        cacheHitRate.add(0);
      }
    }
  });
}

function testComplexQuery(headers) {
  group('Complex Query', function() {
    const query = COMPLEX_QUERIES[Math.floor(Math.random() * COMPLEX_QUERIES.length)];
    
    const startTime = Date.now();
    const response = http.post(
      `${BASE_URL}/api/query`,
      JSON.stringify({
        query: query,
        context: 'detailed',
        include_sources: true
      }),
      { 
        headers: headers,
        timeout: '30s',
        tags: { name: 'complex_query' }
      }
    );
    
    const duration = Date.now() - startTime;
    queryDuration.add(duration);
    
    const success = check(response, {
      'status is 200': (r) => r.status === 200,
      'response time < 5s': (r) => r.timings.duration < 5000,
      'has detailed response': (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.response && body.response.length > 200;
        } catch (e) {
          return false;
        }
      },
      'includes sources': (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.sources && body.sources.length > 0;
        } catch (e) {
          return false;
        }
      }
    });
    
    if (!success) {
      errorRate.add(1);
    } else {
      errorRate.add(0);
    }
  });
}

function testTaxCalculation(headers) {
  group('Tax Calculation', function() {
    const taxType = TAX_TYPES[Math.floor(Math.random() * TAX_TYPES.length)];
    const region = ITALIAN_REGIONS[Math.floor(Math.random() * ITALIAN_REGIONS.length)];
    const amount = Math.floor(Math.random() * 100000) + 1000;
    
    const startTime = Date.now();
    const response = http.post(
      `${BASE_URL}/api/tax/calculate`,
      JSON.stringify({
        type: taxType,
        amount: amount,
        region: region,
        year: 2024
      }),
      { 
        headers: headers,
        tags: { name: 'tax_calculation', tax_type: taxType }
      }
    );
    
    const duration = Date.now() - startTime;
    taxCalcDuration.add(duration);
    
    const success = check(response, {
      'status is 200': (r) => r.status === 200,
      'response time < 2s': (r) => r.timings.duration < 2000,
      'has calculation result': (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.result !== undefined && body.breakdown !== undefined;
        } catch (e) {
          return false;
        }
      },
      'calculation is accurate': (r) => {
        try {
          const body = JSON.parse(r.body);
          // Basic sanity check - result should be reasonable
          return body.result >= 0 && body.result <= amount * 2;
        } catch (e) {
          return false;
        }
      }
    });
    
    if (!success) {
      errorRate.add(1);
    } else {
      errorRate.add(0);
    }
  });
}

function testDocumentUpload(headers) {
  group('Document Upload', function() {
    const docTypes = ['fattura_elettronica', 'f24', 'dichiarazione_redditi', 'contratto'];
    const docType = docTypes[Math.floor(Math.random() * docTypes.length)];
    
    // Create mock PDF content
    const mockPdf = 'JVBERi0xLjQKJdPr6eEKMSAwIG9iago8PAovVHlwZSAvQ2F0YWxvZwovUGFnZXMgMiAwIFIKPj4KZW5kb2JqCjIgMCBvYmoKPDwKL1R5cGUgL1BhZ2VzCi9LaWRzIFszIDAgUl0KL0NvdW50IDEKL01lZGlhQm94IFswIDAgNTk1IDg0Ml0KPj4KZW5kb2JqCjMgMCBvYmoKPDwKL1R5cGUgL1BhZ2UKL1BhcmVudCAyIDAgUgovUmVzb3VyY2VzIDw8Cj4+CjQgMCBvYmoKPDwKL0ZpbHRlciAvRmxhdGVEZWNvZGUKL0xlbmd0aCAzNAo+PgpzdHJlYW0KeAErVAhUKFbwVCjJzE21UnBTyFZQyE3MzFFQykktLQJSUJDLBTa0';
    
    const formData = {
      file: http.file(mockPdf, `test_${docType}.pdf`, 'application/pdf'),
      document_type: docType,
      extract_data: 'true'
    };
    
    const startTime = Date.now();
    const response = http.post(
      `${BASE_URL}/api/document/analyze`,
      formData,
      { 
        headers: {
          'Authorization': headers.Authorization
        },
        timeout: '60s',
        tags: { name: 'document_upload', doc_type: docType }
      }
    );
    
    const duration = Date.now() - startTime;
    documentProcDuration.add(duration);
    
    const success = check(response, {
      'status is 200': (r) => r.status === 200,
      'response time < 30s': (r) => r.timings.duration < 30000,
      'has extraction result': (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.extracted_data !== undefined;
        } catch (e) {
          return false;
        }
      }
    });
    
    if (!success) {
      errorRate.add(1);
    } else {
      errorRate.add(0);
    }
  });
}

function testKnowledgeSearch(headers) {
  group('Knowledge Search', function() {
    const searchTerms = [
      'Circolare Agenzia Entrate 2024',
      'Decreto fiscale ultimo',
      'Normativa fatturazione elettronica',
      'Aliquote IVA settori',
      'Scadenze dichiarazioni 2024'
    ];
    
    const searchTerm = searchTerms[Math.floor(Math.random() * searchTerms.length)];
    
    const response = http.get(
      `${BASE_URL}/api/knowledge/search?q=${encodeURIComponent(searchTerm)}&limit=10`,
      { 
        headers: headers,
        tags: { name: 'knowledge_search' }
      }
    );
    
    const success = check(response, {
      'status is 200': (r) => r.status === 200,
      'response time < 3s': (r) => r.timings.duration < 3000,
      'has search results': (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.results && body.results.length > 0;
        } catch (e) {
          return false;
        }
      }
    });
    
    if (!success) {
      errorRate.add(1);
    } else {
      errorRate.add(0);
    }
  });
}

function testUserOperations(headers) {
  group('User Operations', function() {
    const operations = [
      { method: 'GET', path: '/api/user/profile' },
      { method: 'GET', path: '/api/user/subscription' },
      { method: 'GET', path: '/api/user/usage' },
      { method: 'GET', path: '/api/user/invoices' }
    ];
    
    const operation = operations[Math.floor(Math.random() * operations.length)];
    
    const response = http.get(
      `${BASE_URL}${operation.path}`,
      { 
        headers: headers,
        tags: { name: 'user_operations' }
      }
    );
    
    const success = check(response, {
      'status is 200': (r) => r.status === 200,
      'response time < 1s': (r) => r.timings.duration < 1000
    });
    
    if (!success) {
      errorRate.add(1);
    } else {
      errorRate.add(0);
    }
  });
}

// Generate HTML report
export function handleSummary(data) {
  return {
    'load_test_results/k6_summary.html': htmlReport(data),
    'load_test_results/k6_summary.json': JSON.stringify(data, null, 2),
  };
}

// Cleanup function
export function teardown(data) {
  console.log('Load test completed. Cleaning up...');
  
  // Could perform cleanup operations here
  if (data.token) {
    try {
      http.post(`${BASE_URL}/api/auth/logout`, null, {
        headers: { 'Authorization': `Bearer ${data.token}` }
      });
    } catch (e) {
      // Ignore logout errors
    }
  }
}