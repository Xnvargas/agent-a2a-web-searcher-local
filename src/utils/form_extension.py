"""
=============================================================================
FORM EXTENSION - User Input Request for A2A Protocol
=============================================================================

This module provides utilities for creating form request metadata that follows
the A2A form-request extension specification. Use this when your agent needs
to collect additional information from the user during execution.

USAGE:
------

```python
from utils.form_extension import (
    create_form_request_metadata,
    FormField,
    FieldType
)

# Create a form to request user input
fields = [
    FormField(
        id="api_key",
        type=FieldType.TEXT,
        label="API Key",
        description="Enter your API key for the service",
        required=True,
        col_span=2
    ),
    FormField(
        id="environment",
        type=FieldType.SINGLE_SELECT,
        label="Environment",
        options=[
            {"value": "prod", "label": "Production"},
            {"value": "dev", "label": "Development"},
        ],
        required=True
    ),
    FormField(
        id="confirm",
        type=FieldType.CHECKBOX,
        label="I confirm this action",
        required=True
    )
]

form_metadata = create_form_request_metadata(
    fields=fields,
    title="Additional Information Required",
    description="Please provide the following to continue",
    columns=2
)

# Yield with input-required state
yield AgentMessage(
    text="I need some additional information to proceed.",
    metadata=form_metadata
)
```

A2A PROTOCOL COMPLIANCE:
------------------------

This module supports the A2A form-request extension by providing:
- URI-keyed metadata format for client parsing
- Structured form field definitions
- Support for various field types (text, select, checkbox, etc.)
- Multi-column layout support

=============================================================================
"""

from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from enum import Enum

from .extension_uris import ExtensionURIs, create_extension_metadata


# =============================================================================
# FIELD TYPES
# =============================================================================

class FieldType:
    """Field type constants for form fields."""
    TEXT = "text"
    DATE = "date"
    FILE = "file"
    SINGLE_SELECT = "single_select"
    MULTI_SELECT = "multi_select"
    CHECKBOX = "checkbox"
    TEXTAREA = "textarea"
    NUMBER = "number"
    EMAIL = "email"
    URL = "url"
    PASSWORD = "password"


# =============================================================================
# FORM DATA STRUCTURES
# =============================================================================

@dataclass
class SelectOption:
    """Option for select fields."""
    value: str
    label: str
    description: Optional[str] = None
    disabled: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {
            "value": self.value,
            "label": self.label,
        }
        if self.description:
            data["description"] = self.description
        if self.disabled:
            data["disabled"] = self.disabled
        return data


@dataclass
class FormField:
    """
    Form field definition for A2A form-request extension.

    Attributes:
        id: Unique identifier for the field
        type: Field type from FieldType constants
        label: Display label for the field
        description: Optional help text or description
        required: Whether the field is required
        default_value: Optional default value
        options: List of options for select fields
        col_span: Number of columns to span in multi-column layouts
        placeholder: Optional placeholder text
        validation_pattern: Optional regex pattern for validation
        min_length: Optional minimum length for text fields
        max_length: Optional maximum length for text fields
        min_value: Optional minimum value for number fields
        max_value: Optional maximum value for number fields
    """
    id: str
    type: str
    label: str
    description: Optional[str] = None
    required: bool = False
    default_value: Any = None
    options: Optional[List[Union[SelectOption, Dict[str, str]]]] = None
    col_span: int = 1
    placeholder: Optional[str] = None
    validation_pattern: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = {
            "id": self.id,
            "type": self.type,
            "label": self.label,
        }

        if self.description:
            data["description"] = self.description
        if self.required:
            data["required"] = self.required
        if self.default_value is not None:
            data["default_value"] = self.default_value
        if self.options:
            data["options"] = [
                opt.to_dict() if isinstance(opt, SelectOption) else opt
                for opt in self.options
            ]
        if self.col_span != 1:
            data["col_span"] = self.col_span
        if self.placeholder:
            data["placeholder"] = self.placeholder
        if self.validation_pattern:
            data["validation_pattern"] = self.validation_pattern
        if self.min_length is not None:
            data["min_length"] = self.min_length
        if self.max_length is not None:
            data["max_length"] = self.max_length
        if self.min_value is not None:
            data["min_value"] = self.min_value
        if self.max_value is not None:
            data["max_value"] = self.max_value

        return data


# =============================================================================
# A2A PROTOCOL FORM REQUEST METADATA HELPERS
# =============================================================================

def create_form_request_metadata(
    fields: List[FormField],
    title: Optional[str] = None,
    description: Optional[str] = None,
    columns: int = 1,
    submit_label: str = "Submit",
    cancel_label: str = "Cancel",
    show_cancel: bool = True
) -> Dict[str, Any]:
    """
    Create form request metadata in the A2A protocol format.

    Returns metadata keyed by the form-request extension URI for client parsing.

    Args:
        fields: List of FormField definitions
        title: Optional form title
        description: Optional form description
        columns: Number of columns for layout (1-4)
        submit_label: Label for submit button
        cancel_label: Label for cancel button
        show_cancel: Whether to show cancel button

    Returns:
        Dictionary with form-request extension URI as key and form data as value

    Example:
        ```python
        fields = [
            FormField(id="name", type=FieldType.TEXT, label="Name", required=True)
        ]
        metadata = create_form_request_metadata(
            fields=fields,
            title="User Information",
            description="Please provide your details"
        )
        ```
    """
    form_data = {
        "fields": [f.to_dict() for f in fields],
        "columns": columns,
        "submit_label": submit_label,
    }

    if title:
        form_data["title"] = title
    if description:
        form_data["description"] = description
    if show_cancel:
        form_data["cancel_label"] = cancel_label
        form_data["show_cancel"] = show_cancel

    return create_extension_metadata(ExtensionURIs.FORM_REQUEST, form_data)


