#!/usr/bin/env python3
"""备考打卡工具 - 用爱打造的备考助手 💕"""

import json
import os
import random
import sqlite3
import secrets
import requests
import jwt
from datetime import datetime, date, timedelta
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

APP_DIR = Path("/root/xiaomei-checkin")
DB_FILE = APP_DIR / "xiaomei.db"
IMAGES_DIR = APP_DIR / "images"
OLD_DATA_FILE = APP_DIR / "data.json"

XIAOMI_API_KEY = os.getenv("AI_API_KEY", "")
XIAOMI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.xiaomimimo.com/v1/chat/completions")
AI_MODEL = os.getenv("AI_MODEL", "mimo-v2-flash")

# 学生姓名（用于 AI prompt）
STUDENT_NAME = os.getenv("STUDENT_NAME", "")
# AI 鼓励 prompt，{name} 会被替换为 STUDENT_NAME
AI_PROMPT = os.getenv("AI_PROMPT", "你是一个温柔体贴的人，给正在认真备考的{name}一句温暖的鼓励，20字以内，积极向上")

# 登录密码（从环境变量读取，默认 123456）
LOGIN_PASSWORD = os.getenv("LOGIN_PASSWORD", "123456")
# JWT 密钥（不设置则每次重启会重新生成，之前的 token 会失效）
JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_hex(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_DAYS = 7

# 图片配置
MAX_IMAGE_SIZE = 20 * 1024 * 1024  # 20MB（前端已压缩，这里放宽松）
COMPRESS_QUALITY = 85
MAX_IMAGE_DIMENSION = 2000
THUMB_SIZE = (300, 300)

app = FastAPI(title="备考打卡 💕", version="1.0.0")
security = HTTPBearer(auto_error=False)


# ========== 认证 ==========
def create_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(days=JWT_EXPIRE_DAYS)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="未登录")
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效的登录凭证")


BACKUP_ENCOURAGEMENTS = [
    "今天也很棒！每一份努力都不会白费 💕",
    "你认真学习的样子真好看 🌙",
    "每一页书都是通向未来的路，加油 ❤️",
    "目标在前方等着你，你一定可以的！✨",
    "今天的努力，是明天惊喜的铺垫 💪",
    "坚持就是胜利，你已经很棒了！🌸",
    "熬过这段日子，美好就在前方 🏠",
    "你的努力大家都看在眼里，你是最棒的！🌟",
    "努力终将开花结果 🌺",
    "等到上岸那天，一定要好好庆祝！🎂",
    "你是最努力最优秀的人！👑",
    "每一次打卡，都是进步的脚印 💌",
    "相信自己，你比想象中更强大！💖",
    "今天的你比昨天更优秀了一点点 ✨",
    "认真备考的你闪闪发光呢！⭐",
]


def get_db():
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            subject TEXT NOT NULL,
            content TEXT,
            is_makeup INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stats (
            key TEXT PRIMARY KEY,
            value INTEGER DEFAULT 0
        )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_date ON records(date)")
    
    cursor.execute("""
        INSERT OR IGNORE INTO stats (key, value) VALUES 
        ('zhice_days', 0), ('jiaoji_days', 0), ('total_days', 0), ('streak', 0)
    """)
    
    conn.commit()
    conn.close()


def migrate_old_data():
    if not OLD_DATA_FILE.exists():
        return
    
    try:
        with open(OLD_DATA_FILE, "r", encoding="utf-8") as f:
            old_data = json.load(f)
        
        records = old_data.get("records", [])
        if not records:
            return
        
        conn = get_db()
        cursor = conn.cursor()
        
        for record in records:
            date_str = record.get("date")
            zhice = record.get("zhice")
            if zhice:
                cursor.execute("""
                    INSERT INTO records (date, subject, content, is_makeup)
                    VALUES (?, ?, ?, ?)
                """, (date_str, "zhice", zhice.get("content", ""), 1 if zhice.get("is_makeup") else 0))
            
            jiaoji = record.get("jiaoji")
            if jiaoji:
                cursor.execute("""
                    INSERT INTO records (date, subject, content, is_makeup)
                    VALUES (?, ?, ?, ?)
                """, (date_str, "jiaoji", jiaoji.get("content", ""), 1 if jiaoji.get("is_makeup") else 0))
        
        stats = old_data.get("stats", {})
        for key, value in stats.items():
            cursor.execute("UPDATE stats SET value = ? WHERE key = ?", (value, key))
        
        conn.commit()
        conn.close()
        OLD_DATA_FILE.rename(OLD_DATA_FILE.with_suffix(".json.migrated"))
        print(f"✅ 迁移完成：{len(records)} 条记录")
    except Exception as e:
        print(f"⚠️ 迁移失败：{e}")


