"""
=============================================================================
MERMAID VALIDATOR - Pre-Persist Validation & Auto-Fix for Mermaid Diagrams
=============================================================================

Validates Mermaid diagram blocks extracted from markdown content before
persisting to the database. Catches common syntax errors that cause
client-side rendering failures, especially from smaller LLMs.

Features:
- Extracts all ```mermaid blocks from markdown
- Validates syntax for: erDiagram, graph/flowchart, sequenceDiagram, classDiagram
- Auto-fixes common issues (unquoted labels, inline PK/FK, bad SQL types)
- Falls back to flowchart when erDiagram is too broken to fix
- Returns validated/fixed markdown ready for persistence

=============================================================================
"""

import re
from typing import List, Tuple, Optional
from dataclasses import dataclass, field


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class MermaidBlock:
    """A single Mermaid diagram block extracted from markdown."""
    raw: str
    start_pos: int
    end_pos: int
    diagram_type: str
    lines: List[str] = field(default_factory=list)


@dataclass
class ValidationError:
    """A specific validation error found in a Mermaid block."""
    line_number: int
    line_content: str
    error_type: str
    message: str


@dataclass
class ValidationResult:
    """Result of validating a single Mermaid block."""
    block_index: int
    original: str
    fixed: str
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    was_converted: bool = False  # True if erDiagram was converted to flowchart
    is_valid: bool = True


# ============================================================================
# SQL TYPE MAPPING - Convert SQL types to Mermaid-safe types
# ============================================================================

SQL_TYPE_MAP = {
    "varchar": "string",
    "nvarchar": "string",
    "char": "string",
    "nchar": "string",
    "text": "text",
    "ntext": "text",
    "clob": "text",
    "integer": "int",
    "bigint": "int",
    "smallint": "int",
    "tinyint": "int",
    "serial": "int",
    "bigserial": "int",
    "numeric": "float",
    "decimal": "float",
    "real": "float",
    "double": "float",
    "money": "float",
    "boolean": "bool",
    "bool": "bool",
    "bit": "bool",
    "timestamp": "datetime",
    "timestamptz": "datetime",
    "datetime": "datetime",
    "datetime2": "datetime",
    "smalldatetime": "datetime",
    "date": "date",
    "time": "time",
    "uuid": "string",
    "uniqueidentifier": "string",
    "json": "text",
    "jsonb": "text",
    "xml": "text",
    "bytea": "binary",
    "blob": "binary",
    "varbinary": "binary",
    "binary": "binary",
    "image": "binary",
    "array": "text",
    "enum": "string",
}

# Regex to detect SQL types with precision/length like varchar(255), numeric(10,2)
SQL_TYPE_WITH_PRECISION = re.compile(
    r'^(' + '|'.join(re.escape(k) for k in SQL_TYPE_MAP.keys()) + r')\s*\([^)]*\)$',
    re.IGNORECASE
)


# ============================================================================
# EXTRACTION
# ============================================================================

def extract_mermaid_blocks(markdown: str) -> List[MermaidBlock]:
    """Extract all ```mermaid ... ``` blocks from markdown content."""
    blocks = []
    pattern = re.compile(r'```mermaid\s*\n([\s\S]*?)```', re.MULTILINE)

    for match in pattern.finditer(markdown):
        content = match.group(1)
        lines = content.split('\n')

        # Determine diagram type from first non-empty line
        diagram_type = "unknown"
        for line in lines:
            stripped = line.strip()
            if stripped:
                if stripped.startswith('erDiagram'):
                    diagram_type = "erDiagram"
                elif stripped.startswith(('graph ', 'graph\n', 'flowchart ')):
                    diagram_type = "flowchart"
                elif stripped.startswith('sequenceDiagram'):
                    diagram_type = "sequenceDiagram"
                elif stripped.startswith('classDiagram'):
                    diagram_type = "classDiagram"
                elif stripped.startswith('stateDiagram'):
                    diagram_type = "stateDiagram"
                elif stripped.startswith('gantt'):
                    diagram_type = "gantt"
                elif stripped.startswith('pie'):
                    diagram_type = "pie"
                break

        blocks.append(MermaidBlock(
            raw=content,
            start_pos=match.start(),
            end_pos=match.end(),
            diagram_type=diagram_type,
            lines=lines,
        ))

    return blocks


