#!/usr/bin/env python3
"""
PratikoAI Chat Architecture Analysis Report Generator
Using ReportLab
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Preformatted, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from datetime import datetime


def create_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name='MainTitle',
        parent=styles['Heading1'],
        fontSize=28,
        spaceAfter=6,
        textColor=colors.HexColor('#1E3C72'),
        alignment=TA_CENTER,
    ))

    styles.add(ParagraphStyle(
        name='SubTitle',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=20,
        textColor=colors.HexColor('#666666'),
        alignment=TA_CENTER,
    ))

    styles.add(ParagraphStyle(
        name='ChapterTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceBefore=20,
        spaceAfter=12,
        textColor=colors.HexColor('#1E3C72'),
        borderWidth=0,
        borderPadding=0,
    ))

    styles.add(ParagraphStyle(
        name='SectionTitle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceBefore=16,
        spaceAfter=8,
        textColor=colors.HexColor('#333333'),
    ))

    styles.add(ParagraphStyle(
        name='SubSectionTitle',
        parent=styles['Heading3'],
        fontSize=11,
        spaceBefore=10,
        spaceAfter=6,
        textColor=colors.HexColor('#444444'),
    ))

    styles.add(ParagraphStyle(
        name='BodyTextCustom',
        parent=styles['Normal'],
        fontSize=10,
        spaceBefore=4,
        spaceAfter=8,
        alignment=TA_JUSTIFY,
        leading=14,
    ))

    styles.add(ParagraphStyle(
        name='BulletText',
        parent=styles['Normal'],
        fontSize=10,
        leftIndent=20,
        spaceBefore=2,
        spaceAfter=2,
        bulletIndent=10,
        leading=14,
    ))

    styles.add(ParagraphStyle(
        name='CodeStyle',
        parent=styles['Code'],
        fontSize=8,
        fontName='Courier',
        backColor=colors.HexColor('#F5F5F5'),
        spaceBefore=6,
        spaceAfter=6,
        leftIndent=10,
        rightIndent=10,
        leading=11,
    ))

    styles.add(ParagraphStyle(
        name='WarningTitle',
        parent=styles['Normal'],
        fontSize=10,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#856404'),
        backColor=colors.HexColor('#FFF3CD'),
        spaceBefore=0,
        spaceAfter=0,
    ))

    styles.add(ParagraphStyle(
        name='WarningBody',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#503C00'),
        backColor=colors.HexColor('#FFF3CD'),
        spaceBefore=0,
        spaceAfter=0,
        leading=12,
    ))

    return styles


def create_table(data, col_widths=None):
    """Create a styled table"""
    if col_widths is None:
        col_widths = [1.5*inch] * len(data[0])

    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3C72')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FFFFFF')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#FFFFFF'), colors.HexColor('#F5F5F5')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    return table


def create_warning_box(title, body, styles):
    """Create a warning box"""
    data = [
        [Paragraph(f"<b>! {title}</b>", styles['WarningTitle'])],
        [Paragraph(body, styles['WarningBody'])]
    ]
    table = Table(data, colWidths=[6.5*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FFF3CD')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#FFC107')),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    return table


def build_report():
    output_path = "/home/user/PratikoAi-BE/PratikoAI_Architecture_Analysis_Report.pdf"
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50
    )

    styles = create_styles()
    story = []

    # ========== TITLE PAGE ==========
    story.append(Spacer(1, 2*inch))
    story.append(Paragraph("PratikoAI", styles['MainTitle']))
    story.append(Paragraph("Chat Architecture Analysis", styles['MainTitle']))
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("Deep Dive Report: Prompts, Data Flow & Incoherence Analysis", styles['SubTitle']))
    story.append(Spacer(1, 1*inch))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y')}", styles['BodyTextCustom']))
    story.append(Paragraph("Analysis by: Claude Code Architecture Agent", styles['BodyTextCustom']))
    story.append(PageBreak())

    # ========== EXECUTIVE SUMMARY ==========
    story.append(Paragraph("Executive Summary", styles['ChapterTitle']))
    story.append(Paragraph(
        "This report provides a comprehensive architectural analysis of the PratikoAI chat system, "
        "focusing on prompt architecture, data flow mapping, and identification of incoherence issues "
        "affecting response quality and suggested action relevance.",
        styles['BodyTextCustom']
    ))
    story.append(Spacer(1, 0.2*inch))

    story.append(Paragraph("Key Findings", styles['SectionTitle']))
    bullets = [
        "6 core prompts identified across different routes and use cases",
        "HyDE (Hypothetical Document Embedding) operates without conversation context",
        "Suggested actions generated via TWO different pathways depending on route",
        "Post-proactivity step lacks access to KB context that informed the response",
        "No explicit Chain-of-Thought (CoT) framework despite complex domain requirements",
    ]
    for b in bullets:
        story.append(Paragraph(f"<bullet>&bull;</bullet> {b}", styles['BulletText']))

    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("Critical Issues Identified", styles['SectionTitle']))
    story.append(create_warning_box(
        "CRITICAL: Context Fragmentation",
        "Post-proactivity (Step 100) extracts suggested actions WITHOUT access to the KB context "
        "documents that informed the LLM response, causing disconnected action suggestions.",
        styles
    ))
    story.append(Spacer(1, 0.1*inch))
    story.append(create_warning_box(
        "CRITICAL: Dual Action Generation Paths",
        "Synthesis routes use VERDETTO parsing while standard routes use XML tag parsing, "
        "producing inconsistent action quality and structure.",
        styles
    ))
    story.append(PageBreak())

    # ========== SECTION 1: PROMPT MAPPING ==========
    story.append(Paragraph("1. Prompt Mapping", styles['ChapterTitle']))
    story.append(Paragraph(
        "The following table identifies all system prompts and templates in the codebase, "
        "their locations, and primary purposes.",
        styles['BodyTextCustom']
    ))

    story.append(Paragraph("1.1 Core Prompts Inventory", styles['SectionTitle']))
    prompt_data = [
        ['Prompt', 'File Location', 'Lines', 'Purpose'],
        ['Main System', 'app/core/prompts/system.md', '382', 'Core assistant identity & rules'],
        ['Synthesis', 'app/core/prompts/synthesis_critical.py', '68-144', 'Verdetto format for research'],
        ['HyDE', 'app/services/hyde_generator.py', '51-74', 'Hypothetical doc generation'],
        ['Suggested Actions', 'app/core/prompts/suggested_actions.md', '51', 'XML action instructions'],
        ['Doc Analysis', 'app/core/prompts/document_analysis.md', '172', 'Document analysis framework'],
        ['Doc Override', 'app/core/prompts/document_analysis_override.md', '156', 'Forces doc focus'],
    ]
    story.append(create_table(prompt_data, [1.2*inch, 2.5*inch, 0.6*inch, 2.2*inch]))
    story.append(Spacer(1, 0.2*inch))

    story.append(Paragraph("1.2 HyDE Prompt Details", styles['SectionTitle']))
    story.append(Paragraph("Location: app/services/hyde_generator.py (Lines 51-74)", styles['BodyTextCustom']))
    story.append(Paragraph(
        "The HyDE system generates hypothetical Italian bureaucratic documents to improve vector search recall:",
        styles['BodyTextCustom']
    ))

    hyde_code = """Sei un esperto di normativa fiscale e legale italiana.
