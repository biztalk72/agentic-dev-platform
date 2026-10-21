"""VLM client: keyframe extraction + frame summarization (stub + optional real provider)."""
import base64
import json
import os
from pathlib import Path


class VLMClient:
    """Stub VLM that returns deterministic summaries. Swap for a real provider via env."""

    def __init__(self, provider: str | None = None):
        self.provider = provider or os.getenv("VLM_PROVIDER", "stub")

    def summarize_frame(self, frame_b64: str, context: str = "") -> dict:
        # Stub: deterministic scene summary for demo reproducibility
        return {
            "scene": "login page",
            "elements": ["email input", "password input", "submit button (disabled)"],
            "anomalies": ["layout shift on mobile width"],
            "confidence": 0.8,
        }

    def summarize_clip(self, video_path: Path, max_keyframes: int = 12) -> list[dict]:
        """Extract keyframes (stub: 1 representative frame) and summarize."""
        if not video_path.exists():
            return [self.summarize_frame("", "no video provided")]
        # In a real build: scene-change detection + 1fps sampling capped at max_keyframes
        return [self.summarize_frame(base64.b64encode(b"stub").decode(), f"clip: {video_path.name}")]
