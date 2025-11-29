import os
import torch
import numpy as np
from .utils import HAS_GOOGLE_AUTH

if HAS_GOOGLE_AUTH:
    from google.oauth2 import service_account
    import google.auth
    import google.auth.transport.requests

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
