# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PDFreducer is a Python tool for reducing PDF file sizes through image optimization and compression. It provides both a CLI and a web interface.

## Common Commands

```bash
# Activate virtual environment
source .venv/bin/activate

# Install in development mode
pip install -e .
pip install -e ".[dev]"  # with dev dependencies

# Run CLI
pdfreducer file.pdf                    # Basic usage
pdfreducer file.pdf -o output.pdf      # Specify output
pdfreducer *.pdf --output-dir ./out    # Batch processing
pdfreducer --serve                     # Start web interface
pdfreducer --serve --port 8080         # Custom port

# Run tests
pytest
pytest tests/test_specific.py          # Single test file
pytest -v                              # Verbose output
```

## Architecture

The project has two main interfaces (CLI and web) that share a common core:

```
pdfreducer/
├── cli.py              # CLI entry point (argparse-based)
├── core/
│   ├── options.py      # ReductionOptions dataclass (dpi, quality, grayscale, etc.)
│   ├── reducer.py      # PDFReducer class - main reduction logic using pikepdf
│   └── image_optimizer.py  # ImageOptimizer for Pillow-based image processing
└── web/
    ├── app.py          # FastAPI application with WebSocket support
    ├── queue.py        # Async ProcessingQueue and Job management
    └── static/         # Frontend (index.html, styles.css, app.js)
```

**Core Flow:**
1. `PDFReducer.reduce()` opens PDF with pikepdf
2. Images are extracted, optimized via Pillow (resize, quality, grayscale), and replaced only if smaller
3. PDF is saved with compression options (linearize, object streams, optional aggressive mode)

**Web Flow:**
1. Files uploaded via `/api/upload` are added to `ProcessingQueue`
2. Background worker processes jobs asynchronously
3. WebSocket broadcasts real-time progress updates to connected clients

## Key Dependencies

- **pikepdf**: PDF manipulation (opening, saving, image extraction, compression)
- **Pillow**: Image optimization (resize, format conversion, quality adjustment)
- **FastAPI/uvicorn**: Web interface and API
- **websockets**: Real-time progress updates

## CLI Options Reference

| Option | Default | Description |
|--------|---------|-------------|
| `--dpi` | 150 | Target image DPI (10-600) |
| `--quality` | 80 | JPEG quality (1-100) |
| `--grayscale` | false | Convert images to grayscale |
| `--remove-images` | false | Remove all images |
| `--aggressive` | false | Enable aggressive compression |
| `--strip-metadata` | false | Remove document metadata |
