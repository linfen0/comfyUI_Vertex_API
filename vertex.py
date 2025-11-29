import torch
import numpy as np
import json
import requests
import base64
import io
import os
import time
from PIL import Image

# 尝试导入 google 库
try:
    from google.oauth2 import service_account
    import google.auth
    import google.auth.transport.requests
    HAS_GOOGLE_AUTH = True
except ImportError:
    HAS_GOOGLE_AUTH = False

def get_dynamic_model_list(location="us-central1"):
    """
    尝试从环境中读取凭证并连接 Google Cloud API 获取模型列表。
    如果失败，返回预设的常用模型列表。
    """
    default_models = [
        "gemini-3-pro-image-preview",
        "imagen-3.0-generate-001",
        "gemini-1.5-pro-002",
        "gemini-1.5-flash-002",
        "gemini-1.0-pro-vision",
    ]

    if not HAS_GOOGLE_AUTH:
        return default_models

    # 检查环境变量是否存在，避免不必要的报错
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") and not os.environ.get("GOOGLE_CLOUD_PROJECT"):
        return default_models

    try:
        # 尝试获取默认凭证
        credentials, project_id = google.auth.default()
        
        if not project_id:
            return default_models

        auth_req = google.auth.transport.requests.Request()
        credentials.refresh(auth_req)
        token = credentials.token

        url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/publishers/google/models"
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            model_ids = [m['name'].split('/')[-1] for m in models if 'name' in m]
            gen_models = [m for m in model_ids if 'gemini' in m or 'imagen' in m]
            if gen_models:
                return sorted(list(set(gen_models + default_models)))
    except Exception as e:
        print(f"Vertex AI Node: Failed to fetch dynamic model list ({e}). Using default list.")
    
    return default_models

# 在模块加载时获取一次模型列表
CACHED_MODELS = get_dynamic_model_list()

class VertexBase:
    """基础类，处理认证和通用逻辑"""
    def get_access_token(self, service_account_path):
        if not HAS_GOOGLE_AUTH:
            raise ImportError("请安装 google-auth 库: pip install google-auth requests")
        
        # 1. 优先使用传入的 JSON 路径
        if service_account_path and os.path.exists(service_account_path) and os.path.isfile(service_account_path):
            scopes = ['https://www.googleapis.com/auth/cloud-platform']
            creds = service_account.Credentials.from_service_account_file(service_account_path, scopes=scopes)
            auth_req = google.auth.transport.requests.Request()
            creds.refresh(auth_req)
            return creds.token, creds.project_id
        
        # 2. 其次尝试使用环境默认凭证
        print("Vertex AI: No JSON file provided or found, trying default credentials...")
        creds, project_id = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)
        return creds.token, project_id

    def pil2tensor(self, image):
        return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)

class VertexAIAuth:
    """
    【认证配置节点】
    统一管理 Project ID, Location 和 Service Account
    """
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "project_id": ("STRING", {"default": "auto-detect-if-empty"}),
                "location": ("STRING", {"default": "us-central1"}),
            },
            "optional": {
                "service_account_json": ("STRING", {"default": "", "placeholder": "Path to JSON (leave empty for env vars)"}),
            }
        }

    RETURN_TYPES = ("VERTEX_CONFIG",)
    RETURN_NAMES = ("vertex_config",)
    FUNCTION = "create_config"
    CATEGORY = "VertexAI"

    def create_config(self, project_id, location, service_account_json=""):
        return ({
            "project_id": project_id,
            "location": location,
            "service_account_json": service_account_json
        },)

