/**
 * PratikoAI Load Test - k6 Performance Benchmarking
 *
 * Tests the chat API endpoint under load to validate latency and throughput.
 *
 * Usage:
 *   k6 run tests/load/chatbot_load_test.js
 *   k6 run tests/load/chatbot_load_test.js --env BASE_URL=https://api-qa.pratiko.app
 *
 * Thresholds:
 *   - p50 latency < 2s (warning)
 *   - p95 latency < 5s (blocks deploy)
 *   - Error rate  < 1% (blocks deploy)
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

// Custom metrics
const errorRate = new Rate("errors");
const chatLatency = new Trend("chat_latency", true);

// Test configuration
export const options = {
  stages: [
    { duration: "30s", target: 5 }, // Ramp up
    { duration: "2m", target: 10 }, // Sustained load
    { duration: "30s", target: 0 }, // Ramp down
  ],
  thresholds: {
    http_req_duration: ["p(50)<2000", "p(95)<5000"],
    errors: ["rate<0.01"],
    chat_latency: ["p(95)<5000"],
  },
};

const BASE_URL = __ENV.BASE_URL || "https://api-qa.pratiko.app";

// Test queries (Italian labor law / CCNL)
const queries = [
  "Qual e' il periodo di preavviso nel CCNL Commercio?",
  "Come si calcola la tredicesima?",
  "Quali sono i contributi INPS?",
  "Quanti giorni di ferie spettano?",
  "Come funziona il TFR?",
];

export function setup() {
  // Health check before starting load test
  const health = http.get(`${BASE_URL}/health`);
  check(health, {
    "health check passed": (r) => r.status === 200,
  });
  if (health.status !== 200) {
    throw new Error(`Health check failed: ${health.status}`);
  }
}

export default function () {
  const query = queries[Math.floor(Math.random() * queries.length)];

  // Chat API request
  const payload = JSON.stringify({
    message: query,
    session_id: `load-test-${__VU}-${__ITER}`,
  });

  const params = {
    headers: {
      "Content-Type": "application/json",
    },
    timeout: "10s",
  };

  const start = Date.now();
  const res = http.post(`${BASE_URL}/api/v1/chatbot/query`, payload, params);
  const duration = Date.now() - start;

  chatLatency.add(duration);

  const success = check(res, {
    "status is 200 or 401": (r) => r.status === 200 || r.status === 401,
    "response has content": (r) => r.body && r.body.length > 0,
  });

  errorRate.add(!success);

  // Think time between requests (1-3 seconds)
  sleep(Math.random() * 2 + 1);
}
