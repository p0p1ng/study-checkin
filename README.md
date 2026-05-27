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
pip install fastapi uvicorn requests Pillow python-dotenv
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

编辑 `index.html`，找到这一行：

```javascript
const PASSWORD = '123456';  // ← 修改这里换成你的密码
```

把 `123456` 换成你想要的密码。

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
| `AI_API_KEY` | ❌ | AI API 密钥，不配置则使用内置鼓励语 |
| `AI_BASE_URL` | ❌ | AI API 地址，默认为小米 MiMo |
| `AI_MODEL` | ❌ | AI 模型名，默认 `mimo-v2-flash` |
| `AI_PROMPT` | ❌ | 自定义 AI prompt，`{name}` 会替换为学生姓名 |
| `APP_DIR` | ❌ | 应用目录，默认为脚本所在目录 |

### 支持的 AI 服务

只要兼容 OpenAI API 格式的服务都可以，例如：

- [小米 MiMo](https://mimo.xiaomi.com/) — 速度快，中文好
- [DeepSeek](https://platform.deepseek.com/) — 性价比高
- [OpenAI](https://platform.openai.com/) — GPT 系列
- [SiliconFlow](https://siliconflow.cn/) — 多模型聚合

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

| 接口 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 首页 |
| `/api/checkin` | POST | 打卡（支持 JSON 和 FormData） |
| `/api/makeup` | POST | 补打卡 |
| `/api/data` | GET | 获取所有记录和统计 |
| `/api/records` | GET | 获取记录列表 |
| `/api/stats` | GET | 获取统计数据 |
| `/api/calendar/{yyyy-mm}` | GET | 获取指定月份日历 |
| `/api/image/{path}` | GET | 获取图片 |

## 💡 设计理念

- **单文件前端** — `index.html` 包含所有 CSS 和 JS，部署简单
- **SQLite 存储** — 无需额外数据库服务
- **前端压缩** — 图片在上传前自动压缩，节省流量和存储
- **AI 可选** — 不配置 API 也能正常使用，内置 15 条鼓励语

## 📄 License

MIT License

---

> 为在乎的人做一个小工具，也许就是最浪漫的事 💕
