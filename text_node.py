import requests
from .base import VertexBase
from .utils import CACHED_MODELS

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
                "generation_config": ("GENERATION_CONFIG",),
                "system_instruction": ("STRING", {"multiline": True, "default": "You are a helpful assistant."}),
                "custom_model_name": ("STRING", {"default": "", "placeholder": "Override model name manually"}),
            }
        }

    RETURN_TYPES = ("STRING", "GENERATION_CONFIG")
    RETURN_NAMES = ("text", "generation_config")
    FUNCTION = "generate_text"
    CATEGORY = "VertexAI"

    def generate_text(self, vertex_config, prompt, model_name, temperature, max_tokens, safety_filter_level, generation_config=None, system_instruction="", custom_model_name=""):
        
        # 从 config 解包参数
        project_id = vertex_config.get("project_id")
        location = vertex_config.get("location")
        service_account_json = vertex_config.get("service_account_json")

        target_model = custom_model_name if custom_model_name.strip() else model_name
        token, auth_project_id = self.get_access_token(service_account_json)
        final_project_id = project_id if project_id != "auto-detect-if-empty" else auth_project_id

        url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{final_project_id}/locations/{location}/publishers/google/models/{target_model}:generateContent"

        # 默认 Safety Settings (从 widget 读取)
        threshold_val = safety_filter_level
        safety_settings_payload = [
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": threshold_val},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": threshold_val},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": threshold_val},
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": threshold_val}
        ]

        # 如果提供了 generation_config，覆盖默认参数
        if generation_config:
            temperature = generation_config.get("temperature", temperature)
            max_tokens = generation_config.get("max_output_tokens", max_tokens)
            # top_p = generation_config.get("top_p", 0.95) # 文本节点原本没有 top_p 输入，这里可以隐式支持
            
            # safetySettings 参数
            if "safetySettings" in generation_config:
                safety_settings_payload = generation_config["safetySettings"]

        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "topP": generation_config.get("top_p", 0.95) if generation_config else 0.95,
                "responseModalities": generation_config.get("responseModalities", ["TEXT"]) if generation_config else ["TEXT"]
            },
            "safetySettings": safety_settings_payload
        }

        # systemInstruction: 优先使用 config 中的，如果没有则使用 widget 输入
        if generation_config and "systemInstruction" in generation_config:
             payload["systemInstruction"] = generation_config["systemInstruction"]
        elif system_instruction:
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
            
            # 返回使用的配置
            used_config = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
                "top_p": payload["generationConfig"]["topP"]
            }

            return (output_text, used_config)

        except Exception as e:
            err = f"Error: {e}"
            if hasattr(e, 'response') and e.response:
                err += f"\n{e.response.text}"
            return (err,)
