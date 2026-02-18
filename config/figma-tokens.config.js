// Figma Design Token Sync Configuration
module.exports = {
  source: ['./tokens.json'],
  platforms: {
    css: {
      transformGroup: 'css',
      buildPath: './src/styles/',
      files: [
        {
          destination: 'tokens.css',
          format: 'css/variables',
          options: {
            outputReferences: true
          }
        }
      ]
    },
    js: {
      transformGroup: 'js',
      buildPath: './src/tokens/',
      files: [
        {
          destination: 'index.js',
          format: 'javascript/es6'
        },
        {
          destination: 'tokens.d.ts',
          format: 'typescript/es6-declarations'
        }
      ]
    },
    figma: {
      transformGroup: 'figma',
      buildPath: './.figma/tokens/',
      files: [
        {
          destination: 'design-tokens.json',
          format: 'figma/tokens'
        }
      ]
    }
  },
  transform: {
    'size/px': {
      type: 'value',
      matcher: (token) => token.type === 'dimension',
      transformer: (token) => `${token.value}px`
    },
    'color/hex': {
      type: 'value', 
      matcher: (token) => token.type === 'color',
      transformer: (token) => token.value
    }
  },
  format: {
    'figma/tokens': ({ dictionary }) => {
      return JSON.stringify({
        version: '1.0.0',
        tokens: dictionary.allTokens.reduce((acc, token) => {
          const path = token.path.join('.');
          acc[path] = {
            value: token.value,
            type: token.type,
            description: token.comment || token.description
          };
          return acc;
        }, {})
      }, null, 2);
    }
  }
};