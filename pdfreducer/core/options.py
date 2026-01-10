"""Reduction options configuration."""

from dataclasses import dataclass, field


@dataclass
class ReductionOptions:
    """Options for PDF reduction."""

    # Image settings
    dpi: int = 150
    quality: int = 80
    grayscale: bool = False
    remove_images: bool = False

    # Compression settings
    aggressive: bool = False
    strip_metadata: bool = False

    def __post_init__(self):
        """Validate options after initialization."""
        if not 1 <= self.quality <= 100:
            raise ValueError("Quality must be between 1 and 100")
        if not 10 <= self.dpi <= 600:
            raise ValueError("DPI must be between 10 and 600")

    @classmethod
    def from_dict(cls, data: dict) -> "ReductionOptions":
        """Create options from a dictionary."""
        return cls(
            dpi=data.get("dpi", 150),
            quality=data.get("quality", 80),
            grayscale=data.get("grayscale", False),
            remove_images=data.get("remove_images", False),
            aggressive=data.get("aggressive", False),
            strip_metadata=data.get("strip_metadata", False),
        )

    def to_dict(self) -> dict:
        """Convert options to a dictionary."""
        return {
            "dpi": self.dpi,
            "quality": self.quality,
            "grayscale": self.grayscale,
            "remove_images": self.remove_images,
            "aggressive": self.aggressive,
            "strip_metadata": self.strip_metadata,
        }
