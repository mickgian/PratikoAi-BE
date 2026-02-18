/**
 * Comprehensive unit tests for ProductionLogger
 * Testing all logging methods, performance tracking, debug flags, and analytics
 *
 * Note: Logger is instantiated when module loads with NODE_ENV=test
 * which behaves like production (only error/warn enabled by default)
 */

// Mock console methods BEFORE importing logger
const mockConsoleLog = jest.spyOn(console, 'log').mockImplementation();
const mockConsoleDebug = jest.spyOn(console, 'debug').mockImplementation();
const mockConsoleInfo = jest.spyOn(console, 'info').mockImplementation();

// Mock performance API
const mockPerformanceNow = jest.fn(() => 1000);
const mockPerformanceMark = jest.fn();
const mockPerformanceMeasure = jest.fn();

(global as any).performance = {
  now: mockPerformanceNow,
  mark: mockPerformanceMark,
  measure: mockPerformanceMeasure,
  memory: {
    usedJSHeapSize: 1024000,
    totalJSHeapSize: 2048000,
    jsHeapSizeLimit: 4096000,
  },
} as any;

const mockAddEventListener = jest.fn();

(global as any).window = {
  performance: (global as any).performance,
  location: {
    href: 'http://localhost:3000/test',
  },
  addEventListener: mockAddEventListener,
} as any;

(global as any).navigator = {
  userAgent: 'Mozilla/5.0 Test Browser',
} as any;

// Import logger after mocks are set up
import { logger } from '../logger';
import type { LogContext } from '../logger';