# =============================================================================
# CONVENIENCE FIELD BUILDERS
# =============================================================================

def text_field(
    id: str,
    label: str,
    required: bool = False,
    description: Optional[str] = None,
    placeholder: Optional[str] = None,
    default_value: Optional[str] = None,
    col_span: int = 1
) -> FormField:
    """Create a text input field."""
    return FormField(
        id=id,
        type=FieldType.TEXT,
        label=label,
        required=required,
        description=description,
        placeholder=placeholder,
        default_value=default_value,
        col_span=col_span
    )


def textarea_field(
    id: str,
    label: str,
    required: bool = False,
    description: Optional[str] = None,
    placeholder: Optional[str] = None,
    default_value: Optional[str] = None,
    col_span: int = 2
) -> FormField:
    """Create a textarea field."""
    return FormField(
        id=id,
        type=FieldType.TEXTAREA,
        label=label,
        required=required,
        description=description,
        placeholder=placeholder,
        default_value=default_value,
        col_span=col_span
    )


def select_field(
    id: str,
    label: str,
    options: List[Dict[str, str]],
    required: bool = False,
    description: Optional[str] = None,
    default_value: Optional[str] = None,
    multi: bool = False,
    col_span: int = 1
) -> FormField:
    """Create a select field (single or multi)."""
    return FormField(
        id=id,
        type=FieldType.MULTI_SELECT if multi else FieldType.SINGLE_SELECT,
        label=label,
        options=options,
        required=required,
        description=description,
        default_value=default_value,
        col_span=col_span
    )


def checkbox_field(
    id: str,
    label: str,
    required: bool = False,
    description: Optional[str] = None,
    default_value: bool = False,
    col_span: int = 1
) -> FormField:
    """Create a checkbox field."""
    return FormField(
        id=id,
        type=FieldType.CHECKBOX,
        label=label,
        required=required,
        description=description,
        default_value=default_value,
        col_span=col_span
    )


def number_field(
    id: str,
    label: str,
    required: bool = False,
    description: Optional[str] = None,
    default_value: Optional[float] = None,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    col_span: int = 1
) -> FormField:
    """Create a number input field."""
    return FormField(
        id=id,
        type=FieldType.NUMBER,
        label=label,
        required=required,
        description=description,
        default_value=default_value,
        min_value=min_value,
        max_value=max_value,
        col_span=col_span
    )


def file_field(
    id: str,
    label: str,
    required: bool = False,
    description: Optional[str] = None,
    col_span: int = 2
) -> FormField:
    """Create a file upload field."""
    return FormField(
        id=id,
        type=FieldType.FILE,
        label=label,
        required=required,
        description=description,
        col_span=col_span
    )


# =============================================================================
# COMMON FORM TEMPLATES
# =============================================================================

def create_confirmation_form(
    message: str,
    confirm_label: str = "I confirm this action",
    title: str = "Confirmation Required"
) -> Dict[str, Any]:
    """
    Create a simple confirmation form.

    Args:
        message: The confirmation message to display
        confirm_label: Label for the confirmation checkbox
        title: Form title

    Returns:
        Form request metadata for confirmation
    """
    fields = [
        checkbox_field(
            id="confirmed",
            label=confirm_label,
            required=True,
            col_span=2
        )
    ]

    return create_form_request_metadata(
        fields=fields,
        title=title,
        description=message,
        columns=1,
        submit_label="Confirm",
        cancel_label="Cancel"
    )


def create_api_key_form(
    service_name: str,
    description: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a form requesting an API key.

    Args:
        service_name: Name of the service requiring the API key
        description: Optional additional description

    Returns:
        Form request metadata for API key input
    """
    desc = description or f"Please provide your API key for {service_name}"

    fields = [
        FormField(
            id="api_key",
            type=FieldType.PASSWORD,
            label=f"{service_name} API Key",
            description="Your API key will be used securely",
            required=True,
            placeholder="Enter your API key",
            col_span=2
        )
    ]

    return create_form_request_metadata(
        fields=fields,
        title=f"{service_name} Authentication Required",
        description=desc,
        columns=1,
        submit_label="Submit"
    )


def create_options_selection_form(
    title: str,
    options: List[Dict[str, str]],
    description: Optional[str] = None,
    allow_multiple: bool = False
) -> Dict[str, Any]:
    """
    Create a form for selecting from options.

    Args:
        title: Form title
        options: List of option dicts with 'value' and 'label' keys
        description: Optional description
        allow_multiple: Whether to allow multiple selections

    Returns:
        Form request metadata for option selection
    """
    fields = [
        select_field(
            id="selection",
            label="Please select an option",
            options=options,
            required=True,
            multi=allow_multiple,
            col_span=2
        )
    ]

    return create_form_request_metadata(
        fields=fields,
        title=title,
        description=description,
        columns=1,
        submit_label="Continue"
    )
