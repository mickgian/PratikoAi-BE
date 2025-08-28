"""
HTML Content Formatter for PratikoAI Backend

This module provides HTML formatting capabilities to convert markdown syntax
to display-ready HTML chunks during streaming. Ensures users never see
raw markdown syntax characters.

Critical requirement: Users must NEVER see ###, **, *, -, ` characters.
All content must be formatted as professional HTML before sending to frontend.
"""

import re
import html
from typing import Optional, List, Union, Dict, Tuple
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class ContentFormatter:
    """
    Converts markdown syntax to HTML for display-ready streaming.
    
    Handles all common markdown patterns and Italian-specific formatting
    for tax content, legal references, and financial calculations.
    """
    
    def __init__(self):
        """Initialize the formatter with Italian formatting settings."""
        self.currency_symbol = "€"
        self.thousand_separator = "."
        self.decimal_separator = ","
        
        # Markdown patterns for conversion
        self.markdown_patterns = {
            # Headers (### ## #)
            'h3': re.compile(r'^### (.+)$', re.MULTILINE),
            'h2': re.compile(r'^## (.+)$', re.MULTILINE),
            'h1': re.compile(r'^# (.+)$', re.MULTILINE),
            
            # Text formatting
            'bold': re.compile(r'\*\*([^\*]+)\*\*'),
            'italic': re.compile(r'\*([^\*]+)\*'),  # Simple italic pattern
            'code': re.compile(r'`([^`]+)`'),
            
            # Lists
            'bullet_list': re.compile(r'^- (.+)$', re.MULTILINE),
            'numbered_list': re.compile(r'^(\d+)\. (.+)$', re.MULTILINE),
            
            # Code blocks
            'code_block': re.compile(r'```([^`]+)```', re.DOTALL),
            
            # Tax calculations (numbers with operators)
            'calculation': re.compile(r'(\d+(?:\.?\d+)*)\s*([×x*÷/])\s*(\d+(?:\.?\d+)*%?)\s*=\s*(\d+(?:\.?\d+)*)')
        }
        
        # Legal reference patterns
        self.legal_patterns = {
            'law_reference': re.compile(r'(Legge\s+n\.?\s*\d+/\d+)', re.IGNORECASE),
            'article_reference': re.compile(r'(Art(?:icolo)?\s+\d+(?:,\s*comma\s+\d+)?)', re.IGNORECASE),
            'dpr_reference': re.compile(r'(D\.P\.R\.?\s+\d+/\d+)', re.IGNORECASE)
        }
        
        # Tax terminology for tooltips
        self.tax_terms = {
            'IRPEF': 'Imposta sul Reddito delle Persone Fisiche',
            'IVA': 'Imposta sul Valore Aggiunto',
            'IRAP': 'Imposta Regionale sulle Attività Produttive'
        }
    
    def convert_markdown_to_html(self, markdown_text: str) -> str:
        """
        Convert markdown text to HTML, ensuring no markdown syntax remains.
        
        Args:
            markdown_text: Raw markdown text from LLM
            
        Returns:
            Clean HTML with no markdown syntax characters
        """
        if not markdown_text or not markdown_text.strip():
            return ""
        
        try:
            # Start with the input text
            html_text = markdown_text
            
            # Convert headers first (most specific to least specific)
            html_text = self.markdown_patterns['h3'].sub(r'<h3>\1</h3>', html_text)
            html_text = self.markdown_patterns['h2'].sub(r'<h2>\1</h2>', html_text)
            html_text = self.markdown_patterns['h1'].sub(r'<h1>\1</h1>', html_text)
            
            # Convert code blocks before inline code
            html_text = self.markdown_patterns['code_block'].sub(r'<pre><code>\1</code></pre>', html_text)
            
            # Convert inline formatting (bold first to avoid conflicts)
            html_text = self.markdown_patterns['bold'].sub(r'<strong>\1</strong>', html_text)
            # Convert remaining single asterisks to italic (simple approach)
            html_text = re.sub(r'\*([^\*]+)\*', r'<em>\1</em>', html_text)
            html_text = self.markdown_patterns['code'].sub(r'<code>\1</code>', html_text)
            
            # Convert lists first before other processing
            html_text = self._convert_lists(html_text)
            
            # Convert tax calculations
            html_text = self._convert_calculations(html_text)
            
            # Wrap remaining text in paragraphs if not already wrapped (before other formatting)
            html_text = self._wrap_paragraphs(html_text)
            
            # Format legal references
            html_text = self._format_legal_references(html_text)
            
            # Format tax terminology
            html_text = self._format_tax_terms(html_text)
            
            # Final cleanup - ensure no markdown syntax remains
            html_text = self._cleanup_remaining_markdown(html_text)
            
            return html_text.strip()
            
        except Exception as e:
            logger.error(f"Error converting markdown to HTML: {e}")
            # Fallback: return escaped text wrapped in paragraph
            return f"<p>{html.escape(markdown_text)}</p>"
    
    def _convert_lists(self, text: str) -> str:
        """Convert markdown lists to HTML lists."""
        # Use regex to find and replace list patterns
        
        # First, convert bullet lists
        bullet_pattern = re.compile(r'^((?:^- .+\n?)+)', re.MULTILINE)
        
        def replace_bullet_list(match):
            list_text = match.group(1)
            items = []
            for line in list_text.strip().split('\n'):
                if line.startswith('- '):
                    item_text = line[2:].strip()
                    items.append(f"<li>{item_text}</li>")
            return '<ul>\n' + '\n'.join(items) + '\n</ul>'
        
        text = bullet_pattern.sub(replace_bullet_list, text)
        
        # Then, convert numbered lists
        numbered_pattern = re.compile(r'^((?:^\d+\. .+\n?)+)', re.MULTILINE)
        
        def replace_numbered_list(match):
            list_text = match.group(1)
            items = []
            for line in list_text.strip().split('\n'):
                numbered_match = re.match(r'^(\d+)\. (.+)$', line)
                if numbered_match:
                    item_text = numbered_match.group(2).strip()
                    items.append(f"<li>{item_text}</li>")
            return '<ol>\n' + '\n'.join(items) + '\n</ol>'
        
        text = numbered_pattern.sub(replace_numbered_list, text)
        
        return text
    
    def _convert_calculations(self, text: str) -> str:
        """Convert tax calculations to formatted HTML."""
        def replace_calculation(match):
            operand1 = match.group(1)
            operator = match.group(2)
            operand2 = match.group(3)
            result = match.group(4)
            
            # Format numbers
            formatted_operand1 = self.format_currency(operand1)
            formatted_result = self.format_currency(result)
            
            # Format operator
            operator_map = {'*': '×', 'x': '×', '/': '÷'}
            formatted_operator = operator_map.get(operator, operator)
            
            # Format percentage if present
            if operand2.endswith('%'):
                formatted_operand2 = operand2
            else:
                formatted_operand2 = self.format_percentage(operand2)
            
            return f'<div class="calculation"><span class="formula">{formatted_operand1} {formatted_operator} {formatted_operand2}</span> = <strong class="result">{formatted_result}</strong></div>'
        
        return self.markdown_patterns['calculation'].sub(replace_calculation, text)
    
    def format_tax_calculation(self, calculation_text: str) -> str:
        """
        Format tax calculation with professional styling.
        
        Args:
            calculation_text: Raw calculation text
            
        Returns:
            Formatted HTML with proper styling and currency formatting
        """
        if not calculation_text or not calculation_text.strip():
            return ""
        
        try:
            # Handle different calculation patterns
            lines = calculation_text.strip().split('\n')
            
            # Single line calculation
            if len(lines) == 1:
                return self._format_simple_calculation(lines[0])
            
            # Multi-line calculation (tax brackets, VAT, etc.)
            return self._format_complex_calculation(lines)
            
        except Exception as e:
            logger.error(f"Error formatting tax calculation: {e}")
            return f"<div class=\"calculation\"><p>{html.escape(calculation_text)}</p></div>"
    
    def _format_simple_calculation(self, calc_line: str) -> str:
        """Format a single calculation line."""
        # Pattern: "amount × percentage = result"
        calc_match = re.match(r'(\d+(?:\.\d+)*)\s*[×x*]\s*(\d+(?:\.\d+)*%?)\s*=\s*(\d+(?:\.\d+)*)', calc_line)
        
        if calc_match:
            amount = self.format_currency(calc_match.group(1))
            percentage = calc_match.group(2)
            if not percentage.endswith('%'):
                percentage = self.format_percentage(percentage)
            result = self.format_currency(calc_match.group(3))
            
            return f'''<div class="calculation">
    <span class="formula">{amount} × {percentage}</span> = <strong class="result">{result}</strong>
</div>'''
        
        # Fallback: wrap in calculation div
        return f'<div class="calculation">{html.escape(calc_line)}</div>'
    
    def _format_complex_calculation(self, lines: List[str]) -> str:
        """Format multi-line calculations (tax brackets, VAT, etc.)."""
        formatted_lines = []
        calculation_type = "calculation"
        
        # Detect calculation type
        content = '\n'.join(lines).lower()
        if 'scaglione' in content or 'bracket' in content:
            calculation_type = "tax-brackets"
        elif 'iva' in content or 'vat' in content:
            calculation_type = "vat-calculation"
        elif 'forfettario' in content:
            calculation_type = "forfettario-calculation"
        elif 'ordinario' in content and 'forfettario' in content:
            calculation_type = "comparison-calculation"
        
        formatted_lines.append(f'<div class="calculation {calculation_type}">')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for different line types
            if ':' in line and '=' in line:
                # Calculation line: "Reddito: 50000 × 15% = 7500"
                parts = line.split(':', 1)
                if len(parts) == 2:
                    label = parts[0].strip()
                    calc_part = parts[1].strip()
                    
                    # Format the calculation part
                    calc_match = re.search(r'(\d+(?:\.\d+)*)\s*[×x*]\s*(\d+(?:\.\d+)*%?)\s*=\s*(\d+(?:\.\d+)*)', calc_part)
                    if calc_match:
                        amount = self.format_currency(calc_match.group(1))
                        percentage = calc_match.group(2)
                        if not percentage.endswith('%'):
                            percentage = self.format_percentage(percentage)
                        result = self.format_currency(calc_match.group(3))
                        
                        formatted_lines.append(f'''    <div class="calculation-step">
        <span class="label">{label}:</span> 
        <span class="formula">{amount} × {percentage}</span> = 
        <strong class="result">{result}</strong>
    </div>''')
                    else:
                        formatted_lines.append(f'    <div class="calculation-step">{html.escape(line)}</div>')
                
            elif ':' in line:
                # Label with value: "Reddito: 50000"
                parts = line.split(':', 1)
                if len(parts) == 2:
                    label = parts[0].strip()
                    value = parts[1].strip()
                    
                    # Try to format as currency
                    if re.match(r'^\d+(?:\.\d+)*$', value):
                        formatted_value = self.format_currency(value)
                        formatted_lines.append(f'    <div class="calculation-line"><span class="label">{label}:</span> <span class="amount">{formatted_value}</span></div>')
                    elif value.endswith('%'):
                        formatted_lines.append(f'    <div class="calculation-line"><span class="label">{label}:</span> <span class="percentage">{value}</span></div>')
                    else:
                        formatted_lines.append(f'    <div class="calculation-line"><span class="label">{label}:</span> <span class="value">{html.escape(value)}</span></div>')
            
            elif line.lower().startswith('totale'):
                # Total line
                if ':' in line:
                    parts = line.split(':', 1)
                    value = parts[1].strip()
                    if re.match(r'^\d+(?:\.\d+)*$', value):
                        formatted_value = self.format_currency(value)
                        formatted_lines.append(f'    <div class="calculation-total"><span class="label">Totale:</span> <strong class="result">{formatted_value}</strong></div>')
                    else:
                        formatted_lines.append(f'    <div class="calculation-total">{html.escape(line)}</div>')
                else:
                    formatted_lines.append(f'    <div class="calculation-total">{html.escape(line)}</div>')
            
            else:
                # Regular line
                formatted_lines.append(f'    <div class="calculation-item">{html.escape(line)}</div>')
        
        formatted_lines.append('</div>')
        return '\n'.join(formatted_lines)
    
    def format_currency(self, amount: str) -> str:
        """
        Format currency amount in Italian format (€ 1.234,56).
        
        Args:
            amount: Numeric amount as string
            
        Returns:
            Formatted currency string
        """
        try:
            # Clean the input
            clean_amount = re.sub(r'[^\d.,]', '', str(amount))
            
            # Handle different decimal separators
            if ',' in clean_amount and '.' in clean_amount:
                # Both separators present - assume last is decimal
                if clean_amount.rfind(',') > clean_amount.rfind('.'):
                    # Comma is decimal separator
                    clean_amount = clean_amount.replace('.', '').replace(',', '.')
                else:
                    # Dot is decimal separator
                    clean_amount = clean_amount.replace(',', '')
            elif ',' in clean_amount:
                # Only comma - could be thousands or decimal
                parts = clean_amount.split(',')
                if len(parts) == 2 and len(parts[1]) <= 2:
                    # Decimal separator
                    clean_amount = clean_amount.replace(',', '.')
                else:
                    # Thousands separator
                    clean_amount = clean_amount.replace(',', '')
            
            # Convert to decimal
            decimal_amount = Decimal(clean_amount)
            
            # Format with Italian conventions
            if decimal_amount == int(decimal_amount):
                # Whole number
                formatted = f"{int(decimal_amount):,}".replace(',', '.')
                return f"{self.currency_symbol} {formatted}"
            else:
                # With decimals
                integer_part = int(decimal_amount)
                decimal_part = decimal_amount % 1
                
                # Format integer part with thousand separators
                formatted_integer = f"{integer_part:,}".replace(',', '.')
                
                # Format decimal part
                decimal_str = f"{decimal_part:.2f}"[2:]  # Remove "0."
                
                return f"{self.currency_symbol} {formatted_integer},{decimal_str}"
                
        except (ValueError, TypeError, AttributeError):
            # Fallback for invalid input
            return f"{self.currency_symbol} {amount}"
    
    def format_percentage(self, percentage: str) -> str:
        """
        Format percentage value.
        
        Args:
            percentage: Percentage value as string (could be decimal like 0.15)
            
        Returns:
            Formatted percentage string
        """
        try:
            # Clean the input
            clean_pct = str(percentage).strip().replace('%', '')
            
            # Convert to float
            pct_value = float(clean_pct)
            
            # If value is between 0 and 1, assume it's decimal format (0.15 = 15%)
            if 0 < pct_value < 1:
                pct_value *= 100
            
            # Format as integer if whole number, otherwise with decimals
            if pct_value == int(pct_value):
                return f"{int(pct_value)}%"
            else:
                return f"{pct_value:.1f}%"
                
        except (ValueError, TypeError):
            # Fallback
            return f"{percentage}%" if not str(percentage).endswith('%') else str(percentage)
    
    def _format_legal_references(self, text: str) -> str:
        """Format legal references with proper HTML."""
        # Format law references
        text = self.legal_patterns['law_reference'].sub(
            r'<cite class="legal-ref">\1</cite>', text
        )
        
        # Format article references
        text = self.legal_patterns['article_reference'].sub(
            r'<cite class="legal-ref">\1</cite>', text
        )
        
        # Format DPR references
        text = self.legal_patterns['dpr_reference'].sub(
            r'<cite class="legal-ref">\1</cite>', text
        )
        
        return text
    
    def _format_tax_terms(self, text: str) -> str:
        """Add tooltips to tax terminology."""
        for term, definition in self.tax_terms.items():
            pattern = re.compile(rf'\b{re.escape(term)}\b')
            replacement = f'<abbr title="{definition}">{term}</abbr>'
            text = pattern.sub(replacement, text)
        
        return text
    
    def _wrap_paragraphs(self, text: str) -> str:
        """Wrap text in paragraph tags where appropriate."""
        lines = text.split('\n')
        result_lines = []
        current_paragraph = []
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                if current_paragraph:
                    # End current paragraph
                    paragraph_text = ' '.join(current_paragraph)
                    if not self._is_already_wrapped(paragraph_text):
                        result_lines.append(f"<p>{paragraph_text}</p>")
                    else:
                        result_lines.append(paragraph_text)
                    current_paragraph = []
                continue
            
            # Check if line is already HTML or special content
            if self._is_already_wrapped(line):
                # End current paragraph if any
                if current_paragraph:
                    paragraph_text = ' '.join(current_paragraph)
                    result_lines.append(f"<p>{paragraph_text}</p>")
                    current_paragraph = []
                
                # Add the HTML line as-is
                result_lines.append(line)
            else:
                # Add to current paragraph
                current_paragraph.append(line)
        
        # Handle remaining paragraph
        if current_paragraph:
            paragraph_text = ' '.join(current_paragraph)
            if not self._is_already_wrapped(paragraph_text):
                result_lines.append(f"<p>{paragraph_text}</p>")
            else:
                result_lines.append(paragraph_text)
        
        return '\n\n'.join(filter(None, result_lines))
    
    def _is_already_wrapped(self, text: str) -> bool:
        """Check if text is already wrapped in HTML tags."""
        html_start_tags = ['<h1>', '<h2>', '<h3>', '<h4>', '<h5>', '<h6>', 
                          '<p>', '<div>', '<ul>', '<ol>', '<li>', '<pre>', 
                          '<blockquote>', '<table>', '<cite>', '<abbr>']
        
        html_end_tags = ['</h1>', '</h2>', '</h3>', '</h4>', '</h5>', '</h6>', 
                        '</p>', '</div>', '</ul>', '</ol>', '</li>', '</pre>', 
                        '</blockquote>', '</table>', '</cite>', '</abbr>']
        
        text_stripped = text.strip()
        
        # Check if starts with opening tag or ends with closing tag
        starts_with_html = any(text_stripped.startswith(tag) for tag in html_start_tags)
        ends_with_html = any(text_stripped.endswith(tag) for tag in html_end_tags)
        
        return starts_with_html or ends_with_html
    
    def _cleanup_remaining_markdown(self, text: str) -> str:
        """Final cleanup to remove any remaining markdown syntax."""
        # Simple cleanup without complex lookbehind patterns
        
        # Remove orphaned header markers at start of line
        text = re.sub(r'^#{1,6}\s*$', '', text, flags=re.MULTILINE)
        
        # Remove standalone markdown markers (simple patterns)
        text = re.sub(r'\*\*\s*$', '', text)  # Trailing **
        text = re.sub(r'^\s*\*\*', '', text)  # Leading **
        text = re.sub(r'\*\s*$', '', text)    # Trailing *
        text = re.sub(r'^\s*\*(?!\*)', '', text)  # Leading * (not **)
        
        # Remove orphaned backticks
        text = re.sub(r'`\s*$', '', text)     # Trailing `
        text = re.sub(r'^\s*`', '', text)     # Leading `
        
        return text
    
    def format_block(self, block_text: str) -> str:
        """
        Format a complete block of content.
        
        Args:
            block_text: Complete block of markdown text
            
        Returns:
            Formatted HTML block
        """
        if not block_text or not block_text.strip():
            return ""
        
        return self.convert_markdown_to_html(block_text)


