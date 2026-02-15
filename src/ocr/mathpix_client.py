
import asyncio
import base64
import httpx
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config import settings

from src.config import settings

logger = logging.getLogger(__name__)

class MathpixClient:

    def __init__(self):
        
        self.api_url = settings.mathpix_api_url
        self.app_id = settings.mathpix_app_id
        self.app_key = settings.mathpix_app_key
        self.headers = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "Content-Type": "application/json"
        }
        
        # Rate limiter
        self.rate_limit = settings.ocr_rate_limit
        self.semaphore = asyncio.Semaphore(self.rate_limit)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException))
    )
    async def process_pdf(
        self,
        pdf_path: str,
        page_number: Optional[int] = None
    ) -> Dict[str, Any]:
        
        async with self.semaphore:
            try:
                # Read PDF file
                pdf_data = self._read_pdf(pdf_path)
                
                # Prepare request
                payload = {
                    "src": f"data:application/pdf;base64,{pdf_data}",
                    "formats": ["text", "latex"],
                    "metadata": {
                        "page_number": page_number
                    }
                }
                
                # Make API request
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        self.api_url,
                        json=payload,
                        headers=self.headers
                    )
                    response.raise_for_status()
                    
                    result = response.json()
                    
                    logger.info(f"Successfully processed PDF: {pdf_path}")
                    return {
                        "text": result.get("text", ""),
                        "latex": result.get("latex", ""),
                        "confidence": result.get("confidence", 0.0),
                        "page_number": page_number,
                        "source_file": pdf_path
                    }
                    
            except httpx.HTTPError as e:
                logger.error(f"HTTP error processing PDF {pdf_path}: {e}")
                raise
            except Exception as e:
                logger.error(f"Error processing PDF {pdf_path}: {e}")
                raise
    
    async def process_pdf_batch(
        self,
        pdf_paths: list[str]
    ) -> list[Dict[str, Any]]:
        
        tasks = [self.process_pdf(path) for path in pdf_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to process {pdf_paths[i]}: {result}")
            else:
                valid_results.append(result)
        
        return valid_results
    
    async def process_image(self, image_path: str) -> Dict[str, Any]:

        return await self.process_pdf(image_path)
    
    def _read_pdf(self, pdf_path: str) -> str:
        
        try:
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
                return base64.b64encode(pdf_bytes).decode("utf-8")
        except Exception as e:
            logger.error(f"Error reading PDF {pdf_path}: {e}")
            raise

# Global client instance
mathpix_client = MathpixClient()
