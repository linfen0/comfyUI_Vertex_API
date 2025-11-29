import os
import json
from .utils import save_config_file, load_config_file

class VertexAIAuth:
    """
    【认证配置节点】
    统一管理 Project ID, Location 和 Service Account
    支持将 API Key 保存到本地配置文件，并自动清除输入框
    """
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "config_file": ("STRING", {"default": "vertex_config.json"}),
            },
            "optional": {
                "service_account_json": ("STRING", {"default": "", "placeholder": "Path to JSON (leave empty for env vars)"}),
                "api_key": ("STRING", {"default": "", "placeholder": "Optional: Enter to save, then clear"}),
            }
        }

    RETURN_TYPES = ("VERTEX_CONFIG",)
    RETURN_NAMES = ("vertex_config",)
    FUNCTION = "create_config"
    CATEGORY = "VertexAI"

    def create_config(self, config_file, service_account_json="", api_key=""):
        # 1. 加载现有配置
        saved_config = {}
        try:
            saved_data = load_config_file(config_file)
            saved_config = saved_data.get("vertex_config", {})
        except Exception as e:
            print(f"Vertex AI: Failed to load config {config_file}: {e}")

        # 2. 初始化配置 (使用默认值或已保存的值)
        # 默认 location 为 us-central1，project_id 为 auto-detect
        vertex_config = {
            "project_id": saved_config.get("project_id", "auto-detect-if-empty"),
            "location": saved_config.get("location", "us-central1"),
            "service_account_json": saved_config.get("service_account_json", ""),
            "api_key": saved_config.get("api_key", "")
        }

        # 3. 处理输入更新
        should_save = False
        
        has_valid_creds = vertex_config.get("api_key") or vertex_config.get("service_account_json") or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    
        
        if not api_key and not service_account_json and not vertex_config.get("api_key") and not vertex_config.get("service_account_json"):
             # 只有在真的没有任何凭证来源时才报错
            RED = "\033[31m"
            YELLOW = "\033[33m"
            CYAN = "\033[36m"
            RESET = "\033[0m"
            error_message = (
            f"{RED}Vertex AI Error: Credentials missing.{RESET}\n"
            f"Please refer to the following documentation to obtain the necessary {YELLOW}Credentials{RESET}:\n" 
            f"{CYAN}https://docs.cloud.google.com/vertex-ai/generative-ai/docs/start/api-keys{RESET}"
            )
            raise Exception(error_message)

        # 如果输入了新的 service_account_json，更新并标记保存
        if service_account_json:
            vertex_config["service_account_json"] = service_account_json
            should_save = True
            
        # 如果输入了新的 api_key，更新并标记保存
        if api_key:
            vertex_config["api_key"] = api_key
            should_save = True

        # 4. 保存配置 (如果需要)
        full_path = config_file # Default to input
        if should_save:
            try:
                # 保持原有的 generation_config 不变 (如果有)
                full_data = load_config_file(config_file)
                full_data["vertex_config"] = vertex_config
                # save_config_file 返回完整路径
                full_path = save_config_file(config_file, full_data)
                print(f"Vertex AI: Auth config saved to {full_path}")
            except Exception as e:
                print(f"Vertex AI: Failed to save config: {e}")

        # 5. 返回结果和 UI 更新指令
        # 如果刚刚保存了 API Key，则自动清除 UI 中的输入框，并更新 config_file 路径
        if api_key and api_key.strip('*'):
            return {
                "ui": {
                    "api_key": ["***********"],
                    "config_file": [full_path] # 自动填充保存后的完整路径
                }, 
                "result": (vertex_config,)
            }
        
        return (vertex_config,)
