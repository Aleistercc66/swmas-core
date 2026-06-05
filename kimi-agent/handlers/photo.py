"""Photo handler for Kimi Telegram Agent."""
import io
import logging
import os
from typing import Any

from PIL import Image
from telegram import Update
from telegram.ext import ContextTypes

from brain.llm import llm
from brain.memory import memory
from utils.helpers import format_analysis_response

logger = logging.getLogger(__name__)

# Try to import OCR libraries
try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False
    logger.warning("pytesseract not available")

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    logger.warning("easyocr not available")


class OCREngine:
    """OCR engine wrapper supporting multiple backends."""
    
    def __init__(self):
        self.easyocr_reader = None
        self.preferred = "easyocr" if EASYOCR_AVAILABLE else ("pytesseract" if PYTESSERACT_AVAILABLE else None)
    
    async def extract_text(self, image: Image.Image) -> str:
        """Extract text from image using available OCR."""
        if self.preferred == "easyocr":
            return await self._easyocr_extract(image)
        elif self.preferred == "pytesseract":
            return self._pytesseract_extract(image)
        else:
            return "[OCR not available - no OCR engine installed]"
    
    def _pytesseract_extract(self, image: Image.Image) -> str:
        """Extract text using pytesseract."""
        try:
            from config import settings
            if settings.TESSERACT_CMD:
                pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
            
            text = pytesseract.image_to_string(
                image,
                lang=settings.TESSERACT_LANG.replace("+", "+")
            )
            return text.strip()
        except Exception as e:
            logger.error(f"Pytesseract error: {e}")
            return ""
    
    async def _easyocr_extract(self, image: Image.Image) -> str:
        """Extract text using EasyOCR."""
        try:
            if self.easyocr_reader is None:
                import asyncio
                loop = asyncio.get_event_loop()
                self.easyocr_reader = await loop.run_in_executor(
                    None,
                    lambda: easyocr.Reader(['en', 'el'])
                )
            
            import asyncio
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.easyocr_reader.readtext(
                    image,
                    detail=0,
                    paragraph=True
                )
            )
            return "\n".join(result)
        except Exception as e:
            logger.error(f"EasyOCR error: {e}")
            # Fallback to pytesseract
            if PYTESSERACT_AVAILABLE:
                return self._pytesseract_extract(image)
            return ""


ocr_engine = OCREngine()


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming photo messages."""
    user_id = update.effective_user.id
    
    # Send typing action
    await update.message.chat.send_action(action="typing")
    
    # Get the largest photo
    photo = update.message.photo[-1]  # Last is largest
    
    # Download photo
    photo_file = await photo.get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    
    # Open with PIL
    image = Image.open(io.BytesIO(photo_bytes))
    
    # Extract text via OCR
    extracted_text = await ocr_engine.extract_text(image)
    
    # Build prompt for LLM
    if extracted_text and len(extracted_text.strip()) > 10:
        # Photo contains text - analyze it
        prompt = f"""The user sent a photo containing text. Here's what was extracted via OCR:

EXTRACTED TEXT:
{extracted_text}

Please:
1. Summarize the content
2. Identify key information (dates, names, numbers)
3. Note any important details
4. If it's a chart/graph, describe the data
5. If it's a document, summarize its purpose
"""
        
        analysis = await llm.analyze(prompt, mode="photo")
        
        response = f"""📸 **Photo Analysis**

🔍 **Extracted Text**:
```
{extracted_text[:800]}{'...' if len(extracted_text) > 800 else ''}
```

📊 **Analysis**:
{analysis}
"""
        
        # Check if text has claims
        claims = await llm.extract_claims(extracted_text)
        if claims:
            response += f"\n📝 **Detected {len(claims)} verifiable claims**\n"
            response += "Use `/verify` to fact-check them\n"
        
    else:
        # No text detected - describe the image
        prompt = f"""The user sent a photo. Please describe what you see in detail.

Image dimensions: {image.size}
Image mode: {image.mode}

Describe:
1. What's in the image (objects, people, scenes)
2. Any visible text or signs
3. Colors and composition
4. Context or setting
5. Any notable details
"""
        
        analysis = await llm.analyze(prompt, mode="photo")
        
        response = f"""📸 **Photo Description**

{analysis}

---
ℹ️ No readable text detected in this image.
"""
    
    await update.message.reply_text(response, parse_mode="Markdown")
    
    # Log to memory
    memory.add_message(
        telegram_id=str(user_id),
        role="user",
        content=f"[Photo] {extracted_text[:200] if extracted_text else 'No text extracted'}",
        message_type="photo",
        metadata={"has_text": bool(extracted_text)}
    )
    
    memory.add_message(
        telegram_id=str(user_id),
        role="assistant",
        content=response,
        message_type="photo_analysis"
    )


async def handle_photo_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /analyze_photo command (expects photo reply)."""
    if not update.message.reply_to_message or not update.message.reply_to_message.photo:
        await update.message.reply_text(
            "📸 Please reply to a photo with `/analyze_photo` or just send a photo directly."
        )
        return
    
    # Process the replied photo
    update.message = update.message.reply_to_message
    await handle_photo(update, context)
