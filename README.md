# 养创智寻｜Render 云端部署版

本目录是从用户提供的最终版项目适配得到的 GitHub / Render 部署包。

## 1. 模型分工

- **DeepSeek**：负责所有文本类任务，包括创业对话、养老科技创新机会识别、证据分析、创新方案生成、产品价值评估等。
- **Agnes AI**：仅负责产品外观图片生成，通过后端 `/image` 接口代理调用。Agnes Key 不会写入浏览器端。

当前 Agnes 图像请求沿用项目原有接口协议：`POST {AGNES_BASE_URL}/images/generations`，请求字段为 `model`、`prompt`、`size`、`n`。请在正式上线前用 Agnes 服务商提供的账号和文档核实 Base URL、模型 ID、鉴权方式及返回格式；不同套餐或版本可能有差异。

## 2. 目录结构

```text
养创智寻-Render部署版/
├── index.html                 # 原最终版前端
├── server.py                  # Python 后端（已适配云端监听和同源访问）
├── agent_tools.py             # 外部证据检索工具
├── graph_store.py             # 证据图谱读取
├── evidence_graph.json.gz     # 证据关联图谱
├── .env.example               # 环境变量模板，不含真实密钥
├── .gitignore                 # 忽略 .env、缓存等文件
├── requirements.txt           # 当前项目仅用 Python 标准库
├── render.yaml                # Render Blueprint 配置
└── README.md                  # 本说明
```

未放入部署包的内容：真实 `.env`、原始数据压缩包、`__pycache__`、Windows 本地启动脚本、诊断脚本和数据重建脚本。线上运行需要的 `index.html` 与 `evidence_graph.json.gz` 已保留。

## 3. 上传 GitHub

建议先创建 **Private** 仓库。解压本压缩包后，在 PowerShell 进入项目目录执行：

```powershell
git init
git add .
git status
```

确认待提交清单中没有 `.env`、API Key、原始数据包后执行：

```powershell
git commit -m "Prepare Render deployment"
git branch -M main
git remote add origin https://github.com/你的用户名/仓库名.git
git push -u origin main
```

`index.html` 文件较大（约 33 MB），建议使用 Git 命令行上传，不建议用 GitHub 网页端逐个上传。

## 4. Render 部署

1. 登录 https://render.com/ ，选择 **New → Blueprint**（或 New → Web Service）。
2. 连接 GitHub 并选择刚才的仓库。
3. 如果使用 Blueprint，Render 会读取根目录 `render.yaml`；确认创建 Web Service。
4. 在 Render 服务的 **Environment** 页面填写密钥：
   - `LLM_API_KEY`：DeepSeek API Key
   - `LLM_MODEL`：你的 DeepSeek 账号当前可用的模型 ID
   - `AGNES_API_KEY`：Agnes AI 图像生成 API Key
5. 其他配置已写入 `render.yaml`。Render 自动提供 `PORT`，后端会监听 `0.0.0.0:$PORT`。
6. 等待 Deploy 完成，在 Events / Logs 确认启动成功。
7. 打开 Render 分配的 `https://服务名.onrender.com` 网址。

不要把任何真实 API Key 写入 `render.yaml`、`.env.example`、`index.html` 或 GitHub 提交记录。

## 5. 环境变量说明

| 变量 | 用途 |
|---|---|
| `LLM_API_MODE=chat_completions` | DeepSeek Chat Completions 接口模式 |
| `LLM_BASE_URL=https://api.deepseek.com` | DeepSeek API 基础地址 |
| `LLM_API_KEY` | DeepSeek 密钥（Render Secret） |
| `LLM_MODEL` | DeepSeek 模型 ID，需按账号权限填写 |
| `LLM_JSON_MODE=true` | 请求 JSON 结构化输出 |
| `LLM_MAX_OUTPUT_TOKENS=12000` | 文本模型输出上限，需与模型能力及账号限制相容 |
| `AGNES_API_KEY` | Agnes 图像 API 密钥（Render Secret） |
| `AGNES_BASE_URL` | Agnes 图像 API 基础地址 |
| `AGNES_IMAGE_MODEL` | Agnes 图像模型 ID |
| `HOST=0.0.0.0` | 云端监听所有网卡 |
| `PORT` | Render 自动注入，不要手动固定 |

本地开发可复制 `.env.example` 为 `.env`，填写密钥后运行 `python server.py --open`。本地 `.env` 不要提交。

## 6. 上线后检查

- 首页：`https://你的域名/`
- 健康检查：`https://你的域名/health`

健康检查会返回 `configured`（DeepSeek Key 与模型是否已填写）和 `image_configured`（Agnes Key 是否已填写）。这两个状态只代表配置存在，不代表服务商实际调用成功。

建议依次测试：创业对话 / 机会识别、创新方案生成、价值评估、证据图谱查询、Agnes 产品外观图生成。Agnes 图像生成失败不应影响 DeepSeek 文本分析功能。

## 7. 重要限制与安全提示

1. **服务休眠**：Render 免费实例可能在空闲后休眠，首次访问可能需要等待启动；比赛演示或持续公开访问建议评估付费实例。
2. **公开接口额度**：当前版本的模型接口对外开放。任何知道网址的人都可能触发文本或图片生成并消耗 API 额度。正式公开前建议增加访问认证、速率限制和调用额度控制；不要将网址视为访问控制。
3. **密钥安全**：如果旧 `.env` 曾经被推送到任何 Git 仓库，应在 DeepSeek / Agnes 后台轮换密钥。仅删除文件不能清除 Git 历史。
4. **图片返回方式**：现有前端按服务返回的图片 URL 或 Base64 图片数据展示。若 Agnes 返回格式或异步任务协议与现有接口不同，需要按其最新 API 文档调整适配代码。
5. **持久化**：Render 服务本地文件系统不应作为用户长期数据存储。当前部署包保留静态知识图谱；用户浏览器侧收藏/历史仍按现有前端机制工作。若未来要跨设备同步收藏或保存生成图片，应增加数据库或对象存储。
6. **证据边界**：知识库证据、模型推断和待验证假设应继续区分；不要将相似度或覆盖指数解释为市场成功率。

## 8. 本次适配内容

- 后端监听地址可由 `HOST` 控制；Render 环境设置为 `0.0.0.0`，端口读取 Render 注入的 `PORT`。
- 将本地 Host / Origin 校验调整为同源校验，允许 Render HTTPS 域名访问，同时拒绝跨站 POST 请求。
- DeepSeek 默认接口模式调整为 `chat_completions`，默认 Base URL 调整为 `https://api.deepseek.com`。
- 健康检查增加 `image_configured` 状态。
- 增加 `.env.example`、`.gitignore`、`requirements.txt`、`render.yaml` 与本部署说明。
- 不修改原有创新方案、产品价值评估、证据检索等业务流程。
