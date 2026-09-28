"""
Smart Prompt Engineering Engine for Nano Banana Pro (Google Flow / Imagen 3).
Transforms news articles into tailored, world-class LinkedIn visual prompts
with dynamic archetypes, intelligent color palettes, and structured triptych cards.
Zero generic repetitions. Zero AI cliches.
"""

import json
import logging
from typing import Dict, Optional
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from config import GEMINI_API_KEY, TEXT_MODEL
from fetcher import Article

logger = logging.getLogger(__name__)


class SmartPromptResult(BaseModel):
    headline_en: str = Field(description="Punchy, authoritative English headline in uppercase for the visual banner.")
    sub_headline_en: str = Field(description="1-sentence English context line for the visual.")
    visual_archetype: str = Field(
        description="Best archetype: 'executive_infographic_board', 'cinematic_infrastructure_scene', 'isometric_systems_schematic', or 'hardware_macro_shot'."
    )
    theme_palette: str = Field(
        description="Tailored color palette: e.g. 'Saudi Emerald (#006C35) & Liquid Gold', 'Deep Royal Navy & Electric Cyan', 'Obsidian Slate & Warm Bronze', 'Graphite & Crimson Amber'."
    )
    prompt_for_nano_banana_pro: str = Field(
        description="The complete, masterclass English prompt crafted specifically for Nano Banana Pro on Google Flow (16:9 widescreen)."
    )
    negative_prompt: str = Field(
        description="Negative prompt to exclude artifacts, creepy robots, floating brains, and cartoon coins."
    )


class SmartPromptEngine:
    """Generates highly customized, story-specific visual prompts for Nano Banana Pro."""

    def __init__(self, api_key: Optional[str] = None):
        key = (api_key or GEMINI_API_KEY).strip()
        if not key:
            raise ValueError("GEMINI_API_KEY is required for SmartPromptEngine.")
        self.client = genai.Client(api_key=key)
        self.model = TEXT_MODEL

    def generate_smart_prompt(self, article: Article, sector_hint: Optional[str] = None) -> SmartPromptResult:
        """
        Analyzes the article and synthesizes an authoritative, non-cliche visual prompt for Nano Banana Pro.
        """
        logger.info("Synthesizing dynamic Nano Banana Pro prompt for: '%s'", article.title)

        system_instruction = (
            "You are a World-Class Executive Art Director and Information Designer specializing in "
            "viral, high-engagement visual assets for top technology leaders and VCs on LinkedIn.\n\n"
            "YOUR OBJECTIVE:\n"
            "Analyze the tech/business news article provided and create a customized, professional English visual prompt "
            "engineered specifically for Nano Banana Pro (Google Flow / Imagen 3).\n\n"
            "CRITICAL DESIGN RULES (NO GENERIC REPETITIONS):\n"
            "1. DYNAMIC IDENTITY: Every story must have its own unique visual identity. NEVER reuse the same generic 'frosted glass prism and titanium blocks' prompt!\n"
            "2. CHOOSE THE BEST VISUAL ARCHETYPE for the story:\n"
            "   - 'executive_infographic_board': Ideal for regulations, benchmarks, funding, or multi-step shifts. 3 structured horizontal cards (Left: Context/Old Way, Center: Technical Mechanism/Architecture, Right: Market Impact/Metrics) with crisp typography and vector-sharp schematics.\n"
            "   - 'cinematic_infrastructure_scene': Ideal for energy, data centers, smart cities, and physical tech. Photorealistic 8k render of the actual real-world infrastructure (e.g. high-voltage substation, liquid-cooled server cluster, smart city digital twin).\n"
            "   - 'isometric_systems_schematic': Ideal for software architecture, API gateways, security protocols, and payment orchestration. Clean isometric 3D platform with glowing laser data paths.\n"
            "   - 'hardware_macro_shot': Ideal for chip breakthroughs, silicon wafers, quantum hardware, or robotics sensors. Extreme macro studio photography with shallow depth of field.\n"
            "3. COLOR PALETTE HARMONY: Anchor the color palette in the story's domain:\n"
            "   - Saudi Arabia / GCC / SAMA: Deep Saudi Emerald Green (#006C35), Warm Desert Gold, Obsidian Slate.\n"
            "   - AI & Foundation Models / LLMs: Royal Midnight Navy, Electric Cyan, Ethereal Violet glow.\n"
            "   - FinTech & Payments: Dark Titanium Slate, Vivid Emerald Mint, Liquid Gold accents.\n"
            "   - PropTech & Real Estate: Obsidian Glass, Brushed Bronze, Warm Amber lighting.\n"
            "   - Cyber & Infrastructure: Dark Graphite, Laser Teal, Warning Amber accents.\n"
            "4. NANO BANANA PRO OPTIMIZATION:\n"
            "   - Use explicit uppercase headlines and card labels in quotation marks (Nano Banana Pro renders text beautifully).\n"
            "   - Request clean Dieter Rams / Apple / Stripe design aesthetics.\n"
            "   - Always specify 16:9 widescreen ratio.\n"
            "   - STRICTLY AVOID AI CLICHES: No creepy humanoid robots, no glowing translucent brains, no floating cartoon coins, no blurry generic stock photo suits."
        )

        user_content = (
            f"Article Title: {article.title}\n"
            f"Source: {article.source}\n"
            f"Sector/Category: {sector_hint or 'Tech & Innovation'}\n"
            f"Summary/Facts: {article.summary or ''}\n\n"
            "Craft the optimal visual strategy and Nano Banana Pro prompt according to the schema."
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.6,
                response_mime_type="application/json",
                response_schema=SmartPromptResult,
            ),
        )

        data = json.loads(response.text.strip())
        result = SmartPromptResult(**data)
        logger.info(
            "Smart prompt synthesized successfully! Archetype: '%s', Headline: '%s'",
            result.visual_archetype,
            result.headline_en,
        )
        return result


def build_dynamic_flow_prompt(article: Article, sector_hint: Optional[str] = None) -> str:
    """Convenience helper returning the final prompt string."""
    engine = SmartPromptEngine()
    result = engine.generate_smart_prompt(article, sector_hint)
    return result.prompt_for_nano_banana_pro