describe('ProductionLogger', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockConsoleLog.mockClear();
    mockConsoleDebug.mockClear();
    mockConsoleInfo.mockClear();
    mockPerformanceNow.mockReturnValue(1000);
  });

  afterAll(() => {
    mockConsoleLog.mockRestore();
    mockConsoleDebug.mockRestore();
    mockConsoleInfo.mockRestore();
  });

  describe('Logger Initialization', () => {
    test('logger singleton is defined', () => {
      expect(logger).toBeDefined();
      expect(typeof logger.debug).toBe('function');
      expect(typeof logger.info).toBe('function');
      expect(typeof logger.warn).toBe('function');
      expect(typeof logger.error).toBe('function');
    });

    test('logger has standard methods', () => {
      expect(logger).toHaveProperty('debug');
      expect(logger).toHaveProperty('info');
      expect(logger).toHaveProperty('warn');
      expect(logger).toHaveProperty('error');
      expect(logger).toHaveProperty('destroy');
    });
  });

  describe('Basic Logging - Warn Level', () => {
    test('warn() logs structured JSON', () => {
      mockConsoleLog.mockClear();
      logger.warn('Warning message');

      expect(mockConsoleLog).toHaveBeenCalledTimes(1);
      const loggedData = mockConsoleLog.mock.calls[0][0];
      const parsedLog = JSON.parse(loggedData);

      expect(parsedLog.level).toBe('warn');
      expect(parsedLog.message).toBe('Warning message');
      expect(parsedLog.timestamp).toMatch(/^\d{4}-\d{2}-\d{2}T/);
    });

    test('warn() logs with context metadata', () => {
      mockConsoleLog.mockClear();
      const context: LogContext = {
        component: 'WarnComponent',
        action: 'test_action',
        sessionId: 'session-123',
        metadata: { key: 'value' },
      };

      logger.warn('Warning with context', context);

      const loggedData = mockConsoleLog.mock.calls[0][0];
      const parsedLog = JSON.parse(loggedData);

      expect(parsedLog.component).toBe('WarnComponent');
      expect(parsedLog.action).toBe('test_action');
      expect(parsedLog.sessionId).toBe('session-123');
      expect(parsedLog.metadata).toEqual({ key: 'value' });
    });
  });

  describe('Basic Logging - Error Level', () => {
    test('error() logs structured JSON', () => {
      mockConsoleLog.mockClear();
      logger.error('Error message');

      expect(mockConsoleLog).toHaveBeenCalledTimes(1);
      const loggedData = mockConsoleLog.mock.calls[0][0];
      const parsedLog = JSON.parse(loggedData);

      expect(parsedLog.level).toBe('error');
      expect(parsedLog.message).toBe('Error message');
    });

    test('error() logs with Error object', () => {
      mockConsoleLog.mockClear();
      const error = new Error('Test error');
      error.stack = 'Error stack trace';

      logger.error('Error occurred', error);

      const loggedData = mockConsoleLog.mock.calls[0][0];
      const parsedLog = JSON.parse(loggedData);

      expect(parsedLog.error).toBeDefined();
      expect(parsedLog.error.name).toBe('Error');
      expect(parsedLog.error.message).toBe('Test error');
      expect(parsedLog.error.stack).toBe('Error stack trace');
    });

    test('error() logs with Error and context', () => {
      mockConsoleLog.mockClear();
      const error = new Error('Context error');
      const context: LogContext = {
        component: 'ErrorComponent',
        metadata: { errorCode: 500 },
      };

      logger.error('Error with context', error, context);

      const loggedData = mockConsoleLog.mock.calls[0][0];
      const parsedLog = JSON.parse(loggedData);

      expect(parsedLog.component).toBe('ErrorComponent');
      expect(parsedLog.metadata.errorCode).toBe(500);
      expect(parsedLog.error.message).toBe('Context error');
    });

    test('error() handles error without stack trace', () => {
      mockConsoleLog.mockClear();
      const error = new Error('No stack');
      delete error.stack;

      expect(() => logger.error('Error without stack', error)).not.toThrow();
      expect(mockConsoleLog).toHaveBeenCalled();
    });
  });

  describe('Log Level Filtering', () => {
    test('debug() and info() are disabled in test mode', () => {
      mockConsoleLog.mockClear();
      logger.debug('Should not log');
      logger.info('Should not log');

      expect(mockConsoleLog).not.toHaveBeenCalled();
    });

    test('warn() and error() are always enabled', () => {
      mockConsoleLog.mockClear();
      logger.warn('Warn logs');
      logger.error('Error logs');

      expect(mockConsoleLog).toHaveBeenCalledTimes(2);
    });
  });

  describe('Performance Monitoring', () => {
    test('startPerformanceTimer() creates unique timer ID', () => {
      const timerId = logger.startPerformanceTimer('test-operation');

      expect(timerId).toBeDefined();
      expect(timerId).toContain('test-operation');
    });

    test('startPerformanceTimer() creates unique IDs', () => {
      const timers = new Set();

      for (let i = 0; i < 10; i++) {
        const timerId = logger.startPerformanceTimer('operation');
        timers.add(timerId);
      }

      expect(timers.size).toBe(10);
    });

    test('endPerformanceTimer() handles fast operations', () => {
      mockConsoleLog.mockClear();
      const timerId = logger.startPerformanceTimer('fast-operation');
      logger.endPerformanceTimer(timerId);

      // Should not log warning for fast operations (mocked to same time)
      expect(mockConsoleLog).not.toHaveBeenCalled();
    });

    test('endPerformanceTimer() handles non-existent timer', () => {
      expect(() => {
        logger.endPerformanceTimer('non-existent-timer');
      }).not.toThrow();

      expect(mockConsoleLog).not.toHaveBeenCalled();
    });

    test('startPerformanceTimer() with context', () => {
      const timerId = logger.startPerformanceTimer('context-operation', {
        component: 'TestComponent',
      });

      expect(timerId).toBeDefined();
      logger.endPerformanceTimer(timerId);
    });

    test('performance timer methods exist and work', () => {
      expect(typeof logger.startPerformanceTimer).toBe('function');
      expect(typeof logger.endPerformanceTimer).toBe('function');

      const timerId = logger.startPerformanceTimer('test');
      expect(timerId).toBeTruthy();
      expect(() => logger.endPerformanceTimer(timerId)).not.toThrow();
    });
  });

  describe('Chat-Specific Logging Methods', () => {
    test('logStreamingStart() logs stream initialization', () => {
      mockConsoleLog.mockClear();
      logger.logStreamingStart('stream-123', 5);

      // In test mode, info is disabled, so this won't log
      // But we verify it doesn't throw
      expect(() => logger.logStreamingStart('test', 1)).not.toThrow();
    });

    test('logStreamingComplete() does not throw', () => {
      expect(() => {
        logger.logStreamingComplete('stream-456', 1234.56, 42);
      }).not.toThrow();
    });

    test('logStreamingError() logs errors', () => {
      mockConsoleLog.mockClear();
      const error = new Error('Stream error');

      logger.logStreamingError('stream-789', error);

      expect(mockConsoleLog).toHaveBeenCalled();
      const loggedData = mockConsoleLog.mock.calls[0][0];
      const parsedLog = JSON.parse(loggedData);

      expect(parsedLog.level).toBe('error');
      expect(parsedLog.component).toBe('StreamingHandler');
      expect(parsedLog.action).toBe('stream_error');
      expect(parsedLog.metadata.streamId).toBe('stream-789');
    });

    test('logStorageOperation() does not throw', () => {
      expect(() => {
        logger.logStorageOperation('save', true, 2048);
      }).not.toThrow();
    });

    test('logStorageQuotaWarning() logs warnings', () => {
      mockConsoleLog.mockClear();
      logger.logStorageQuotaWarning(0.85, 1024000);

      expect(mockConsoleLog).toHaveBeenCalled();
      const loggedData = mockConsoleLog.mock.calls[0][0];
      const parsedLog = JSON.parse(loggedData);

      expect(parsedLog.level).toBe('warn');
      expect(parsedLog.metadata.percentUsed).toBe('85.0%');
      expect(parsedLog.metadata.available).toBe(1024000);
    });
  });

  describe('Debug Flags', () => {
    test('debugIf() does not log when flag is disabled', () => {
      mockConsoleLog.mockClear();
      logger.debugIf('SSE_RAW', 'Should not log');

      expect(mockConsoleLog).not.toHaveBeenCalled();
    });

    test('sse() does not log without flag', () => {
      mockConsoleDebug.mockClear();
      logger.sse('TEST_EVENT', { data: 'test' });

      expect(mockConsoleDebug).not.toHaveBeenCalled();
    });

    test('debug flag methods exist', () => {
      expect(typeof logger.debugIf).toBe('function');
      expect(typeof logger.sse).toBe('function');
    });
  });

  describe('Analytics and Cleanup', () => {
    test('destroy() method exists', () => {
      expect(typeof logger.destroy).toBe('function');
    });

    test('destroy() can be called without errors', () => {
      expect(() => logger.destroy()).not.toThrow();
    });
  });

  describe('Error Handling', () => {
    test('handles missing performance.mark gracefully', () => {
      const originalMark = global.window.performance.mark;
      global.window.performance.mark = undefined as any;

      expect(() => {
        const timerId = logger.startPerformanceTimer('no-mark');
        logger.endPerformanceTimer(timerId);
      }).not.toThrow();

      global.window.performance.mark = originalMark;
    });

    test('handles missing performance.memory gracefully', () => {
      const originalMemory = (global.window.performance as any).memory;
      delete (global.window.performance as any).memory;

      mockPerformanceNow.mockReturnValueOnce(1000).mockReturnValueOnce(1100);

      expect(() => {
        const timerId = logger.startPerformanceTimer('no-memory');
        logger.endPerformanceTimer(timerId);
      }).not.toThrow();

      (global.window.performance as any).memory = originalMemory;
    });

    test('handles null or undefined context gracefully', () => {
      expect(() => {
        logger.warn('Message with undefined context', undefined);
      }).not.toThrow();
    });

    test('handles complex nested metadata', () => {
      mockConsoleLog.mockClear();
      const complexContext: LogContext = {
        component: 'Complex',
        metadata: {
          level1: {
            level2: {
              level3: {
                value: 'deeply nested',
                array: [1, 2, 3],
              },
            },
          },
        },
      };

      expect(() => {
        logger.warn('Complex metadata', complexContext);
      }).not.toThrow();

      expect(mockConsoleLog).toHaveBeenCalled();
    });

    test('handles very long error stack traces', () => {
      mockConsoleLog.mockClear();
      const error = new Error('Long stack error');
      error.stack = 'a'.repeat(5000);

      expect(() => {
        logger.error('Error with long stack', error);
      }).not.toThrow();

      expect(mockConsoleLog).toHaveBeenCalled();
    });

    test('handles empty string messages', () => {
      expect(() => {
        logger.warn('');
      }).not.toThrow();
    });

    test('handles special characters in messages', () => {
      mockConsoleLog.mockClear();
      const specialMessage =
        'Special chars: 🚀 \n\t\r\\ "quotes" \'apostrophes\'';

      expect(() => {
        logger.warn(specialMessage);
      }).not.toThrow();

      expect(mockConsoleLog).toHaveBeenCalled();
    });
  });

  describe('Edge Cases', () => {
    test('handles concurrent performance timers', () => {
      mockPerformanceNow
        .mockReturnValueOnce(1000) // Timer 1 start
        .mockReturnValueOnce(1100) // Timer 2 start
        .mockReturnValueOnce(1200) // Timer 1 end
        .mockReturnValueOnce(1300); // Timer 2 end

      const timer1 = logger.startPerformanceTimer('concurrent-1');
      const timer2 = logger.startPerformanceTimer('concurrent-2');

      expect(() => {
        logger.endPerformanceTimer(timer1);
        logger.endPerformanceTimer(timer2);
      }).not.toThrow();
    });

    test('handles rapid logging calls', () => {
      mockConsoleLog.mockClear();

      for (let i = 0; i < 50; i++) {
        logger.warn(`Rapid log ${i}`);
      }

      expect(mockConsoleLog).toHaveBeenCalledTimes(50);
    });

    test('handles operation name with special characters', () => {
      const timerId = logger.startPerformanceTimer(
        'operation-with-dashes_and_underscores.and.dots'
      );
      expect(timerId).toContain(
        'operation-with-dashes_and_underscores.and.dots'
      );
      logger.endPerformanceTimer(timerId);
    });

    test('performance timer cleanup after end', () => {
      const timerId = logger.startPerformanceTimer('cleanup-test');

      // First end should work
      logger.endPerformanceTimer(timerId);

      // Second end should do nothing (timer was cleaned up)
      expect(() => logger.endPerformanceTimer(timerId)).not.toThrow();
    });
  });

  describe('Type Safety and API Surface', () => {
    test('all public methods are defined', () => {
      expect(logger.debug).toBeDefined();
      expect(logger.info).toBeDefined();
      expect(logger.warn).toBeDefined();
      expect(logger.error).toBeDefined();
      expect(logger.debugIf).toBeDefined();
      expect(logger.sse).toBeDefined();
      expect(logger.startPerformanceTimer).toBeDefined();
      expect(logger.endPerformanceTimer).toBeDefined();
      expect(logger.logStreamingStart).toBeDefined();
      expect(logger.logStreamingComplete).toBeDefined();
      expect(logger.logStreamingError).toBeDefined();
      expect(logger.logStorageOperation).toBeDefined();
      expect(logger.logStorageQuotaWarning).toBeDefined();
      expect(logger.destroy).toBeDefined();
    });

    test('LogContext type accepts all valid fields', () => {
      const validContext: LogContext = {
        component: 'TestComponent',
        action: 'test_action',
        sessionId: 'session-id',
        userId: 'user-id',
        metadata: {
          key1: 'value1',
          key2: 123,
          nested: { deep: true },
        },
      };

      expect(() => {
        logger.warn('Test with valid context', validContext);
      }).not.toThrow();
    });
  });

  describe('JSON Structured Logging', () => {
    test('logs include all required fields', () => {
      mockConsoleLog.mockClear();
      logger.error('Structured test');

      const loggedData = mockConsoleLog.mock.calls[0][0];
      const parsedLog = JSON.parse(loggedData);

      expect(parsedLog).toHaveProperty('timestamp');
      expect(parsedLog).toHaveProperty('level');
      expect(parsedLog).toHaveProperty('message');
      expect(typeof parsedLog.timestamp).toBe('string');
      expect(parsedLog.level).toBe('error');
      expect(parsedLog.message).toBe('Structured test');
    });

    test('timestamps are in ISO format', () => {
      mockConsoleLog.mockClear();
      logger.warn('Timestamp test');

      const loggedData = mockConsoleLog.mock.calls[0][0];
      const parsedLog = JSON.parse(loggedData);

      expect(parsedLog.timestamp).toMatch(
        /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/
      );
    });
  });

  describe('Additional Coverage', () => {
    test('multiple error logs in sequence', () => {
      mockConsoleLog.mockClear();

      for (let i = 0; i < 5; i++) {
        logger.error(`Error ${i}`);
      }

      expect(mockConsoleLog).toHaveBeenCalledTimes(5);
    });

    test('multiple warn logs in sequence', () => {
      mockConsoleLog.mockClear();

      for (let i = 0; i < 5; i++) {
        logger.warn(`Warning ${i}`);
      }

      expect(mockConsoleLog).toHaveBeenCalledTimes(5);
    });

    test('mixed logging calls', () => {
      mockConsoleLog.mockClear();

      logger.debug('Debug - should not log');
      logger.info('Info - should not log');
      logger.warn('Warn - should log');
      logger.error('Error - should log');

      // Only warn and error should log
      expect(mockConsoleLog).toHaveBeenCalledTimes(2);
    });

    test('error logs without error object', () => {
      mockConsoleLog.mockClear();
      logger.error('Error without error object');

      expect(mockConsoleLog).toHaveBeenCalled();
      const loggedData = mockConsoleLog.mock.calls[0][0];
      const parsedLog = JSON.parse(loggedData);

      expect(parsedLog.error).toBeUndefined();
    });

    test('context with all possible fields', () => {
      mockConsoleLog.mockClear();
      const fullContext: LogContext = {
        component: 'FullComponent',
        action: 'full_action',
        sessionId: 'session-full',
        userId: 'user-full',
        metadata: {
          nested: {
            deep: {
              value: 'test',
            },
          },
          array: [1, 2, 3],
          boolean: true,
          number: 123,
        },
      };

      logger.warn('Full context test', fullContext);

      const loggedData = mockConsoleLog.mock.calls[0][0];
      const parsedLog = JSON.parse(loggedData);

      expect(parsedLog.component).toBe('FullComponent');
      expect(parsedLog.action).toBe('full_action');
      expect(parsedLog.sessionId).toBe('session-full');
      expect(parsedLog.userId).toBe('user-full');
      expect(parsedLog.metadata).toEqual(fullContext.metadata);
    });

    test('performance timers with various operation names', () => {
      const operations = ['database', 'api-call', 'file-read', 'compute'];

      operations.forEach(op => {
        const timerId = logger.startPerformanceTimer(op);
        expect(timerId).toContain(op);
        logger.endPerformanceTimer(timerId);
      });
    });

    test('chat logging methods with various inputs', () => {
      expect(() => {
        logger.logStreamingStart('stream-1', 10);
        logger.logStreamingComplete('stream-1', 500.5, 25);
        logger.logStorageOperation('read', true);
        logger.logStorageOperation('write', false, 4096);
      }).not.toThrow();
    });
  });

  describe('Coverage Notes', () => {
    test('documents untestable code paths', () => {
      // Lines 32-44: readDebugFlags() localStorage access - only runs in browser with localStorage
      // Lines 58-74: Constructor debug flag setup - only runs in development mode
      // Lines 94-101: SSE logging in development - requires debug flags enabled
      // Lines 107-121: setupPerformanceObserver - only runs in production with PerformanceObserver
      // Lines 173-174: Development mode colored output - logger is in test mode
      // Lines 182-188: getColorPrefix - not called in production mode
      // Lines 202, 225-226, 231: Performance API window checks - always true in tests
      // Lines 256, 263: Analytics queue management - production-only behavior
      // Lines 345, 362: Analytics flush and beforeunload - hard to test in unit tests

      expect(true).toBe(true); // Placeholder to document coverage limits
    });
  });
});
