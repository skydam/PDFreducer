# PDFreducer

A Python tool for reducing PDF file sizes through image optimization and compression. Provides both a command-line interface and a web interface.

## Features

- **Image Optimization**: Reduce image DPI and JPEG quality
- **Grayscale Conversion**: Convert images to black & white
- **Aggressive Compression**: Maximum compression for smaller files
- **Metadata Stripping**: Remove document metadata
- **Batch Processing**: Process multiple PDFs at once
- **Web Interface**: User-friendly browser-based UI with real-time progress
- **Download All**: Download multiple processed PDFs as a ZIP archive

## Installation

```bash
# Clone the repository
git clone https://github.com/skydam/PDFreducer.git
cd PDFreducer

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package
pip install -e .
```

## Usage

### Command Line

```bash
# Basic usage - creates file_reduced.pdf
pdfreducer document.pdf

# Specify output file
pdfreducer document.pdf -o smaller.pdf

# Batch processing
pdfreducer *.pdf --output-dir ./reduced

# With options
pdfreducer document.pdf --dpi 100 --quality 60 --grayscale --aggressive
```

### Web Interface

```bash
# Start the web server
pdfreducer --serve

# Custom port
pdfreducer --serve --port 8080
```

Then open http://localhost:8000 in your browser.

**Web Workflow:**
1. Drop or select PDF files
2. Adjust compression settings
3. Click "Process" to start
4. Download individual files or "Download All" as ZIP

## CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `--dpi` | 150 | Target image DPI (10-600) |
| `--quality` | 80 | JPEG quality (1-100) |
| `--grayscale` | - | Convert images to grayscale |
| `--remove-images` | - | Remove all images from PDF |
| `--aggressive` | - | Enable aggressive compression |
| `--strip-metadata` | - | Remove document metadata |
| `-o, --output` | - | Output file path |
| `--output-dir` | - | Output directory for batch processing |
| `--serve` | - | Start web interface |
| `--port` | 8000 | Web server port |

## Requirements

- Python 3.8+
- pikepdf
- Pillow
- FastAPI (for web interface)
- uvicorn (for web interface)

## License

MIT
