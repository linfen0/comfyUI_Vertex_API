import os
import time
import json
from .utils import list_config_files, save_config_file, load_config_file

class VertexGenerationConfig:
    """
    【生成参数配置节点】
    """
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "temperature": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 2.0, "step": 0.1}),
                "top_p": ("FLOAT", {"default": 0.95, "min": 0.0, "max": 1.0, "step": 0.01}),
                "thinkingLevel":(["HIGH", "LOW"], {"default": "HIGH"}),
                "max_output_tokens": ("INT", {"default": 8192, "min": 1, "max": 32768}),
                "safety_filter_level": (["BLOCK_NONE", "BLOCK_ONLY_HIGH", "BLOCK_MEDIUM_AND_ABOVE", "OFF"], {"default": "OFF"}),
                "response_modalities": (["TEXT_AND_IMAGE", "TEXT", "IMAGE"], {"default": "TEXT_AND_IMAGE"}),
            },
            "optional": {
                "system_instruction": ("STRING", {"multiline": True, "default": ""}),
            }
        }

    RETURN_TYPES = ("GENERATION_CONFIG",)
    RETURN_NAMES = ("generation_config",)
    FUNCTION = "create_config"
    CATEGORY = "VertexAI/Config"

    def create_config(self, temperature, top_p, max_output_tokens, safety_filter_level, response_modalities, system_instruction="",thinkingLevel=""):
        
        modalities = ["TEXT", "IMAGE"]
        if response_modalities == "TEXT":
            modalities = ["TEXT"]
        elif response_modalities == "IMAGE":
            modalities = ["IMAGE"]
            
        config = {
            "temperature": temperature,
            "topP": top_p,
            "thinkingConfig": {
            "thinkingLevel": thinkingLevel
        },
            "maxOutputTokens": max_output_tokens,
            "responseModalities": modalities,
            "safetySettings": [
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": safety_filter_level},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": safety_filter_level},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": safety_filter_level},
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": safety_filter_level}
            ]
        }
        
        if system_instruction:
            config["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }
            
        return (config,)

class VertexSaveConfig:
    """
    【保存配置节点】
    保存 Vertex Config 和 Generation Config 到 JSON 文件
    """
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "filename_prefix": ("STRING", {"default": "vertex_config"}),
            },
            "optional": {
                "vertex_config": ("VERTEX_CONFIG",),
                "generation_config": ("GENERATION_CONFIG",),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("filepath",)
    FUNCTION = "save_config"
    CATEGORY = "VertexAI/Config"
    OUTPUT_NODE = True

    def save_config(self, filename_prefix, vertex_config=None, generation_config=None):
        timestamp = int(time.time())
        filename = f"{timestamp}_{filename_prefix}.json"
        
        data = {}
        if vertex_config:
            data["vertex_config"] = vertex_config
        if generation_config:
            data["generation_config"] = generation_config
            
        filepath = save_config_file(filename, data)
        print(f"Vertex AI: Config saved to {filepath}")
        return (filepath,)

class VertexLoadConfig:
    """
    【加载配置节点】
    从 JSON 文件加载配置
    """
    @classmethod
    def INPUT_TYPES(s):
        files = list_config_files()
        if not files:
            files = ["none"]
        return {
            "required": {
                "config_file": (files,),
            }
        }

    RETURN_TYPES = ("VERTEX_CONFIG", "GENERATION_CONFIG")
    RETURN_NAMES = ("vertex_config", "generation_config")
    FUNCTION = "load_config"
    CATEGORY = "VertexAI/Config"

    def load_config(self, config_file):
        if config_file == "none":
            return ({}, {})
            
        data = load_config_file(config_file)
        return (data.get("vertex_config", {}), data.get("generation_config", {}))
