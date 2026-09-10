"""
Obsidian Bridge —— 飞书多维表 -> 本地 Obsidian 跳转中转服务

作用：
  飞书多维表里的超链接列存 http://127.0.0.1:8765/open?vault=XX&file=YY
  你点击后，请求打到本机这个服务，服务直接调用操作系统命令唤起 obsidian://

零依赖，只用 Python 标准库。启动：
  双击 start_bridge.bat   或   python obsidian_bridge.py
"""

import os
import sys
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

# 让日志实时输出，避免被 stdout 缓冲吃掉
try:
    sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
except Exception:  # noqa: BLE001
    pass

# ============ 配置区 ============
PORT = 8765
HOST = "127.0.0.1"
# 你的 Obsidian 库名（obsidian://open?vault= 后面那个值）
DEFAULT_VAULT = "MyIOTO"
# 防抖窗口（秒）：同一篇笔记在这个时间内重复请求，只唤起一次
DEBOUNCE_SECONDS = 1.0
# ================================

# 防抖记录：{ "vault|file": 上次唤起的时间戳 }
_last_open: dict[str, float] = {}


def build_obsidian_uri(vault: str, file: str) -> str:
    """把 vault + 文件相对路径拼成 obsidian:// URI。"""
    vault_q = urllib.parse.quote(vault, safe="")
    file_q = urllib.parse.quote(file, safe="/")
    return f"obsidian://open?vault={vault_q}&file={file_q}"


def open_with_os(uri: str) -> None:
    """调用操作系统唤起自定义协议，不经过浏览器。"""
    if sys.platform.startswith("win"):
        os.startfile(uri)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        os.system(f'open "{uri}"')
    else:
        os.system(f'xdg-open "{uri}"')


def should_open(key: str) -> bool:
    """防抖：同一篇笔记在 DEBOUNCE_SECONDS 秒内只放行一次。"""
    now = time.time()
    last = _last_open.get(key, 0.0)
    if now - last < DEBOUNCE_SECONDS:
        return False
    _last_open[key] = now
    return True


# ---- 返回给浏览器的页面 ----

CLOSE_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>正在打开 Obsidian</title>
<style>
  html,body{margin:0;height:100%;}
  body{display:flex;align-items:center;justify-content:center;
       background:#f6f7f9;color:#1f2329;
       font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;}
  .box{text-align:center;}
  .dot{width:44px;height:44px;margin:0 auto 16px;border-radius:50%;
       border:3px solid #d9dde3;border-top-color:#3370ff;
       animation:spin .8s linear infinite;}
  @keyframes spin{to{transform:rotate(360deg);}}
  .t{font-size:15px;font-weight:600;}
  .s{font-size:12px;color:#8f959e;margin-top:6px;}
</style>
</head>
<body>
  <div class="box">
    <div class="dot"></div>
    <div class="t">正在打开 Obsidian…</div>
    <div class="s" id="hint">如果窗口没有自动关闭，手动关掉即可</div>
  </div>
<script>
  // 唤起已由服务端完成，这里只负责体面地关闭窗口
  setTimeout(function () {
    window.close();
    // 有些浏览器禁止脚本关闭非脚本打开的窗口，兜底改提示
    setTimeout(function () {
      var h = document.getElementById('hint');
      if (h) h.textContent = '已唤起，请手动关闭此标签页';
    }, 400);
  }, 500);
</script>
</body>
</html>
"""

ERROR_PAGE_TMPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>出错了</title>
<style>
  body{{display:flex;align-items:center;justify-content:center;height:100vh;margin:0;
       background:#f6f7f9;color:#1f2329;
       font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;}}
  .box{{text-align:center;max-width:520px;padding:0 24px;}}
  .t{{font-size:16px;font-weight:600;color:#d83931;margin-bottom:8px;}}
  .m{{font-size:13px;color:#646a73;word-break:break-all;line-height:1.7;}}
</style></head>
<body><div class="box"><div class="t">{title}</div><div class="m">{msg}</div></div></body>
</html>
"""


def error_page(title: str, msg: str) -> str:
    """安全渲染错误页——避免 CSS 大括号与 str.format 冲突。"""
    return ERROR_PAGE_TMPL.replace("{title}", title).replace("{msg}", msg)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        # 验证端点：证明飞书请求确实打到了本机
        if parsed.path == "/" and "test" in params:
            self._respond(200, "text/plain; charset=utf-8",
                          "BRIDGE-OK: 飞书的请求已到达本机服务 ✅")
            print("[TEST ] 收到飞书测试请求 -> 飞书放行 localhost ✅")
            return

        # 健康检查端点
        if parsed.path == "/" and "ping" in params:
            self._respond(200, "text/plain; charset=utf-8", "pong")
            return

        # 核心：打开笔记
        if parsed.path == "/open":
            vault = params.get("vault", [DEFAULT_VAULT])[0]
            file = params.get("file", [""])[0]
            if not file:
                self._respond(400, "text/html; charset=utf-8",
                              error_page("缺少 file 参数",
                                         "链接里没有带上笔记路径，请检查同步脚本写入的 URL。"))
                return

            uri = build_obsidian_uri(vault, file)
            key = f"{vault}|{file}"

            if not should_open(key):
                print(f"[SKIP ] 防抖拦截（{DEBOUNCE_SECONDS}s 内重复）file={file}")
                self._respond(200, "text/html; charset=utf-8", CLOSE_PAGE)
                return

            print(f"[OPEN ] vault={vault} file={file}")
            print(f"[URI  ] {uri}")
            try:
                open_with_os(uri)
                self._respond(200, "text/html; charset=utf-8", CLOSE_PAGE)
            except Exception as e:  # noqa: BLE001
                print(f"[ERROR] 唤起失败: {e}")
                self._respond(500, "text/html; charset=utf-8",
                              error_page("唤起 Obsidian 失败",
                                         f"错误信息：{e}｜请确认本机已安装 Obsidian 且协议已注册。"))
            return

        self._respond(404, "text/plain; charset=utf-8",
                      "Not Found. 可用：/?test=1  /?ping=1  /open?vault=&file=")

    def _respond(self, code: int, ctype: str, text: str) -> None:
        body = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):  # 静默默认日志，避免刷屏
        pass


def main():
    try:
        server = HTTPServer((HOST, PORT), Handler)
    except OSError as e:
        print(f"[FATAL] 端口 {PORT} 无法绑定：{e}")
        print("        可能服务已经在运行，或端口被别的程序占用。")
        print("        查看占用：netstat -ano | findstr :8765")
        input("\n按回车键退出…")
        return

    print("=" * 60)
    print(f"  Obsidian Bridge 已启动 -> http://{HOST}:{PORT}")
    print(f"  默认 vault : {DEFAULT_VAULT}")
    print(f"  防抖窗口   : {DEBOUNCE_SECONDS} 秒")
    print( "-" * 60)
    print( "  健康检查 : http://127.0.0.1:8765/?ping=1")
    print( "  连通验证 : http://127.0.0.1:8765/?test=1")
    print(f"  跳转示例 : http://127.0.0.1:8765/open?vault={DEFAULT_VAULT}&file=xxx.md")
    print( "-" * 60)
    print( "  按 Ctrl+C 停止服务")
    print("=" * 60)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")


if __name__ == "__main__":
    main()