# Supporting classes for streaming implementation

class BlockBuffer:
    """
    Buffers content until complete blocks can be formatted.
    
    Ensures that only complete, well-formed HTML blocks are sent
    to the frontend. Handles streaming token accumulation and
    semantic boundary detection.
    """
    
    def __init__(self):
        """Initialize the block buffer."""
        self.buffer = ""
        self.formatter = ContentFormatter()
        # CRITICAL FIX: Add time-based fallback to prevent content getting stuck
        import time
        self.last_addition_time = time.time()
        self.buffer_timeout = 2.0  # Send buffered content after 2 seconds
    
    def add_chunk(self, chunk: str) -> Optional[Union[str, List[str]]]:
        """
        Add a chunk and return complete blocks when ready.
        
        Args:
            chunk: New content chunk from streaming
            
        Returns:
            Complete formatted block(s) or None if still accumulating
        """
        import time
        current_time = time.time()
        
        self.buffer += chunk
        self.last_addition_time = current_time
        
        # Check for multiple complete blocks in buffer
        blocks = self._extract_complete_blocks()
        if blocks:
            return blocks
        
        # CRITICAL FIX: Time-based fallback - if we haven't found complete blocks but have substantial content
        # that has been accumulating, send it anyway to ensure smooth streaming
        if (not blocks and 
            self.buffer.strip() and 
            len(self.buffer.strip()) > 100):  # If we have substantial content but no "complete" blocks
            
            # Check if we should force send based on content patterns
            buffer_content = self.buffer.strip()
            should_force_send = (
                # Has paragraph-like content
                len(buffer_content) > 150 or
                # Has multiple sentences  
                buffer_content.count('.') >= 2 or
                # Has section headers
                '###' in buffer_content or
                # Has list items
                bool(re.search(r'^[-*]\s+', buffer_content, re.MULTILINE))
            )
            
            if should_force_send:
                # Format and send the buffered content
                formatted_block = self.formatter.format_block(buffer_content)
                if formatted_block:
                    self.buffer = ""  # Clear the buffer
                    return [formatted_block]
        
        return None
    
    def _extract_complete_blocks(self) -> List[str]:
        """Extract all complete blocks from buffer."""
        blocks = []
        
        # Split buffer into potential blocks
        # Look for double newlines as block separators
        parts = self.buffer.split('\n\n')
        
        # All parts except the last are complete blocks
        for i in range(len(parts) - 1):
            block_text = parts[i].strip()
            if block_text:
                formatted_block = self.formatter.format_block(block_text)
                if formatted_block:
                    blocks.append(formatted_block)
        
        # Check if the last part is a complete block
        if len(parts) > 1:
            last_part = parts[-1].strip()
            if self._is_block_complete(last_part):
                formatted_block = self.formatter.format_block(last_part)
                if formatted_block:
                    blocks.append(formatted_block)
                # Reset buffer to empty
                self.buffer = ""
            else:
                # Keep the last incomplete part in buffer
                self.buffer = last_part
        
        return blocks
    
    def _is_block_complete(self, text: str) -> bool:
        """Determine if text forms a complete block.
        
        CRITICAL FIX: Made less strict to work with OpenAI's small streaming chunks.
        Now accepts partial blocks to ensure smooth frontend typing experience.
        """
        if not text.strip():
            return False
        
        # RELAXED: Accept sentences ending with punctuation
        if text.strip().endswith(('.', '!', '?', ':', ';')):
            return True
        
        # RELAXED: Accept any heading (don't require newline)
        if re.match(r'^#{1,6}\s+.+', text.strip()):
            return True
        
        # RELAXED: Accept single list items (was requiring 2+)
        lines = text.strip().split('\n')
        list_items = [line for line in lines if re.match(r'^[-*]\s+.+|^\d+\.\s+.+', line)]
        if len(list_items) >= 1:  # Single list item is now complete
            return True
        
        # NEW: Accept paragraphs that are reasonably long (80+ chars)
        if len(text.strip()) >= 80 and not text.strip().endswith((',', 'e', 'a', 'o', 'i', 'u')):
            # Avoid breaking mid-word by checking it doesn't end with common word endings
            return True
        
        # NEW: Accept content with double newlines (clear paragraph breaks)
        if '\n\n' in text:
            return True
        
        return False
    
    def is_paragraph_complete(self, text: str) -> bool:
        """Check if text forms a complete paragraph."""
        return text.strip().endswith('\n\n') or text.strip().endswith(('.', '!', '?'))
    
    def is_list_complete(self, text: str) -> bool:
        """Check if text forms a complete list."""
        return text.strip().endswith('\n\n') and any(
            re.match(r'^[-*]\s+.+|^\d+\.\s+.+', line) 
            for line in text.strip().split('\n')
        )
    
    def is_heading_complete(self, text: str) -> bool:
        """Check if text forms a complete heading."""
        return bool(re.match(r'^#{1,6}\s+.+\n', text)) or text.strip().endswith('\n')
    
    def finalize(self) -> Optional[str]:
        """Force completion of any remaining content in buffer."""
        if self.buffer.strip():
            formatted = self.formatter.format_block(self.buffer.strip())
            self.buffer = ""
            return formatted
        return None


