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
    """

    id: str = Field(..., description="Unique identifier for the action", min_length=1)
    label: str = Field(..., description="Display label for the action button", min_length=1)
    icon: str = Field(..., description="Icon name for the action button", min_length=1)
    category: ActionCategory = Field(..., description="Category of the action")
    prompt_template: str = Field(..., description="Template string with {placeholders}", min_length=1)
    requires_input: bool = Field(default=False, description="Whether action needs user input")
    input_placeholder: str | None = Field(default=None, description="Placeholder for input field")
    input_type: str | None = Field(default=None, description="Input type (text, number, etc.)")


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


class InteractiveQuestion(BaseModel):
    """Interactive question for parameter clarification.

    Represents a structured question shown to the user when
    the query is ambiguous or missing required parameters.
    Rendered inline in chat (Claude Code style).

    Attributes:
        id: Unique identifier for the question
        trigger_query: Query pattern that triggers this question
        text: Question text to display
        question_type: Type of question (single_choice, multi_choice)
        options: List of selectable options (minimum 2)
        allow_custom_input: Whether to allow free-text input
        custom_input_placeholder: Placeholder for custom input field
        prefilled_params: Parameters already extracted from query
    """

    id: str = Field(..., description="Unique identifier for the question", min_length=1)
    trigger_query: str | None = Field(default=None, description="Query pattern that triggers this question")
    text: str = Field(..., description="Question text to display", min_length=1)
    question_type: str = Field(..., description="Type of question (single_choice, multi_choice)")
    options: list[InteractiveOption] = Field(..., description="List of options (minimum 2)", min_length=2)
    allow_custom_input: bool = Field(default=False, description="Allow free-text input")
    custom_input_placeholder: str | None = Field(default=None, description="Placeholder for custom input")
    prefilled_params: dict[str, Any] | None = Field(default=None, description="Pre-filled parameters")

    @field_validator("options")
    @classmethod
    def validate_options(cls, v: list[InteractiveOption]) -> list[InteractiveOption]:
        """Validate that at least 2 options are provided."""
        if len(v) < 2:
            raise ValueError("At least 2 options are required")
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
        action_type: Type of action detected (e.g., fiscal_calculation)
        document_type: Type of document if attached (e.g., fattura, f24)
        user_history: List of previous queries in session
    """

    session_id: str = Field(..., description="Unique session identifier", min_length=1)
    domain: str = Field(..., description="Classified domain", min_length=1)
    action_type: str | None = Field(default=None, description="Type of action detected")
    document_type: str | None = Field(default=None, description="Type of document if attached")
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
    extraction_result: "ParameterExtractionResult | None" = Field(
        default=None, description="Extraction results"
    )
    processing_time_ms: float = Field(..., description="Processing time in milliseconds", ge=0.0)
