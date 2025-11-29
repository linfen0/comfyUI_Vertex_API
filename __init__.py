from .auth_node import VertexAIAuth
from .image_node import VertexGeminiImageGenerator
from .text_node import VertexGeminiTextGenerator
from .config_nodes import VertexGenerationConfig, VertexSaveConfig, VertexLoadConfig

NODE_CLASS_MAPPINGS = {
    "VertexAIAuth": VertexAIAuth,
    "VertexGeminiImageGenerator": VertexGeminiImageGenerator,
    "VertexGeminiTextGenerator": VertexGeminiTextGenerator,
    "VertexGenerationConfig": VertexGenerationConfig,
    "VertexSaveConfig": VertexSaveConfig,
    "VertexLoadConfig": VertexLoadConfig
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "VertexAIAuth": "Vertex AI Auth/Config",
    "VertexGeminiImageGenerator": "Vertex AI Image (Gemini 3/Imagen)",
    "VertexGeminiTextGenerator": "Vertex AI Text (Gemini LLM)",
    "VertexGenerationConfig": "Vertex Generation Config",
    "VertexSaveConfig": "Vertex Save Config",
    "VertexLoadConfig": "Vertex Load Config"
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