# ============================================================================
# ER DIAGRAM VALIDATION & AUTO-FIX
# ============================================================================

# ER relationship operators
ER_RELATIONSHIP_CHARS = re.compile(r'(\|\||\|o|o\||o\{|\}o|\{o|\|\{|\}\||--)')

# Valid ER relationship line pattern: ENTITY1 <rel> ENTITY2 : "label"
ER_RELATIONSHIP_PATTERN = re.compile(
    r'^\s*(\w+)\s+'
    r'((?:\|\||o\{|\}o|\|o|o\||\|\{|\}\||--)+)'
    r'\s+(\w+)\s*:\s*(.*?)\s*$'
)

# ER attribute line: exactly "type name" (2 tokens on indented line)
ER_ATTRIBUTE_PATTERN = re.compile(r'^\s+(\S+)\s+(\S+)\s*$')

# ER attribute with extra tokens (PK, FK, etc.)
ER_ATTRIBUTE_EXTRA = re.compile(r'^\s+(\S+)\s+(\S+)\s+(.+)$')

# Entity block header
ER_ENTITY_BLOCK = re.compile(r'^\s*(\w+)\s*\{')


def _normalize_sql_type(type_token: str) -> str:
    """Convert SQL-style types to Mermaid-safe simple types."""
    # Check for type with precision like varchar(255)
    base_type = re.sub(r'\([^)]*\)', '', type_token).strip().lower()
    return SQL_TYPE_MAP.get(base_type, type_token)


def _ensure_quoted_label(label: str) -> str:
    """Ensure an ER relationship label is in double quotes."""
    label = label.strip()
    if not label:
        return '"relates_to"'
    # Already quoted
    if label.startswith('"') and label.endswith('"'):
        return label
    # Single-quoted — convert
    if label.startswith("'") and label.endswith("'"):
        return f'"{label[1:-1]}"'
    # Unquoted
    return f'"{label}"'


