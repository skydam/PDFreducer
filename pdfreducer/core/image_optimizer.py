"""Image optimization utilities for PDF reduction."""

import io
from typing import Optional

from PIL import Image

from pdfreducer.core.options import ReductionOptions


class ImageOptimizer:
    """Handles image optimization within PDFs."""

    def __init__(self, options: ReductionOptions):
        self.options = options

    def optimize_image(self, image_data: bytes, current_dpi: Optional[float] = None) -> Optional[bytes]:
        """
        Optimize an image according to the reduction options.

        Args:
            image_data: Raw image bytes
            current_dpi: Current DPI of the image (if known)

        Returns:
            Optimized image bytes, or None if image should be removed
        """
        if self.options.remove_images:
            return None

        try:
            img = Image.open(io.BytesIO(image_data))
        except Exception:
            # If we can't open the image, return original
            return image_data

        # Convert to RGB if necessary (for JPEG output)
        if img.mode in ("RGBA", "P"):
            # Create white background for transparency
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Convert to grayscale if requested
        if self.options.grayscale:
            img = img.convert("L").convert("RGB")

        # Calculate scaling factor based on DPI
        if current_dpi and current_dpi > self.options.dpi:
            scale_factor = self.options.dpi / current_dpi
            new_size = (int(img.width * scale_factor), int(img.height * scale_factor))
            if new_size[0] > 0 and new_size[1] > 0:
                img = img.resize(new_size, Image.Resampling.LANCZOS)

        # Save optimized image
        output = io.BytesIO()
        img.save(
            output,
            format="JPEG",
            quality=self.options.quality,
            optimize=True,
        )
        return output.getvalue()

    def estimate_image_dpi(self, width_pixels: int, width_points: float) -> float:
        """
        Estimate the DPI of an image based on its pixel and point dimensions.

        Args:
            width_pixels: Width in pixels
            width_points: Width in PDF points (1 point = 1/72 inch)

        Returns:
            Estimated DPI
        """
        if width_points <= 0:
            return 72.0  # Default fallback
        return (width_pixels / width_points) * 72.0
