"""
Image Generation Service using Google Gemini.
Generates topic-relevant academic images for assignment sections.
Compatible with google-generativeai==0.8.4
"""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from typing import List, Optional

import google.generativeai as genai

from app.utils.file_helpers import ensure_directory, generate_unique_filename
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class GeneratedImage:
    section_title: str
    image_path: str
    caption: str
    prompt: str
    success: bool = True
    error: str = ""


class ImageGenerationService:
    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.0-flash-exp",
        storage_path: str = "storage/images",
    ) -> None:
        genai.configure(api_key=api_key)
        self._api_key = api_key
        self._storage_path = os.path.abspath(storage_path)
        ensure_directory(self._storage_path)
        logger.info("ImageGenerationService initialized | storage=%s", self._storage_path)

    def _generate_single_image(self, prompt: str) -> Optional[bytes]:
        """
        Generate image using available Gemini APIs.
        Tries multiple approaches for compatibility with google-generativeai 0.8.4
        """

        # ── Attempt 1: Imagen 3 via REST (most reliable) ──
        try:
            import requests
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"imagen-3.0-generate-002:predict?key={self._api_key}"
            )
            payload = {
                "instances": [{"prompt": prompt}],
                "parameters": {
                    "sampleCount": 1,
                    "aspectRatio": "16:9",
                    "safetyFilterLevel": "block_only_high",
                    "personGeneration": "allow_adult",
                },
            }
            resp = requests.post(url, json=payload, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                predictions = data.get("predictions", [])
                if predictions and "bytesBase64Encoded" in predictions[0]:
                    logger.info("Imagen 3 REST success")
                    return base64.b64decode(predictions[0]["bytesBase64Encoded"])
            else:
                logger.warning("Imagen 3 REST failed | status=%d | %s", resp.status_code, resp.text[:100])
        except Exception as e:
            logger.warning("Imagen 3 REST error | %s", str(e)[:100])

        # ── Attempt 2: Gemini 2.0 Flash with image output ──
        try:
            model = genai.GenerativeModel("gemini-2.0-flash-exp")
            response = model.generate_content(
                contents=[{
                    "role": "user",
                    "parts": [{
                        "text": (
                            f"Create a detailed, photorealistic educational illustration showing: {prompt}. "
                            "The image should be professional, clear, and suitable for an academic document."
                        )
                    }]
                }],
                generation_config=genai.GenerationConfig(
                    temperature=0.4,
                    candidate_count=1,
                ),
            )
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "inline_data") and part.inline_data and part.inline_data.data:
                        logger.info("Gemini Flash image success")
                        return base64.b64decode(part.inline_data.data)
        except Exception as e:
            logger.warning("Gemini Flash image error | %s", str(e)[:100])

        # ── Attempt 3: Gemini 1.5 Flash ──
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(
                f"Generate an educational illustration for: {prompt}",
                generation_config=genai.GenerationConfig(candidate_count=1),
            )
            if response.candidates:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "inline_data") and part.inline_data and part.inline_data.data:
                        logger.info("Gemini 1.5 Flash image success")
                        return base64.b64decode(part.inline_data.data)
        except Exception as e:
            logger.warning("Gemini 1.5 Flash error | %s", str(e)[:100])

        logger.warning("All image generation attempts failed for prompt: %s", prompt[:60])
        return None

    def generate_section_images(
        self,
        sections: List[dict],
        assignment_id: str,
    ) -> List[GeneratedImage]:
        logger.info(
            "Generating images | assignment=%s | sections=%d",
            assignment_id, len(sections)
        )
        results: List[GeneratedImage] = []

        for idx, section in enumerate(sections):
            prompt = section.get("image_prompt", "")
            title = section.get("title", f"Section {idx + 1}")

            if not prompt:
                logger.info("Skipping image (no prompt) | section='%s'", title)
                continue

            try:
                image_bytes = self._generate_single_image(prompt)

                if image_bytes:
                    filename = generate_unique_filename(
                        "png", prefix=f"img_{assignment_id[:8]}"
                    )
                    # Always save as absolute path
                    filepath = os.path.join(self._storage_path, filename)
                    with open(filepath, "wb") as f:
                        f.write(image_bytes)

                    logger.info(
                        "Image saved | section='%s' | path=%s | size=%d bytes",
                        title, filepath, len(image_bytes)
                    )
                    results.append(GeneratedImage(
                        section_title=title,
                        image_path=filepath,          # absolute path
                        caption=f"Figure {idx + 1}: {title}",
                        prompt=prompt,
                        success=True,
                    ))
                else:
                    logger.warning("No image bytes returned | section='%s'", title)
                    results.append(GeneratedImage(
                        section_title=title, image_path="", caption="",
                        prompt=prompt, success=False, error="No image data returned",
                    ))

            except Exception as e:
                logger.warning(
                    "Image generation failed (graceful skip) | section='%s' | error=%s",
                    title, str(e)[:120]
                )
                results.append(GeneratedImage(
                    section_title=title, image_path="", caption="",
                    prompt=prompt, success=False, error=str(e),
                ))

        success_count = sum(1 for r in results if r.success)
        logger.info(
            "Image generation done | success=%d / total=%d",
            success_count, len(results)
        )
        return results
