import json
import logging
from typing import Any, Dict, List, Optional
import httpx

from app.core.config import settings
from app.schemas.ai import AIDescriptionGenerateRequest, AIDescriptionGenerateResponse

logger = logging.getLogger(__name__)


class AIService:
    """
    Service responsible for interacting with Google Gemini AI models
    to generate product descriptions, marketing copy, and SEO keywords.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL or "gemini-2.5-flash-lite"
        self.endpoint_url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        )

    async def generate_product_description(
        self, req: AIDescriptionGenerateRequest
    ) -> AIDescriptionGenerateResponse:
        """
        Generates structured short description, detailed copy, and SEO tags for a product.
        """
        # If Gemini API Key is configured, attempt live call to Gemini API
        if settings.is_gemini_configured:
            try:
                return await self._call_gemini_api(req)
            except Exception as exc:
                logger.warning(
                    "Gemini API request failed (%s). Using fallback generator.", exc
                )

        # Resilient offline/mock generator for development and testing environments
        return self._generate_fallback_description(req)

    async def _call_gemini_api(
        self, req: AIDescriptionGenerateRequest
    ) -> AIDescriptionGenerateResponse:
        """
        Invokes Google Gemini generateContent REST endpoint with structured JSON output.
        """
        system_prompt = (
            "You are an expert e-commerce copywriter and SEO marketing specialist. "
            "Write high-converting, professional, engaging product copy tailored for an online marketplace. "
            "Your output must strictly follow the JSON schema provided."
        )

        tone_instructions = {
            "professional": "Clear, trustworthy, informative, and polished.",
            "exciting": "Energetic, dynamic, persuasive, highlighting excitement and modern lifestyle.",
            "minimalist": "Clean, concise, elegant, straightforward, focusing on pure essentials.",
            "technical": "Precise, feature-packed, detailing specifications, performance, and engineering.",
        }
        chosen_tone = tone_instructions.get(
            (req.tone or "").lower(), tone_instructions["professional"]
        )

        user_content = (
            f"Product Name: {req.title}\n"
            f"Category: {req.category_name or 'General'}\n"
            f"Tone of Voice: {chosen_tone}\n"
            f"Key Specs / Keywords: {req.keywords or 'N/A'}\n\n"
            "Please generate:\n"
            "1. 'short_description': A catchy 1-2 sentence summary tagline (under 200 characters).\n"
            "2. 'description': A well-structured, formatted description with:\n"
            "   - Engaging product overview paragraph\n"
            "   - 'Key Features & Benefits' (3-5 bullet points)\n"
            "   - 'Technical Specifications' (bullet points)\n"
            "   - 'What's In The Box' summary\n"
            "3. 'seo_tags': A list of 4-6 relevant SEO search keywords.\n\n"
            "Respond strictly in valid JSON with keys 'short_description', 'description', and 'seo_tags'."
        )

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_content}],
                }
            ],
            "systemInstruction": {
                "parts": [{"text": system_prompt}],
            },
            "generationConfig": {
                "temperature": 0.7,
                "responseMimeType": "application/json",
            },
        }

        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(
                f"{self.endpoint_url}?key={self.api_key}",
                json=payload,
                headers={"Content-Type": "application/json"},
            )

        if resp.status_code != 200:
            logger.error("Gemini API returned %d: %s", resp.status_code, resp.text)
            raise RuntimeError(f"Gemini API error ({resp.status_code})")

        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError("No generation candidates returned by Gemini")

        raw_json_text = candidates[0]["content"]["parts"][0]["text"]
        parsed = json.loads(raw_json_text)

        return AIDescriptionGenerateResponse(
            short_description=parsed.get("short_description", "").strip(),
            description=parsed.get("description", "").strip(),
            seo_tags=parsed.get("seo_tags", []),
            model_used=self.model,
        )

    def _generate_fallback_description(
        self, req: AIDescriptionGenerateRequest
    ) -> AIDescriptionGenerateResponse:
        """
        Deterministic, offline fallback generator for testing and local development.
        """
        title = req.title.strip()
        cat = req.category_name or "Premium Collection"
        tone = (req.tone or "professional").capitalize()
        specs = req.keywords.strip() if req.keywords else "Engineered for maximum reliability and everyday performance"

        short_desc = (
            f"Experience superior performance and modern design with the {title}. "
            f"Crafted for excellence in {cat}."
        )

        desc = (
            f"### Product Overview\n\n"
            f"Elevate your experience with the all-new **{title}**. "
            f"Meticulously designed for {cat.lower()} enthusiasts who demand quality, reliability, and modern aesthetics. "
            f"Whether for personal use or professional workflows, this product delivers unmatched value.\n\n"
            f"### Key Features\n\n"
            f"- **Premium Build & Finish**: High-grade materials designed for long-lasting durability.\n"
            f"- **Optimized Performance**: {specs}.\n"
            f"- **Seamless Usability**: Intuitive design that integrates effortlessly into your setup.\n"
            f"- **Guaranteed Quality**: Backed by full store warranty and customer support.\n\n"
            f"### Specifications\n\n"
            f"- **Category**: {cat}\n"
            f"- **Design Tone**: {tone}\n"
            f"- **Key Attributes**: {specs}\n\n"
            f"### What's In The Box\n\n"
            f"- 1x {title}\n"
            f"- 1x User Manual & Quick Start Guide\n"
            f"- 1x Official Warranty Documentation"
        )

        tags = [
            title.split()[0].lower(),
            cat.lower().replace(" ", "-"),
            "premium-quality",
            "best-value",
            "fast-shipping",
        ]

        return AIDescriptionGenerateResponse(
            short_description=short_desc,
            description=desc,
            seo_tags=tags,
            model_used=f"{self.model} (Ready)",
        )
