"""Main PDF reduction logic."""

import io
from pathlib import Path
from typing import Callable, Optional, Union

import pikepdf
from PIL import Image

from pdfreducer.core.image_optimizer import ImageOptimizer
from pdfreducer.core.options import ReductionOptions


class PDFReducer:
    """Reduces PDF file sizes through various optimization techniques."""

    def __init__(self, options: Optional[ReductionOptions] = None):
        """
        Initialize the PDF reducer.

        Args:
            options: Reduction options. Uses defaults if not provided.
        """
        self.options = options or ReductionOptions()
        self.image_optimizer = ImageOptimizer(self.options)

    def reduce(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> Path:
        """
        Reduce a PDF file.

        Args:
            input_path: Path to the input PDF file
            output_path: Path for the output file. If None, appends '_reduced' to filename.
            progress_callback: Optional callback for progress updates (0-100, message)

        Returns:
            Path to the reduced PDF file
        """
        input_path = Path(input_path)
        if output_path is None:
            output_path = input_path.parent / f"{input_path.stem}_reduced.pdf"
        else:
            output_path = Path(output_path)

        def report(pct: float, msg: str):
            if progress_callback:
                progress_callback(pct, msg)

        report(0, "Opening PDF...")

        with pikepdf.open(input_path) as pdf:
            total_pages = len(pdf.pages)

            # Process images if not removing them entirely
            if not self.options.remove_images:
                report(5, "Optimizing images...")
                self._optimize_images(pdf, report, total_pages)
            else:
                report(5, "Removing images...")
                self._remove_images(pdf, report, total_pages)

            report(80, "Applying compression...")

            # Strip metadata if requested
            if self.options.strip_metadata:
                report(85, "Stripping metadata...")
                self._strip_metadata(pdf)

            report(90, "Saving optimized PDF...")

            # Save with compression options
            # Note: normalize_content and linearize cannot be used together
            save_options = {
                "compress_streams": True,
                "stream_decode_level": pikepdf.StreamDecodeLevel.specialized,
                "object_stream_mode": pikepdf.ObjectStreamMode.generate,
                "linearize": True,
            }

            if self.options.aggressive:
                save_options["recompress_flate"] = True
                # Use normalize_content for aggressive mode (disables linearize)
                save_options["linearize"] = False
                save_options["normalize_content"] = True

            pdf.save(output_path, **save_options)

        report(100, "Complete!")
        return output_path

    def _optimize_images(
        self,
        pdf: pikepdf.Pdf,
        report: Callable[[float, str], None],
        total_pages: int,
    ):
        """Optimize images in the PDF."""
        images_processed = 0
        images_to_process = []

        # Collect all images first
        for page_num, page in enumerate(pdf.pages):
            if "/Resources" not in page:
                continue
            resources = page["/Resources"]
            if "/XObject" not in resources:
                continue

            xobjects = resources["/XObject"]
            for name, xobj_ref in xobjects.items():
                try:
                    xobj = xobj_ref
                    if not isinstance(xobj, pikepdf.Stream):
                        continue
                    if xobj.get("/Subtype") != "/Image":
                        continue
                    images_to_process.append((page_num, name, xobj))
                except Exception:
                    continue

        total_images = len(images_to_process)
        if total_images == 0:
            return

        for idx, (page_num, name, xobj) in enumerate(images_to_process):
            try:
                self._process_single_image(pdf, xobj)
                images_processed += 1
                progress = 5 + (70 * (idx + 1) / total_images)
                report(progress, f"Optimized image {idx + 1}/{total_images}")
            except Exception:
                # Skip problematic images
                continue

    def _process_single_image(self, pdf: pikepdf.Pdf, xobj: pikepdf.Stream):
        """Process a single image object."""
        try:
            # Get image dimensions
            width = int(xobj.get("/Width", 0))
            height = int(xobj.get("/Height", 0))

            if width == 0 or height == 0:
                return

            # Extract image data
            raw_data = xobj.read_raw_bytes()

            # Try to decode the image
            pil_image = None

            # Check for common image filters
            filter_type = xobj.get("/Filter")

            if filter_type == "/DCTDecode":
                # JPEG image
                try:
                    pil_image = Image.open(io.BytesIO(raw_data))
                except Exception:
                    return
            elif filter_type == "/FlateDecode":
                # Try to reconstruct from raw data
                try:
                    decoded = xobj.read_bytes()
                    color_space = xobj.get("/ColorSpace")
                    bits = int(xobj.get("/BitsPerComponent", 8))

                    if color_space == "/DeviceRGB":
                        mode = "RGB"
                    elif color_space == "/DeviceGray":
                        mode = "L"
                    elif color_space == "/DeviceCMYK":
                        mode = "CMYK"
                    else:
                        # Complex color space, skip
                        return

                    pil_image = Image.frombytes(mode, (width, height), decoded)
                except Exception:
                    return
            else:
                # Unsupported filter, skip
                return

            if pil_image is None:
                return

            # Convert to RGB for optimization
            if pil_image.mode == "CMYK":
                pil_image = pil_image.convert("RGB")
            elif pil_image.mode == "L":
                if not self.options.grayscale:
                    pil_image = pil_image.convert("RGB")
            elif pil_image.mode in ("RGBA", "P"):
                background = Image.new("RGB", pil_image.size, (255, 255, 255))
                if pil_image.mode == "P":
                    pil_image = pil_image.convert("RGBA")
                if pil_image.mode == "RGBA":
                    background.paste(pil_image, mask=pil_image.split()[-1])
                pil_image = background

            # Apply grayscale if requested
            if self.options.grayscale and pil_image.mode != "L":
                pil_image = pil_image.convert("L")

            # Resize based on DPI target
            # Assume 72 DPI as base for PDF coordinates
            current_dpi = max(width, height) / 10  # Rough estimate
            if current_dpi > self.options.dpi:
                scale = self.options.dpi / current_dpi
                new_width = max(1, int(width * scale))
                new_height = max(1, int(height * scale))
                pil_image = pil_image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Save optimized image
            output = io.BytesIO()
            if pil_image.mode == "L":
                pil_image.save(output, format="JPEG", quality=self.options.quality, optimize=True)
            else:
                pil_image = pil_image.convert("RGB")
                pil_image.save(output, format="JPEG", quality=self.options.quality, optimize=True)

            optimized_data = output.getvalue()

            # Only replace if smaller
            if len(optimized_data) < len(raw_data):
                # Update the image stream
                xobj.write(optimized_data, filter=pikepdf.Name("/DCTDecode"))
                xobj["/Width"] = pil_image.width
                xobj["/Height"] = pil_image.height
                xobj["/ColorSpace"] = pikepdf.Name("/DeviceGray" if pil_image.mode == "L" else "/DeviceRGB")
                xobj["/BitsPerComponent"] = 8

                # Remove any decode params that might conflict
                if "/DecodeParms" in xobj:
                    del xobj["/DecodeParms"]
                if "/SMask" in xobj:
                    del xobj["/SMask"]

        except Exception:
            # Skip any problematic images
            pass

    def _remove_images(
        self,
        pdf: pikepdf.Pdf,
        report: Callable[[float, str], None],
        total_pages: int,
    ):
        """Remove all images from the PDF."""
        for page_num, page in enumerate(pdf.pages):
            if "/Resources" not in page:
                continue
            resources = page["/Resources"]
            if "/XObject" not in resources:
                continue

            xobjects = resources["/XObject"]
            images_to_remove = []

            for name, xobj_ref in xobjects.items():
                try:
                    xobj = xobj_ref
                    if not isinstance(xobj, pikepdf.Stream):
                        continue
                    if xobj.get("/Subtype") == "/Image":
                        images_to_remove.append(name)
                except Exception:
                    continue

            # Remove image references
            for name in images_to_remove:
                del xobjects[name]

            progress = 5 + (70 * (page_num + 1) / total_pages)
            report(progress, f"Processed page {page_num + 1}/{total_pages}")

    def _strip_metadata(self, pdf: pikepdf.Pdf):
        """Remove metadata from the PDF."""
        # Clear document info
        with pdf.open_metadata() as meta:
            # Delete all metadata entries
            for key in list(meta.keys()):
                del meta[key]

        # Clear document info dictionary
        if "/Info" in pdf.trailer:
            del pdf.trailer["/Info"]


def reduce_pdf(
    input_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    options: Optional[ReductionOptions] = None,
    progress_callback: Optional[Callable[[float, str], None]] = None,
) -> Path:
    """
    Convenience function to reduce a PDF file.

    Args:
        input_path: Path to the input PDF file
        output_path: Path for the output file
        options: Reduction options
        progress_callback: Optional callback for progress updates

    Returns:
        Path to the reduced PDF file
    """
    reducer = PDFReducer(options)
    return reducer.reduce(input_path, output_path, progress_callback)