def calc_stats() -> dict:
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT date, subject FROM records ORDER BY date")
    rows = cursor.fetchall()
    
    daily_records = {}
    for row in rows:
        date_str = row['date']
        if date_str not in daily_records:
            daily_records[date_str] = set()
        daily_records[date_str].add(row['subject'])
    
    zhice_days = sum(1 for subjects in daily_records.values() if 'zhice' in subjects)
    jiaoji_days = sum(1 for subjects in daily_records.values() if 'jiaoji' in subjects)
    total_days = len(daily_records)
    
    streak = 0
    if daily_records:
        check_date = date.today()
        for i in range(len(daily_records)):
            check_str = check_date.isoformat()
            if check_str in daily_records:
                streak += 1
                check_date = check_date.fromordinal(check_date.toordinal() - 1)
            else:
                break
    
    cursor.execute("UPDATE stats SET value = ? WHERE key = ?", (zhice_days, 'zhice_days'))
    cursor.execute("UPDATE stats SET value = ? WHERE key = ?", (jiaoji_days, 'jiaoji_days'))
    cursor.execute("UPDATE stats SET value = ? WHERE key = ?", (total_days, 'total_days'))
    cursor.execute("UPDATE stats SET value = ? WHERE key = ?", (streak, 'streak'))
    
    conn.commit()
    conn.close()
    
    return {
        "zhice_days": zhice_days,
        "jiaoji_days": jiaoji_days,
        "total_days": total_days,
        "streak": streak
    }


def get_encouragement() -> str:
    """尝试用 AI 生成鼓励语，失败则使用内置鼓励语"""
    if not XIAOMI_API_KEY:
        return random.choice(BACKUP_ENCOURAGEMENTS)

    try:
        prompt = AI_PROMPT.replace("{name}", STUDENT_NAME) if STUDENT_NAME else AI_PROMPT.replace("{name}", "TA")
        response = requests.post(
            XIAOMI_BASE_URL,
            headers={
                "Authorization": f"Bearer {XIAOMI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": AI_MODEL,
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": "TA刚完成了今天的打卡，给一句鼓励"}
                ],
                "max_tokens": 100
            },
            timeout=3
        )
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
    except Exception:
        pass
    return random.choice(BACKUP_ENCOURAGEMENTS)


def compress_image(image_data: bytes, max_size: int = MAX_IMAGE_DIMENSION) -> bytes:
    """压缩图片"""
    from io import BytesIO
    from PIL import Image
    
    img = Image.open(BytesIO(image_data))
    if img.mode in ('RGBA', 'LA', 'P'):
        img = img.convert('RGB')
    
    width, height = img.size
    if width > max_size or height > max_size:
        ratio = min(max_size / width, max_size / height)
        new_size = (int(width * ratio), int(height * ratio))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
    
    output = BytesIO()
    img.save(output, format='JPEG', quality=COMPRESS_QUALITY, optimize=True)
    return output.getvalue()


def create_thumbnail(image_data: bytes, size: tuple = THUMB_SIZE) -> bytes:
    """创建缩略图"""
    from io import BytesIO
    from PIL import Image
    
    img = Image.open(BytesIO(image_data))
    if img.mode in ('RGBA', 'LA', 'P'):
        img = img.convert('RGB')
    
    img.thumbnail(size, Image.Resampling.LANCZOS)
    output = BytesIO()
    img.save(output, format='JPEG', quality=75, optimize=True)
    return output.getvalue()


