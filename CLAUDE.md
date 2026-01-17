# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PDFreducer is a Python tool for reducing PDF file sizes through image optimization and compression. It also supports text extraction from PDFs. Provides both a CLI and a web interface.

## Common Commands

```bash
# Activate virtual environment
source .venv/bin/activate

# Install in development mode
pip install -e .
pip install -e ".[dev]"  # with dev dependencies

# Run CLI - PDF Reduction
pdfreducer file.pdf                    # Basic usage
pdfreducer file.pdf -o output.pdf      # Specify output
pdfreducer *.pdf --output-dir ./out    # Batch processing

# Run CLI - Text Extraction
pdfreducer --extract-text ./folder     # Extract text, move PDFs to _originals/
pdfreducer --extract-text ./folder --keep  # Extract text, keep PDFs in place

# Run Web Interface
pdfreducer --serve                     # Start web interface
pdfreducer --serve --port 8080         # Custom port
pdfreducer --serve --host 0.0.0.0      # Bind to all interfaces (Docker)

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
│   ├── image_optimizer.py  # ImageOptimizer for Pillow-based image processing
│   └── text_extractor.py   # Text extraction using pdfplumber
└── web/
    ├── app.py          # FastAPI application with WebSocket support
    ├── queue.py        # Async ProcessingQueue and Job management (supports reduce/extract modes)
    └── static/         # Frontend (index.html, styles.css, app.js)
```

**Core Flow:**
1. `PDFReducer.reduce()` opens PDF with pikepdf
2. Images are extracted, optimized via Pillow (resize, quality, grayscale), and replaced only if smaller
3. PDF is saved with compression options (linearize, object streams, optional aggressive mode)

**Web Flow:**
1. User selects mode: "Reduce Size" or "Extract Text"
2. Files uploaded via `/api/upload` are added to `ProcessingQueue` in pending state
3. User adjusts settings (for reduce mode) and clicks "Process" button
4. `POST /api/process` triggers processing of all pending jobs
5. Background worker processes jobs asynchronously (reduce or extract based on mode)
6. WebSocket broadcasts real-time progress updates to connected clients
7. Completed files (.pdf or .txt) can be downloaded individually or as ZIP

## Key Dependencies

- **pikepdf**: PDF manipulation (opening, saving, image extraction, compression)
- **Pillow**: Image optimization (resize, format conversion, quality adjustment)
- **pdfplumber**: Text extraction from PDFs
- **FastAPI/uvicorn**: Web interface and API
- **websockets**: Real-time progress updates

## Web API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/upload` | POST | Upload PDF file (returns job in pending state) |
| `/api/process` | POST | Start processing all pending jobs |
| `/api/jobs` | GET | List all jobs |
| `/api/jobs/{id}` | GET | Get job status |
| `/api/jobs/{id}` | DELETE | Remove a job |
| `/api/jobs/clear-completed` | POST | Clear completed/failed jobs |
| `/api/download/{id}` | GET | Download processed PDF |
| `/api/download-all` | GET | Download all completed PDFs as ZIP |
| `/ws` | WebSocket | Real-time job updates |

## CLI Options Reference

### Reduction Options
| Option | Default | Description |
|--------|---------|-------------|
| `--dpi` | 150 | Target image DPI (10-600) |
| `--quality` | 80 | JPEG quality (1-100) |
| `--grayscale` | false | Convert images to grayscale |
| `--remove-images` | false | Remove all images |
| `--aggressive` | false | Enable aggressive compression |
| `--strip-metadata` | false | Remove document metadata |

### Text Extraction Options
| Option | Default | Description |
|--------|---------|-------------|
| `--extract-text` | - | Folder containing PDFs to extract text from |
| `--keep` | false | Keep original PDFs in place (don't move to _originals/) |

### Server Options
| Option | Default | Description |
|--------|---------|-------------|
| `--serve` | false | Start web interface |
| `--host` | 127.0.0.1 | Host to bind to |
| `--port` | 8000 | Port to listen on |

## Docker Deployment

The project includes Docker support for NAS deployment. See `NAS-Docker-Deployment-Guide.md` for details.

```bash
# Build and run
docker build -t pdfreducer .
docker run -d -p 5052:8000 --name pdfreducer pdfreducer
```
