"""
Image processing and OCR for visual content ingestion.
"""

import base64
import logging
import os
from io import BytesIO
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
        Store image file to disk.
        
        Args:
            image_bytes: Raw image bytes
            doc_id: Document ID
        
        Returns:
            File path where image was saved
        """
        # Create images directory if doesn't exist
        images_dir = "stored_images"
        os.makedirs(images_dir, exist_ok=True)
        
        # Save image
        filepath = os.path.join(images_dir, f"doc_{doc_id}.png")
        
        try:
            image = Image.open(BytesIO(image_bytes))
            image.save(filepath, "PNG")
            logger.info(f"Saved image to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save image: {e}")
            return ""