def validate_er_diagram(block: MermaidBlock) -> ValidationResult:
    """Validate and auto-fix an erDiagram block."""
    result = ValidationResult(
        block_index=0,
        original=block.raw,
        fixed=block.raw,
    )

    fixed_lines = []
    in_entity_block = False
    entity_error_count = 0

    for i, line in enumerate(block.lines):
        stripped = line.strip()

        # Skip empty lines and diagram type declaration
        if not stripped or stripped == 'erDiagram':
            fixed_lines.append(line)
            continue

        # Skip comments
        if stripped.startswith('%%'):
            fixed_lines.append(line)
            continue

        # Entity block open
        entity_match = ER_ENTITY_BLOCK.match(line)
        if entity_match:
            in_entity_block = True
            fixed_lines.append(line)
            continue

        # Entity block close
        if stripped == '}':
            in_entity_block = False
            fixed_lines.append(line)
            continue

        # Inside entity block — validate attributes
        if in_entity_block:
            # Check for extra tokens (PK, FK annotations)
            extra_match = ER_ATTRIBUTE_EXTRA.match(line)
            if extra_match:
                type_token = extra_match.group(1)
                name_token = extra_match.group(2)
                extras = extra_match.group(3).strip()

                # Fix SQL types
                safe_type = _normalize_sql_type(type_token)

                result.errors.append(ValidationError(
                    line_number=i,
                    line_content=stripped,
                    error_type="er_attribute_extra_tokens",
                    message=f"ER attribute has extra tokens '{extras}' — "
                            f"Mermaid erDiagram only supports 'type name' format. "
                            f"Stripped to '{safe_type} {name_token}'."
                ))
                entity_error_count += 1

                # Fix: strip extra tokens, normalize type
                indent = line[:len(line) - len(line.lstrip())]
                fixed_lines.append(f"{indent}{safe_type} {name_token}")
                continue

            # Check for SQL type with precision
            attr_match = ER_ATTRIBUTE_PATTERN.match(line)
            if attr_match:
                type_token = attr_match.group(1)
                name_token = attr_match.group(2)
                safe_type = _normalize_sql_type(type_token)

                if safe_type != type_token:
                    result.warnings.append(
                        f"Line {i}: Normalized SQL type '{type_token}' → '{safe_type}'"
                    )
                    indent = line[:len(line) - len(line.lstrip())]
                    fixed_lines.append(f"{indent}{safe_type} {name_token}")
                    continue

            # Check for type with parentheses like varchar(255)
            paren_match = re.match(r'^\s+(\w+\([^)]*\))\s+(\w+)', line)
            if paren_match:
                sql_type = paren_match.group(1)
                name_token = paren_match.group(2)
                base = re.sub(r'\([^)]*\)', '', sql_type).strip().lower()
                safe_type = SQL_TYPE_MAP.get(base, "string")

                result.errors.append(ValidationError(
                    line_number=i,
                    line_content=stripped,
                    error_type="er_sql_type_with_precision",
                    message=f"SQL type '{sql_type}' not supported — converted to '{safe_type}'"
                ))
                entity_error_count += 1
                indent = line[:len(line) - len(line.lstrip())]
                fixed_lines.append(f"{indent}{safe_type} {name_token}")
                continue

            fixed_lines.append(line)
            continue

        # Relationship line
        rel_match = ER_RELATIONSHIP_PATTERN.match(line)
        if rel_match:
            entity1 = rel_match.group(1)
            relationship = rel_match.group(2)
            entity2 = rel_match.group(3)
            label = rel_match.group(4)

            # Validate relationship direction characters
            valid_ops = {'||', '|{', '}|', 'o{', '}o', '|o', 'o|', '--'}
            # Simple check: ensure the relationship string has valid operators
            ops_in_rel = re.findall(r'\|\||o\{|\}o|\|o|o\||\|\{|\}\||--', relationship)
            if len(ops_in_rel) < 2:
                result.errors.append(ValidationError(
                    line_number=i,
                    line_content=stripped,
                    error_type="er_bad_relationship",
                    message=f"Relationship '{relationship}' may be malformed. "
                            f"Expected format like '||--o{{' or '||--|{{'."
                ))

            # Fix unquoted label
            quoted_label = _ensure_quoted_label(label)
            if quoted_label != label.strip():
                result.errors.append(ValidationError(
                    line_number=i,
                    line_content=stripped,
                    error_type="er_unquoted_label",
                    message=f"Relationship label must be quoted. "
                            f"Fixed: '{label.strip()}' → {quoted_label}"
                ))
                indent = line[:len(line) - len(line.lstrip())]
                fixed_lines.append(f"{indent}{entity1} {relationship} {entity2} : {quoted_label}")
                continue

            fixed_lines.append(line)
            continue

        # Check for relationship-like lines that don't match the pattern
        if ER_RELATIONSHIP_CHARS.search(line) and ':' in line:
            # Looks like a relationship but didn't parse — try to fix
            parts = stripped.split(':')
            if len(parts) == 2:
                left = parts[0].strip()
                label = parts[1].strip()
                quoted_label = _ensure_quoted_label(label)

                result.errors.append(ValidationError(
                    line_number=i,
                    line_content=stripped,
                    error_type="er_malformed_relationship",
                    message=f"Relationship line may be malformed. Ensured quoted label."
                ))
                indent = line[:len(line) - len(line.lstrip())]
                fixed_lines.append(f"{indent}{left} : {quoted_label}")
                continue

        # Check for relationship-like lines missing the colon+label entirely
        if ER_RELATIONSHIP_CHARS.search(line) and ':' not in line:
            tokens = stripped.split()
            if len(tokens) >= 3:
                result.errors.append(ValidationError(
                    line_number=i,
                    line_content=stripped,
                    error_type="er_missing_label",
                    message="ER relationship missing ':' and label. "
                            "Added default label."
                ))
                indent = line[:len(line) - len(line.lstrip())]
                fixed_lines.append(f'{indent}{stripped} : "relates_to"')
                continue

        fixed_lines.append(line)

    result.fixed = '\n'.join(fixed_lines)
    result.is_valid = len(result.errors) == 0

    # If there are too many errors, the diagram is likely unsalvageable as ER
    if entity_error_count > 5:
        result.warnings.append(
            "erDiagram has many attribute errors. Consider using a flowchart instead."
        )

    return result