Il tuo compito e generare un documento ipotetico che risponda
alla domanda dell'utente.

STILE RICHIESTO:
- Stile burocratico/amministrativo italiano
- Linguaggio formale e tecnico
- Riferimenti normativi (Leggi, Decreti, Circolari)

REQUISITI:
- Lunghezza: 150-250 parole
- Includi riferimenti a leggi, decreti, articoli specifici"""
    story.append(Preformatted(hyde_code, styles['CodeStyle']))

    story.append(Paragraph("<bullet>&bull;</bullet> Model: GPT-4o-mini (ModelTier.BASIC)", styles['BulletText']))
    story.append(Paragraph("<bullet>&bull;</bullet> Skipped for: CHITCHAT, CALCULATOR routes", styles['BulletText']))
    story.append(Paragraph("<bullet>&bull;</bullet> Output stored in: state['hyde_result']", styles['BulletText']))

    story.append(Paragraph("1.3 Suggested Actions Prompt", styles['SectionTitle']))
    story.append(Paragraph("Location: app/core/prompts/suggested_actions.md (51 lines)", styles['BodyTextCustom']))
    story.append(Paragraph(
        "Instructs the LLM to output structured XML tags for proactive suggestions:",
        styles['BodyTextCustom']
    ))

    actions_code = """<answer>
