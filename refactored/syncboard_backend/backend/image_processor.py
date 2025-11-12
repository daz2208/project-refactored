"""
Image processing and OCR for visual content ingestion.
"""

import base64
import logging
import os
from io import BytesIO
from pathlib import Path
from typing import Dict
from PIL import Image
import pytesseract

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Process images for ingestion."""
    
    def __init__(self):
        # Windows users may need to set tesseract path
        tesseract_cmd = os.environ.get("TESSERACT_CMD")
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    
    def extract_text_from_image(self, image_bytes: bytes) -> str:
        """
        Extract text from image using OCR.
        
        Args:
            image_bytes: Raw image bytes
        
        Returns:
            Extracted text or empty string
        """
        try:
            image = Image.open(BytesIO(image_bytes))
            
            # Convert to RGB if needed
            if image.mode not in ('RGB', 'L'):
                image = image.convert('RGB')
            
            # Extract text
            text = pytesseract.image_to_string(image)
            
            logger.info(f"Extracted {len(text)} characters from image")
            return text.strip()
            
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return ""
    
    def get_image_metadata(self, image_bytes: bytes) -> Dict:
        """
        Extract image metadata.
        
        Returns:
            {
                "width": int,
                "height": int,
                "format": str,
                "mode": str,
                "size_bytes": int
            }
        """
        try:
            image = Image.open(BytesIO(image_bytes))
            
            return {
                "width": image.width,
                "height": image.height,
                "format": image.format or "unknown",
                "mode": image.mode,
                "size_bytes": len(image_bytes)
            }
        except Exception as e:
            logger.error(f"Failed to get image metadata: {e}")
            return {}
    
    def store_image(self, image_bytes: bytes, doc_id: int) -> str:
        """
        Store image file to disk with path traversal protection.

        Args:
            image_bytes: Raw image bytes
            doc_id: Document ID

        Returns:
            File path where image was saved

        Raises:
            ValueError: If path validation fails (path traversal attempt)
        """
        # Validate doc_id is a positive integer
        if not isinstance(doc_id, int) or doc_id < 0:
            raise ValueError(f"Invalid doc_id: {doc_id}")

        # Create images directory with absolute path
        images_dir = Path("stored_images").resolve()
        images_dir.mkdir(parents=True, exist_ok=True)

        # Construct filepath with validated doc_id (use abs() to ensure positive)
        filename = f"doc_{abs(doc_id)}.png"
        filepath = images_dir / filename

        # Security check: ensure filepath is within images_dir
        # This prevents path traversal attacks like "../../../etc/passwd"
        try:
            if not filepath.resolve().is_relative_to(images_dir):
                raise ValueError(f"Path traversal detected: {filepath}")
        except ValueError as e:
            logger.error(f"Security: Path validation failed - {e}")
            raise

        try:
            image = Image.open(BytesIO(image_bytes))
            image.save(str(filepath), "PNG")
            logger.info(f"Saved image to {filepath}")
            return str(filepath)
        except Exception as e:
            logger.error(f"Failed to save image: {e}")
            return ""
