# HTML-Formatted Streaming Implementation Specification

## 🎯 Critical Requirement
**Backend must send display-ready HTML chunks. Users must NEVER see markdown syntax characters.**

## 📋 Implementation Overview

### Current Problem
```
Backend sends: "###", "1", ".", " ", "D", "e", "f", "i", "n", "i", "z", "i", "o", "n", "e"
Frontend sees: ###1. Definizione (RAW MARKDOWN - UNACCEPTABLE)
```

### Required Solution
```
Backend sends: "<h3>1. Definizione</h3>"
Frontend displays: Beautiful formatted heading (PROFESSIONAL APPEARANCE)
```

## 🔧 Implementation Architecture

### 1. **ContentFormatter Class**
**File**: `/app/core/content_formatter.py`

```python
class ContentFormatter:
    """Converts markdown to HTML for display-ready streaming."""
    
    def convert_markdown_to_html(self, markdown_text: str) -> str:
        """Convert markdown to clean HTML."""
        
    def format_tax_calculation(self, calculation_text: str) -> str:
        """Format tax calculations with proper styling."""
        
    def format_currency(self, amount: str) -> str:
        """Format currency as €1.234,56."""
        
    def format_percentage(self, percentage: str) -> str:
        """Format percentages properly."""
```

### 2. **StreamingHTMLProcessor Class**
**File**: `/app/core/content_formatter.py`

```python
class StreamingHTMLProcessor:
    """Handles HTML generation during streaming."""
    
    async def process_token(self, token: str) -> Optional[str]:
        """Process incoming token and return HTML chunk when ready."""
        
    def format_sse_message(self, html_content: str, done: bool = False) -> str:
        """Format HTML content as SSE message."""
```

### 3. **BlockBuffer Class**
**File**: `/app/core/content_formatter.py`

```python
class BlockBuffer:
    """Buffers content until complete blocks can be formatted."""
    
    def add_chunk(self, chunk: str) -> Optional[Union[str, List[str]]]:
        """Add chunk and return complete blocks when ready."""
        
    def is_block_complete(self, content: str) -> bool:
        """Determine if content forms a complete block."""
```

## 📝 Conversion Specifications

### Markdown to HTML Mapping

| Markdown Input | HTML Output | CSS Classes |
|---------------|-------------|-------------|
| `### Heading` | `<h3>Heading</h3>` | `.tax-heading` |
| `**bold**` | `<strong>bold</strong>` | `.emphasis` |
| `*italic*` | `<em>italic</em>` | `.legal-term` |
| `- List item` | `<ul><li>List item</li></ul>` | `.tax-list` |
| `1. Numbered` | `<ol><li>Numbered</li></ol>` | `.example-list` |
| `` `code` `` | `<code>code</code>` | `.tax-code` |

### Tax Calculation Formatting

| Raw Calculation | Formatted HTML |
|----------------|----------------|
| `50000 × 15% = 7500` | `<div class="calculation"><span class="formula">€50.000 × 15%</span> = <strong class="result">€7.500</strong></div>` |
| `Reddito: 50000` | `<div class="calculation-line"><span class="label">Reddito:</span> <span class="amount">€50.000</span></div>` |

### Currency and Number Formatting

| Raw Input | Formatted Output |
|-----------|------------------|
| `50000` | `€ 50.000` |
| `1234.56` | `€ 1.234,56` |
| `15%` | `15%` |
| `0.15` | `15%` |

## 🏗️ Integration Points

### 1. **Update LangGraph Agent**
**File**: `/app/core/langgraph/graph.py`
**Method**: `get_stream_response()`

```python
async def get_stream_response(self, messages, session_id, user_id=None):
    formatter = ContentFormatter()
    processor = StreamingHTMLProcessor()
    
    async for token, _ in self._graph.astream(...):
        html_chunk = await processor.process_token(token.content)
        if html_chunk:
            yield html_chunk  # Yield HTML, not raw tokens
```

### 2. **Update Streaming Endpoint**
**File**: `/app/api/v1/chatbot.py`
**Method**: `event_generator()`

```python
async def event_generator():
    async for html_chunk in agent.get_stream_response(...):
        # html_chunk is already formatted HTML
        response = StreamResponse(content=html_chunk, done=False)
        yield f"data: {json.dumps(response.model_dump())}\n\n"
```

