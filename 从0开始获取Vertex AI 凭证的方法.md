# **第一阶段：环境与账号准备**
## **注意：在开始前你必须注册一个谷歌账号，开通并激活GCP服务，且虚拟卡会被拒绝，这意味着你至少一张实体外币卡来激活GCP**
## **步骤 1：创建项目并启用 API**

### **1. 登录 Google Cloud Console**
访问控制台：  
👉 https://console.cloud.google.com/

---

### **2. 新建项目**
1. 点击顶部导航栏的 **项目选择器** → **新建项目**
2. 填写项目信息：
   - **项目名称**：`vertex-ai-curl-test`
   - **项目 ID（自动生成）**：例如 `vertex-ai-curl-test-83920`  
     > ⚠️ **务必记录项目 ID**，后续所有命令都需要用到。
3. 点击 **创建**

---

### **3. 激活计费**
1. 打开左侧 **结算 (Billing)**  
2. 点击 **关联结算账号**
3. 选择企业结算账号或个人信用卡账号

---

### **4. 启用 Vertex AI API**
1. 顶部搜索栏输入：`Vertex AI API`
2. 进入 API 详情页（Marketplace）
3. 点击蓝色按钮 **启用 (Enable)**

> 该操作会自动启用：  
> - **Service Usage API**  
> - **AI Platform API**  
> 并为项目分配初始配额。

---

## **步骤 2：创建服务账号 (IAM)**

### **1. 打开服务账号设置**
导航路径：  
**IAM 和管理 (IAM & Admin) → 服务账号 (Service Accounts)**

---

### **2. 创建服务账号**
点击右上角：**+ 创建服务账号**

填写以下信息：
- **服务账号名称**：`gemini-api-caller`
- **服务账号 ID**：  
  `gemini-api-caller@vertex-ai-curl-test-83920.iam.gserviceaccount.com`
- **描述**：用于 Curl 测试 Gemini API 的专用账号

点击 **创建并继续**

---

### **3. 授予权限**
在“选择角色”栏搜索：


选择：
- ✅ `Vertex AI User (roles/aiplatform.user)`

> ⚠️ 请注意：  
> - ❌ Viewer 权限不足  
> - ❌ Admin 权限过大，不推荐

点击 **继续 → 完成**

---

## **步骤 3：配置验证方式**

你可以选择两种方式之一：

- **方式一（推荐）：Service Account JSON（更安全）**  
- **方式二（最方便）：API Key**

---

# **方式一（推荐）：Service Account JSON 身份验证**

### **1. 下载密钥文件**
1. 在服务账号列表中点击刚创建的 `gemini-api-caller`
2. 切换到顶部标签 **密钥 (Keys)**
3. 点击：
   **添加密钥 (Add Key) → 创建新密钥 (Create new key)**  
4. 选择：
   - **JSON**
5. 点击 **创建**

浏览器会下载一个 `.json` 文件。

> 你只需将该 JSON 文件的路径配置到对应的节点即可。

---

# **方式二（最方便）：API Key 验证**

打开页面：  
👉 https://console.cloud.google.com/vertex-ai/studio/multimodal

操作步骤：
1. 左侧点击 **获取 API 密钥**
2. 创建新的 API Key
3. 复制生成的 **API KEY** 到节点即可使用


