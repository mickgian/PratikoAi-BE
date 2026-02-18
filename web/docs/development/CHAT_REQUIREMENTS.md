# PratikoAI Chat Interface Requirements

## Overview

This document outlines the requirements for the PratikoAI chat interface based on the Figma export analysis and implementation discussions. The chat system consists of two main components: a floating chat widget for the home page and a full-page chat interface for authenticated users.

## Key Implementation Requirements (CRITICAL)

### Session Management

- **ChatGPT/Claude Style**: Always create new empty session on app launch
  - **Session Persistence**: Keep old sessions accessible in sidebar
  - **No Empty Sessions**: Never display empty sessions in sidebar
  - **Action Buttons**: Hide edit/delete for new sessions until first Q&A pair completes

### Typing Effect & Streaming

- **Progressive Reveal**: HTML-aware progressive text reveal with realistic cadence
  - **No Raw HTML Tags**: Never show HTML tags during typing animation
  - **Format Preservation**: Bold stays bold, headings stay as headings during typing
  - **Immediate Start**: Begin typing with first chunk, continue seamlessly
  - **Variable Speed**: Token/word-aware cadence (60-80 cps base with variation)

### Content Handling

- **No Duplication**: Prevent duplicate content (e.g., "Section 1" appearing twice)
  - **HTML Rendering**: Properly render HTML without exposing tags
  - **Clean Architecture**: Separate session history from active streaming state
  - **Context Provider**: Use shared context to prevent multiple hook instances

## 1. Core Chat Components

### 1.1 Floating Chat Interface (ChatInterface.tsx)

#### Layout & Positioning

- **Container**: Fixed positioning, bottom-right corner (6px from edges)
  - **Dimensions**: 380px width × 500px height
  - **Mobile responsive**: 90vw width × 80vh height on small screens
  - **Z-index**: 50 for chat window, 40 for backdrop
  - **Border radius**: 16px (rounded-2xl)
  - **Background**: White with shadow-2xl
  - **Border**: 1px solid #C4BDB4 with 20% opacity

#### Chat Window Structure

- **Header**: 56px height, #2A5D67 background, rounded top corners
  - **Messages area**: Flexible height, white background, 16px padding
  - **Input area**: 56px height, white background with top border

### 1.2 Full-Page Chat Interface (ChatPage.tsx)

#### Overall Layout

- **Container**: Full screen height, #F8F5F1 background
  - **Structure**: Horizontal flex layout (sidebar + main chat area)
  - **Sidebar**: 320px width on desktop, collapsible on mobile
  - **Main area**: Flexible width, white background

#### Header Bar

