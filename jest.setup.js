// Add all polyfills FIRST before any imports
const { TextEncoder, TextDecoder } = require('util');
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;

// Add Web Streams API polyfills
try {
  const {
    ReadableStream,
    WritableStream,
    TransformStream,
  } = require('node:stream/web');
  global.ReadableStream = global.ReadableStream || ReadableStream;
  global.WritableStream = global.WritableStream || WritableStream;
  global.TransformStream = global.TransformStream || TransformStream;
} catch (_error) {
  // Fallback for older Node versions
  global.ReadableStream = global.ReadableStream || class ReadableStream {};
  global.WritableStream = global.WritableStream || class WritableStream {};
  global.TransformStream = global.TransformStream || class TransformStream {};
}

// Add Headers polyfill
global.Headers =
  global.Headers ||
  class Headers {
    constructor(init) {
      this.map = new Map();
      if (init) {
        if (Array.isArray(init)) {
          init.forEach(([key, value]) =>
            this.map.set(key.toLowerCase(), value)
          );
        } else if (typeof init === 'object') {
          Object.entries(init).forEach(([key, value]) =>
            this.map.set(key.toLowerCase(), value)
          );
        }
      }
    }

    get(name) {
      return this.map.get(name.toLowerCase());
    }
    set(name, value) {
      this.map.set(name.toLowerCase(), value);
    }
    has(name) {
      return this.map.has(name.toLowerCase());
    }
    delete(name) {
      this.map.delete(name.toLowerCase());
    }
    entries() {
      return this.map.entries();
    }
    keys() {
      return this.map.keys();
    }
    values() {
      return this.map.values();
    }
  };

// Add Request polyfill
global.Request =
  global.Request ||
  class Request {
    constructor(input, init = {}) {
      this.url = typeof input === 'string' ? input : input.url;
      this.method = init.method || 'GET';
      this.headers = new Headers(init.headers);
      this.body = init.body;
    }
  };

// Add Response polyfill
global.Response =
  global.Response ||
  class Response {
    constructor(body, init = {}) {
      this.body = body;
      this.status = init.status || 200;
      this.statusText = init.statusText || 'OK';
      this.headers = new Headers(init.headers);
      this.ok = this.status >= 200 && this.status < 300;
    }

    json() {
      return Promise.resolve(JSON.parse(this.body || '{}'));
    }

    text() {
      return Promise.resolve(this.body || '');
    }

    static json(data, init) {
      return new Response(JSON.stringify(data), {
        ...init,
        headers: {
          'Content-Type': 'application/json',
          ...(init?.headers || {}),
        },
      });
    }
  };

// Now import everything else
import '@testing-library/jest-dom';
import 'whatwg-fetch';

// MSW server setup commented out due to Node.js compatibility issues
// import { server } from './src/mocks/server'

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
  takeRecords() {
    return [];
  }
};

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
global.localStorage = localStorageMock;

// Mock indexedDB
const indexedDBMock = {
  open: jest.fn(() => ({
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    result: {
      createObjectStore: jest.fn(),
      transaction: jest.fn(() => ({
        objectStore: jest.fn(() => ({
          get: jest.fn(),
          put: jest.fn(),
          delete: jest.fn(),
          clear: jest.fn(),
          getAll: jest.fn(),
        })),
      })),
    },
  })),
  deleteDatabase: jest.fn(),
};
global.indexedDB = indexedDBMock;

// Mock fetch
global.fetch = jest.fn();

// MSW server lifecycle hooks commented out due to compatibility issues
// beforeAll(() => {
//   server.listen()
// })

// afterEach(() => {
//   server.resetHandlers()
// })

// afterAll(() => {
//   server.close()
// })

// Reset all mocks before each test
beforeEach(() => {
  jest.clearAllMocks();
  localStorageMock.getItem.mockReset();
  localStorageMock.setItem.mockReset();
  localStorageMock.removeItem.mockReset();
  localStorageMock.clear.mockReset();
});