# ============================================================================
# FLOWCHART / GRAPH VALIDATION
# ============================================================================

# Node ID pattern — alphanumeric and underscores only
FLOWCHART_NODE_ID = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

# Arrow patterns
FLOWCHART_ARROWS = re.compile(r'-->|-.->|==>|---|-.-|===|-->')

# Subgraph
FLOWCHART_SUBGRAPH = re.compile(r'^\s*subgraph\s+')


def validate_flowchart(block: MermaidBlock) -> ValidationResult:
    """Validate and auto-fix a flowchart/graph block."""
    result = ValidationResult(
        block_index=0,
        original=block.raw,
        fixed=block.raw,
    )

    fixed_lines = []

    for i, line in enumerate(block.lines):
        stripped = line.strip()

        # Skip empty, comment, type declaration, style, classDef, end, click
        if (not stripped or
                stripped.startswith('%%') or
                stripped.startswith(('graph ', 'flowchart ')) or
                stripped.startswith('style ') or
                stripped.startswith('classDef ') or
                stripped.startswith('class ') or
                stripped.startswith('click ') or
                stripped.startswith('linkStyle ') or
                stripped == 'end'):
            fixed_lines.append(line)
            continue

        # Subgraph declarations
        if FLOWCHART_SUBGRAPH.match(line):
            fixed_lines.append(line)
            continue

        # Check for HTML tags (unsupported in strict mode)
        if re.search(r'<(?!br)(?!sub)(?!sup)[a-zA-Z]+', stripped):
            result.errors.append(ValidationError(
                line_number=i,
                line_content=stripped,
                error_type="flowchart_html_tag",
                message="HTML tags found in flowchart. Mermaid may not render these correctly."
            ))

        # Check arrow labels — should use |"label"| format
        pipe_label = re.search(r'\|([^|]*)\|', stripped)
        if pipe_label:
            label_content = pipe_label.group(1)
            # Warn if label contains special chars without quotes
            if re.search(r'[{}()<>]', label_content) and not label_content.startswith('"'):
                result.warnings.append(
                    f"Line {i}: Arrow label '{label_content}' contains special characters. "
                    f"Consider quoting: |\"{label_content}\"|"
                )

        fixed_lines.append(line)

    result.fixed = '\n'.join(fixed_lines)
    result.is_valid = len(result.errors) == 0
    return result


# ============================================================================
# SEQUENCE DIAGRAM VALIDATION
# ============================================================================

SEQUENCE_MESSAGE = re.compile(r'^\s*\w[\w\s]*\s*->>[\+\-]?\s*\w[\w\s]*\s*:')
SEQUENCE_PARTICIPANT = re.compile(r'^\s*participant\s+')
SEQUENCE_ACTOR = re.compile(r'^\s*actor\s+')
SEQUENCE_NOTE = re.compile(r'^\s*Note\s+', re.IGNORECASE)
SEQUENCE_LOOP = re.compile(r'^\s*(loop|alt|else|opt|par|critical|break|rect)\s*', re.IGNORECASE)
SEQUENCE_ACTIVATE = re.compile(r'^\s*(activate|deactivate)\s+', re.IGNORECASE)