- **Height**: Dynamic (approximately 72px)
  - **Background**: White with bottom border (#C4BDB4/20)
  - **Content**: Logo, title, status indicator, navigation buttons
  - **Mobile**: Hamburger menu for navigation

#### Messages Area

- **Background**: #F8F5F1
  - **Container**: Max-width 1024px, centered
  - **Padding**: 24px on all sides
  - **Spacing**: 24px between messages

#### Input Area

- **Position**: Fixed bottom of main area
  - **Background**: #F8F5F1
  - **Container**: Max-width 1024px, centered
  - **Padding**: 24px

## 2. Message Display System

### 2.1 User Messages

- **Alignment**: Right-aligned (justify-end)
  - **Background**: #F8F5F1 (avorio color)
  - **Text color**: #1E293B (dark-slate)
  - **Max width**: 280px
  - **Padding**: 12px
  - **Border radius**: 16px with bottom-right corner squared (rounded-br-sm)
  - **Typography**: 14px, leading-relaxed

### 2.2 AI Messages

- **Alignment**: Left-aligned (justify-start)
  - **Background**: White
  - **Border**: 3px left border in #2A5D67 (blu-petrolio)
  - **Text color**: #1E293B (dark-slate)
  - **Max width**: 280px (floating) / broader on full page
  - **Padding**: 12px
  - **Border radius**: 16px with bottom-left corner squared (rounded-bl-sm)
  - **Shadow**: Small shadow (shadow-sm)

### 2.3 Message Features

#### Timestamps

- **Position**: Below message content
  - **Font size**: 12px (text-xs)
  - **Color**: #C4BDB4 (grigio-tortora)
  - **Format**: HH:MM (Italian locale)

#### Source Citations

- **Container**: Border-top divider with #C4BDB4/20
  - **Label**: "Fonti:" in 12px, #2A5D67 color, font-medium
  - **Sources**: Flex-wrapped, 12px underlined text, hover effects
  - **Color**: #2A5D67, hover to #1E293B
  - **Interactive**: Clickable with scale animation (1.05x)

#### Message Animations

- **Entry**: opacity 0→1, y 20px→0px, 0.2s duration
  - **Hover effects**: Scale 1.05x on source links
  - **Transition**: All animations use spring physics where applicable

## 3. Input System

### 3.1 Text Input Field

- **Background**: #F8F5F1 (floating) / white (full page)
  - **Border**: None, focus ring with #2A5D67/20
  - **Border radius**: 24px (rounded-3xl)
  - **Padding**: 12px left, 48px right, 12px vertical
  - **Placeholder**:
    - Floating: "Fai una domanda..."
    - Full page: Dynamic based on input mode
  - **Typography**: 14px, #1E293B text, #C4BDB4 placeholder

### 3.2 Send Button

- **Position**: Absolute right, centered vertically
  - **Size**: 32px × 32px
  - **Border radius**: Full circle (rounded-full)
  - **States**:
    - **Disabled**: #C4BDB4 background, not clickable
    - **Enabled**: #2A5D67 background, hover #1E293B
  - **Icon**: Send icon (Lucide), 16px size
  - **Animations**: Scale 1.1x on hover, 0.9x on tap

### 3.3 Input Mode Selection (Full Page)

- **Container**: Horizontal scrollable row, 16px bottom margin
  - **Buttons**: Rounded pills with icons and labels
  - **States**:
    - **Inactive**: #C4BDB4/20 border, transparent background
    - **Active**: #2A5D67 background, white text
  - **Special indicator**: Orange dot for "Interactive" mode
  - **Typography**: 14px font-medium, no wrap

#### Input Modes

1. **Simple**: MessageSquare icon, "Domanda Semplice" 2. **Complex**: Brain icon, "Domanda Complessa"  
   3. **Interactive**: Search icon, "Domanda Interattiva" (with pulse dot) 4. **Document**: FileCheck icon, "Analisi Documento"

## 4. Typing & Loading States

### 4.1 Typing Indicator

- **Container**: Flex row with 16px padding
  - **Dots**: 3 circles, 8px size, #C4BDB4 color
  - **Animation**: Opacity fade 0.3→1→0.3, staggered timing
  - **Duration**: 1.4s cycle, infinite repeat
  - **Text**: "PratikoAI sta scrivendo..." in 12px #C4BDB4

### 4.2 AI Response Simulation

- **Delay**: 2 seconds after user message
  - **Process**: Show typing → hide typing → show AI response
  - **Message ID**: Timestamp + 1 for uniqueness

## 5. Interactive Features

### 5.1 Message Feedback System (Full Page)

- **Position**: Below AI messages
  - **Trigger**: Hover to show feedback options
  - **Options**:
    - **Correct**: Green (ThumbsUp icon)
    - **Incomplete**: Yellow (AlertTriangle icon)
    - **Wrong**: Red (ThumbsDown icon)
  - **Modal**: Detailed feedback collection with categories
  - **Animation**: Scale effects on hover/selection

### 5.2 Clear Chat Functionality

- **Button**: "Pulisci Chat" / "Nuova Chat"
  - **Style**: Outline button, #2A5D67 border and text
  - **Hover**: Filled background with white text
  - **Action**: Reset messages array, clear input, scroll to top

## 6. Sidebar (Full Page Only)

### 6.1 Layout

- **Width**: 320px desktop, full-width mobile overlay
  - **Background**: White
  - **Shadow**: Large shadow (shadow-2xl on mobile)
  - **Animation**: Slide from left (-300px → 0px)

### 6.2 Conversation History

- **Container**: Scrollable list
  - **Item height**: Variable based on content
  - **Selected state**: Visual highlighting
  - **Preview**: Title, timestamp, message preview
  - **Types**: Visual indicators for conversation type

### 6.3 Quick Actions

- **Grid**: Icon + label + count
  - **Items**: 6 predefined actions (Modelli, Scadenze, etc.)
  - **Style**: Hover effects, construction icons for "coming soon"

## 7. Color Palette & Design Tokens

### 7.1 Primary Colors

- **Blu Petrolio**: #2A5D67 (Primary brand color)
  - **Dark Slate**: #1E293B (Text color)
  - **Avorio**: #F8F5F1 (Background, user messages)
  - **Grigio Tortora**: #C4BDB4 (Muted text, borders)
  - **Oro Antico**: #D4A574 (Accents, notifications)
  - **Verde Salvia**: #A9C1B7 (Status indicators)

### 7.2 Interactive States

- **Hover**: Darken primary colors by ~10%
  - **Focus**: Ring color #2A5D67 with 20% opacity
  - **Active**: Scale transform 0.95x - 1.05x range
  - **Disabled**: #C4BDB4 background, reduced opacity

## 8. Typography Specifications

### 8.1 Font Stack

- **Primary**: 'Inter', system fonts fallback
  - **Base size**: 14px root font size
  - **Line heights**: 1.5 (normal) to 1.6 (relaxed)

### 8.2 Text Sizes

- **12px**: Timestamps, labels, small text
  - **14px**: Input text, message content, buttons
  - **16px**: Titles, headers within messages
  - **18px**: Main titles
  - **20px+**: Page headers

## 9. Responsive Design

### 9.1 Breakpoints

- **Mobile**: < 768px
  - **Tablet**: 768px - 1024px
  - **Desktop**: > 1024px

### 9.2 Mobile Adaptations

- **Floating chat**: 90vw × 80vh, positioned 16px from edges
  - **Full page**: Sidebar becomes overlay, header collapses navigation
  - **Input modes**: Horizontal scroll, preserved functionality
  - **Messages**: Maintain max-width constraints

## 10. Animations & Transitions

### 10.1 Message Animations

- **Entry**: Fade + slide up, 200ms duration
  - **Exit**: Fade out, 150ms duration
  - **Hover**: Subtle scale on interactive elements

### 10.2 UI Transitions

- **Modal**: Scale + fade, spring physics
  - **Sidebar**: Slide transition, spring damping
  - **Buttons**: Transform on press/release
  - **Typing indicator**: Continuous dot animation

### 10.3 Performance Considerations

- **Reduced motion**: Respect user preferences
  - **Animation duration**: 0.01ms when reduced motion enabled
  - **GPU acceleration**: Transform properties preferred

## 11. State Management Requirements

### 11.1 Message State

```text
interface Message {
  id: string
  type: 'user' | 'ai'
  content: string
  timestamp: string
  sources?: string[]
  feedback?: MessageFeedback
  isInteractiveQuestion?: boolean
}
```

### 11.2 Chat State

- **messages**: Array of Message objects
  - **inputValue**: Current input text
  - **isTyping**: Boolean for AI typing state
  - **inputMode**: Selected mode ('simple' | 'complex' | 'interactive' | 'document')
  - **selectedConversationId**: For sidebar navigation

### 11.3 UI State

- **isSidebarOpen**: Sidebar visibility (mobile)
  - **showFeedbackModal**: Feedback dialog state
  - **selectedFeedbackType**: Current feedback category
  - **showMobileNav**: Mobile navigation state

## 12. Accessibility Requirements

### 12.1 Keyboard Navigation

- **Tab order**: Logical flow through interactive elements
  - **Enter key**: Send message, submit forms
  - **Escape key**: Close modals, cancel actions
  - **Arrow keys**: Navigate message history (if implemented)

### 12.2 Screen Reader Support

- **ARIA labels**: All interactive elements labeled
  - **Live regions**: Message area for dynamic content
  - **Focus management**: Proper focus on modal open/close
  - **Alt text**: Icons have meaningful descriptions

### 12.3 Visual Accessibility

- **Color contrast**: WCAG AA compliant ratios
  - **Focus indicators**: Visible focus rings
  - **Text sizing**: Respects user zoom preferences
  - **Reduced motion**: Animation preferences honored

## 13. Performance Requirements

### 13.1 Message Handling

- **Virtual scrolling**: Consider for >100 messages
  - **Message limit**: Reasonable cap with pagination
  - **Memory management**: Clean up old conversation data

### 13.2 Animation Performance

- **60fps target**: Smooth animations on modern devices
  - **GPU acceleration**: Transform3d usage
  - **Debouncing**: Input validation, API calls

### 13.3 Bundle Size

- **Code splitting**: Load chat components separately
  - **Icon optimization**: Tree-shake unused icons
  - **CSS optimization**: Purge unused styles

## Assumptions

### Technical Assumptions

1. **Framework**: React 18+ with modern hooks 2. **Styling**: Tailwind CSS for utility classes 3. **Animation**: Framer Motion for complex animations 4. **Icons**: Lucide React icon library 5. **State**: Component-level state, consider Context for global state

### Design Assumptions

1. **Italian language**: All text content in Italian 2. **Legal domain**: Specialized for legal/tax professionals 3. **Professional audience**: Higher complexity tolerance 4. **Desktop-first**: Primary usage on desktop devices 5. **Real-time**: Expectation of immediate AI responses

## 14. Content Formatting Requirements (ACTUAL BACKEND IMPLEMENTATION)

### 14.1 Backend Content Format (IMPLEMENTED)

- **Current State**: Backend ContentFormatter converts markdown to HTML
  - **Process Flow**: LLM (markdown) → ContentFormatter → HTML → Frontend
  - **User Experience**: Users NEVER see markdown symbols (###, \*_, _, `, etc.)
  - **Format**: Complete HTML blocks with proper tags (<h3>, <strong>, <em>, <ul>, <li>, etc.)
  - **Italian Formatting**: Currency (€ 1.234,56), dates (DD/MM/YYYY), legal references
  - **STREAMING CLARIFICATION**: Streaming chunks are HTML formatted, not raw markdown
  - **Block Completion**: Backend ensures chunks contain complete HTML blocks, never partial tags

### 14.2 Tax Calculation Formatting (AS RECEIVED FROM BACKEND)

```html
<!-- Simple calculation -->
<div class="calculation">
  <span class="formula">€ 85.000 × 15%</span> =
  <strong class="result">€ 12.750</strong>
</div>

<!-- Complex multi-line calculation -->
<div class="calculation tax-brackets">
  <div class="calculation-step">
    <span class="label">Scaglione 1:</span>
    <span class="formula">€ 15.000 × 23%</span> =
    <strong class="result">€ 3.450</strong>
  </div>
  <div class="calculation-step">
    <span class="label">Scaglione 2:</span>
    <span class="formula">€ 13.000 × 25%</span> =
    <strong class="result">€ 3.250</strong>
  </div>
  <div class="calculation-total">
    <span class="label">Totale:</span>
    <strong class="result">€ 25.150</strong>
  </div>
</div>

<!-- Forfettario calculation -->
<div class="calculation forfettario-calculation">
  <div class="calculation-line">
    <span class="label">Ricavi:</span>
    <span class="amount">€ 65.000</span>
  </div>
  <div class="calculation-line">
    <span class="label">Coefficiente:</span>
    <span class="percentage">78%</span>
  </div>
  <div class="calculation-item">€ 65.000 × 78% = € 50.700</div>
</div>
```

### 14.3 Legal Reference Formatting (AS IMPLEMENTED)

- **Format**: `<cite class="legal-ref">Legge n.190/2014</cite>`
  - **Article References**: `<cite class="legal-ref">Art. 1, comma 54</cite>`
  - **DPR References**: `<cite class="legal-ref">D.P.R. 633/1972</cite>`
  - **Display**: Should be styled with italic and #2A5D67 color in frontend CSS

### 14.4 Tax Terminology Formatting

- **Abbreviations with Tooltips**: `<abbr title="Imposta sul Valore Aggiunto">IVA</abbr>`
  - **Common Terms**:
    - **IRPEF** → `<abbr title="Imposta sul Reddito delle Persone Fisiche">IRPEF</abbr>`
    - **IVA** → `<abbr title="Imposta sul Valore Aggiunto">IVA</abbr>`
    - **IRAP** → `<abbr title="Imposta Regionale sulle Attività Produttive">IRAP</abbr>`

### 14.5 BlockBuffer Streaming Behavior

- **Accumulation**: Backend accumulates tokens until semantic boundaries
  - **Complete Blocks**: Sends only when paragraph/list/heading is complete
  - **Never Partial HTML**: Frontend never receives broken tags
  - **Boundaries**: Sends at:
    - End of sentences (. ! ?)
    - Complete headings (after newline)
    - Complete list items
    - Complete calculation blocks

### 14.6 Frontend CSS Requirements

- **Purpose**: The frontend must provide CSS for these backend-generated classes:
  css/_ Calculation styling _/
  .calculation {
  background: #F8F5F1;
  padding: 12px;
  border-radius: 8px;
  margin: 8px 0;
  }

.calculation .formula {
color: #1E293B;
font-family: monospace;
}

.calculation .result {
color: #2A5D67;
font-weight: bold;
}

.calculation-step {
margin: 4px 0;
padding-left: 16px;
}

.calculation-total {
border-top: 1px solid #C4BDB4;
margin-top: 8px;
padding-top: 8px;
font-weight: bold;
}

/_ Specific calculation types _/
.tax-brackets { }
.forfettario-calculation { }
.vat-calculation { }
.comparison-calculation { }

/_ Legal references _/
.legal-ref {
font-style: italic;
color: #2A5D67;
text-decoration: underline;
text-decoration-style: dotted;
}

/_ Abbreviations _/
abbr {
text-decoration: underline;
text-decoration-style: dotted;
cursor: help;
}

/_ Values and labels _/
.label {
font-weight: 600;
color: #1E293B;
}

.amount {
font-weight: 500;
color: #2A5D67;
}

.percentage {
color: #D4A574;
}

### 14.7 Frontend HTML Rendering & Typing Effect (IMPROVED SPEC)

#### Typing Effect Philosophy

- **Goal**: Realistic, human-like streaming of AI responses without exposing raw HTML tags
- **Approach**: HTML-aware progressive reveal with variable cadence
- **Backend**: Streams complete, sanitized HTML blocks (never broken tags)
- **Frontend**: Performs progressive text reveal while preserving formatting

#### Streaming Behavior

##### Backend Responsibilities

- Always stream valid HTML blocks (`<p>`, `<li>`, `<div class="calculation">`, etc.)
- Never send incomplete tags or partial attributes
- Chunk boundaries at: sentence end, list item, heading, or calculation block
- Guarantee no duplication (idempotent block streaming)

##### Frontend Responsibilities

- Maintain two states:
  - **Confirmed blocks**: Already finalized and appended
  - **Active block buffer**: Latest incomplete block being typed out
- On each SSE chunk:
  - Append to active block buffer
  - If chunk closes a block, finalize it and move buffer pointer

#### Typing Effect Rules

##### HTML Parsing

- Parse each streamed block once into DOM fragment (AST)
- Traverse nodes:
  - **Element nodes**: Insert immediately (format wrapper)
  - **Text nodes**: Progressively reveal character by character
- Ensures `<strong>`, `<em>`, `<ul>`, `<li>`, `<cite>` appear instantly

##### Progressive Reveal

- Typing progresses inside the last open text node
- At each tick: append 1-3 characters depending on cadence function
- Always maintain valid HTML by including full element wrappers

##### Cadence Function (Realistic Speed)

- **Base speed**: 60-80 cps
- **Add**: ±15% random jitter per tick for natural variation
- **Slow down**: 50% after punctuation (. , ; : ? !)
- **Pause**: 150-300ms at sentence boundaries
- This mimics ChatGPT/Claude instead of robotic fixed speed

#### Implementation Algorithm

```text
// useTypingEffect hook
function useTypingEffect(htmlChunk: string, onComplete: () => void) {
  const [displayHTML, setDisplayHTML] = useState("");

  useEffect(() => {
    const fragment = parseHTMLToNodes(htmlChunk); // DOMParser → nodes[]
    const queue = flattenToTextAndTags(fragment); // [{type:'tagOpen', html}, {type:'text', text}, …]

    let i = 0, charIndex = 0, buffer = "";

    function tick() {
      const node = queue[i];
      if (!node) { onComplete(); return; }

      if (node.type === "tagOpen" || node.type === "tagClose") {
        buffer += node.html; // inject tag instantly
        i++;
      } else if (node.type === "text") {
        buffer += node.text[charIndex++];
        if (charIndex >= node.text.length) { i++; charIndex = 0; }
      }

      setDisplayHTML(buffer + `<span class="cursor">▌</span>`);

      const delay = calcDelay(buffer); // cadence function
      setTimeout(tick, delay);
    }

    tick();
  }, [htmlChunk]);

  return displayHTML;
}
```

#### Cursor Handling

- Show blinking cursor `<span class="cursor">▌</span>` during typing
- Remove cursor once block is finalized
- Cursor styled via CSS animation (opacity 0.2→1)

#### Accessibility

- Mark typing container as `aria-live="polite"`
- Buffer announcements until:
  - End of sentence (punctuation + space), or
  - Block finalization
- Ensures screen readers hear natural phrases, not letter soup

#### Performance Safeguards

- Never overwrite entire innerHTML each tick
- Update only the last text node + cursor (DOM mutation)
- Store parsed nodes in ref; use dangerouslySetInnerHTML only at block completion
- During typing, render via custom TextTyper component

#### Example Flow

Backend streams:

```html
<p><strong>Regime forfettario:</strong> L'aliquota è del 15%.</p>
```

FE parses to nodes:

1. `<p>` open
2. `<strong>` open
3. text "Regime forfettario:"
4. `</strong>` close
5. text " L'aliquota è del 15%."
6. `</p>` close

Typing sequence:

- `<p><strong>` appears instantly
- "R", "Re", "Reg" … typed progressively
- `</strong>` appears instantly when bold text completes
- Continue typing " L'aliquota è del 15%."
- Close `</p>` appended instantly at block end

#### Testing Requirements

- **Latency test**: First character visible < 200ms after first chunk
- **Integrity test**: HTML always valid at each render step
- **Duplication test**: No text repeats after streaming completes
- **Accessibility test**: Screen readers announce sentences, not characters
- **Performance test**: No FPS drops on 1,000-char responses

## 15. Streaming Requirements (CRITICAL)

### 15.1 Streaming Architecture (IMPLEMENTED AND TESTED)

- **SSE (Server-Sent Events)**: Backend streams HTML chunks via SSE
  - **Chunk Format**: Complete HTML blocks (paragraph-sized), never partial tags
  - **Backend Chunks**: Backend intentionally sends paragraph-sized HTML chunks for formatting purposes
  - **No buffering needed**: Frontend receives display-ready HTML chunks
  - **Content Accumulation**: Frontend MUST accumulate chunks, not replace them
  - **State Isolation Fix**: Components must use `useSharedChatState()`, not direct `useChatState()`
  - **Typing Effect**: HTML-aware character-by-character typing while accumulating chunks
  - **Clean Architecture**: Separate session history (immutable) from active streaming state

### 15.2 Streaming Rules

- **One message at a time**: Only ONE AI message can stream at any moment
  - **No duplicates**: Each message has unique ID, never create duplicate messages
  - **Update existing**: Streaming updates existing message content, doesn't create new messages
  - **State machine**: IDLE → WAITING → STREAMING → COMPLETE (no invalid transitions)

### 15.3 Typing Effect (IMPROVED HTML-AWARE IMPLEMENTATION)

- **Progressive reveal**: HTML-aware progressive text reveal with variable cadence
  - **HTML preservation**: Parse HTML, type visible text, maintain valid HTML structure
  - **Variable Speed**: 60-80 cps base with ±15% jitter, punctuation pauses
  - **Cursor**: Show blinking cursor at end of typed content during streaming
  - **Scrolling**: User can freely scroll during streaming
  - **Two-State System**:
    - **Confirmed blocks**: Already typed and finalized
    - **Active buffer**: Currently typing block
  - **HTML Parsing Algorithm**:
    1. Parse HTML blocks into DOM fragments
    2. Element nodes appear instantly (formatting)
    3. Text nodes type progressively with cadence
    4. Never expose raw HTML tags in display
  - **Performance**: Update only last text node + cursor, not full innerHTML
  - **Display**: Use dangerouslySetInnerHTML only at block completion

### 15.4 Critical Streaming Constraints (IMPLEMENTED)

typescript// NEVER do this (creates duplicates):
messages.push(newMessage) // during streaming

// ALWAYS do this (updates existing):
messages = messages.map(msg =>
msg.id === streamingId
? { ...msg, content: msg.content + newChunk } // ACCUMULATE
: msg
)

// CRITICAL: Use shared state, not isolated state
// ❌ WRONG: import { useChatState } from '../hooks/useChatState'
// ✅ CORRECT: import { useSharedChatState } from '../hooks/useChatState'

// Reducer implementation for content accumulation:
case 'UPDATE_STREAMING_CONTENT': {
const messageToUpdate = state.messages.find(msg => msg.id === action.messageId)
const newContent = messageToUpdate.content + action.content // ACCUMULATE
return {
...state,
messages: state.messages.map(msg =>
msg.id === action.messageId
? { ...msg, content: newContent }
: msg
)
}
}

## 15.5 Implementation Details (BACKEND AND FRONTEND REQUIREMENTS)

### 15.5.1 Backend Streaming Requirements

- **Content Format**: Stream HTML chunks, never raw markdown
  - **Chunk Completeness**: Ensure complete HTML blocks (no broken tags)
  - **SSE Headers**: Proper Server-Sent Events implementation
  - **Session Persistence**: Messages saved to session when streaming completes
  - **Error Handling**: Graceful error responses via SSE

### 15.5.2 Frontend State Management Requirements

```text
// CORRECT: Shared state usage
const {
  addUserMessage,
  startAIStreaming,
  updateStreamingContent,
  completeStreaming
} = useSharedChatState() // ✅ Use shared state

// WRONG: Isolated state (causes messages to disappear)
const { addUserMessage } = useChatState() // ❌ Creates isolated state
```

### 15.5.3 Streaming Flow Example (CORRECT IMPLEMENTATION)

```text
// 1. User sends message
addUserMessage(content)

// 2. Start AI streaming (creates empty AI message)
const messageId = startAIStreaming()

// 3. Backend streams HTML chunks via SSE
streamingService.onChunk = (chunk: string) => {
  updateStreamingContent(messageId, chunk) // Accumulates content
}

// 4. Complete streaming when done
streamingService.onComplete = () => {
  completeStreaming()
}
```

### 15.5.4 Content Accumulation (CRITICAL)

The reducer MUST accumulate content, never replace:

```text
// ✅ CORRECT: Accumulation
const newContent = messageToUpdate.content + action.content

// ❌ WRONG: Replacement (causes typing effect issues)
const newContent = action.content
```

### 15.5.5 Component Implementation Requirements

- **AIMessage**: Use `dangerouslySetInnerHTML` for HTML content display
  - **ChatInputArea**: Use `useSharedChatState()` for state access
  - **State Isolation**: Never import `useChatState` directly in components
  - **Streaming UI**: Show `<TypingCursor />` during streaming, remove when complete

### 15.5.6 Common Streaming Issues and Solutions

#### Issue: Messages not appearing on screen

**Problem**: Using `useChatState()` directly instead of `useSharedChatState()`
**Solution**: Always import and use `useSharedChatState()` in all components
**Files**: ChatInputArea.tsx, ChatMessagesArea.tsx

#### Issue: Typing effect shows characters then deletes them

**Problem**: Content replacement instead of accumulation in reducer
**Solution**: Change `content: action.content` to `content: messageToUpdate.content + action.content`
**File**: useChatState.ts reducer case 'UPDATE_STREAMING_CONTENT'

#### Issue: "Message not found" errors

**Problem**: Inconsistent streaming state or message ID mismatches  
**Solution**: Fix streaming state validation and allow updates when message exists
**File**: useChatState.ts lines 98-104

#### Issue: Second message fails to stream

**Problem**: Streaming state not properly cleaned up after first message
**Solution**: Ensure `completeStreaming()` is called and cleans up `isStreaming` and `streamingMessageId`
**File**: RealAPIStreamingService onComplete callback

### 15.6 Double Response Prevention (CRITICAL)

**Critical Requirement**: Prevent content duplication when streaming completes.

#### 15.6.1 The Double Response Bug

**OLD BUG**: After streaming completes, the full response was added again, resulting in:

- User sees: "Hello world" → "Hello world!" → "Hello world!Hello world!"
  - **MUST NEVER HAPPEN**

#### 15.6.2 Prevention Implementation

```text
// ✅ CORRECT: UPDATE_STREAMING_CONTENT accumulates
case 'UPDATE_STREAMING_CONTENT': {
  const messageToUpdate = state.messages.find(msg => msg.id === action.messageId)
  const newContent = messageToUpdate.content + action.content // ACCUMULATE
  return {
    ...state,
    messages: state.messages.map(msg =>
      msg.id === action.messageId
        ? { ...msg, content: newContent }
        : msg
    )
  }
}

// ✅ CORRECT: COMPLETE_STREAMING only updates flags
case 'COMPLETE_STREAMING': {
  return {
    ...state,
    isStreaming: false,     // Only update streaming status
    streamingMessageId: null // Only clear streaming message ID
    // NEVER touch messages array content
  }
}
```

#### 15.6.3 Backend "Done" Signal Handling

When backend sends `{"content": "", "done": true}`:

- ✅ **MUST**: Trigger COMPLETE_STREAMING action
  - ✅ **MUST**: Only update streaming flags (isStreaming, streamingMessageId)
  - ❌ **MUST NOT**: Add empty content to message
  - ❌ **MUST NOT**: Re-add accumulated content
  - ❌ **MUST NOT**: Create new message
  - ❌ **MUST NOT**: Duplicate existing content

#### 15.6.4 Content Flow Requirements

- **During streaming**: Chunks accumulate progressively in single message
  - **At completion**: Accumulated content IS the final content
  - **No post-processing**: No additional content added after "done" signal
  - **Final state**: `message.content = chunk1 + chunk2 + ... + chunkN`

#### 15.6.5 Test Requirements

All implementations MUST pass these critical tests:

```text
// Content accumulates correctly
expect(afterChunk1.content).toBe('<p>Hello')
expect(afterChunk2.content).toBe('<p>Hello world')
expect(afterChunk3.content).toBe('<p>Hello world!</p>')

// Completion doesn't duplicate
expect(afterCompletion.content).toBe('<p>Hello world!</p>')
expect(afterCompletion.content).not.toBe('<p>Hello world!</p><p>Hello world!</p>')
```

#### 15.6.6 Implementation Mistakes to Avoid

- ❌ Adding final response in COMPLETE_STREAMING reducer case
  - ❌ Listening for separate "complete" message with full content
  - ❌ Duplicating content on backend "done" signal
  - ❌ Resetting and re-adding content in completion handler
  - ❌ Processing {"content": "", "done": true} as content to add

## 16. Message State Management (CRITICAL)

### 16.1 Message Uniqueness

- **Unique IDs**: Use UUID/nanoid for guaranteed uniqueness
  - **ID persistence**: Message IDs never change once created
  - **No collision**: System must prevent ID collisions

### 16.2 Message Update Rules

- **User messages**: Created once, never modified
  - **AI messages**: Created empty, content appended during streaming
  - **Immutable updates**: Never mutate state directly
  - **Atomic operations**: All state updates must be atomic

### 16.3 Sequential Message Handling

- **First message**: Must work correctly
  - **Second message**: Must work correctly (was broken before!)
  - **Nth message**: Unlimited messages must work
  - **Session continuity**: Conversation continues across any number of exchanges

## 17. Persistence Requirements

### 17.1 Storage Strategy

- **Auto-save**: After each message completion
  - **Format preservation**: HTML formatting must survive storage
  - **Character encoding**: Properly handle Italian special characters (à, è, é, ì, ò, ù, €)
  - **Large content**: Handle messages up to 100KB
  - **Storage Backend**: Use IndexedDB for message content (localStorage ~5MB limit insufficient)
  - **localStorage**: Only for session metadata and small state

### 17.2 Navigation Persistence

- **Browser navigation**: Messages persist when navigating away
  - **Page refresh**: F5/refresh maintains complete conversation with formatting
  - **Browser back/forward**: Full conversation restored
  - **Tab synchronization**: Multiple tabs stay in sync (localStorage events)

### 17.3 Session Recovery

- **Corrupted data**: Graceful recovery from corrupted storage
  - **Partial restoration**: Recover what's possible if some data is corrupted
  - **Version migration**: Handle storage format changes

## 18. Error Prevention Requirements

### 18.1 Duplicate Prevention

- **Single typing indicator**: Only ONE typing indicator ever shown
  - **Single streaming connection**: Only ONE SSE connection per message
  - **Cleanup on completion**: Always cleanup streaming resources
  - **No orphaned listeners**: Remove all event listeners on cleanup

### 18.2 Memory Management

- **Connection cleanup**: Properly close SSE connections
  - **Event listener removal**: Remove all listeners when done
  - **Abort controllers**: Use AbortController for cancellable operations
  - **Resource limits**: Cap message history at reasonable limit (e.g., 1000 messages)

## 19. Critical Test Scenarios

### 19.1 The "Second Message Test"

1. **Send**: "Prima domanda" 2. **Receive**: AI response (formatted HTML) 3. **Send**: "Seconda domanda" 4. **MUST receive**: Second AI response (this was broken!)

### 19.2 The "No Duplicates Test"

1. **Send message** 2. **Check**: Exactly ONE user message appears 3. **Check**: Exactly ONE typing indicator appears 4. **Check**: Exactly ONE AI message appears 5. **Check**: Content streams into existing message (not new message)

### 19.3 The "Formatting Preservation Test"

1. **Receive**: HTML formatted response with tax calculation 2. **Refresh page** (F5) 3. **Check**: Formatting intact (no markdown symbols visible) 4. **Navigate away and back** 5. **Check**: Formatting still intact

---

## 20. Chat Session Management Requirements

### 20.1 Session Creation & Initialization

- **New Session on Launch**: Always create a new empty session when app is launched (ChatGPT/Claude style behavior)
  - **Session Persistence**: Keep old sessions accessible in the sidebar
  - **No Empty Sessions Display**: Never display empty sessions in the sidebar
  - **Single Instance**: Ensure only one instance of session management hook runs (prevent duplicate sessions)
  - **Session Token**: Ensure valid session token before sending messages
  - **Auto-Create**: Automatically create session if none exists when sending first message

### 20.2 Session List Display

- **Location**: Sidebar on desktop, overlay on mobile
  - **Information shown**:
    - Session title (user-editable)
    - Last message preview (truncated to ~50 chars)
    - Timestamp (relative: "2 ore fa", "Ieri", "3 giorni fa")
    - Message count or session type indicator
  - **Order**: Most recent first
  - **Active indicator**: Highlight currently active session

### 20.3 Session Title Management

#### Default Title Generation

- **Auto-generate**: From first user message (first 50 chars) immediately after sending
  - **Format**: Smart extraction of meaningful text
  - **Timing**: Update title optimistically, don't wait for async operations
  - **Examples**:
    - User: "Come funziona il regime forfettario?" → Title: "Regime forfettario"
    - User: "Calcola IRPEF su 85000 euro" → Title: "Calcolo IRPEF 85000"

#### Title Editing

- **Trigger**: Click on edit icon (pencil) or double-click title
  - **UI States**:
    - **Normal**: Title text with edit icon on hover
    - **Editing**: Input field with Save/Cancel buttons
  - **Input field**: Same styling as title, auto-focus on edit
  - **Save**: Enter key or checkmark button
  - **Cancel**: Escape key or X button
  - **Validation**: Max 100 characters, trim whitespace
  - **Persistence**: Update immediately in storage

### 20.4 Session Actions Visibility

#### Action Button Rules

- **New Empty Sessions**:
  - Hide edit and delete buttons until first Q&A pair is complete
  - Mark session as "used" only after AI response completes
  - **Sessions with Content**:
    - Always show edit and delete buttons for sessions with complete Q&A pairs
    - Enable actions immediately after first AI response completes

### 20.5 Session Deletion

#### Delete Button

- **Location**: On hover/focus of session item (trash icon)
  - **Color**: Red (#EF4444) on hover
  - **Position**: Right side of session item
  - **Visibility**: Only show for sessions with complete Q&A pairs

#### Confirmation Dialog

- **Trigger**: Click delete button
  - **Modal content**:
    - **Title**: "Elimina conversazione"
    - **Message**: "Sei sicuro di voler eliminare questa conversazione? Questa azione non può essere annullata."
    - **Buttons**: Annulla / Elimina
  - **Styling**:
    - **Modal backdrop with blur**
    - **White modal, centered**
    - **Red "Elimina" button, gray "Annulla"**

#### Deletion Process

- **Current session**: If deleting active session, redirect to new empty chat
  - **Other session**: Just remove from list, stay in current chat
  - **Storage**: Remove from localStorage/database
  - **Animation**: Fade out + slide effect

### 20.6 Session Actions UI

#### Hover State

```html
<div class="session-item">
  <div class="session-content">
    <div class="session-title">
      <span>Calcolo IRPEF 2024</span>
      <button class="edit-btn" aria-label="Modifica titolo">✏️</button>
    </div>
    <div class="session-preview">Come calcolare l'IRPEF per...</div>
    <div class="session-meta">2 ore fa • 15 messaggi</div>
  </div>
  <button class="delete-btn" aria-label="Elimina">🗑️</button>
</div>
Edit Mode html
<div class="session-item editing">
  <div class="session-content">
    <div class="session-title-edit">
      <input type="text" value="Calcolo IRPEF 2024" />
      <button class="save-btn" aria-label="Salva">✓</button>
      <button class="cancel-btn" aria-label="Annulla">✗</button>
    </div>
  </div>
</div>
```

### 20.7 Keyboard Shortcuts

#### Title Editing

- **F2**: Start editing selected session title
  - **Enter**: Save title changes
  - **Escape**: Cancel editing
  - **Tab**: Move to next editable element

#### Session Management

- **Delete key**: Open delete confirmation for selected session
  - **Ctrl/Cmd + D**: Delete current session (with confirmation)
  - **Ctrl/Cmd + N**: Start new chat session

### 20.8 State Management for Sessions

#### Context Provider Pattern

- **SharedContext**: Use React Context to share session state across components
  - **Prevent Duplicates**: Context provider prevents multiple hook instances
  - **Global State**: All components access same session state via useSharedChatSessions()
    typescriptinterface ChatSession {
    id: string
    title: string
    messages: Message[]
    createdAt: string
    updatedAt: string
    messageCount: number
    lastMessagePreview?: string
    isActive?: boolean // Whether session has been used (has complete Q&A pair)
    token?: string // Session token for API communication
    }

interface SessionManagementState {
sessions: ChatSession[]
activeSessionId: string | null
editingSessionId: string | null
deletingSessionId: string | null
showDeleteConfirmation: boolean
}

### 20.9 Session Management Actions

typescript// Actions for session management
type SessionAction =
| { type: 'UPDATE_SESSION_TITLE'; sessionId: string; title: string }
| { type: 'DELETE_SESSION'; sessionId: string }
| { type: 'START_EDITING_TITLE'; sessionId: string }
| { type: 'CANCEL_EDITING_TITLE' }
| { type: 'SHOW_DELETE_CONFIRMATION'; sessionId: string }
| { type: 'HIDE_DELETE_CONFIRMATION' }
| { type: 'CONFIRM_DELETE_SESSION' }

### 20.10 Visual Feedback

#### Title Edit Animation

- **Transition**: Smooth morph from text to input field
  - **Focus ring**: Blue outline on input (#2A5D67)
  - **Success**: Brief green checkmark animation on save

#### Delete Animation

- **Hover**: Trash icon scales to 1.1x, turns red
  - **Confirmation**: Modal slides in from top with fade
  - **Deletion**: Session fades out + slides left
  - **List reflow**: Smooth animation as gap closes

### 20.11 Error Handling

#### Session Creation Errors

- **Multiple Sessions**: Prevent creating multiple empty sessions on login
  - **Race Conditions**: Prevent race conditions between session loading and streaming
  - **Token Validation**: Ensure session has valid token before messaging

#### Title Edit Errors

- **Empty title**: Show error "Il titolo non può essere vuoto"
  - **Too long**: Show character count "95/100"
  - **Save failure**: Toast notification "Impossibile salvare il titolo"

#### Delete Errors

- **Active session**: Handle gracefully, create new session
  - **Network error**: Show toast "Impossibile eliminare la conversazione"
  - **Storage error**: Attempt cleanup, show warning

### 20.12 Mobile Considerations

#### Touch Interactions

- **Long press**: Show context menu with Edit/Delete options
  - **Swipe left**: Reveal delete button (iOS style)
  - **Swipe right**: Reveal edit button

#### Responsive Layout

- **Mobile**: Full-width session items
  - **Tablet**: Two-column grid
  - **Desktop**: Single column in sidebar

## 21. Bulk Session Management (Optional Enhancement)

### 21.1 Search & Filter

- **Search bar**: Filter sessions by title or content
  - **Date filter**: Today, Yesterday, Last 7 days, Last 30 days
  - **Sort options**: Recent, Alphabetical

## 22. File Upload & Document Analysis

### 22.1 File Upload Capability

- **Supported formats**: PDF, Word, Excel, Images (for tax documents, fatture, etc.)
  - **Max file size**: 10MB per file
  - **Multiple files**: Support batch upload?
  - **Drag & drop**: Drop zone for files
  - **Progress indicator**: Upload progress bar
  - **File preview**: Show uploaded file name, size, type

_This requirements document should be reviewed and validated against the actual product vision before implementation begins._
