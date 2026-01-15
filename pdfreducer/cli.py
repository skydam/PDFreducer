"""Command-line interface for PDF Reducer."""

import argparse
import sys
import webbrowser
from pathlib import Path
from typing import List

from pdfreducer.core.options import ReductionOptions
from pdfreducer.core.reducer import PDFReducer


def format_size(size_bytes: int) -> str:
    """Format bytes as human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def reduce_file(
    input_path: Path,
    output_path: Path,
    options: ReductionOptions,
    verbose: bool = True,
) -> bool:
    """Reduce a single PDF file."""
    if verbose:
        print(f"\nProcessing: {input_path.name}")

    original_size = input_path.stat().st_size

    def progress_callback(pct: float, msg: str):
        if verbose:
            bar_length = 30
            filled = int(bar_length * pct / 100)
            bar = "█" * filled + "░" * (bar_length - filled)
            print(f"\r  [{bar}] {pct:5.1f}% - {msg:<30}", end="", flush=True)

    try:
        reducer = PDFReducer(options)
        reducer.reduce(input_path, output_path, progress_callback)

        if verbose:
            print()  # New line after progress bar

        new_size = output_path.stat().st_size
        reduction = ((original_size - new_size) / original_size) * 100

        if verbose:
            print(f"  {format_size(original_size)} → {format_size(new_size)} ({reduction:+.1f}%)")
            print(f"  Saved to: {output_path}")

        return True

    except Exception as e:
        if verbose:
            print(f"\n  Error: {e}")
        return False


def get_output_path(input_path: Path, output_dir: Path | None, output_file: Path | None) -> Path:
    """Determine the output path for a file."""
    if output_file:
        return output_file

    if output_dir:
        return output_dir / f"{input_path.stem}_reduced.pdf"

    return input_path.parent / f"{input_path.stem}_reduced.pdf"


def main(args: List[str] | None = None):
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog="pdfreducer",
        description="Reduce PDF file sizes through image optimization and compression.",
    )

    # Input files
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        help="PDF files to reduce",
    )

    # Output options
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output file path (for single file processing)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory for batch processing",
    )

    # Image options
    parser.add_argument(
        "--dpi",
        type=int,
        default=150,
        help="Target image DPI (default: 150)",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=80,
        help="JPEG quality 1-100 (default: 80)",
    )
    parser.add_argument(
        "--grayscale",
        action="store_true",
        help="Convert images to grayscale",
    )
    parser.add_argument(
        "--remove-images",
        action="store_true",
        help="Remove all images from the PDF",
    )

    # Compression options
    parser.add_argument(
        "--aggressive",
        action="store_true",
        help="Apply aggressive compression",
    )
    parser.add_argument(
        "--strip-metadata",
        action="store_true",
        help="Remove document metadata",
    )

    # Web server
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Start the web interface",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Web server port (default: 8000)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't open browser automatically",
    )

    # Other options
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress output",
    )

    parsed_args = parser.parse_args(args)

    # Start web server if requested
    if parsed_args.serve:
        from pdfreducer.web.app import run_server

        url = f"http://localhost:{parsed_args.port}"
        print(f"Starting PDF Reducer web interface at {url}")

        if not parsed_args.no_browser:
            webbrowser.open(url)

        run_server(host=parsed_args.host, port=parsed_args.port)
        return 0

    # Validate inputs
    if not parsed_args.files:
        parser.print_help()
        print("\nError: No input files specified. Use --serve to start the web interface.")
        return 1

    # Validate output options
    if parsed_args.output and len(parsed_args.files) > 1:
        print("Error: --output can only be used with a single input file")
        return 1

    # Create output directory if specified
    if parsed_args.output_dir:
        parsed_args.output_dir.mkdir(parents=True, exist_ok=True)

    # Create reduction options
    options = ReductionOptions(
        dpi=parsed_args.dpi,
        quality=parsed_args.quality,
        grayscale=parsed_args.grayscale,
        remove_images=parsed_args.remove_images,
        aggressive=parsed_args.aggressive,
        strip_metadata=parsed_args.strip_metadata,
    )

    # Process files
    verbose = not parsed_args.quiet
    success_count = 0
    total_original = 0
    total_reduced = 0

    for input_path in parsed_args.files:
        if not input_path.exists():
            if verbose:
                print(f"Error: File not found: {input_path}")
            continue

        if not input_path.suffix.lower() == ".pdf":
            if verbose:
                print(f"Skipping non-PDF file: {input_path}")
            continue

        output_path = get_output_path(input_path, parsed_args.output_dir, parsed_args.output)

        original_size = input_path.stat().st_size
        if reduce_file(input_path, output_path, options, verbose):
            success_count += 1
            total_original += original_size
            total_reduced += output_path.stat().st_size

    # Print summary for batch processing
    if len(parsed_args.files) > 1 and verbose:
        print(f"\n{'='*50}")
        print(f"Processed {success_count}/{len(parsed_args.files)} files")
        if total_original > 0:
            total_reduction = ((total_original - total_reduced) / total_original) * 100
            print(f"Total: {format_size(total_original)} → {format_size(total_reduced)} ({total_reduction:+.1f}%)")

    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
