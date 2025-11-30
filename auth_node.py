import os
import json
from .utils import save_config_file, load_config_file
import time
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
            import sys
            # 导入 colorama 库
            from colorama import init, Fore, Style 

            # 在程序开始时初始化 colorama，这将使得 ANSI 颜色代码在 Windows 上也能工作
            init() 

            # 定义颜色代码 (使用 colorama 的常量更标准，但你也可以继续用你的 ANSI 字符串)
            # 推荐使用 colorama 的常量，因为它更可靠：
            RED = Fore.RED + Style.BRIGHT
            YELLOW = Fore.YELLOW
            CYAN = Fore.CYAN
            RESET = Style.RESET_ALL # 使用 Style.RESET_ALL 代替 \033[0m
            error_message = (
            f"{RED}Vertex AI Error: Credentials missing.{RESET}\n"
            f"Please refer to the following documentation to obtain the necessary {YELLOW}Credentials{RESET}:\n" 
            f"{CYAN}https://github.com/linfen0/comfyUI_Vertex_API/blob/master/%E4%BB%8E0%E5%BC%80%E5%A7%8B%E8%8E%B7%E5%8F%96Vertex%20AI%20%E5%87%AD%E8%AF%81%E7%9A%84%E6%96%B9%E6%B3%95.md{RESET}"
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
           
            #config_file为空则创建一个，格式为vertex_config+时间戳.json
            if not os.path.exists(config_file):
                #创建config文件夹
                config_dir="config"
                if not config_file:
                    os.makedirs("config", exist_ok=True)
                else:
                    os.makedirs(os.path.dirname(config_file), exist_ok=True)
                    config_dir=os.path.dirname(config_file)
                #创建文件
                config_file=config_dir+"/vertex_config_" + str(int(time.time())) + ".json"
                print(config_file)
                with open(config_file, "w",encoding="utf-8") as f:
                    json.dump("", f)
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
        # 如果刚刚保存了 API Key，则自动清除 UI 中的输入框，并更新 config_file 路
        
        return (vertex_config,)
