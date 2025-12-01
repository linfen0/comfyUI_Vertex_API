import json
import requests
import base64
import io
import torch
from PIL import Image
from .base import VertexBase
from .utils import CACHED_MODELS, tensor_to_base64

class VertexGeminiImageGenerator(VertexBase):
    """
    【图像生成专用节点】
    支持多模态输入 (Image + Text) 和 API Key 认证
    """
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "vertex_config": ("VERTEX_CONFIG",),
                "prompt": ("STRING", {"multiline": True, "default": "A cinematic shot of a cyberpunk detective"}),
                "model_name": (CACHED_MODELS, {"default": "gemini-3-pro-image-preview"}),
                "aspect_ratio": (["1:1", "16:9", "9:16", "4:3", "3:4", "21:9"], {"default": "1:1"}),
                "person_generation": (["ALLOW_ADULT", "ALLOW_ALL", "DONT_ALLOW"], {"default": "ALLOW_ADULT"}),
                "output_resolution": (["1K", "2K", "4K"], {"default": "1K"}),
                "output_format": (["image/png", "image/jpeg"], {"default": "image/png"}),
            },
            "optional": {
                "image_input": ("IMAGE",), # 主要图片输入
                "image_2": ("IMAGE",),
                "image_3": ("IMAGE",),
                "image_4": ("IMAGE",),
                "generation_config": ("GENERATION_CONFIG",),
                "negative_prompt": ("STRING", {"multiline": True, "default": ""}),
                "custom_model_name": ("STRING", {"default": "", "placeholder": "Override model name manually"}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING", "GENERATION_CONFIG")
    RETURN_NAMES = ("image", "raw_response", "generation_config")
    FUNCTION = "generate_image"
    CATEGORY = "VertexAI"

    def generate_image(self, vertex_config, prompt, model_name, aspect_ratio, person_generation, output_resolution, output_format, image_input=None, image_2=None, image_3=None, image_4=None, generation_config=None, negative_prompt="", custom_model_name=""):
        
        # 1. 解包认证信息
        #优先从config.json中解包
        
        vertex_config_file = vertex_config.get("config_file")
        if vertex_config_file:
            from .utils import load_config_file
            loaded_config=load_config_file(vertex_config_file).get('vertex_config')
            project_id = loaded_config.get('project_id')
            service_account_json = loaded_config.get('service_account_json')
            api_key = loaded_config.get('api_key')
            
        else:
            project_id = vertex_config.get("project_id")
            service_account_json = vertex_config.get("service_account_json")
            api_key = vertex_config.get('api_key')

        target_model = custom_model_name if custom_model_name.strip() else model_name
        
        # 2. 确定 API URL 和 Headers
        if api_key:
            # 使用 API Key 方式
            url = f"https://aiplatform.googleapis.com/v1/publishers/google/models/{target_model}:streamGenerateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
        else:
            # 使用 OAuth 方式
            (location,token, auth_project_id) = self.get_access_token(service_account_json)
            
            url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{auth_project_id}/locations/{location}/publishers/google/models/{target_model}:streamGenerateContent"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8"
            }

        # 3. 构建 Contents (多模态)
        parts = [{"text": prompt}]
        if negative_prompt:
             parts[0]["text"] += f" --negative_prompt={negative_prompt}"
             
        # 处理所有图片输入
        all_images = [img for img in [image_input, image_2, image_3, image_4] if img is not None]
        
        for img_tensor in all_images:
            # 支持 batch 图片，但通常 ComfyUI 传进来的是 [B, H, W, C]
            for i in range(img_tensor.shape[0]):
                b64_img, mime_type = tensor_to_base64(img_tensor[i])
                parts.append({
                    "inlineData": {
                        "mimeType": mime_type,
                        "data": b64_img
                    }
                })

        contents = [{"role": "user", "parts": parts}]

        # 4. 构建 Generation Config
        # 默认值
        gen_config_payload = {
            "temperature": 1.0,
            "maxOutputTokens": 32768,
            "topP": 0.95,
            "responseModalities": ["TEXT", "IMAGE"],
            # imageConfig 必须由节点参数构建
            "imageConfig": {
                "aspectRatio": aspect_ratio,
                "imageSize": output_resolution,
                "personGeneration": person_generation,
                "imageOutputOptions": {
                    "mimeType": output_format
                }
            }
        }
        
        # 默认 Safety Settings (默认为 OFF)
        threshold_val = "OFF"
        safety_settings_payload = [
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": threshold_val},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": threshold_val},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": threshold_val}, 
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": threshold_val}
        ]
        
        # 如果有传入 config，则合并
        if generation_config:
            # 顶层参数
            for key in ["temperature", "topP","maxOutputTokens", "responseModalities"]:
                if key in generation_config:
                    gen_config_payload[key] = generation_config[key]
            
            # 注意：imageConfig 不再从 generation_config 读取，强制使用节点参数
                
            # safetySettings 参数
            if "safetySettings" in generation_config:
                safety_settings_payload = generation_config["safetySettings"]

        # 5. 构建完整 Payload
        payload = {
            "contents": contents,
            "generationConfig": gen_config_payload,
            "safetySettings": safety_settings_payload
        }
        
        # systemInstruction 参数 (从 config 读取)
        if generation_config and "systemInstruction" in generation_config:
            payload["systemInstruction"] = generation_config["systemInstruction"]

        print(f"VertexAI Image Request to: {target_model}")
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=120)
            #(payload)
            response.raise_for_status()
            # streamGenerateContent 返回的是列表（流式），但这里我们一次性接收
            # 或者是 JSON 数组，或者是一行行的 JSON
            # 注意：streamGenerateContent 接口返回的是一个 JSON 数组 [...]
            try:
                result_list = response.json()
                if isinstance(result_list, dict): # 兼容非流式接口返回
                    result_list = [result_list]
            except:
                # 尝试解析多行 JSON
                result_list = [json.loads(line) for line in response.text.splitlines() if line.strip()]
                
        except requests.exceptions.RequestException as e:
            msg = f"API Error: {e}"
            if e.response: msg += f"\nBody: {e.response.text}"
            raise Exception(msg)

        # 6. 解析结果
        output_images = []
        full_response_text = json.dumps(result_list, indent=2)
        
        for result in result_list:
            candidates = result.get('candidates', [])
            if not candidates: continue
        
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

        return (torch.cat(output_images, dim=0), full_response_text, gen_config_payload)
