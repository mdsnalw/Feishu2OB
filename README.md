# Feishu2OB

**在飞书多维表格里点一下，直接用 Obsidian 打开对应笔记。**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](#license)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](#)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)

---

## 解决什么问题

如果你用 Obsidian 写笔记，同时用飞书多维表格做笔记的归档和检索，会遇到一个尴尬：

**飞书表里有笔记的 `obsidian://` 链接，但点不动。**

原因不是配置问题，而是飞书的安全策略——**飞书客户端对链接做 scheme 白名单校验，只允许 `http` 和 `https`**。无论是按钮字段、超链接字段、公式 `HYPERLINK()`，还是消息卡片，`obsidian://` 这类自定义协议一律被判定为"链接不合法"。

这个项目用一个**本机中转服务**绕开限制：

```
飞书里点击 http://127.0.0.1:8765/open?vault=X&file=Y
        ↓
本机中转服务收到请求（飞书放行 localhost）
        ↓
服务调用系统命令唤起 obsidian://open?vault=X&file=Y
        ↓
Obsidian 打开笔记 ✅
```

---

## 功能特性

| 特性 | 说明 |
|---|---|
| 🔗 **一键跳转** | 飞书表格里点击链接，秒开 Obsidian 对应笔记 |
| 🚫 **防抖保护** | 同一篇笔记 1 秒内重复点击只唤起一次，避免 Obsidian 窗口乱跳 |
| 🪟 **无感体验** | 浏览器页面唤起后自动关闭，不留残留标签页 |
| 🩺 **健康检查** | 访问 `/?ping=1` 返回 `pong`，随时确认服务是否存活 |
| 🪶 **零依赖** | 仅用 Python 标准库，无需 `pip install` 任何东西 |
| 🖥 **跨平台** | Windows / macOS / Linux 均可运行 |

---

## 快速开始

### 1. 启动中转服务

```bash
python obsidian_bridge.py
```

Windows 用户可直接双击 `start_bridge.bat`。

启动成功会看到：

```
============================================================
  Obsidian Bridge 已启动 -> http://127.0.0.1:8765
  默认 vault : MyVault
  防抖窗口   : 1.0 秒
------------------------------------------------------------
  健康检查 : http://127.0.0.1:8765/?ping=1
  连通验证 : http://127.0.0.1:8765/?test=1
------------------------------------------------------------
```

> ⚠️ **这个服务需要常驻后台运行**，关掉它飞书里的链接就会失效。

### 2. 验证飞书是否放行

在飞书多维表里新建一条记录，在**超链接字段**中填入：

```
http://127.0.0.1:8765/?test=1
```

点击它。如果弹出页面显示 `BRIDGE-OK`，说明你的飞书环境放行了 localhost，方案可用 ✅

### 3. 构造跳转链接

链接格式：

```
http://127.0.0.1:8765/open?vault=<库名>&file=<笔记相对路径>
```

示例：

```
http://127.0.0.1:8765/open?vault=MyVault&file=Projects/Ideas.md
http://127.0.0.1:8765/open?vault=MyVault&file=%E7%AC%94%E8%AE%B0/%E6%97%A5%E8%AE%B0.md
```

- `vault`：Obsidian 库名（`obsidian://open?vault=` 后面那个值）
- `file`：笔记在库内的相对路径，**用 URL 编码**，但 `/` 保持原样不编码

把生成的链接写进飞书表的超链接字段（或按钮字段的"打开链接"动作），点击即可跳转。

---

## 与 Obsidian 同步脚本集成

如果你用脚本（如 Templater user script）把笔记批量同步到飞书，只需在写入字段时增加一个 URL 字段：

```js
// 构造 OpenURL：与 obsidian:// 用同一套路径编码规则
function buildOpenURL(vaultName, filePath, port = 8765) {
  const v = encodeURIComponent(vaultName);
  const f = encodeURIComponent(filePath).replace(/%2F/g, '/');
  return `http://127.0.0.1:${port}/open?vault=${v}&file=${f}`;
}
```

写入飞书时**注意字段类型**——超链接字段（type=15）不接受裸字符串，必须传对象：

```js
fields: {
  Title: file.basename,
  // ✅ 正确：{ text, link } 对象
  OpenURL: file.openURL ? { text: '打开笔记', link: file.openURL } : null,
}
```

> ❌ 直接写 `OpenURL: "http://..."`（裸字符串）会报 `code=1254068 URLFieldConvFail`。

---

## 接口说明

| 端点 | 用途 | 返回 |
|---|---|---|
| `GET /?ping=1` | 健康检查 | `pong` |
| `GET /?test=1` | 连通验证 | `BRIDGE-OK: ...` |
| `GET /open?vault=&file=` | 唤起 Obsidian | 自动关闭页 / 错误页 |

---

## 配置

编辑 `obsidian_bridge.py` 顶部的配置区：

```python
PORT = 8765              # 服务监听端口
HOST = "127.0.0.1"       # 绑定地址（请勿改为 0.0.0.0）
DEFAULT_VAULT = "MyVault"  # 默认库名（URL 未带 vault 参数时使用）
DEBOUNCE_SECONDS = 1.0   # 防抖窗口（秒）
```

> 如果你改了 `PORT`，飞书里的链接和同步脚本都要同步修改。

---

## 常见问题

**Q：链接点了没反应？**
先确认服务在运行——浏览器访问 `http://127.0.0.1:8765/?ping=1`，返回 `pong` 即正常。没返回就重新启动服务。

**Q：浏览器报"无法访问此网站"？**
服务没启动，或端口被别的程序占用。检查端口占用：
```bash
# Windows
netstat -ano | findstr :8765
# macOS / Linux
lsof -i :8765
```

**Q：能不能在手机飞书 / 别人电脑上点击？**
不能。链接指向 `127.0.0.1`，即"点击者自己的本机"。只有当**服务和 Obsidian 都跑在同一台机器上**时才有效。

**Q：有没有不依赖本机服务的方案？**
有，但要依赖第三方：使用 Obsidian 插件生成 `https://obsid.net/?vault=X&file=Y` 形式的链接（浏览器访问会自动重定向到 `obsidian://`）。本项目选择本机服务方案，是为了不把入口押在第三方域名的存活上。

**Q：为什么不用飞书自带的按钮 / 自动化？**
飞书的按钮字段、自动化流程、消息卡片全部走同一套 scheme 白名单，只认 http/https，无法直接唤起自定义协议。

---

## 项目结构

```
Feishu2OB/
├── obsidian_bridge.py     # 本机中转服务（核心）
├── start_bridge.bat       # Windows 双击启动器
├── README.md              # 本文档
└── README_使用说明.md      # 详细部署与排错文档（中文）
```

---

## 工作原理细节

1. 飞书客户端对超链接做 scheme 校验，放行 `http`/`https`，并允许指向 localhost
2. 点击后由系统默认浏览器打开 `http://127.0.0.1:8765/...`
3. 本机服务解析 `vault` 和 `file` 参数，拼成标准 `obsidian://open` URI
4. 通过操作系统命令唤起协议：
   - Windows：`os.startfile(uri)`
   - macOS：`open <uri>`
   - Linux：`xdg-open <uri>`
5. Obsidian 响应协议调用，打开对应笔记

---

## License

MIT
