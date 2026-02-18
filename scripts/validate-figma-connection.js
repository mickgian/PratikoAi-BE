#!/usr/bin/env node

/**
 * Figma API Connection Validation Script
 * Tests direct Figma API access and MCP server connectivity
 */

const https = require('https');
const { execSync } = require('child_process');
require('dotenv').config({ path: '.env.local' });

const FIGMA_TOKEN = process.env.FIGMA_ACCESS_TOKEN;
const FIGMA_FILE_ID = process.env.FIGMA_FILE_ID;

console.log('🔍 Figma Connection Validation\n');

// Test 1: Environment Variables
console.log('1️⃣ Checking environment variables...');
if (!FIGMA_TOKEN) {
  console.error('❌ FIGMA_ACCESS_TOKEN not found in .env.local');
  process.exit(1);
}
if (!FIGMA_FILE_ID) {
  console.error('❌ FIGMA_FILE_ID not found in .env.local');
  process.exit(1);
}
console.log('✅ Environment variables loaded');
console.log(`   Token: ${FIGMA_TOKEN.substring(0, 10)}...`);
console.log(`   File ID: ${FIGMA_FILE_ID}\n`);

// Test 2: Direct Figma API Call
console.log('2️⃣ Testing direct Figma API access...');
const options = {
  hostname: 'api.figma.com',
  port: 443,
  path: `/v1/files/${FIGMA_FILE_ID}`,
  method: 'GET',
  headers: {
    'X-Figma-Token': FIGMA_TOKEN,
    'User-Agent': 'PratikoAI-Validator/1.0'
  }
};

const req = https.request(options, (res) => {
  console.log(`   Status: ${res.statusCode}`);
  console.log(`   Headers: ${JSON.stringify(res.headers, null, 2)}`);
  
  let data = '';
  res.on('data', (chunk) => {
    data += chunk;
  });
  
  res.on('end', () => {
    if (res.statusCode === 200) {
      console.log('✅ Figma API connection successful');
      const fileData = JSON.parse(data);
      console.log(`   File name: ${fileData.name}`);
      console.log(`   Last modified: ${fileData.lastModified}`);
      console.log(`   Thumbnail: ${fileData.thumbnailUrl ? 'Available' : 'Not available'}\n`);
    } else {
      console.error('❌ Figma API connection failed');
      console.error(`   Response: ${data}\n`);
    }
    
    // Test 3: MCP Server Check
    console.log('3️⃣ Testing MCP server installations...');
    testMCPServers();
  });
});

req.on('error', (e) => {
  console.error(`❌ Request failed: ${e.message}\n`);
  testMCPServers();
});

req.end();

function testMCPServers() {
  const mcpTests = [
    {
      name: '@MatthewDailey/figma-mcp',
      command: 'npx @MatthewDailey/figma-mcp --help'
    },
    {
      name: 'figma-developer-mcp',
      command: 'npx figma-developer-mcp --help'
    }
  ];

  mcpTests.forEach((test, index) => {
    try {
      console.log(`   Testing ${test.name}...`);
      execSync(test.command, { stdio: 'pipe' });
      console.log(`   ✅ ${test.name} is available`);
    } catch (error) {
      console.log(`   ❌ ${test.name} not available or not working`);
      console.log(`      Install with: npm install -g ${test.name}`);
    }
  });
  
  console.log('\n4️⃣ Next steps:');
  console.log('   1. Copy claude_desktop_config.json to your Claude Desktop config location');
  console.log('   2. Restart Claude Desktop application');
  console.log('   3. Test MCP integration in Claude Desktop');
  console.log('   4. Run: npm run validate:mcp for additional checks');
}