"""PDF Reducer - A tool to reduce PDF file sizes."""

__version__ = "0.1.0"

from pdfreducer.core.options import ReductionOptions
from pdfreducer.core.reducer import PDFReducer

__all__ = ["PDFReducer", "ReductionOptions"]
