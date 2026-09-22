"""
AI Content & Image Generator module for ai_news_agent.
Uses the official Google GenAI SDK (google-genai) with Gemini models
to draft professional Arabic LinkedIn posts and Imagen 3 for technical visualizations.
"""

import io
import json
import logging
from pathlib import Path
from typing import Dict, Optional
from PIL import Image

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from config import GEMINI_API_KEY, IMAGE_MODEL, IMAGES_DIR, TEXT_MODEL
from fetcher import Article

logger = logging.getLogger(__name__)


class GenerationResult(BaseModel):
    """Pydantic model for structured Gemini post generation."""
    short_hook: str = Field(
        description="A punchy 1-2 sentence hook in Arabic summarizing the breakthrough."
    )
    linkedin_post: str = Field(
        description=(
            "A comprehensive, authoritative, and deeply detailed LinkedIn post in professional Arabic blended naturally with English technical terms. "
            "Must be exhaustive and educational (between 1,500 and 2,500 characters) containing complete depth: "
            "1. Bold curiosity-igniting opening hook. "
            "2. Complete strategic context & regional relevance to Saudi Arabia, the GCC, or global tech landscape. "
            "3. Deep architectural / financial / engineering breakdown with 4 to 5 structured bullet points analyzing concrete mechanics under the hood (APIs, regulations like SAMA/CMA/REGA, open banking, property valuation AI, benchmarks, latency, unit economics). "
            "4. Practical engineering and business impact for software teams, fintech/proptech founders, and investors in the region. "
            "5. Strategic debate question for tech & business leaders in the comments. "
            "6. Source attribution line: '📌 المصدر: [Source Name] | [Article Title]'. "
            "7. Contextual hashtags for Saudi Arabia, GCC, FinTech, PropTech, and Tech."
        )
    )
    telegram_caption: str = Field(
        description="A concise version of the news in Arabic (strictly under 950 characters) designed specifically as a single Telegram photo caption."
    )
    image_prompt: str = Field(
        description="A detailed English prompt for Google Flow's Nano Banana Pro model creating a professional LinkedIn tech infographic summarizing the news."
    )

    @property
    def post_text(self) -> str:
        return self.linkedin_post