class VertexGeminiImageGenerator(VertexBase):
    """
    【图像生成专用节点】
    输入现在需要连接 'vertex_config'
    """
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "vertex_config": ("VERTEX_CONFIG",), # 新增：必须连接配置节点
                "prompt": ("STRING", {"multiline": True, "default": "A cinematic shot of a cyberpunk detective"}),
                "model_name": (CACHED_MODELS, {"default": "gemini-3-pro-image-preview"}),
                "aspect_ratio": (["1:1", "16:9", "9:16", "4:3", "3:4", "21:9"], {"default": "1:1"}),
                "person_generation": (["ALLOW_ADULT", "ALLOW_ALL", "DONT_ALLOW"], {"default": "ALLOW_ADULT"}),
                "output_resolution": (["1K", "2K", "4K"], {"default": "1K"}),
                "safety_filter_level": (["BLOCK_NONE", "BLOCK_ONLY_HIGH", "BLOCK_MEDIUM_AND_ABOVE", "OFF"], {"default": "OFF"}),
            },
            "optional": {
                "negative_prompt": ("STRING", {"multiline": True, "default": ""}),
                "custom_model_name": ("STRING", {"default": "", "placeholder": "Override model name manually"}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image", "raw_response")
    FUNCTION = "generate_image"
    CATEGORY = "VertexAI"

    def generate_image(self, vertex_config, prompt, model_name, aspect_ratio, person_generation, output_resolution, safety_filter_level, negative_prompt="", custom_model_name=""):
        
        # 从 config 解包参数
        project_id = vertex_config.get("project_id")
        location = vertex_config.get("location")
        service_account_json = vertex_config.get("service_account_json")

        # 优先使用自定义模型名
        target_model = custom_model_name if custom_model_name.strip() else model_name
        
        token, auth_project_id = self.get_access_token(service_account_json)
        # 如果用户没填 project_id，使用凭证中的
        final_project_id = project_id if project_id != "auto-detect-if-empty" else auth_project_id

        url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{final_project_id}/locations/{location}/publishers/google/models/{target_model}:generateContent"

        threshold_val = safety_filter_level
        
        final_prompt = prompt
        if negative_prompt:
             final_prompt += f" --negative_prompt={negative_prompt}"

        payload = {
            "contents": [{"role": "user", "parts": [{"text": final_prompt}]}],
            "generationConfig": {
                "temperature": 1.0,
                "maxOutputTokens": 32768,
                "topP": 0.95,
                "aspectRatio": aspect_ratio,
                "personGeneration": person_generation,
                "outputResolution": output_resolution,
                "outputFormat": "png",
                "responseModalities": ["TEXT", "IMAGE"],
                "safetyCatFilters": [
                    {"category": "HATE_SPEECH", "threshold": threshold_val},
                    {"category": "DANGEROUS_CONTENT", "threshold": threshold_val},
                    {"category": "SEXUALLY_EXPLICIT_CONTENT", "threshold": threshold_val},
                    {"category": "HARASSMENT_CONTENT", "threshold": threshold_val}
                ]
            }
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }

        print(f"VertexAI Image Request to: {target_model}")
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=120)
            response.raise_for_status()
            result = response.json()
        except requests.exceptions.RequestException as e:
            msg = f"API Error: {e}"
            if e.response: msg += f"\nBody: {e.response.text}"
            raise Exception(msg)

        output_images = []
        try:
            candidates = result.get('candidates', [])
            if not candidates:
                 raise Exception(f"No content returned. Check Safety filters. Response: {json.dumps(result)}")

            parts = candidates[0].get('content', {}).get('parts', [])
            for part in parts:
                if 'inlineData' in part:
                    data_str = part['inlineData'].get('data')
                    if data_str:
                        img = Image.open(io.BytesIO(base64.b64decode(data_str))).convert('RGB')
                        output_images.append(self.pil2tensor(img))
            
            if not output_images:
                print("Warning: No image found in response, creating black placeholder.")
                output_images.append(self.pil2tensor(Image.new('RGB', (512, 512), color='black')))

            return (torch.cat(output_images, dim=0), json.dumps(result, indent=2))

        except Exception as e:
            raise Exception(f"Parsing Error: {e}\nRaw: {json.dumps(result)}")


class VertexGeminiTextGenerator(VertexBase):
    """
    【文本生成专用节点】
    输入现在需要连接 'vertex_config'
    """
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "vertex_config": ("VERTEX_CONFIG",), # 新增
                "prompt": ("STRING", {"multiline": True, "default": "Explain quantum physics in simple terms."}),
                "model_name": (CACHED_MODELS, {"default": "gemini-1.5-pro-002"}),
                "temperature": ("FLOAT", {"default": 0.7, "min": 0.0, "max": 2.0, "step": 0.1}),
                "max_tokens": ("INT", {"default": 8192, "min": 1, "max": 1000000}),
                "safety_filter_level": (["BLOCK_NONE", "BLOCK_ONLY_HIGH", "BLOCK_MEDIUM_AND_ABOVE", "OFF"], {"default": "BLOCK_NONE"}),
            },
            "optional": {
                "system_instruction": ("STRING", {"multiline": True, "default": "You are a helpful assistant."}),
                "custom_model_name": ("STRING", {"default": "", "placeholder": "Override model name manually"}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "generate_text"
    CATEGORY = "VertexAI"

    def generate_text(self, vertex_config, prompt, model_name, temperature, max_tokens, safety_filter_level, system_instruction="", custom_model_name=""):
        
        # 从 config 解包参数
        project_id = vertex_config.get("project_id")
        location = vertex_config.get("location")
        service_account_json = vertex_config.get("service_account_json")

        target_model = custom_model_name if custom_model_name.strip() else model_name
        token, auth_project_id = self.get_access_token(service_account_json)
        final_project_id = project_id if project_id != "auto-detect-if-empty" else auth_project_id

        url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{final_project_id}/locations/{location}/publishers/google/models/{target_model}:generateContent"

        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "topP": 0.95,
                "responseModalities": ["TEXT"]
            },
            "safetySettings": [
                 {"category": "HATE_SPEECH", "threshold": safety_filter_level},
                 {"category": "DANGEROUS_CONTENT", "threshold": safety_filter_level},
                 {"category": "SEXUALLY_EXPLICIT_CONTENT", "threshold": safety_filter_level},
                 {"category": "HARASSMENT_CONTENT", "threshold": safety_filter_level}
            ]
        }

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }

        print(f"VertexAI Text Request to: {target_model}")

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            
            output_text = ""
            candidates = result.get('candidates', [])
            if candidates:
                parts = candidates[0].get('content', {}).get('parts', [])
                for part in parts:
                    if 'text' in part:
                        output_text += part['text']
            
            return (output_text,)

        except Exception as e:
            err = f"Error: {e}"
            if hasattr(e, 'response') and e.response:
                err += f"\n{e.response.text}"
            return (err,)

NODE_CLASS_MAPPINGS = {
    "VertexAIAuth": VertexAIAuth,
    "VertexGeminiImageGenerator": VertexGeminiImageGenerator,
    "VertexGeminiTextGenerator": VertexGeminiTextGenerator
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "VertexAIAuth": "Vertex AI Auth/Config",
    "VertexGeminiImageGenerator": "Vertex AI Image (Gemini 3/Imagen)",
    "VertexGeminiTextGenerator": "Vertex AI Text (Gemini LLM)"
}