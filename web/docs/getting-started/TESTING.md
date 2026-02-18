# Testing Guide for PratikoAi WebApp

This document provides comprehensive information about the testing infrastructure for the PratikoAi web application.

## Overview

Our testing strategy follows Android development best practices, providing multiple layers of testing to ensure code quality and prevent regressions. Tests must pass before any code can be merged into the main branch.

## Table of Contents

- [Quick Start](#quick-start)
- [Testing Architecture](#testing-architecture)
- [Test Types](#test-types)
- [Running Tests](#running-tests)
- [Writing Tests](#writing-tests)
- [CI/CD Integration](#cicd-integration)
- [Coverage Requirements](#coverage-requirements)
- [Best Practices](#best-practices)

## Quick Start

```bash
# Install dependencies
npm install

# Run all unit tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage

# Run E2E tests
npm run test:e2e

# Run linter
npm run lint
```

## Testing Architecture

### Framework Stack

- **Jest**: Testing framework for unit and integration tests
- **React Testing Library**: Component testing utilities
- **Playwright**: End-to-end testing framework
- **MSW (Mock Service Worker)**: API mocking for reliable tests
- **Husky**: Git hooks for pre-commit testing
- **lint-staged**: Run tests only on changed files

### Directory Structure

```
web/
├── __tests__/
│   ├── fixtures/           # Mock data and test fixtures
│   │   └── mockData.ts     # Centralized mock data
│   ├── unit/               # Unit and integration tests
│   │   ├── StreamingHandler.test.ts
│   │   ├── useChatSessions.test.tsx
│   │   ├── ApiClient.test.ts
│   │   └── Button.test.tsx
│   ├── utils/              # Test utilities and helpers
│   │   └── testUtils.tsx   # Custom render functions
│   └── setup.test.ts       # Test setup validation
├── e2e/                    # End-to-end tests
│   └── happy-path.spec.ts  # User journey tests
├── src/mocks/              # MSW API mocks
│   ├── handlers.ts         # Request handlers
│   └── server.ts           # MSW server setup
├── jest.config.js          # Jest configuration
├── jest.setup.js           # Test environment setup
└── playwright.config.ts    # Playwright configuration
```

## Test Types

### 1. Unit Tests

Test individual functions, classes, and components in isolation.

**Examples:**

- API client methods
- Utility functions
- React hooks
- Individual components

**Location:** `__tests__/unit/`

### 2. Integration Tests

Test how different parts of the application work together.

**Examples:**

- StreamingHandler with API client
- Component integration with hooks
- State management flows

### 3. Component Tests

Test React components with user interactions.

**Examples:**

- Button interactions
- Form validation
- State changes

### 4. End-to-End Tests

Test complete user workflows in a real browser.

**Examples:**

- User registration flow
- Chat conversation flow
- Navigation between pages

**Location:** `e2e/`

## Running Tests

### Unit Tests

```bash
# Run all tests once
npm test

# Run tests in watch mode (during development)
npm run test:watch

# Run tests with coverage report
npm run test:coverage

# Run specific test file
npm test Button.test.tsx

# Run tests matching a pattern
npm test -- --testNamePattern="should render"
```

### End-to-End Tests

```bash
# Run all E2E tests
npm run test:e2e

# Run E2E tests with UI mode
npm run test:e2e:ui

# Run E2E tests in debug mode
npm run test:e2e:debug

# Run specific E2E test
npx playwright test happy-path.spec.ts
```

### All Tests

```bash
# Run all test suites
npm run test && npm run test:e2e
```

## Writing Tests

### Unit Test Example

```text
import { render, screen } from '@testing-library/react'
import { Button } from '@/components/ui/button'

describe('Button', () => {
  test('renders with correct text', () => {
    render(<Button>Click me</Button>)

    expect(screen.getByRole('button', { name: /click me/i }))
      .toBeInTheDocument()
  })
})
```

### Component Test with Interaction

```text
import userEvent from '@testing-library/user-event'

test('handles click events', async () => {
  const handleClick = jest.fn()
  const user = userEvent.setup()

  render(<Button onClick={handleClick}>Click me</Button>)

  await user.click(screen.getByRole('button'))
  expect(handleClick).toHaveBeenCalledTimes(1)
})
```

### E2E Test Example

```text
import { test, expect } from '@playwright/test'

test('user can navigate to chat', async ({ page }) => {
  await page.goto('/')

  await page.click('[data-testid="chat-button"]')

  await expect(page).toHaveURL(/\/chat/)
  await expect(page.locator('input')).toBeVisible()
})
```

### API Test Example

```text
import apiClient from '@/lib/api'

describe('ApiClient', () => {
  beforeEach(() => {
    global.fetch = jest.fn()
  })

  test('handles login successfully', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ access_token: 'token' })
    })

    const result = await apiClient.login('user', 'pass')

    expect(result.access_token).toBe('token')
  })
})
```

## CI/CD Integration

### GitHub Actions

Tests run automatically on:

- Every push to `main`, `develop`, or `DEV-*` branches
- Every pull request to `main` or `develop`

**Workflow:** `.github/workflows/test.yml`

### Branch Protection

- All tests must pass before PR can be merged
- Linting must pass
- Build must succeed

### Pre-commit Hooks

Husky runs the following on every commit:

- ESLint on changed files
- Jest tests for changed files
- Prettier formatting

## Coverage Requirements

### Thresholds (configured in `jest.config.js`)

- **Branches:** 70%
- **Functions:** 70%
- **Lines:** 80%
- **Statements:** 80%

### Viewing Coverage

```bash
npm run test:coverage
open coverage/lcov-report/index.html
```

### Coverage Exclusions

- `src/app/**/*.{js,jsx,ts,tsx}` (Next.js pages)
- `*.stories.{js,jsx,ts,tsx}` (Storybook files)
- `*.d.ts` (Type definitions)

## Best Practices

### General Testing Principles

1. **Write tests first** (TDD when possible)
2. **Test behavior, not implementation**
3. **Keep tests simple and focused**
4. **Use descriptive test names**
5. **Arrange, Act, Assert pattern**

### Component Testing

- Use `data-testid` for reliable element selection
- Test user interactions, not internal state
- Mock external dependencies
- Use realistic test data

### API Testing

- Mock all external API calls
- Test error scenarios
- Verify request parameters
- Test authentication flows

### E2E Testing

- Focus on critical user paths
- Keep tests independent
- Use page objects for complex interactions
- Test across different browsers

### Performance

- Use `beforeEach` and `afterEach` for setup/cleanup
- Mock heavy operations
- Avoid unnecessary DOM queries
- Use `screen` queries from React Testing Library

## Common Commands

### Development

```bash
# Run tests while developing
npm run test:watch

# Run specific test file
npm test ComponentName.test.tsx

# Debug failing test
npm test -- --verbose ComponentName.test.tsx
```

### CI/CD

```bash
# Full test suite (CI-like)
npm run lint && npm test -- --coverage --watchAll=false

# Build and test
npm run build && npm test
```

### Debugging

```bash
# Debug E2E tests
npm run test:e2e:debug

# Run E2E tests with UI
npm run test:e2e:ui

# Verbose Jest output
npm test -- --verbose
```

## Troubleshooting

### Common Issues

#### Tests timeout

- Increase Jest timeout in `jest.config.js`
- Check for unresolved promises
- Verify async/await usage

#### MSW not intercepting requests

- Ensure server is started in `jest.setup.js`
- Check handler URL patterns
- Verify request method (GET, POST, etc.)

#### E2E tests fail locally

- Check if dev server is running
- Verify port 3000 is available
- Update Playwright browsers: `npx playwright install`

#### Coverage too low

- Add tests for uncovered branches
- Remove exclusions from `jest.config.js`
- Focus on critical business logic

### Getting Help

1. Check Jest documentation: https://jestjs.io/docs/
2. React Testing Library guides: https://testing-library.com/docs/react-testing-library/intro/
3. Playwright documentation: https://playwright.dev/

## Contributing

When adding new features:

1. Write tests for new components/functions
2. Update existing tests if APIs change
3. Ensure coverage thresholds are met
4. Run full test suite before submitting PR

The testing infrastructure is designed to catch issues early and maintain code quality. Following these guidelines will help ensure a robust and maintainable codebase.