[Complete response with citations]
</answer>

<suggested_actions>
[
  {"id": "1", "label": "Azione breve", "icon": "...",
   "prompt": "Full prompt for execution"},
  ...
]
</suggested_actions>"""
    story.append(Preformatted(actions_code, styles['CodeStyle']))

    story.append(create_warning_box(
        "IMPORTANT: Conditional Injection",
        "This prompt is ONLY appended for non-synthesis routes (Line 749 in prompting.py). "
        "Synthesis routes never receive these instructions, relying on VERDETTO parsing instead.",
        styles
    ))

    story.append(Paragraph("1.4 Synthesis (Verdetto) Prompt", styles['SectionTitle']))
    story.append(Paragraph("Location: app/core/prompts/synthesis_critical.py (Lines 68-144)", styles['BodyTextCustom']))
    story.append(Paragraph(
        "Used for technical_research routes. Defines 4 analysis tasks (Compiti):",
        styles['BodyTextCustom']
    ))
    story.append(Paragraph("<bullet>&bull;</bullet> COMPITO 1: ANALISI CRONOLOGICA - Order documents by date, identify evolution", styles['BulletText']))
    story.append(Paragraph("<bullet>&bull;</bullet> COMPITO 2: RILEVAMENTO CONFLITTI - Detect contradictions between sources", styles['BulletText']))
    story.append(Paragraph("<bullet>&bull;</bullet> COMPITO 3: APPLICAZIONE GERARCHIA - Apply legal hierarchy (Legge > Decreto > Circolare)", styles['BulletText']))
    story.append(Paragraph("<bullet>&bull;</bullet> COMPITO 4: VERDETTO OPERATIVO - Structured output with action/risk/deadline", styles['BulletText']))

    story.append(Paragraph("1.5 Missing: Chain-of-Thought (CoT)", styles['SectionTitle']))
    story.append(create_warning_box(
        "GAP IDENTIFIED",
        "No explicit Chain-of-Thought prompts found in the codebase. The synthesis prompt has "
        "implicit reasoning via the '4 Compiti' structure, but no 'think step by step' framework "
        "exists for complex multi-source reasoning.",
        styles
    ))
    story.append(PageBreak())

    # ========== SECTION 2: DATA FLOW ==========
    story.append(Paragraph("2. Data Flow Mapping", styles['ChapterTitle']))
    story.append(Paragraph(
        "The following diagram shows the complete execution sequence from user query to response, "
        "highlighting where each prompt is applied and where context flows.",
        styles['BodyTextCustom']
    ))

    story.append(Paragraph("2.1 Pipeline Overview", styles['SectionTitle']))
    flow_code1 = """USER QUERY
    |
    v
STEP 14: PRE-PROACTIVITY
  - Detect calculator intent (IRPEF, IVA, INPS, F24)
  - If missing params -> Return InteractiveQuestion
    |
    v
STEP 31-34: CLASSIFICATION
  - DomainActionClassifier -> domain, action, confidence
  - LLMRouter -> technical_research / chitchat / calculator
    |
    +------------------+------------------+
    |                  |                  |
    v                  v                  v
STEP 39a:          STEP 39b:          (parallel)
MultiQuery         HyDE Generation
(expansion)        (GPT-4o-mini)
    |                  |
    +--------+---------+
             v
STEP 39c: PARALLEL RETRIEVAL (3-way search)
  - Original query + Expanded queries + HyDE doc
             |
             v