def save_image(image_data: bytes, date_str: str) -> tuple:
    """保存图片，返回 (原图路径, 缩略图路径)"""
    import uuid
    
    date_dir = IMAGES_DIR / date_str
    date_dir.mkdir(parents=True, exist_ok=True)
    
    file_id = uuid.uuid4().hex[:12]
    
    compressed = compress_image(image_data)
    image_path = date_dir / f"{file_id}.jpg"
    image_path.write_bytes(compressed)
    
    thumb_data = create_thumbnail(compressed)
    thumb_path = date_dir / f"{file_id}_thumb.jpg"
    thumb_path.write_bytes(thumb_data)
    
    return str(image_path.relative_to(APP_DIR)), str(thumb_path.relative_to(APP_DIR))


@app.on_event("startup")
async def startup():
    init_db()
    migrate_old_data()
    calc_stats()


@app.get("/", response_class=HTMLResponse)
async def root():
    index_path = APP_DIR / "index.html"
    return index_path.read_text(encoding="utf-8")


@app.post("/api/login")
async def login(request: Request):
    """登录接口 - 验证密码返回 JWT"""
    data = await request.json()
    password = data.get("password", "")
    if password == LOGIN_PASSWORD:
        token = create_token({"sub": "user"})
        return {"status": "ok", "token": token, "expires_in": JWT_EXPIRE_DAYS * 86400}
    return {"status": "error", "message": "密码不对哦~"}


@app.get("/api/check")
async def auth_check(user=Depends(verify_token)):
    """检查 token 是否有效"""
    return {"status": "ok"}


@app.post("/api/checkin")
async def checkin(request: Request, user=Depends(verify_token)):
    """打卡接口 - 支持可选图片"""
    content_type = request.headers.get("content-type", "")
    
    # 判断是JSON还是FormData
    if "application/json" in content_type:
        data = await request.json()
        subject = data.get("subject")
        content = data.get("content", "")
        image_data = None
    else:
        form = await request.form()
        subject = form.get("subject")
        content = form.get("content", "")
        image_file = form.get("image")
        image_data = await image_file.read() if image_file else None
    
    today = date.today().isoformat()
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM records WHERE date = ? AND subject = ?", (today, subject))
    if cursor.fetchone():
        conn.close()
        return {"status": "error", "message": f"今天已经打过{'职测' if subject == 'zhice' else '教基'}的卡啦~"}
    
    image_path = None
    thumb_path = None
    
    # 如果有图片，处理图片
    if image_data:
        if len(image_data) > MAX_IMAGE_SIZE:
            conn.close()
            return {"status": "error", "message": "图片太大啦，最大10MB哦~"}
        try:
            image_path, thumb_path = save_image(image_data, today)
        except Exception as e:
            conn.close()
            return {"status": "error", "message": f"图片处理失败：{str(e)}"}
    
    cursor.execute("""
        INSERT INTO records (date, subject, content, image_path, thumb_path, is_makeup)
        VALUES (?, ?, ?, ?, ?, 0)
    """, (today, subject, content, image_path, thumb_path))
    
    conn.commit()
    conn.close()
    
    stats = calc_stats()
    encouragement = get_encouragement()
    
    return {
        "status": "ok",
        "message": f"{'职测' if subject == 'zhice' else '教基'}打卡成功！💕",
        "stats": stats,
        "encouragement": encouragement
    }


