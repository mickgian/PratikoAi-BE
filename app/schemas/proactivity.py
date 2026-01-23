"""Proactivity schemas for PratikoAI v1.5 - DEV-150.

This module defines Pydantic V2 models for:
- Suggested Actions (FR-001)
- Interactive Questions (FR-002)
- Smart Parameter Extraction (FR-003)

Models:
- ActionCategory: Enum for action types (CALCULATE, SEARCH, VERIFY, EXPORT, EXPLAIN)
- Action: Suggested action with prompt template
- InteractiveOption: Option for interactive questions
- InteractiveQuestion: Structured clarification question
- ExtractedParameter: Parameter extracted from query with confidence
- ParameterExtractionResult: Coverage and extraction results
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ActionCategory(str, Enum):
    """Category of suggested action.

    DEPRECATED (DEV-245 Phase 5.15): Suggested actions feature removed per user feedback.
    This class is kept for backwards compatibility with existing data.

    Enum values:
    - CALCULATE: Mathematical calculations (IRPEF, IVA, INPS)
    - SEARCH: Search operations (normative, jurisprudence)
    - VERIFY: Verification checks (deadlines, compliance)
    - EXPORT: Export/download operations (PDF, Excel)
    - EXPLAIN: Explanations and clarifications
    """

    CALCULATE = "calculate"
    SEARCH = "search"
    VERIFY = "verify"
    EXPORT = "export"
    EXPLAIN = "explain"


class Action(BaseModel):
    """Suggested action model.

    DEPRECATED (DEV-245 Phase 5.15): Suggested actions feature removed per user feedback.
    This class is kept for backwards compatibility with existing data.

    Represents an action button that can be shown to the user
    after an AI response. Actions have a prompt template that
    gets filled with parameters when executed.

    Attributes:
        id: Unique identifier for the action
        label: Display label for the action button
        icon: Icon name for the action button
        category: Category of the action
        prompt_template: Template string with placeholders
        requires_input: Whether action needs user input before execution
        input_placeholder: Placeholder text for input field
        input_type: Type of input field (text, number, etc.)
        source_id: DEV-236 - Paragraph ID for source grounding (links to kb_sources_metadata)
        source_excerpt: DEV-236 - Excerpt from source document for tooltip display
    """

    id: str = Field(..., description="Unique identifier for the action", min_length=1)
    label: str = Field(..., description="Display label for the action button", min_length=1)
    icon: str = Field(..., description="Icon name for the action button", min_length=1)
    category: ActionCategory = Field(..., description="Category of the action")
    prompt_template: str = Field(..., description="Template string with {placeholders}", min_length=1)
    requires_input: bool = Field(default=False, description="Whether action needs user input")
    input_placeholder: str | None = Field(default=None, description="Placeholder for input field")
    input_type: str | None = Field(default=None, description="Input type (text, number, etc.)")
    # DEV-236: Paragraph-level source grounding
    source_id: str | None = Field(default=None, description="Paragraph ID linking to kb_sources_metadata")
    source_excerpt: str | None = Field(default=None, description="Excerpt from source for tooltip display")


class ActionSummary(BaseModel):
    """Minimal action summary for ActionContext (DEV-242 Phase 12A).

    DEPRECATED (DEV-245 Phase 5.15): Suggested actions feature removed per user feedback.
    This class is kept for backwards compatibility with existing data.

    Used to record available actions without full details.
    """

    id: str = Field(..., description="Action ID")
    label: str = Field(..., description="Action label")


class ActionContext(BaseModel):
    """Context for messages originated from suggested actions (DEV-242 Phase 12A).

    DEPRECATED (DEV-245 Phase 5.15): Suggested actions feature removed per user feedback.
    This class is kept for backwards compatibility with existing data.

    Tracks which suggested action was selected and what alternatives were available.
    This enables historical traceability - users can see, even months later, what
    actions were available and which one they chose.

    Attributes:
        selected_action_id: ID of the action that was clicked
        selected_action_label: Label of the selected action
        available_actions: All actions that were available at that moment
        timestamp: When the action was selected
    """

    selected_action_id: str = Field(..., description="ID of the action that was clicked")
    selected_action_label: str = Field(..., description="Label of the selected action")
    available_actions: list[ActionSummary] = Field(default_factory=list, description="All actions that were available")
    timestamp: str = Field(..., description="ISO timestamp when action was selected")


class InteractiveOption(BaseModel):
    """Option for an interactive question.

    Represents a selectable option in an interactive question.
    Options can lead to follow-up questions or require custom input.

    Attributes:
        id: Unique identifier for the option
        label: Display label for the option
        icon: Optional icon name
        leads_to: ID of follow-up question (multi-step flows)
        requires_input: Whether selecting this option requires custom input
    """

    id: str = Field(..., description="Unique identifier for the option", min_length=1)
    label: str = Field(..., description="Display label for the option", min_length=1)
    icon: str | None = Field(default=None, description="Icon name for the option")
    leads_to: str | None = Field(default=None, description="ID of follow-up question")
    requires_input: bool = Field(default=False, description="Whether option requires custom input")


class InputField(BaseModel):
    """Single input field in a multi-field question.

    Used for Claude Code style multi-field questions where multiple
    parameters are collected at once (e.g., IRPEF calculation with
    reddito, deduzioni, detrazioni).

    Attributes:
        id: Field identifier (used as parameter name)
        label: Display label for the field
        placeholder: Placeholder text for the input
        input_type: Type of input (text, number, currency, date)
        required: Whether this field is required
        validation: Optional regex validation pattern
    """

    id: str = Field(..., description="Field identifier", min_length=1)
    label: str = Field(..., description="Display label for the field", min_length=1)
    placeholder: str | None = Field(default=None, description="Placeholder text")
    input_type: str = Field(default="text", description="Input type (text, number, currency, date)")
    required: bool = Field(default=True, description="Whether this field is required")
    validation: str | None = Field(default=None, description="Regex validation pattern")


class InteractiveQuestion(BaseModel):
    """Interactive question for parameter clarification.

    Represents a structured question shown to the user when
    the query is ambiguous or missing required parameters.
    Rendered inline in chat (Claude Code style).

    Question Types:
    - single_choice: User selects one option from a list
    - multi_choice: User can select multiple options
    - multi_field: Claude Code style with multiple input fields (Tab navigation)

    Attributes:
        id: Unique identifier for the question
        trigger_query: Query pattern that triggers this question
        text: Question text to display
        question_type: Type of question (single_choice, multi_choice, multi_field)
        options: List of selectable options (for single_choice/multi_choice)
        fields: List of input fields (for multi_field type)
        allow_custom_input: Whether to allow free-text input
        custom_input_placeholder: Placeholder for custom input field
        prefilled_params: Parameters already extracted from query
    """

    id: str = Field(..., description="Unique identifier for the question", min_length=1)
    trigger_query: str | None = Field(default=None, description="Query pattern that triggers this question")
    text: str = Field(..., description="Question text to display", min_length=1)
    question_type: str = Field(..., description="Type of question (single_choice, multi_choice, multi_field)")
    options: list[InteractiveOption] = Field(default_factory=list, description="List of options (for choice types)")
    fields: list[InputField] = Field(default_factory=list, description="List of input fields (for multi_field type)")
    allow_custom_input: bool = Field(default=False, description="Allow free-text input")
    custom_input_placeholder: str | None = Field(default=None, description="Placeholder for custom input")
    prefilled_params: dict[str, Any] | None = Field(default=None, description="Pre-filled parameters")

    @field_validator("options")
    @classmethod
    def validate_options(cls, v: list[InteractiveOption], info) -> list[InteractiveOption]:
        """Validate options based on question_type."""
        # For multi_field questions, options are not required
        # Validation happens in model_validator for cross-field checks
        return v

    @field_validator("fields")
    @classmethod
    def validate_fields(cls, v: list[InputField]) -> list[InputField]:
        """Validate fields for multi_field questions."""
        return v


class ExtractedParameter(BaseModel):
    """Parameter extracted from user query.

    Represents a parameter value extracted from the query text
    along with confidence score and source information.

    Attributes:
        name: Parameter name (e.g., 'reddito', 'tipo_contribuente')
        value: Extracted value as string
        confidence: Confidence score (0.0 to 1.0)
        source: Where the value came from (query, context, default)
    """

    name: str = Field(..., description="Parameter name", min_length=1)
    value: str = Field(..., description="Extracted value as string")
    confidence: float = Field(..., description="Confidence score (0.0 to 1.0)", ge=0.0, le=1.0)
    source: str = Field(..., description="Source of the value", min_length=1)


class ParameterExtractionResult(BaseModel):
    """Result of parameter extraction from query.

    Contains the extracted parameters, missing required parameters,
    coverage percentage, and whether the query can proceed.

    Attributes:
        intent: Detected intent (e.g., 'calcolo_irpef', 'calcolo_iva')
        extracted: List of extracted parameters
        missing_required: List of missing required parameter names
        coverage: Percentage of required params found (0.0 to 1.0)
        can_proceed: Whether enough params are present to proceed
    """

    intent: str = Field(..., description="Detected intent", min_length=1)
    extracted: list[ExtractedParameter] = Field(default_factory=list, description="Extracted parameters")
    missing_required: list[str] = Field(default_factory=list, description="Missing required parameter names")
    coverage: float = Field(..., description="Coverage percentage (0.0 to 1.0)", ge=0.0, le=1.0)
    can_proceed: bool = Field(..., description="Whether query can proceed")


class ProactivityContext(BaseModel):
    """Context for proactivity processing.

    Contains session information, domain classification, and user history
    to inform action selection and question generation.

    Attributes:
        session_id: Unique session identifier for tracking
        domain: Classified domain (tax, labor, legal, documents, default)
        action_type: Type of action detected (e.g., calculation_request)
        document_type: Type of document if attached (e.g., fattura, f24)
        sub_domain: Sub-domain from classification (e.g., irpef, iva, inps)
        classification_confidence: Confidence score from DomainActionClassifier
        user_history: List of previous queries in session
    """

    session_id: str = Field(..., description="Unique session identifier", min_length=1)
    domain: str = Field(..., description="Classified domain", min_length=1)
    action_type: str | None = Field(default=None, description="Type of action detected")
    document_type: str | None = Field(default=None, description="Type of document if attached")
    sub_domain: str | None = Field(default=None, description="Sub-domain from classification (irpef, iva, etc.)")
    classification_confidence: float = Field(
        default=0.0, description="Confidence score from classifier", ge=0.0, le=1.0
    )
    user_history: list[str] = Field(default_factory=list, description="Previous queries in session")


class ProactivityResult(BaseModel):
    """Result of proactivity processing.

    Contains the selected actions, optional interactive question,
    extraction result, and processing metrics.

    Attributes:
        actions: List of suggested actions to display
        question: Interactive question if query needs clarification
        extraction_result: Parameter extraction results
        processing_time_ms: Time taken to process in milliseconds
    """

    actions: list[Action] = Field(default_factory=list, description="Suggested actions")
    question: InteractiveQuestion | None = Field(default=None, description="Interactive question")
    extraction_result: "ParameterExtractionResult | None" = Field(default=None, description="Extraction results")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds", ge=0.0)


class ActionExecuteRequest(BaseModel):
    """Request model for /actions/execute endpoint - DEV-160.

    Contains the action to execute, optional parameters, and session context.

    Attributes:
        action_id: ID of the action template to execute
        parameters: Optional parameters to substitute in prompt_template
        session_id: Session ID for context tracking
    """

    action_id: str = Field(..., description="ID of the action template to execute", min_length=1)
    parameters: dict[str, Any] | None = Field(default=None, description="Parameters for prompt template")
    session_id: str = Field(..., description="Session ID for context tracking", min_length=1)


class QuestionAnswerRequest(BaseModel):
    """Request model for /questions/answer endpoint - DEV-161.

    Contains the question answer, selected option, and optional custom input.
    Supports both single-choice and multi-field question types.

    Attributes:
        question_id: ID of the question being answered
        selected_option: ID of the selected option (for single/multi_choice)
        custom_input: Optional custom input if option requires it
        field_values: Dict of field_id -> value (for multi_field questions)
        session_id: Session ID for context tracking
    """

    question_id: str = Field(..., description="ID of the question being answered", min_length=1)
    selected_option: str | None = Field(default=None, description="ID of the selected option (for choice types)")
    custom_input: str | None = Field(default=None, description="Custom input if option requires it")
    field_values: dict[str, str] | None = Field(default=None, description="Field values for multi_field questions")
    session_id: str = Field(..., description="Session ID for context tracking", min_length=1)


class QuestionAnswerResponse(BaseModel):
    """Response model for /questions/answer endpoint - DEV-161.

    Contains either a follow-up question (multi-step) or an answer (terminal).

    Attributes:
        next_question: Follow-up question if multi-step flow
        answer: Answer text if terminal question
        suggested_actions: Follow-up actions after answer
    """

    next_question: InteractiveQuestion | None = Field(default=None, description="Follow-up question")
    answer: str | None = Field(default=None, description="Answer text if terminal")
    suggested_actions: list[Action] | None = Field(default=None, description="Follow-up actions")
