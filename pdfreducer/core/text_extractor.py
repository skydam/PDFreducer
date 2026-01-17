"""Text extraction from PDF files."""

from pathlib import Path
from typing import Optional

import pdfplumber


def table_to_markdown(table: list[list]) -> str:
    """Convert a table to markdown format."""
    if not table or not table[0]:
        return ""

    # Clean cells: replace None with empty string, strip whitespace
    cleaned = []
    for row in table:
        cleaned_row = [(cell or "").strip().replace("\n", " ") for cell in row]
        cleaned.append(cleaned_row)

    # Calculate column widths
    col_count = max(len(row) for row in cleaned)
    col_widths = [3] * col_count  # minimum width of 3

    for row in cleaned:
        for i, cell in enumerate(row):
            if i < col_count:
                col_widths[i] = max(col_widths[i], len(cell))

    # Pad rows to have same number of columns
    for row in cleaned:
        while len(row) < col_count:
            row.append("")

    # Build markdown table
    lines = []

    # Header row
    header = "| " + " | ".join(cell.ljust(col_widths[i]) for i, cell in enumerate(cleaned[0])) + " |"
    lines.append(header)

    # Separator
    separator = "|" + "|".join("-" * (w + 2) for w in col_widths) + "|"
    lines.append(separator)

    # Data rows
    for row in cleaned[1:]:
        data_row = "| " + " | ".join(cell.ljust(col_widths[i]) for i, cell in enumerate(row)) + " |"
        lines.append(data_row)

    return "\n".join(lines)


def table_to_csv(table: list[list]) -> str:
    """Convert a table to CSV format."""
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output)

    for row in table:
        cleaned_row = [(cell or "").strip().replace("\n", " ") for cell in row]
        writer.writerow(cleaned_row)

    return output.getvalue()


def extract_text(pdf_path: Path, extract_csv: bool = False) -> tuple[str, Optional[list[tuple[int, str]]]]:
    """Extract text content from a PDF file with tables as markdown.

    Args:
        pdf_path: Path to the PDF file
        extract_csv: If True, also return tables as CSV data

    Returns:
        Tuple of (text content, optional list of (page_num, csv_data) tuples)
    """
    text_parts = []
    csv_tables = [] if extract_csv else None

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            page_content = []

            # Extract tables from this page
            tables = page.extract_tables()
            table_bboxes = []

            if tables:
                # Get table bounding boxes to exclude from text extraction
                for table_settings in page.find_tables():
                    table_bboxes.append(table_settings.bbox)

                # Add tables as markdown
                for i, table in enumerate(tables):
                    if table and len(table) > 0:
                        md_table = table_to_markdown(table)
                        if md_table:
                            page_content.append(md_table)

                        # Also save as CSV if requested
                        if extract_csv:
                            csv_data = table_to_csv(table)
                            if csv_data.strip():
                                csv_tables.append((page_num, i + 1, csv_data))

            # Extract text outside of tables
            if table_bboxes:
                # Filter out table regions
                filtered_page = page
                for bbox in table_bboxes:
                    # Create page without table area
                    pass  # pdfplumber doesn't easily support this, so we'll use full text

            # Get regular text
            text = page.extract_text()
            if text:
                # If we have tables, the text might include table content
                # For now, include both - tables as markdown and full text
                # This ensures we don't lose any content
                if tables:
                    page_content.insert(0, text)
                else:
                    page_content.append(text)

            if page_content:
                text_parts.append("\n\n".join(page_content))

    result_text = "\n\n---\n\n".join(text_parts)  # Page separator

    if extract_csv:
        return result_text, csv_tables
    return result_text, None
