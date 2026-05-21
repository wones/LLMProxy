from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from config.database import engine, Base
from routes import config_routes, proxy_routes, parser_routes, log_routes
import os
import sys
import webbrowser
import time
import threading

Base.metadata.create_all(bind=engine)

app = FastAPI(title="LLM Proxy Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(config_routes.router)
app.include_router(proxy_routes.router)
app.include_router(parser_routes.router)
app.include_router(log_routes.router)

# 获取正确的路径
def get_frontend_path():
    if getattr(sys, 'frozen', False):
        # 如果是打包后的 exe
        base_path = sys._MEIPASS
        frontend_path = os.path.join(base_path, 'views')
        if not os.path.exists(frontend_path):
            frontend_path = os.path.join(os.path.dirname(sys.executable), 'views')
    else:
        # 开发环境 - 优先使用backend/views，其次使用frontend/views
        base_dir = os.path.dirname(os.path.abspath(__file__))
        frontend_path = os.path.join(base_dir, 'views')
        if not os.path.exists(frontend_path):
            frontend_path = os.path.join(base_dir, '..', 'frontend', 'views')
        frontend_path = os.path.normpath(frontend_path)
    return frontend_path

# 挂载静态文件
frontend_path = get_frontend_path()
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

# 页面路由
@app.get("/")
async def root():
    frontend_path = get_frontend_path()
    index_file = os.path.join(frontend_path, 'index.html')
    if os.path.exists(index_file):
        with open(index_file, 'r', encoding='utf-8') as f:
            content = f.read()
        return HTMLResponse(content=content, media_type='text/html; charset=utf-8')
    else:
        return HTMLResponse(content="""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM 代理服务</title>
</head>
<body>
    <h1>页面加载中...</h1>
</body>
</html>
        """, media_type='text/html; charset=utf-8')

@app.get("/config")
async def config_page():
    frontend_path = get_frontend_path()
    config_file = os.path.join(frontend_path, 'config.html')
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
        return HTMLResponse(content=content, media_type='text/html; charset=utf-8')
    else:
        return HTMLResponse(content="""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>配置管理</title>
</head>
<body>
    <h1>配置管理</h1>
</body>
</html>
        """, media_type='text/html; charset=utf-8')

@app.get("/logs")
async def logs_page():
    frontend_path = get_frontend_path()
    logs_file = os.path.join(frontend_path, 'logs.html')
    if os.path.exists(logs_file):
        with open(logs_file, 'r', encoding='utf-8') as f:
            content = f.read()
        return HTMLResponse(content=content, media_type='text/html; charset=utf-8')
    else:
        return HTMLResponse(content="""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>调用日志</title>
</head>
<body>
    <h1>调用日志</h1>
</body>
</html>
        """, media_type='text/html; charset=utf-8')

@app.get("/statistics")
async def statistics_page():
    frontend_path = get_frontend_path()
    stats_file = os.path.join(frontend_path, 'statistics.html')
    if os.path.exists(stats_file):
        with open(stats_file, 'r', encoding='utf-8') as f:
            content = f.read()
        return HTMLResponse(content=content, media_type='text/html; charset=utf-8')
    else:
        return HTMLResponse(content="""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>统计分析</title>
</head>
<body>
    <h1>统计分析</h1>
</body>
</html>
        """, media_type='text/html; charset=utf-8')

# 测试聊天路由 - 提供简单的模拟响应
from fastapi import Request
@app.post("/test-chat")
async def test_chat(request: Request):
    try:
        data = await request.json()
        message = data.get('message', '')
        # 简单的模拟响应，不调用其他服务
        return {
            "choices": [
                {
                    "message": {
                        "content": f"收到您的消息：「" + message + "」\n\n这是一个模拟响应！"
                    }
                }
            ]
        }
    except Exception as e:
        return {"error": str(e)}

def open_browser():
    """延迟打开浏览器"""
    time.sleep(2)
    webbrowser.open("http://localhost:8000")

if __name__ == "__main__":
    # 如果没有指定端口，使用 8000 作为前端端口
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    
    port = args.port
    
    if not args.no_browser:
        # 在新线程中打开浏览器
        threading.Thread(target=open_browser, daemon=True).start()
    
    print(f"""
╔═══════════════════════════════════════════╗
║         LLM Proxy Service                ║
╠═══════════════════════════════════════════╣
║  Frontend:  http://localhost:{port}          ║
║  Backend:   http://localhost:{port}          ║
╚═══════════════════════════════════════════╝
    """)
    
    import uvicorn
    
    # 单个服务 - 同时提供前端和后端
    uvicorn.run(app, host="0.0.0.0", port=port)