### 3. **Update Frontend**
**File**: `/src/lib/api.ts`

```typescript
// Frontend becomes trivial - just append HTML
(chunk: string) => {
    // chunk is already formatted HTML like "<h3>Heading</h3>"
    setMessageContent(prev => prev + chunk)  // Direct append, no processing
}
```

## 🧪 Test Categories

### 1. **Markdown Conversion Tests**
- Headers: `###` → `<h3>`
- Bold: `**text**` → `<strong>text</strong>`
- Italic: `*text*` → `<em>text</em>`
- Lists: `- item` → `<ul><li>item</li></ul>`
- Code: `` `code` `` → `<code>code</code>`

### 2. **Tax Calculation Tests**
- Simple: `50000 × 15% = 7500` → Professional calculation display
- Complex: Multi-line calculations with proper formatting
- Currency: All amounts formatted as `€ 1.234,56`

### 3. **Streaming Tests**
- Incremental building: `"###"` + `" "` + `"Heading"` → `<h3>Heading</h3>`
- Chunk boundaries: Complete blocks only
- Error recovery: Handle malformed markdown

### 4. **Professional Appearance Tests**
- No markdown syntax in output: Critical requirement
- Proper currency formatting: `€ 50.000`
- Legal references: `<cite>Legge n.190/2014</cite>`
- Tax terms: `<abbr title="...">IRPEF</abbr>`

## ✅ Success Criteria

### Critical Requirements
1. **No Markdown Syntax**: Users NEVER see `###`, `**`, `*`, `-`, `` ` ``
2. **Display-Ready HTML**: Backend sends `<h3>`, `<strong>`, `<em>`, `<ul>`, etc.
3. **Professional Appearance**: Currency, percentages, legal refs properly formatted
4. **Complete Blocks**: No partial tags, no broken formatting

### Performance Requirements
- **Chunk Size**: 10-500 characters per chunk
- **Semantic Boundaries**: Break at word/sentence boundaries
- **Processing Speed**: < 1ms per token processing
- **Memory Efficiency**: No large buffer accumulation

### Frontend Simplification
- **Zero Parsing**: Frontend just appends HTML chunks
- **No Markdown Processing**: All formatting done backend
- **Direct Display**: `innerHTML += chunk` type approach

## 🚀 Implementation Steps

### Phase 1: Core Formatter (High Priority)
1. Create `ContentFormatter` class
2. Implement basic markdown → HTML conversion
3. Add tax calculation formatting
4. Write and pass basic tests

### Phase 2: Streaming Integration (High Priority)
1. Create `StreamingHTMLProcessor` class
2. Integrate with LangGraph agent
3. Update streaming endpoint
4. Test end-to-end streaming

### Phase 3: Professional Polish (Medium Priority)
1. Add currency/percentage formatting
2. Implement legal reference formatting
3. Add tax terminology tooltips
4. Polish CSS classes and styling

### Phase 4: Performance Optimization (Low Priority)
1. Optimize chunk sizes
2. Implement intelligent buffering
3. Add streaming performance monitoring
4. Memory usage optimization

## 📊 Expected Results

### Before Implementation
```
User sees: ###1. Definizione**Il regime forfettario** è*semplificato*- Item 1- Item 2
Appearance: Raw, unprofessional, technical-looking
```

### After Implementation
```
User sees: Beautiful formatted headings, bold text, italics, proper lists
Appearance: Professional, polished, ChatGPT-quality formatting
```

## 🔧 Development Tools

### Testing
```bash
# Run all formatting tests
pytest tests/test_markdown_to_html_conversion.py
pytest tests/test_tax_calculation_formatting.py
pytest tests/test_complete_block_formatting.py
pytest tests/test_streaming_html_chunks.py

# Test streaming integration
pytest tests/test_backend_integration.py -v
```

### Debugging
```python
# Debug formatter output
formatter = ContentFormatter()
result = formatter.convert_markdown_to_html("### Test")
print(f"Input: '### Test'")
print(f"Output: '{result}'")
assert "###" not in result  # Critical check
```

### Performance Monitoring
```python
# Monitor chunk sizes and timing
import time
start = time.time()
chunks = process_streaming_response(tokens)
end = time.time()
print(f"Processed {len(chunks)} chunks in {end-start:.3f}s")
```

This specification ensures that the backend sends beautiful, display-ready HTML content while maintaining professional tax consulting appearance standards.