def validate_sequence_diagram(block: MermaidBlock) -> ValidationResult:
    """Validate a sequence diagram block."""
    result = ValidationResult(
        block_index=0,
        original=block.raw,
        fixed=block.raw,
    )

    fixed_lines = []

    for i, line in enumerate(block.lines):
        stripped = line.strip()

        if (not stripped or
                stripped == 'sequenceDiagram' or
                stripped.startswith('%%') or
                stripped == 'end'):
            fixed_lines.append(line)
            continue

        # Check participant declarations
        if SEQUENCE_PARTICIPANT.match(stripped) or SEQUENCE_ACTOR.match(stripped):
            fixed_lines.append(line)
            continue

        # Check messages
        if '->' in stripped or '->>' in stripped:
            if ':' not in stripped:
                result.errors.append(ValidationError(
                    line_number=i,
                    line_content=stripped,
                    error_type="sequence_missing_message",
                    message="Sequence message missing ':' and message text."
                ))
                # Fix: add empty message
                fixed_lines.append(f"{line}: ")
                continue

        # Notes, loops, activations
        if (SEQUENCE_NOTE.match(stripped) or
                SEQUENCE_LOOP.match(stripped) or
                SEQUENCE_ACTIVATE.match(stripped)):
            fixed_lines.append(line)
            continue

        fixed_lines.append(line)

    result.fixed = '\n'.join(fixed_lines)
    result.is_valid = len(result.errors) == 0
    return result


# ============================================================================
# ER DIAGRAM → FLOWCHART CONVERSION
# ============================================================================

# Default color palette for entity domains
ENTITY_COLORS = [
    ("#1e3a5f", "#4a90d9", "#fff"),  # Blue
    ("#2d5016", "#6ba33e", "#fff"),  # Green
    ("#5c3d1e", "#d4a94a", "#fff"),  # Brown/Gold
    ("#4a1942", "#b266b2", "#fff"),  # Purple
    ("#1a4a4a", "#4ab2b2", "#fff"),  # Teal
    ("#5c1a1a", "#b24a4a", "#fff"),  # Red
]


@dataclass
class EREntity:
    """Parsed ER diagram entity with attributes."""
    name: str
    attributes: List[Tuple[str, str]] = field(default_factory=list)  # (type, name) pairs


@dataclass
class ERRelationship:
    """Parsed ER diagram relationship."""
    entity1: str
    operator: str
    entity2: str
    label: str


def _parse_er_entities_and_relationships(
    lines: List[str],
) -> Tuple[List[EREntity], List[ERRelationship]]:
    """Parse entities and relationships from erDiagram lines."""
    entities = []
    relationships = []
    current_entity: Optional[EREntity] = None

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped == 'erDiagram' or stripped.startswith('%%'):
            continue

        # Entity block open
        entity_match = ER_ENTITY_BLOCK.match(line)
        if entity_match:
            current_entity = EREntity(name=entity_match.group(1))
            continue

        # Entity block close
        if stripped == '}' and current_entity:
            entities.append(current_entity)
            current_entity = None
            continue

        # Attribute inside entity block
        if current_entity:
            # Handle various attribute formats
            extra = ER_ATTRIBUTE_EXTRA.match(line)
            if extra:
                safe_type = _normalize_sql_type(extra.group(1))
                current_entity.attributes.append((safe_type, extra.group(2)))
                continue
            attr = ER_ATTRIBUTE_PATTERN.match(line)
            if attr:
                safe_type = _normalize_sql_type(attr.group(1))
                current_entity.attributes.append((safe_type, attr.group(2)))
                continue
            # Fallback: try splitting on whitespace
            tokens = stripped.split()
            if len(tokens) >= 2:
                safe_type = _normalize_sql_type(tokens[0])
                current_entity.attributes.append((safe_type, tokens[1]))
            continue

        # Relationship line
        rel_match = ER_RELATIONSHIP_PATTERN.match(line)
        if rel_match:
            label = rel_match.group(4).strip().strip('"').strip("'")
            if not label:
                label = "relates_to"
            relationships.append(ERRelationship(
                entity1=rel_match.group(1),
                operator=rel_match.group(2),
                entity2=rel_match.group(3),
                label=label,
            ))
            continue

        # Relationship-like line with : separator
        if ER_RELATIONSHIP_CHARS.search(line) and ':' in line:
            parts = stripped.split(':')
            if len(parts) == 2:
                left_tokens = parts[0].strip().split()
                label = parts[1].strip().strip('"').strip("'") or "relates_to"
                if len(left_tokens) >= 3:
                    relationships.append(ERRelationship(
                        entity1=left_tokens[0],
                        operator=left_tokens[1],
                        entity2=left_tokens[2],
                        label=label,
                    ))

    return entities, relationships