STEP 40: BUILD CONTEXT
  - Merge KB documents + User documents + PII mapping"""
    story.append(Preformatted(flow_code1, styles['CodeStyle']))

    flow_code2 = """             |
             v
STEP 41-47: PROMPT SELECTION
  +---------------------------+---------------------------+
  | Route='technical_research'| Route=other               |
  |---------------------------|---------------------------|
  | SYNTHESIS_PROMPT          | SYSTEM_PROMPT             |
  | (Verdetto format)         | + SUGGESTED_ACTIONS       |
  | NO action instructions    | (XML tags expected)       |
  +---------------------------+---------------------------+
             |
             v
STEP 64: LLM CALL (Claude Opus 4.5)
  - System prompt + Context + Query
             |
             v
STEP 100: POST-PROACTIVITY
  Priority 1: Document templates (if attachment)
  Priority 2: Parse VERDETTO (for technical_research)
  Priority 3: Parse <suggested_actions> XML
             |
             v
RESPONSE: {response, suggested_actions, metadata}"""
    story.append(Preformatted(flow_code2, styles['CodeStyle']))

    story.append(Paragraph("2.2 Key LangGraph Nodes", styles['SectionTitle']))
    nodes_data = [
        ['Step', 'Node File', 'Purpose'],
        ['14', 'step_014__pre_proactivity.py', 'Check calculable intents'],
        ['39a', 'step_039a__multi_query.py', 'Expand user query'],
        ['39b', 'step_039b__hyde.py', 'Generate hypothetical document'],
        ['39c', 'step_039c__parallel_retrieval.py', '3-way vector search'],
        ['40', 'step_040__build_context.py', 'Merge context sources'],
        ['44', 'step_044__default_sys_prompt.py', 'Select system prompt'],
        ['64', 'step_064__llm_call.py', 'Execute LLM call'],
        ['100', 'step_100__post_proactivity.py', 'Extract suggested actions'],
    ]
    story.append(create_table(nodes_data, [0.6*inch, 2.8*inch, 2.5*inch]))
    story.append(PageBreak())

    # ========== SECTION 3: INCOHERENCE ANALYSIS ==========
    story.append(Paragraph("3. Incoherence Analysis", styles['ChapterTitle']))
    story.append(Paragraph(
        "This section identifies context fragmentation issues that cause chat incoherence "
        "and poor suggested action quality.",
        styles['BodyTextCustom']
    ))

    story.append(Paragraph("3.1 CRITICAL: Suggested Actions Context Gap", styles['SectionTitle']))
    story.append(Paragraph("Location: app/core/langgraph/nodes/step_100__post_proactivity.py", styles['BodyTextCustom']))
    gap_code = """LLM Call (Step 64)     ->   Has: System Prompt + KB Context + Query
                            Outputs: Response text (+ possibly XML tags)
                                     |
                                     v
Post-Proactivity       ->   Receives: LLM response text ONLY
(Step 100)                  Does NOT receive: KB context documents
                            Result: Actions disconnected from sources"""
    story.append(Preformatted(gap_code, styles['CodeStyle']))
    story.append(Paragraph(
        "IMPACT: Suggested actions are generated based only on the LLM's output text, "
        "without access to the underlying KB documents that informed the response. "
        "This causes actions that may not align with the source material.",
        styles['BodyTextCustom']
    ))

    story.append(Paragraph("3.2 CRITICAL: Synthesis Route Missing Action Instructions", styles['SectionTitle']))
    story.append(Paragraph("Location: app/orchestrators/prompting.py:749", styles['BodyTextCustom']))
    synth_code = """if not is_synthesis_route:
    prompt = prompt + '\\n\\n' + SUGGESTED_ACTIONS_PROMPT"""
    story.append(Preformatted(synth_code, styles['CodeStyle']))
    story.append(Paragraph(
        "For technical_research routes: Uses SYNTHESIS_SYSTEM_PROMPT (Verdetto format), "
        "does NOT append SUGGESTED_ACTIONS_PROMPT, LLM never receives instructions to generate "
        "<suggested_actions> XML, Post-proactivity falls back to parsing VERDETTO structure instead.",
        styles['BodyTextCustom']
    ))
    story.append(create_warning_box(
        "RESULT",
        "Two completely different action generation pathways depending on route, "
        "producing inconsistent action quality and structure.",
        styles
    ))

    story.append(Paragraph("3.3 HyDE Has No Memory", styles['SectionTitle']))
    story.append(Paragraph("Location: app/services/hyde_generator.py:51-74", styles['BodyTextCustom']))
    story.append(Paragraph(
        "HyDE generation uses ONLY the current query - no conversation history, "
        "no previous context from earlier turns.",
        styles['BodyTextCustom']
    ))
    hyde_mem_code = """# HyDE prompt receives ONLY:
