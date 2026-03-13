import logging
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)

@dataclass
class SafetySetting:
    category: str
    threshold: str

@dataclass
class ModelConfig:
    model_name: str
    safety_settings: List[SafetySetting] = field(default_factory=list)

@dataclass
class ImageConfig:
    aspect_ratio: str = '1:1'
    number_of_images: int = 1

class GeneratedImage:
    def __init__(self, data=None):
        self._data = data

    def save(self, path: str):
        # In a real scenario, this would save actual image data.
        # For now, it's a mock that might need actual integration if not just a placeholder.
        logger.info(f"Mock: Saving image to {path}")
        with open(path, "wb") as f:
            f.write(b"MOCK IMAGE DATA")

class ImageGenerationResponse:
    def __init__(self, images: List[GeneratedImage]):
        self.images = images

class ImageGenerationModel:
    def __init__(self, config: ModelConfig):
        self.config = config

    def generate_image(self, prompt: str, config: ImageConfig) -> ImageGenerationResponse:
        logger.info(f"Mock: Generating image for prompt: {prompt[:50]}...")
        # Return a mock image
        return ImageGenerationResponse(images=[GeneratedImage()])