def convert_er_to_flowchart(block: MermaidBlock) -> str:
    """Convert an erDiagram to a flowchart representation."""
    entities, relationships = _parse_er_entities_and_relationships(block.lines)

    lines = ["graph TB"]

    # Create entity nodes
    if entities:
        lines.append('    subgraph DataModel["Data Model"]')
        for i, entity in enumerate(entities):
            # Build attribute string
            attrs = []
            for attr_type, attr_name in entity.attributes:
                attrs.append(f"{attr_type} {attr_name}")
            attr_str = "\\n".join(attrs) if attrs else "..."
            display = f"{entity.name}\\n{'─' * 12}\\n{attr_str}"
            node_id = entity.name.replace(' ', '_')
            lines.append(f'        {node_id}["{display}"]')
        lines.append('    end')

    # Create relationship arrows
    for rel in relationships:
        e1 = rel.entity1.replace(' ', '_')
        e2 = rel.entity2.replace(' ', '_')
        lines.append(f'    {e1} -->|"{rel.label}"| {e2}')

    # Add styles
    for i, entity in enumerate(entities):
        color_idx = i % len(ENTITY_COLORS)
        fill, stroke, text_color = ENTITY_COLORS[color_idx]
        node_id = entity.name.replace(' ', '_')
        lines.append(f'    style {node_id} fill:{fill},color:{text_color},stroke:{stroke}')

    return '\n'.join(lines)


# ============================================================================
# GENERAL VALIDATION RULES (all diagram types)
# ============================================================================

def _check_general_issues(block: MermaidBlock) -> List[ValidationError]:
    """Check for issues common to all diagram types."""
    errors = []

    # Check overall line count
    non_empty = [l for l in block.lines if l.strip()]
    if len(non_empty) > 80:
        errors.append(ValidationError(
            line_number=0,
            line_content="(entire diagram)",
            error_type="diagram_too_large",
            message=f"Diagram has {len(non_empty)} non-empty lines. "
                    f"Consider splitting into multiple smaller diagrams."
        ))

    for i, line in enumerate(block.lines):
        stripped = line.strip()

        # Check for Unicode that Mermaid can't render
        if re.search(r'[^\x00-\x7F]', stripped):
            # Allow common Unicode like arrows, bullets, em-dash
            non_ascii = re.findall(r'[^\x00-\x7F]+', stripped)
            for char_seq in non_ascii:
                if not all(c in '→←↑↓•–—·' for c in char_seq):
                    errors.append(ValidationError(
                        line_number=i,
                        line_content=stripped[:60],
                        error_type="unicode_characters",
                        message=f"Non-ASCII characters '{char_seq}' may cause rendering issues."
                    ))
                    break

    return errors


# ============================================================================
# MAIN VALIDATION & FIX PIPELINE
# ============================================================================

