import base64
from typing import Dict
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from app.config import settings
import aiofiles
import json
import os
from pathlib import Path


class VisionService:
    """Service for analyzing clothing images using OpenAI Vision API"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",  # GPT-4 with vision
            temperature=0.3,
            openai_api_key=settings.OPENAI_API_KEY
        )
        # Create uploads directory if it doesn't exist
        self.upload_dir = Path("uploads/wardrobe")
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    async def analyze_clothing_image(self, image_content: bytes, content_type: str) -> Dict:
        """
        Analyze a clothing image and extract details using GPT-4 Vision.
        
        Returns:
            Dict with keys: name, category, primary_color, secondary_colors, 
                          seasons, occasions, style_tags, brand (if visible)
        """
        # Convert image to base64
        image_base64 = base64.b64encode(image_content).decode('utf-8')
        image_url = f"data:{content_type};base64,{image_base64}"
        
        # Create vision prompt
        prompt = """Analyze this clothing item image and provide detailed information in JSON format.

Extract the following information:
1. **name**: A descriptive name for the item (e.g., "White Cotton T-Shirt", "Blue Denim Jeans")
2. **category**: One of [top, bottom, dress, outerwear, shoes, accessory]
3. **primary_color**: The main color of the item
4. **secondary_colors**: List of other prominent colors (if any)
5. **seasons**: Which seasons this is suitable for from [spring, summer, fall, winter, all_season]
6. **occasions**: What occasions this fits from [casual, business, formal, sports, party, date]
7. **style_tags**: Descriptive style tags (e.g., "minimalist", "vintage", "streetwear", "bohemian", "elegant", "sporty")
8. **brand**: Brand name if visible (null if not visible)
9. **pattern**: Type of pattern if any (solid, striped, floral, checkered, etc.)
10. **material_guess**: Your best guess at the material (cotton, denim, leather, silk, etc.)

Return ONLY valid JSON with these exact keys. Be specific and accurate.

Example output:
{
    "name": "Navy Blue Blazer",
    "category": "outerwear",
    "primary_color": "navy blue",
    "secondary_colors": ["silver"],
    "seasons": ["fall", "winter", "spring"],
    "occasions": ["business", "formal"],
    "style_tags": ["professional", "classic", "tailored"],
    "brand": null,
    "pattern": "solid",
    "material_guess": "wool blend"
}"""
        
        # Call Vision API
        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]
        )
        
        response = await self.llm.ainvoke([message])
        
        # Parse response
        try:
            content = response.content
            # Extract JSON from markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            analysis = json.loads(content)
            
            # Validate and normalize the response
            return self._normalize_analysis(analysis)
            
        except json.JSONDecodeError as e:
            # Fallback to basic analysis if JSON parsing fails
            return {
                "name": "Clothing Item",
                "category": "top",
                "primary_color": "unknown",
                "secondary_colors": [],
                "seasons": ["all_season"],
                "occasions": ["casual"],
                "style_tags": [],
                "brand": None,
                "pattern": "unknown",
                "material_guess": "unknown"
            }
    
    def _normalize_analysis(self, analysis: Dict) -> Dict:
        """Normalize and validate AI analysis results"""
        # Valid categories
        valid_categories = ["top", "bottom", "dress", "outerwear", "shoes", "accessory"]
        if analysis.get("category") not in valid_categories:
            analysis["category"] = "top"
        
        # Valid seasons
        valid_seasons = ["spring", "summer", "fall", "winter", "all_season"]
        analysis["seasons"] = [s for s in analysis.get("seasons", []) if s in valid_seasons]
        if not analysis["seasons"]:
            analysis["seasons"] = ["all_season"]
        
        # Valid occasions
        valid_occasions = ["casual", "business", "formal", "sports", "party", "date"]
        analysis["occasions"] = [o for o in analysis.get("occasions", []) if o in valid_occasions]
        if not analysis["occasions"]:
            analysis["occasions"] = ["casual"]
        
        # Ensure required fields exist
        analysis.setdefault("name", "Clothing Item")
        analysis.setdefault("primary_color", "unknown")
        analysis.setdefault("secondary_colors", [])
        analysis.setdefault("style_tags", [])
        analysis.setdefault("brand", None)
        analysis.setdefault("pattern", "unknown")
        analysis.setdefault("material_guess", "unknown")
        
        return analysis
    
    async def store_image(self, image_content: bytes, user_id: str, filename: str) -> str:
        """
        Store the clothing image and return URL/path.
        
        For production, you'd want to:
        1. Upload to S3/Cloudinary/etc
        2. Return the public URL
        
        For now, we'll save locally and return a path.
        """
        # Create user directory
        user_dir = self.upload_dir / user_id
        user_dir.mkdir(exist_ok=True)
        
        # Generate unique filename
        from datetime import datetime
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        file_extension = filename.split('.')[-1] if '.' in filename else 'jpg'
        unique_filename = f"{timestamp}_{filename}"
        
        # Save file asynchronously
        file_path = user_dir / unique_filename
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(image_content)
        
        # Return relative path (in production, return full URL)
        return f"/uploads/wardrobe/{user_id}/{unique_filename}"
    
    async def compare_outfits(self, outfit_items: list, occasion: str, user_preferences: Dict) -> Dict:
        """
        Use vision to evaluate how well outfit items work together.
        Can analyze color harmony, style coherence, etc.
        """
        # This could be enhanced to actually look at the images together
        # For now, we'll do a text-based analysis
        
        prompt = f"""Evaluate this outfit combination for a {occasion} occasion:

Items:
{json.dumps(outfit_items, indent=2)}

User Preferences:
{json.dumps(user_preferences, indent=2)}

Provide:
1. **compatibility_score**: 0-10 score for how well items work together
2. **color_harmony**: Assessment of color combination
3. **style_coherence**: Whether styles mesh well
4. **occasion_appropriateness**: How suitable for the occasion
5. **suggestions**: Any suggestions to improve the outfit

Return as JSON."""

        response = await self.llm.ainvoke(prompt)
        
        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            return json.loads(content)
        except:
            return {
                "compatibility_score": 7.5,
                "color_harmony": "Good",
                "style_coherence": "Coherent",
                "occasion_appropriateness": "Appropriate",
                "suggestions": []
            }


# Singleton instance
vision_service = VisionService()