class StreamingHTMLProcessor:
    """
    Processes incoming LLM tokens character-by-character to build HTML.
    
    Maintains context for proper formatting and ensures complete
    HTML blocks are generated during streaming.
    """
    
    def __init__(self):
        """Initialize the streaming processor."""
        self.block_buffer = BlockBuffer()
        self.formatter = ContentFormatter()
        self.token_buffer = ""
        
    async def process_token(self, token: str) -> Optional[str]:
        """
        Process an incoming token and return HTML chunk when ready.
        
        Args:
            token: Single token from LLM streaming
            
        Returns:
            Formatted HTML chunk or None if still accumulating
        """
        # Add token to buffer
        self.token_buffer += token
        
        # Check for complete blocks
        complete_blocks = self.block_buffer.add_chunk(token)
        
        if complete_blocks:
            if isinstance(complete_blocks, list):
                # Multiple blocks ready
                result = '\n\n'.join(complete_blocks)
            else:
                # Single block ready
                result = complete_blocks
            
            return result
        
        return None
    
    def process_token_sync(self, token: str) -> Optional[str]:
        """Synchronous version of process_token for testing."""
        # Add token to buffer
        self.token_buffer += token
        
        # Check for complete blocks
        complete_blocks = self.block_buffer.add_chunk(token)
        
        if complete_blocks:
            if isinstance(complete_blocks, list):
                # Multiple blocks ready
                result = '\n\n'.join(complete_blocks)
            else:
                # Single block ready
                result = complete_blocks
            
            return result
        
        return None
    
    def format_sse_message(self, html_content: str, done: bool = False) -> str:
        """
        Format HTML content as SSE message.
        
        Args:
            html_content: Formatted HTML content
            done: Whether this is the final message
            
        Returns:
            SSE-formatted message
        """
        import json
        
        response_data = {
            "content": html_content,
            "done": done
        }
        
        return f"data: {json.dumps(response_data)}\n\n"
    
    async def finalize(self) -> Optional[str]:
        """Force completion of any remaining content."""
        return self.block_buffer.finalize()
    
    def format_currency(self, amount: str) -> str:
        """Format currency using the formatter."""
        return self.formatter.format_currency(amount)
    
    def format_percentage(self, percentage: str) -> str:
        """Format percentage using the formatter."""
        return self.formatter.format_percentage(percentage)
    
    def format_tax_term(self, term: str) -> str:
        """Format tax terminology with tooltips."""
        definition = self.formatter.tax_terms.get(term)
        if definition:
            return f'<abbr title="{definition}">{term}</abbr>'
        return term
    
    def format_legal_reference(self, reference: str) -> str:
        """Format legal references."""
        # Clean up spacing and formatting
        cleaned = re.sub(r'\s+', ' ', reference.strip())
        return f'<cite class="legal-ref">{cleaned}</cite>'