@app.post("/api/makeup")
async def makeup(request: Request, user=Depends(verify_token)):
    """补打卡接口 - 支持可选图片"""
    content_type = request.headers.get("content-type", "")
    
    # 判断是JSON还是FormData
    if "application/json" in content_type:
        data = await request.json()
        target_date = data.get("date")
        subjects = data.get("subjects", [])
        content = data.get("content", "")
        image_data = None
    else:
        form = await request.form()
        target_date = form.get("date")
        subjects_str = form.get("subjects", "")
        subjects = [s.strip() for s in subjects_str.split(",") if s.strip()]
        content = form.get("content", "")
        image_file = form.get("image")
        image_data = await image_file.read() if image_file else None
    
    today = date.today().isoformat()
    if target_date >= today:
        return {"status": "error", "message": "不能补打今天或未来的卡哦~"}
    
    conn = get_db()
    cursor = conn.cursor()
    
    image_path = None
    thumb_path = None
    
    # 如果有图片，处理图片
    if image_data:
        if len(image_data) > MAX_IMAGE_SIZE:
            conn.close()
            return {"status": "error", "message": "图片太大啦，最大10MB哦~"}
        try:
            image_path, thumb_path = save_image(image_data, target_date)
        except Exception as e:
            conn.close()
            return {"status": "error", "message": f"图片处理失败：{str(e)}"}
    
    success_subjects = []
    for subject in subjects:
        cursor.execute("SELECT id FROM records WHERE date = ? AND subject = ?", (target_date, subject))
        if cursor.fetchone():
            continue
        
        cursor.execute("""
            INSERT INTO records (date, subject, content, image_path, thumb_path, is_makeup)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (target_date, subject, content if content else "补打卡 ✓", image_path, thumb_path))
        
        success_subjects.append("职测" if subject == "zhice" else "教基")
    
    conn.commit()
    conn.close()
    
    if not success_subjects:
        return {"status": "error", "message": "这些科目都已经打过卡啦~"}
    
    stats = calc_stats()
    subjects_str = "、".join(success_subjects)
    
    return {
        "status": "ok",
        "message": f"补打{subjects_str}成功！💕",
        "stats": stats
    }


@app.get("/api/records")
async def get_records(month: str = None, user=Depends(verify_token)):
    conn = get_db()
    cursor = conn.cursor()
    
    if month:
        cursor.execute("""
            SELECT * FROM records WHERE date LIKE ? ORDER BY date DESC, created_at DESC
        """, (f"{month}%",))
    else:
        cursor.execute("SELECT * FROM records ORDER BY date DESC, created_at DESC LIMIT 100")
    
    rows = cursor.fetchall()
    conn.close()
    
    records = []
    for row in rows:
        records.append({
            "id": row["id"],
            "date": row["date"],
            "subject": row["subject"],
            "content": row["content"],
            "is_makeup": bool(row["is_makeup"]),
            "created_at": row["created_at"]
        })
    
    return {"status": "ok", "records": records}


@app.get("/api/stats")
async def get_stats(user=Depends(verify_token)):
    stats = calc_stats()
    return {"status": "ok", "stats": stats}


@app.get("/api/calendar/{year_month}")
async def get_calendar(year_month: str, user=Depends(verify_token)):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT date, subject, content, is_makeup 
        FROM records WHERE date LIKE ? ORDER BY date, created_at
    """, (f"{year_month}%",))
    
    rows = cursor.fetchall()
    conn.close()
    
    calendar = {}
    for row in rows:
        date_str = row['date']
        if date_str not in calendar:
            calendar[date_str] = []
        calendar[date_str].append({
            "subject": row['subject'],
            "content": row['content'],
            "is_makeup": bool(row['is_makeup'])
        })
    
    return {"status": "ok", "calendar": calendar}


@app.get("/api/data")
async def get_data(user=Depends(verify_token)):
    """获取所有数据（records + stats）"""
    conn = get_db()
    cursor = conn.cursor()
    
    # 获取记录
    cursor.execute("SELECT * FROM records ORDER BY date DESC, created_at DESC LIMIT 100")
    rows = cursor.fetchall()
    conn.close()
    
    # 按日期分组，转换为前端期望的格式
    daily_records = {}
    for row in rows:
        date_str = row["date"]
        if date_str not in daily_records:
            daily_records[date_str] = {"date": date_str}
        
        daily_records[date_str][row["subject"]] = {
            "content": row["content"],
            "is_makeup": bool(row["is_makeup"]),
            "time": row["created_at"],
            "image_path": row["image_path"],
            "thumb_path": row["thumb_path"]
        }
    
    records = list(daily_records.values())
    
    # 获取统计
    stats = calc_stats()
    
    return {
        "records": records,
        "stats": stats
    }


@app.get("/api/image/{path:path}")
async def get_image(path: str):
    """获取图片"""
    from fastapi.responses import FileResponse
    
    image_path = APP_DIR / path
    if not image_path.exists():
        return JSONResponse(status_code=404, content={"status": "error", "message": "图片不存在"})
    
    return FileResponse(
        str(image_path),
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=80)
