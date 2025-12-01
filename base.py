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
    def get_access_token(self, service_account_filename):
        if not HAS_GOOGLE_AUTH:
            raise ImportError("请安装 google-auth 库: pip install google-auth requests")
        #获取current_dir，并在其中创建key文件夹
        current_dir = os.path.dirname(os.path.abspath(__file__))
        key_dir = os.path.join(current_dir, "key")
        if not os.path.exists(key_dir):
            os.makedirs(key_dir)
        #构造service_account_path
        service_account_path = os.path.join(key_dir, service_account_filename)
       #获得其中标记的location
        with open(service_account_path, 'r') as f:
            service_account_json = json.load(f)
            location = service_account_json.get('location')
        if service_account_path and os.path.exists(service_account_path) and os.path.isfile(service_account_path):
            scopes = ['https://www.googleapis.com/auth/cloud-platform']
            creds = service_account.Credentials.from_service_account_file(service_account_path, scopes=scopes)
            auth_req = google.auth.transport.requests.Request()
            creds.refresh(auth_req)
            return location,creds.token, creds.project_id
        
        # 2. 其次尝试使用环境默认凭证
        print("Vertex AI: No JSON file provided or found, trying default credentials...")
        creds, project_id = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)
        return location,creds.token, project_id

    def pil2tensor(self, image):
        return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)
