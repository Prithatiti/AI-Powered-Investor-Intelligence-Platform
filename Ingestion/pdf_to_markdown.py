"""
PDF to Markdown Conversion Module

This module provides utilities for converting PDF annual reports into Markdown format.
It uses the pymupdf4llm library, which is optimized for LLM-ready Markdown output,
preserving structure such as headings, tables, and text blocks.

Directory structure:
    Data/
        annual_reports_pdfs/     <- Source PDF files
        reports_markdown/        <- Converted Markdown output (auto-created)

Usage:
    # Convert a single PDF file
    from Ingestion.pdf_to_markdown import convert_single_pdf
    convert_single_pdf("Data/annual_reports_pdfs/2024_Apple.pdf")

    # Convert all PDFs in the annual_reports_pdfs directory
    from Ingestion.pdf_to_markdown import convert_all_pdfs
    convert_all_pdfs()
"""

from pathlib import Path

import pymupdf4llm

# ---------------------------------------------------------------------------
# Configuration: centralised directory paths
# ---------------------------------------------------------------------------
# Resolve paths relative to the project root so the script works regardless of
# the current working directory.  The project root is assumed to be one level
# above the Ingestion/ package folder.

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Directory that contains the raw PDF annual reports
PDF_SOURCE_DIR: Path = PROJECT_ROOT / "Data" / "annual_reports_pdfs"

# Directory where converted Markdown files will be written
MARKDOWN_OUTPUT_DIR: Path = PROJECT_ROOT / "Data" / "reports_markdown"


# ---------------------------------------------------------------------------
# Single-file conversion
# ---------------------------------------------------------------------------
def convert_single_pdf(
    pdf_path: str | Path,
    output_dir: str | Path | None = None,
) -> Path:
    """Convert a single PDF file to Markdown and write it to disk.

    Parameters
    ----------
    pdf_path : str | Path
        Absolute or relative path to the PDF file to convert.
    output_dir : str | Path | None, optional
        Directory where the resulting ``.md`` file will be saved.
        When *None* the default ``MARKDOWN_OUTPUT_DIR`` is used.
        The directory is created automatically if it does not exist.

    Returns
    -------
    Path
        The absolute path of the newly created Markdown file.

    Raises
    ------
    FileNotFoundError
        If ``pdf_path`` does not point to an existing file.
    """

    # Normalise to Path objects for reliable attribute access
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir) if output_dir else MARKDOWN_OUTPUT_DIR

    # Guard: the source PDF must exist
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    # Ensure the output directory exists (creates intermediate dirs too)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Derive the Markdown filename from the PDF stem.
    # Example: "2024_Apple.pdf" -> "2024_Apple.md"
    md_filename = pdf_path.stem + ".md"
    md_path = output_dir / md_filename

    # ------------------------------------------------------------------
    # Core conversion using pymupdf4llm
    # ------------------------------------------------------------------
    # `pymupdf4llm.to_markdown()` reads the PDF and returns a Markdown
    # string.  Key parameters:
    #   - page_chunks=False  : return one continuous string instead of
    #                          per-page dicts (simpler for flat docs).
    #   - write_images=False : skip embedding images inline to keep the
    #                          output lightweight and text-focused.
    # ------------------------------------------------------------------
    md_text = pymupdf4llm.to_markdown(
        str(pdf_path),
        page_chunks=False,
        write_images=False,
    )

    # Write the Markdown content to the output file
    md_path.write_text(md_text, encoding="utf-8")

    print(f"[OK] {pdf_path.name} -> {md_path}")
    return md_path


# ---------------------------------------------------------------------------
# Batch conversion
# ---------------------------------------------------------------------------
def convert_all_pdfs(
    source_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> list[Path]:
    """Batch-convert every PDF inside *source_dir* to Markdown.

    The function iterates over all ``*.pdf`` files (case-insensitive) in
    the source directory, converts each one, and writes the results to
    *output_dir*.  Files that have already been converted are skipped if
    a ``.md`` file with the same stem already exists in the output folder.

    Parameters
    ----------
    source_dir : str | Path | None, optional
        Directory that contains PDF files.  Defaults to ``PDF_SOURCE_DIR``
        (``Data/annual_reports_pdfs``).
    output_dir : str | Path | None, optional
        Directory for the resulting Markdown files.  Defaults to
        ``MARKDOWN_OUTPUT_DIR`` (``Data/reports_markdown``).

    Returns
    -------
    list[Path]
        A list of absolute paths to all Markdown files that were created
        (or already existed) after the run.
    """

    source_dir = Path(source_dir) if source_dir else PDF_SOURCE_DIR
    output_dir = Path(output_dir) if output_dir else MARKDOWN_OUTPUT_DIR

    # Validate that the source directory exists
    if not source_dir.is_dir():
        raise NotADirectoryError(f"Source directory not found: {source_dir}")

    # Collect every PDF in the directory (sorted for deterministic order)
    pdf_files = sorted(source_dir.glob(pattern="*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in {source_dir}")
        return []

    # Ensure the output directory exists before we start
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Found {len(pdf_files)} PDF(s) in {source_dir}\n")

    converted_paths: list[Path] = []

    for pdf_file in pdf_files:
        md_filename = pdf_file.stem + ".md"
        md_path = output_dir / md_filename

        # Skip conversion if the Markdown file already exists
        if md_path.exists():
            print(f"[SKIP] {pdf_file.name} (already converted)")
            converted_paths.append(md_path)
            continue

        try:
            path = convert_single_pdf(
                  pdf_path=pdf_file,
                  output_dir=output_dir
            )
            converted_paths.append(path)
            
        except Exception as exc:  # noqa: BLE001
            # Log the error but continue with the remaining files so one
            # bad PDF does not halt the entire batch.
            print(f"[ERROR] {pdf_file.name}: {exc}")

    print(f"\nDone. {len(converted_paths)}/{len(pdf_files)} file(s) "
          f"converted -> {output_dir}")

    return converted_paths


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # When run directly (``python -m Ingestion.pdf_to_markdown`` or
    # ``python Ingestion/pdf_to_markdown.py``) perform a full batch
    # conversion of all PDFs in the source directory.
    convert_all_pdfs()
