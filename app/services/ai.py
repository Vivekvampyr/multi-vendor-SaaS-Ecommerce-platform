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
        self.api_key = (api_key or settings.GEMINI_API_KEY or "").strip()
        raw_model = (model or settings.GEMINI_MODEL or "gemini-3.6-flash").strip()
        if raw_model.startswith("models/"):
            raw_model = raw_model[7:]
        self.model = raw_model
        self.endpoint_url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        )

    async def generate_product_description(
        self, req: AIDescriptionGenerateRequest
    ) -> AIDescriptionGenerateResponse:
        """
        Generates structured short description, detailed copy, and SEO tags for a product.
        Calls live Google Gemini API if configured, otherwise provides an offline preview.
        """
        if settings.is_gemini_configured or self.api_key:
            return await self._call_gemini_api(req)

        # Resilient offline/mock generator for development and testing
        return self._generate_fallback_description(req)

    async def _call_gemini_api(
        self, req: AIDescriptionGenerateRequest
    ) -> AIDescriptionGenerateResponse:
        """
        Invokes Google Gemini generateContent REST endpoint with structured JSON output.
        """
        system_prompt = (
            "You are a world-class senior hardware engineer, tech specialist, and high-converting e-commerce copywriter. "
            "Your task is to write accurate, highly detailed, professional product marketing copy for an e-commerce platform. "
            "IMPORTANT ACCURACY GUIDELINES:\n"
            "- If the product is a known real-world hardware item, GPU, CPU, smartphone, electronics, appliance, or brand name (such as AMD Radeon, NVIDIA GeForce, Intel, Apple, Sony, ASRock, Asus, Samsung, etc.), "
            "you MUST utilize your accurate real-world technical knowledge regarding its real architecture, VRAM, memory bus, cooling system, compute units, clock speeds, and target gaming/workstation performance.\n"
            "- Do not output generic placeholder text if real specifications are known.\n"
            "- If any key specs or keywords are provided by the merchant, highlight them prominently.\n"
            "- Respond strictly in valid JSON adhering to the specified schema."
        )

        tone_instructions = {
            "professional": "Clear, trustworthy, informative, polished, and factual.",
            "exciting": "Energetic, dynamic, persuasive, highlighting high performance, immersion, and excitement.",
            "minimalist": "Clean, concise, elegant, straightforward, focusing on pure essentials.",
            "technical": "Precise, spec-heavy, detailing architecture, silicon, bandwidth, thermal solutions, and performance metrics.",
        }
        chosen_tone = tone_instructions.get(
            (req.tone or "").lower(), tone_instructions["professional"]
        )

        user_content = (
            f"Product Name: {req.title}\n"
            f"Category: {req.category_name or 'Electronics / Hardware'}\n"
            f"Tone: {chosen_tone}\n"
            f"Vendor Notes / Keywords: {req.keywords or 'N/A'}\n\n"
            "Please generate:\n"
            "1. 'short_description': A catchy, punchy 1-2 sentence summary tagline (under 200 characters).\n"
            "2. 'description': A well-structured Markdown copy formatted with:\n"
            "   ### Product Overview\n"
            "   (Engaging product overview highlighting its real-world capabilities and build)\n\n"
            "   ### Key Features\n"
            "   - **Feature 1**: Details\n"
            "   - **Feature 2**: Details\n"
            "   - **Feature 3**: Details\n"
            "   - **Feature 4**: Details\n\n"
            "   ### Technical Specifications\n"
            "   - **Architecture / GPU**: Accurate details\n"
            "   - **Memory / VRAM**: Accurate details\n"
            "   - **Connectivity & Cooling**: Accurate details\n\n"
            "   ### What's In The Box\n"
            "   - 1x Item\n"
            "   - Included accessories and documentation\n\n"
            "3. 'seo_tags': A list of 4-6 highly relevant search keywords for this exact product.\n\n"
            "Return strictly valid JSON with keys 'short_description', 'description', and 'seo_tags'."
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
                "temperature": 0.5,
                "responseMimeType": "application/json",
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.endpoint_url}?key={self.api_key}",
                json=payload,
                headers={"Content-Type": "application/json"},
            )

        if resp.status_code != 200:
            error_data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            error_msg = error_data.get("error", {}).get("message", resp.text)
            logger.error("Gemini API returned %d: %s", resp.status_code, error_msg)
            raise RuntimeError(f"Gemini API Error ({resp.status_code}): {error_msg}")

        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError("No generation response returned by Gemini model.")

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
