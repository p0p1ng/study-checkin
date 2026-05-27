# 💕 备考打卡系统

一个温馨可爱的备考打卡小工具，支持每日打卡、补打卡、图片记录，还有 AI 生成的鼓励语～

为需要坚持备考的你（或你关心的人）量身打造 ✨

![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?logo=fastapi)

## ✨ 功能

- 📝 **每日打卡** — 职测 / 教基两科独立打卡
- 📅 **日历视图** — 一目了然的打卡记录
- 🔄 **补打卡** — 落下也能补回来
- 📸 **图片打卡** — 上传学习笔记/截图，自动压缩
- 🤖 **AI 鼓励** — 打卡后给你一句温暖的话（可选，支持 MiMo / OpenAI / DeepSeek 等）
- 🔒 **密码保护** — 简单的前端密码验证
- 📊 **学习统计** — 连续打卡天数、各科累计

## 🚀 快速部署

### 1. 安装依赖

```bash
pip install fastapi uvicorn requests Pillow python-dotenv PyJWT
```

### 2. 配置

```bash
# 复制配置模板
cp .env.example .env

# 编辑配置
vim .env
```

`.env` 中至少需要配置：

```env
STUDENT_NAME=你想要的名字
```

### 3. 修改密码

编辑 `.env` 文件：

```env
LOGIN_PASSWORD=你的新密码
```

> 密码存在服务端，前端看不到，安全 🔒

### 4. 启动

```bash
# 直接运行
python main.py

# 或用 systemd 守护运行（推荐）
sudo cp xiaomei-checkin.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now xiaomei-checkin
```

访问 `http://你的服务器IP` 即可～

## 🔧 配置说明

| 环境变量 | 必填 | 说明 |
|---------|------|------|
| `STUDENT_NAME` | ✅ | 学生姓名，显示在页面和 AI 鼓励语中 |
| `LOGIN_PASSWORD` | ✅ | 登录密码 |
| `JWT_SECRET` | ❌ | JWT 签名密钥，不设置则每次重启后 token 失效 |
| `AI_API_KEY` | ❌ | AI API 密钥，不配置则使用内置鼓励语 |
| `AI_BASE_URL` | ❌ | AI API 地址，默认为小米 MiMo |
| `AI_MODEL` | ❌ | AI 模型名，默认 `mimo-v2-flash` |
| `AI_PROMPT` | ❌ | 自定义 AI prompt，`{name}` 会替换为学生姓名 |
| `APP_DIR` | ❌ | 应用目录，默认为脚本所在目录 |

### 🤖 配置 AI 鼓励语

打卡成功后会随机显示一句鼓励语。你也可以接入 AI 生成更个性化的鼓励。

**第一步：选择 AI 服务**

只要兼容 OpenAI API 格式的服务都可以：

| 服务 | 获取 API Key | Base URL |
|------|-------------|----------|
| [小米 MiMo](https://mimo.xiaomi.com/) | 注册后获取 | `https://api.xiaomimimo.com/v1/chat/completions` |
| [DeepSeek](https://platform.deepseek.com/) | 注册后获取 | `https://api.deepseek.com/v1/chat/completions` |
| [SiliconFlow](https://siliconflow.cn/) | 注册后获取 | `https://api.siliconflow.cn/v1/chat/completions` |
| [OpenAI](https://platform.openai.com/) | 注册后获取 | `https://api.openai.com/v1/chat/completions` |

**第二步：配置 .env**

```env
# 学生姓名（替换 prompt 中的 {name}）
STUDENT_NAME=小美

# AI API 配置
AI_API_KEY=sk-你的密钥
AI_BASE_URL=https://api.deepseek.com/v1/chat/completions
AI_MODEL=deepseek-chat
```

**第三步（可选）：自定义鼓励语 Prompt**

默认 prompt 比较通用。如果你想定制风格，可以设置 `AI_PROMPT`：

```env
# 甜蜜情侣风
AI_PROMPT=你是{name}的对象，给正在备考的{name}一句甜蜜温暖的鼓励，20字以内

# 正经教练风
AI_PROMPT=你是一个严格的备考教练，给正在学习的{name}一句简短有力的激励，15字以内

# 搞笑朋友风  
AI_PROMPT=你是{name}的好朋友，用轻松幽默的方式鼓励{name}继续备考，20字以内

# 二次元风格
AI_PROMPT=用可爱的二次元语气给{name}一句备考鼓励，加上颜文字，20字以内
```

> `{name}` 会被自动替换为 `STUDENT_NAME` 的值。不设置 `STUDENT_NAME` 则替换为 "TA"。

不配置 `AI_API_KEY` 也没关系，系统会使用内置的 15 条鼓励语。

## 📁 项目结构

```
.
├── main.py              # 后端 FastAPI 应用
├── index.html           # 前端页面（单文件，含 CSS/JS）
├── .env.example         # 配置模板
├── .gitignore           # Git 忽略规则
└── README.md            # 本文件
```

运行后自动生成：

```
├── checkin.db           # SQLite 数据库
└── images/              # 上传的图片目录
```

## 🛠️ API 接口

所有 `/api/*` 接口需要 JWT 鉴权（`Authorization: Bearer <token>`），除以下接口外：

| 接口 | 方法 | 鉴权 | 说明 |
|------|------|------|------|
| `/` | GET | ❌ | 首页 |
| `/api/login` | POST | ❌ | 登录，返回 JWT token |
| `/api/check` | GET | ✅ | 检查 token 是否有效 |
| `/api/checkin` | POST | ✅ | 打卡（支持 JSON 和 FormData） |
| `/api/makeup` | POST | ✅ | 补打卡 |
| `/api/data` | GET | ✅ | 获取所有记录和统计 |
| `/api/records` | GET | ✅ | 获取记录列表 |
| `/api/stats` | GET | ✅ | 获取统计数据 |
| `/api/calendar/{yyyy-mm}` | GET | ✅ | 获取指定月份日历 |
| `/api/image/{path}` | GET | ❌ | 获取图片 |

## 💡 设计理念

- **单文件前端** — `index.html` 包含所有 CSS 和 JS，部署简单
- **SQLite 存储** — 无需额外数据库服务
- **前端压缩** — 图片在上传前自动压缩，节省流量和存储
- **AI 可选** — 不配置 API 也能正常使用，内置 15 条鼓励语

## 📄 License

MIT License

---

> 为在乎的人做一个小工具，也许就是最浪漫的事 💕