user_prompt = f'Genera un documento ipotetico... Domanda: {query}'

# Missing: Previous conversation turns
# Missing: Document context from earlier in conversation"""
    story.append(Preformatted(hyde_mem_code, styles['CodeStyle']))

    story.append(Paragraph("3.4 Dual Action Extraction Paths", styles['SectionTitle']))
    dual_data = [
        ['Route', 'Action Source', 'Method'],
        ['technical_research', 'VERDETTO parsing', 'Extract azione_consigliata, rischio, scadenza'],
        ['All other routes', 'XML tag parsing', 'Parse <suggested_actions> JSON block'],
    ]
    story.append(create_table(dual_data, [1.5*inch, 1.5*inch, 3*inch]))
    story.append(Paragraph(
        "These two extraction methods produce different action structures and inconsistent quality.",
        styles['BodyTextCustom']
    ))
    story.append(PageBreak())

    # ========== SECTION 4: BOTTLENECKS ==========
    story.append(Paragraph("4. Bottlenecks & Contradictions", styles['ChapterTitle']))

    story.append(Paragraph("4.1 No Chain-of-Thought Framework", styles['SectionTitle']))
    story.append(Paragraph(
        "Despite complex multi-source reasoning requirements for Italian tax/legal domain, "
        "there is no explicit CoT guidance in any prompt:",
        styles['BodyTextCustom']
    ))
    story.append(Paragraph("<bullet>&bull;</bullet> system.md: Focuses on formatting/citations, not reasoning process", styles['BulletText']))
    story.append(Paragraph("<bullet>&bull;</bullet> synthesis_critical.py: Has '4 Compiti' structure but no step-by-step instructions", styles['BulletText']))
    story.append(Paragraph("<bullet>&bull;</bullet> No 'Let's think through this systematically' type prompts", styles['BulletText']))

    story.append(Paragraph("4.2 Document Priority Confusion", styles['SectionTitle']))
    story.append(Paragraph("Two competing document analysis systems may send mixed signals:", styles['BodyTextCustom']))
    story.append(Paragraph("<bullet>&bull;</bullet> document_analysis.md - Comprehensive analysis framework", styles['BulletText']))
    story.append(Paragraph("<bullet>&bull;</bullet> document_analysis_override.md - Forces focus ONLY on user docs", styles['BulletText']))
    story.append(Paragraph(
        "When query_composition='hybrid', both may be active simultaneously, "
        "creating conflicting instructions for the LLM.",
        styles['BodyTextCustom']
    ))

    story.append(Paragraph("4.3 Synthesis vs Standard Prompt Divergence", styles['SectionTitle']))
    diverge_data = [
        ['Aspect', 'SYSTEM_PROMPT', 'SYNTHESIS_PROMPT'],
        ['Output format', 'Free-form with XML tags', 'Structured Verdetto'],
        ['Action instruction', '<suggested_actions>', 'None (parsed from verdetto)'],
        ['Reasoning visible', 'No', 'Partial (via Compiti)'],
    ]
    story.append(create_table(diverge_data, [1.5*inch, 2.2*inch, 2.2*inch]))

    story.append(Paragraph("4.4 Context Window Competition", styles['SectionTitle']))
    story.append(Paragraph("Multiple context sources compete for the same token budget:", styles['BodyTextCustom']))
    story.append(Paragraph("<bullet>&bull;</bullet> KB documents (Step 40) - Variable size", styles['BulletText']))
    story.append(Paragraph("<bullet>&bull;</bullet> User documents (Step 40) - Variable size", styles['BulletText']))
    story.append(Paragraph("<bullet>&bull;</bullet> System prompt - ~2000+ tokens", styles['BulletText']))
    story.append(Paragraph("<bullet>&bull;</bullet> Suggested actions instructions - ~500 tokens", styles['BulletText']))
    story.append(create_warning_box(
        "GAP",
        "No visible prioritization or truncation strategy found in the codebase. "
        "Risk of context overflow with large document sets.",
        styles
    ))
    story.append(PageBreak())

    # ========== SECTION 5: FILES ==========
    story.append(Paragraph("5. Key Files for Refactoring", styles['ChapterTitle']))

    story.append(Paragraph("5.1 Priority 1 - Prompt Unification", styles['SectionTitle']))
    files_code1 = """app/core/prompts/
  |-- __init__.py              # Prompt loading logic
  |-- system.md                # Main system prompt
  |-- synthesis_critical.py    # Synthesis route prompt
  |-- suggested_actions.md     # Action generation instructions
  |-- document_analysis.md     # Document analysis framework
  +-- document_analysis_override.md"""
    story.append(Preformatted(files_code1, styles['CodeStyle']))

    story.append(Paragraph("5.2 Priority 2 - Flow Control", styles['SectionTitle']))
    files_code2 = """app/core/langgraph/nodes/
  |-- step_014__pre_proactivity.py    # Pre-response questions
  |-- step_039b__hyde.py              # HyDE generation
  |-- step_040__build_context.py      # Context merging
  |-- step_044__default_sys_prompt.py # Prompt selection
  |-- step_064__llm_call.py           # LLM execution
  +-- step_100__post_proactivity.py   # Action extraction"""
    story.append(Preformatted(files_code2, styles['CodeStyle']))

    story.append(Paragraph("5.3 Priority 3 - Services", styles['SectionTitle']))
    files_code3 = """app/services/
  |-- hyde_generator.py               # HyDE document creation
  |-- proactivity_graph_service.py    # Action logic
  |-- synthesis_prompt_builder.py     # Synthesis assembly
  |-- llm_response_parser.py          # XML parsing
  +-- verdetto_parser.py              # Verdetto parsing"""
    story.append(Preformatted(files_code3, styles['CodeStyle']))
    story.append(PageBreak())

    # ========== SECTION 6: RECOMMENDATIONS ==========
    story.append(Paragraph("6. Recommendations", styles['ChapterTitle']))

    story.append(Paragraph("6.1 Immediate Fixes", styles['SectionTitle']))

    story.append(Paragraph("Fix 1: Unify Action Generation", styles['SubSectionTitle']))
    story.append(Paragraph("<bullet>&bull;</bullet> Create single ActionGenerationPrompt used by ALL routes", styles['BulletText']))
    story.append(Paragraph("<bullet>&bull;</bullet> Append to both synthesis and standard prompts", styles['BulletText']))
    story.append(Paragraph("<bullet>&bull;</bullet> Parse same XML structure regardless of route", styles['BulletText']))

    story.append(Paragraph("Fix 2: Add CoT Framework", styles['SubSectionTitle']))
    story.append(Paragraph("<bullet>&bull;</bullet> Create reasoning_framework.md with explicit step-by-step reasoning", styles['BulletText']))
    story.append(Paragraph("<bullet>&bull;</bullet> Inject before final answer generation in both routes", styles['BulletText']))
    story.append(Paragraph("<bullet>&bull;</bullet> Include 'Ragiona passo dopo passo' instructions", styles['BulletText']))

    story.append(Paragraph("Fix 3: Pass Context to Post-Proactivity", styles['SubSectionTitle']))
    story.append(Paragraph("<bullet>&bull;</bullet> Modify Step 100 to receive state['context'] summary", styles['BulletText']))
    story.append(Paragraph("<bullet>&bull;</bullet> Use context for action relevance scoring", styles['BulletText']))
    story.append(Paragraph("<bullet>&bull;</bullet> Validate suggested actions against source material", styles['BulletText']))

    story.append(Paragraph("Fix 4: HyDE Context Awareness", styles['SubSectionTitle']))
    story.append(Paragraph("<bullet>&bull;</bullet> Pass last N conversation turns to HyDE generator", styles['BulletText']))
    story.append(Paragraph("<bullet>&bull;</bullet> Include document filenames mentioned in conversation", styles['BulletText']))
    story.append(Paragraph("<bullet>&bull;</bullet> Improve retrieval relevance for follow-up questions", styles['BulletText']))

    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("6.2 Proposed Unified Pipeline", styles['SectionTitle']))
    unified_code = """Query -> Classification -> [HyDE + MultiQuery + Retrieval]
                                    |
                                    v
                            Context Building
                                    |
                                    v
                +--------------------------------------+
                |     UNIFIED PROMPT TEMPLATE          |
                |   - System identity                  |
                |   - CoT reasoning framework          |
                |   - Context + Documents              |
                |   - Action generation rules          |
                |   - Output format spec               |
                +--------------------------------------+
                                    |
                                    v
                              LLM Call
                                    |
                                    v
                +--------------------------------------+
                |     UNIFIED RESPONSE PARSER          |
                |   - Extract reasoning trace          |
                |   - Extract main answer              |
                |   - Extract suggested actions        |
                |   - Validate against context         |
                +--------------------------------------+"""
    story.append(Preformatted(unified_code, styles['CodeStyle']))
    story.append(PageBreak())

    # ========== SECTION 7: SUMMARY ==========
    story.append(Paragraph("7. Summary", styles['ChapterTitle']))

    story.append(Paragraph("Architecture Strengths", styles['SectionTitle']))
    story.append(Paragraph("<bullet>&bull;</bullet> Clear prompt separation for different routes (synthesis vs. standard)", styles['BulletText']))
    story.append(Paragraph("<bullet>&bull;</bullet> Document-aware processing with specialized prompts", styles['BulletText']))
    story.append(Paragraph("<bullet>&bull;</bullet> Hierarchical source authority in synthesis prompt (law > decree > circular)", styles['BulletText']))
    story.append(Paragraph("<bullet>&bull;</bullet> Two-tier proactivity system (pre-question + post-actions)", styles['BulletText']))
    story.append(Paragraph("<bullet>&bull;</bullet> PII protection integrated throughout pipeline (DEV-007)", styles['BulletText']))

    story.append(Paragraph("Architecture Weaknesses", styles['SectionTitle']))
    story.append(Paragraph("<bullet>&bull;</bullet> Missing explicit Chain-of-Thought guidance despite complex domain", styles['BulletText']))
    story.append(Paragraph("<bullet>&bull;</bullet> Context fragmentation in suggested action generation", styles['BulletText']))
    story.append(Paragraph("<bullet>&bull;</bullet> Limited reasoning transparency in synthesis output", styles['BulletText']))
    story.append(Paragraph("<bullet>&bull;</bullet> Dual action extraction paths causing inconsistency", styles['BulletText']))
    story.append(Paragraph("<bullet>&bull;</bullet> HyDE lacks conversation memory for follow-up questions", styles['BulletText']))

    story.append(Paragraph("Next Steps", styles['SectionTitle']))
    story.append(Paragraph(
        "1. Review this report with the development team\n"
        "2. Prioritize fixes based on impact to user experience\n"
        "3. Create unified prompt template architecture\n"
        "4. Implement Chain-of-Thought framework\n"
        "5. Refactor post-proactivity to receive context\n"
        "6. Add comprehensive testing for prompt combinations",
        styles['BodyTextCustom']
    ))

    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph("End of Report", styles['SubTitle']))

    # Build PDF
    doc.build(story)
    return output_path


if __name__ == "__main__":
    path = build_report()
    print(f"Report generated: {path}")
