/**
 * Type definitions for test utilities
 * Used to replace 'any' types in test files
 */

export interface MockStreamingCallbacks {
  onMessage: (content: string) => void
  onComplete: () => void
  onError: (error: Error) => void
}

export interface MockStreamingService {
  instanceId: number | string
  sendMessage: jest.MockedFunction<(message: string) => Promise<void>>
  cleanup: jest.MockedFunction<() => void>
  abort: jest.MockedFunction<() => void>
}

export interface MockChatSession {
  id: string
  token: string
  name?: string
  createdAt?: string
}

export interface MockChatState {
  messages: unknown[]
  currentSessionId: string | null
  isStreaming: boolean
  streamingContent: string
  [key: string]: unknown
}

export interface TestRenderOptions {
  initialState?: Partial<MockChatState>
  mockCallbacks?: Partial<MockStreamingCallbacks>
}

export interface StreamingTestContext {
  instances: MockStreamingService[]
  callbacks: (() => void)[]
  messageCount: number
  duplicateDetected: boolean
}

// Generic event handler type for tests
export type TestEventHandler = (event: unknown) => void

// Mock function type for test utilities
export type MockFunction<T extends (...args: unknown[]) => unknown> = jest.MockedFunction<T>

// Component props type for testing
export interface TestComponentProps {
  [key: string]: unknown
}