def validate_mermaid_block(block: MermaidBlock, auto_convert_er: bool = True) -> ValidationResult:
    """
    Validate a single Mermaid block and auto-fix issues.

    Args:
        block: The extracted Mermaid block
        auto_convert_er: If True, convert badly broken erDiagrams to flowcharts

    Returns:
        ValidationResult with original, fixed content, and error details
    """
    # General checks
    general_errors = _check_general_issues(block)

    # Type-specific validation
    if block.diagram_type == "erDiagram":
        result = validate_er_diagram(block)
        result.errors = general_errors + result.errors

        # If too many errors and auto-convert is enabled, convert to flowchart
        er_errors = [e for e in result.errors if e.error_type.startswith('er_')]
        if auto_convert_er and len(er_errors) > 3:
            flowchart_content = convert_er_to_flowchart(block)
            result.fixed = flowchart_content
            result.was_converted = True
            result.warnings.append(
                f"erDiagram had {len(er_errors)} syntax errors. "
                f"Automatically converted to flowchart for reliable rendering."
            )

    elif block.diagram_type == "flowchart":
        result = validate_flowchart(block)
        result.errors = general_errors + result.errors

    elif block.diagram_type == "sequenceDiagram":
        result = validate_sequence_diagram(block)
        result.errors = general_errors + result.errors

    else:
        # For other types, just do general checks
        result = ValidationResult(
            block_index=0,
            original=block.raw,
            fixed=block.raw,
            errors=general_errors,
        )

    result.is_valid = len(result.errors) == 0
    return result


def validate_and_fix_mermaid(
    markdown: str,
    auto_convert_er: bool = True
) -> Tuple[str, List[ValidationResult]]:
    """
    Validate and fix all Mermaid blocks in markdown content.

    Args:
        markdown: Full markdown content containing ```mermaid blocks
        auto_convert_er: If True, convert broken erDiagrams to flowcharts

    Returns:
        Tuple of (fixed_markdown, list_of_validation_results)
    """
    blocks = extract_mermaid_blocks(markdown)

    if not blocks:
        return markdown, []

    results = []
    fixed_markdown = markdown

    # Process blocks in reverse order so position indices remain valid
    for i, block in enumerate(reversed(blocks)):
        result = validate_mermaid_block(block, auto_convert_er=auto_convert_er)
        result.block_index = len(blocks) - 1 - i
        results.insert(0, result)

        # Replace block content in markdown if it was fixed
        if result.fixed != result.original:
            original_block = f"```mermaid\n{block.raw}```"
            fixed_block = f"```mermaid\n{result.fixed}\n```"
            # Use position-based replacement to avoid duplicate issues
            fixed_markdown = (
                fixed_markdown[:block.start_pos]
                + fixed_block
                + fixed_markdown[block.end_pos:]
            )

    return fixed_markdown, results


def format_validation_summary(results: List[ValidationResult]) -> str:
    """Format validation results into a human-readable summary."""
    if not results:
        return "No Mermaid diagrams found in content."

    total_errors = sum(len(r.errors) for r in results)
    total_warnings = sum(len(r.warnings) for r in results)
    conversions = sum(1 for r in results if r.was_converted)

    if total_errors == 0 and total_warnings == 0:
        return f"All {len(results)} Mermaid diagram(s) passed validation."

    lines = [f"Mermaid validation: {len(results)} diagram(s) checked"]

    if total_errors > 0:
        lines.append(f"  - {total_errors} error(s) auto-fixed")
    if total_warnings > 0:
        lines.append(f"  - {total_warnings} warning(s)")
    if conversions > 0:
        lines.append(f"  - {conversions} erDiagram(s) converted to flowchart")

    for r in results:
        if r.errors or r.warnings:
            lines.append(f"\n  Diagram {r.block_index + 1}:")
            for err in r.errors:
                lines.append(f"    [FIXED] {err.error_type}: {err.message}")
            for warn in r.warnings:
                lines.append(f"    [WARN] {warn}")

    return '\n'.join(lines)
