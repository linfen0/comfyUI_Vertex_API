import os
import requests

# 尝试导入 google 库
try:
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
        "gemini-3.0-pro-preview",
        "gemini-2.5-flash-image",
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

def get_config_dir():
    """获取配置文件夹路径"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(current_dir, "config")
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    return config_dir

def list_config_files():
    """列出所有配置文件"""
    config_dir = get_config_dir()
    files = [f for f in os.listdir(config_dir) if f.endswith(".json")]
    return sorted(files, reverse=True)

def save_config_file(filename, data):
    """保存配置文件"""
    config_dir = get_config_dir()
    filepath = os.path.join(config_dir, filename)
    import json
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return filepath

def load_config_file(filename):
    """加载配置文件"""
    config_dir = get_config_dir()
    filepath = os.path.join(config_dir, filename)
    import json
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def tensor_to_base64(image_tensor):
    """
    Convert a single image tensor (C, H, W) or (H, W, C) to base64 string.
    Returns: (base64_string, mime_type)
    """
    from PIL import Image
    import io
    import base64
    import numpy as np
    
    # Handle batch dimension if present
    if len(image_tensor.shape) == 4:
        image_tensor = image_tensor[0]
        
    img_np = np.clip(255. * image_tensor.cpu().numpy(), 0, 255).astype(np.uint8)
    img = Image.fromarray(img_np)
    
    # Determine format based on channels (last dimension of numpy array)
    # ComfyUI tensors are usually [H, W, C]
    channels = img_np.shape[-1] if len(img_np.shape) == 3 else 1
    
    if channels == 4:
        fmt = "PNG"
        mime = "image/png"
    else:
        fmt = "JPEG"
        mime = "image/jpeg"
    
    buffered = io.BytesIO()
    # For JPEG, we can set quality
    if fmt == "JPEG":
        img.save(buffered, format=fmt, quality=90)
    else:
        img.save(buffered, format=fmt)
        
    return base64.b64encode(buffered.getvalue()).decode("utf-8"), mime