class AIGenerator:
    """Orchestrates Gemini text generation and Imagen 3 image generation."""

    def __init__(self, api_key: Optional[str] = None):
        key = (api_key or GEMINI_API_KEY).strip()
        if not key:
            raise ValueError("GEMINI_API_KEY is missing. Please set it in your environment or .env file.")
        self.client = genai.Client(api_key=key)
        self.text_model = TEXT_MODEL
        self.image_model = IMAGE_MODEL

    def generate_post_and_prompt(self, article: Article) -> GenerationResult:
        """
        Generates a high-engagement LinkedIn post in technical Arabic and an
        English prompt for Imagen 3 based on the supplied article.
        """
        logger.info("Generating Arabic LinkedIn post for: '%s'", article.title)

        system_instruction = (
            "You are Mohamed Elbaloty, an elite Technology Leader, Principal AI & Software Architect, "
            "and authoritative industry voice specializing in Artificial Intelligence, FinTech (التقنية المالية), "
            "and PropTech (التقنية العقارية) across Saudi Arabia and the GCC (Gulf Cooperation Council) region.\n"
            "Your audience comprises senior founders, CTOs, fintech and proptech executives, venture capitalists (VCs), "
            "banking leaders, real estate developers, and software engineering managers.\n\n"
            "CORE MISSION:\n"
            "You will be given a breaking news article covering AI, FinTech, PropTech, or GCC/Saudi tech transformation. "
            "You must read it critically, grasp the underlying engineering, financial, and strategic significance, "
            "and produce:\n"
            "1. 'linkedin_post': An authoritative, viral, and deeply detailed LinkedIn post (1,500 to 2,500 characters) in clear, modern Arabic blended naturally with standard English technical/business terminology. Do NOT write a superficial summary! Provide deep architectural analysis, regulatory/market context, and actionable takeaways.\n"
            "2. 'telegram_caption': A punchy, condensed version of the post (strictly under 950 characters) suitable as a single Telegram photo caption.\n"
            "3. 'image_prompt': A bespoke editorial infographic prompt for Google's Nano Banana Pro model.\n\n"
            "LINKEDIN POST ARCHITECTURE (ARABIC WITH ENGLISH TERMS, 1500-2500 CHARACTERS):\n"
            "- 🚀 The Hook: A bold, curiosity-igniting opening statement that cuts through hype. State what just fundamentally changed in AI, FinTech, or PropTech.\n"
            "- 🌍 Strategic Context & Regional Alignment: Connect the news to the broader landscape—especially how it impacts the Saudi market (Vision 2030, SAMA sandbox, CMA, REGA / الهيئة العامة للعقار) and the GCC digital economy.\n"
            "- 🔬 Architectural & Operational Breakdown: 4 to 5 structured, high-value bullet points analyzing the mechanics under the hood "
            "(e.g., open banking APIs, digital escrow, property valuation AI, tokenization & fractional ownership, test-time compute, inference latency, credit scoring models, payments orchestration). Explain concrete metrics, protocols, or unit economics.\n"
            "- 💼 Engineering & Business Implications: What this means practically for software teams, product leaders, and fintech/proptech founders building in Saudi Arabia and the Gulf.\n"
            "- 💬 Provocative Discussion Question (CTA): A strategic technical or business trade-off question directed at tech leaders, founders, and investors to drive high-caliber debate in the comments.\n"
            "- 📌 Source Attribution: Clearly state the news source at the end:\n"
            "  '📌 المصدر: [اسم المصدر - Source Name] | [عنوان الخبر المرجعي]'\n"
            "- 🏷️ Hashtags: Include targeted hashtags for Saudi, GCC, FinTech, and PropTech:\n"
            "  #فنتك #بروب_تك #التقنية_العقارية #التقنية_المالية #السعودية #رؤية_السعودية_2030 #Fintech #Proptech #SaudiTech #GCC #AI #SoftwareEngineering\n\n"
            "IMAGE PROMPT DIRECTIVE (LINKEDIN TECHNICAL INFOGRAPHIC FOR NANO BANANA PRO 🍌):\n"
            "Craft a bespoke English prompt for Google Flow's Nano Banana Pro model instructing it to create a professional LinkedIn tech infographic:\n"
            "- Command: 'Create a professional LinkedIn tech infographic and visual design about: [Exact News Headline / FinTech / PropTech / AI Breakthrough]'\n"
            "- News Summary: 'News Summary: [2 to 3 detailed, concrete sentences summarizing the exact news event and technical/economic implications]'\n"
            "- Structured Visual Sections: 'Visual Layout: [Describe 3 structured concept cards, system flowcharts, financial data cards, or architecture blocks visualizing the key aspects]'\n"
            "- Design Aesthetics: 'Design Style: Sleek modern corporate tech design for LinkedIn, clean visual hierarchy, data visualization cards, elegant modern typography, high-contrast dark slate aesthetic with glowing cyan and gold accent indicators, premium presentation slide layout, 16:9 widescreen composition.'\n"
        )

        user_content = (
            f"Article Title: {article.title}\n"
            f"Source: {article.source}\n"
            f"Publication Date: {article.published_at}\n"
            f"Summary/Content: {article.summary}\n"
            f"Reference URL: {article.link}\n\n"
            "Please generate the output according to the requested schema."
        )

        candidate_text_models = [
            self.text_model,
            "gemini-3.5-flash",
            "gemini-3.5-flash-lite",
            "gemini-3-flash-preview",
            "gemini-3.6-flash",
        ]
        # Deduplicate while preserving order
        candidate_text_models = list(dict.fromkeys(candidate_text_models))

        last_error = None
        for model_name in candidate_text_models:
            try:
                logger.info("Attempting text generation with model: %s", model_name)
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=user_content,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.7,
                        response_mime_type="application/json",
                        response_schema=GenerationResult,
                    ),
                )

                # Parse response
                raw_text = response.text.strip()
                data = json.loads(raw_text)
                result = GenerationResult(**data)
                logger.info("Successfully generated LinkedIn post and image prompt with %s.", model_name)
                return result

            except Exception as e:
                logger.warning("Generation with %s encountered an issue: %s", model_name, str(e)[:150])
                last_error = e
                continue

        logger.error("All text candidate models failed. Last error: %s", last_error, exc_info=True)
        raise last_error

    def _generate_fallback_image(self, prompt: str, target_path: Path, title: str = "AI BREAKTHROUGH") -> Path:
        """
        Creates a sleek, high-resolution 16:9 editorial tech graphic using PIL
        when the Imagen API endpoint is unavailable (e.g. quota or free-tier restrictions).
        """
        from PIL import ImageDraw, ImageFont
        width, height = 1280, 720
        # Dark modern slate gradient background
        img = Image.new("RGB", (width, height), color=(13, 17, 23))
        draw = ImageDraw.Draw(img)

        # Draw decorative tech grid lines
        grid_color = (25, 35, 50)
        for x in range(0, width, 40):
            draw.line([(x, 0), (x, height)], fill=grid_color, width=1)
        for y in range(0, height, 40):
            draw.line([(0, y), (width, y)], fill=grid_color, width=1)

        # Draw glowing accent banner card
        card_margin = 60
        draw.rectangle(
            [(card_margin, card_margin), (width - card_margin, height - card_margin)],
            outline=(56, 189, 248),
            width=2,
        )

        # Decorative glowing corner brackets
        bracket_len = 30
        for cx, cy in [
            (card_margin, card_margin),
            (width - card_margin, card_margin),
            (card_margin, height - card_margin),
            (width - card_margin, height - card_margin),
        ]:
            dx = bracket_len if cx == card_margin else -bracket_len
            dy = bracket_len if cy == card_margin else -bracket_len
            draw.line([(cx, cy), (cx + dx, cy)], fill=(168, 85, 247), width=4)
            draw.line([(cx, cy), (cx, cy + dy)], fill=(168, 85, 247), width=4)

        # Header tag
        draw.text(
            (card_margin + 40, card_margin + 40),
            "[ AI INTELLIGENCE PIPELINE // EDITORIAL UPDATE ]",
            fill=(56, 189, 248),
        )

        # Topic summary text
        clean_desc = prompt.replace("\n", " ").strip()
        if len(clean_desc) > 180:
            clean_desc = clean_desc[:177] + "..."

        draw.text(
            (card_margin + 40, height // 2 - 40),
            clean_desc,
            fill=(241, 245, 249),
        )

        # Footer hashtags
        draw.text(
            (card_margin + 40, height - card_margin - 60),
            "#AI  #SoftwareEngineering  #AgenticAI  #TechBreakthrough",
            fill=(148, 163, 184),
        )

        img.save(target_path, format="JPEG", quality=95)
        logger.info("Generated sleek editorial fallback image at %s", target_path)
        return target_path

    def _generate_flux_image(self, prompt: str, target_path: Path) -> Path:
        """
        Generates an ultra-realistic 16:9 AI image using FLUX.1 (state-of-the-art open visual model)
        as an automatic high-fidelity alternative.
        """
        import urllib.parse
        import requests
        logger.info("Generating cinematic AI visual with FLUX.1...")
        encoded = urllib.parse.quote(prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded}?model=flux&width=1280&height=720&nologo=true"
        response = requests.get(url, timeout=45)
        if response.status_code == 200 and len(response.content) > 1000:
            with open(target_path, "wb") as f:
                f.write(response.content)
            logger.info("FLUX.1 image generated and saved successfully to %s", target_path)
            return target_path
        raise RuntimeError(f"FLUX.1 generation returned status {response.status_code}")

    def _generate_gflow_image(self, prompt: str, target_path: Path) -> Path:
        """
        Generates an image directly through Google Flow Pro using the true 'Nano Banana Pro 🍌' model.
        """
        from flow_banana import generate_flow_banana_pro
        logger.info("Attempting image generation via Google Flow Pro with 'Nano Banana Pro 🍌'...")
        return generate_flow_banana_pro(prompt, target_path)

    def generate_image(self, prompt: str, article_id: str, output_dir: Path = IMAGES_DIR) -> Path:
        """
        Generates an ultra high-quality studio technical visual using Google's Nano Banana Pro model
        either via Google Flow Pro direct session or Google GenAI API fallback.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{article_id[:16]}.jpg"
        target_path = output_dir / filename

        from image_watermark import stamp_author_branding

        # 1. Absolute First Priority: True Google Flow Pro 'Nano Banana Pro 🍌' model
        try:
            raw_path = self._generate_gflow_image(prompt, target_path)
            return stamp_author_branding(raw_path)
        except Exception as e:
            logger.warning("Google Flow Nano Banana Pro generation failed: %s. Falling back to Google GenAI API...", str(e)[:150])

        # 2. Second Priority: Google GenAI API Image models (Nano Banana Pro / DeepMind)
        candidate_models = [
            "nano-banana-pro-preview",
            "gemini-3-pro-image",
            self.image_model,
            "gemini-3.1-flash-image",
        ]
        candidate_models = list(dict.fromkeys(candidate_models))

        for model_name in candidate_models:
            logger.info("Generating studio visual with %s...", model_name)
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                    ),
                )

                if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
                    for part in response.candidates[0].content.parts:
                        if hasattr(part, "inline_data") and part.inline_data and part.inline_data.data:
                            img = Image.open(io.BytesIO(part.inline_data.data))
                            img.save(target_path, format="JPEG", quality=95)
                            logger.info("Google Studio image successfully saved to %s (size: %s)", target_path, img.size)
                            return stamp_author_branding(target_path)
            except Exception as e:
                logger.warning("Generation with %s encountered an issue: %s", model_name, str(e)[:150])
                continue

        # If Google models fail, use FLUX.1
        try:
            raw_path = self._generate_flux_image(prompt, target_path)
            return stamp_author_branding(raw_path)
        except Exception as e:
            logger.warning("FLUX.1 generation encountered an issue (%s). Falling back to graphic.", str(e))
            raw_path = self._generate_fallback_image(prompt, target_path)
            return stamp_author_branding(raw_path)


def create_ai_bundle(article: Article, skip_image: bool = False) -> Dict[str, any]:
    """
    Convenience orchestrator for generating post copy, image prompt, and optionally generating the image file.
    Returns a dictionary containing the post text, hook, image prompt, and image file path (or None if skip_image=True).
    """
    generator = AIGenerator()
    content_result = generator.generate_post_and_prompt(article)
    image_path = None
    if not skip_image:
        image_path = generator.generate_image(content_result.image_prompt, article.id)

    return {
        "article": article,
        "short_hook": content_result.short_hook,
        "post_text": content_result.linkedin_post,
        "linkedin_post": content_result.linkedin_post,
        "telegram_caption": content_result.telegram_caption,
        "image_prompt": content_result.image_prompt,
        "image_path": image_path,
    }

