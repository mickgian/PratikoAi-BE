// Mock for react-markdown ESM module
// This module uses ESM syntax which Jest can't parse by default
const React = require('react');

function ReactMarkdown({ children }) {
  return React.createElement(
    'div',
    { 'data-testid': 'mock-markdown' },
    children
  );
}

module.exports = ReactMarkdown;
module.exports.default = ReactMarkdown;
