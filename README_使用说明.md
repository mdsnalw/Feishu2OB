# 飞书多维表 → 打开本地 Obsidian 笔记

## 这是什么
让飞书多维表里的每一行，都能"点一下跳回 Obsidian 打开对应的笔记"。

原理：飞书只允许 http/https 链接跳转，不认 `obsidian://`。
所以在飞书和 Obsidian 之间加一个**本机小服务**做中转：

```
飞书点链接
  → http://127.0.0.1:8765/open?vault=MyIOTO&file=xxx.md   （飞书放行）
  → 本机服务收到请求，调系统命令唤起 obsidian://          （obsidian_bridge.py）
  → Obsidian 打开那篇笔记
```

---

## 日常使用（三步）

### 1. 启动中转服务
双击 `start_bridge.bat`，出现一个黑窗口，显示"Obsidian Bridge 已启动"就绪。
**这个窗口要一直开着**，关掉 = 飞书里点链接没反应。

> 忘了开怎么办？飞书里点链接会没反应，回来双击一下 `.bat` 就行。

### 2. 在 Obsidian 里同步笔记
打开一篇笔记 → 命令面板 → `Templater: Insert Template` → 选 `My-TP-OBSyncFeishu`
（脚本会自动把 `OpenURL` 一起写进飞书）

### 3. 在飞书里点击
多维表里找到 **OpenURL** 列，点那个 http 链接 → Obsidian 自动打开对应笔记。

---

## 文件清单

| 文件 | 位置 | 作用 |
|---|---|---|
| `obsidian_bridge.py` | `D:\...\1_Feishu2OB\` | 本机中转服务（核心） |
| `start_bridge.bat` | 同上 | 双击启动服务 |
| `ObSyncFeishu.js` | `D:\Obsidian\MyIOTO\0-辅助\IOTO\Scripts\` | 同步脚本（已加 OpenURL 字段） |
| `My-TP-OBSyncFeishu.md` | `D:\Obsidian\MyIOTO\0-辅助\IOTO\Templates\Templater\MyIOTO\同步模板\` | 配置（已加 bridgePort） |
| `ObSyncFeishu.js.bak.20260910` | 同脚本目录 | 改动前的原始备份 |

---

## 需要你手动做的一件事

**在飞书多维表里新建一个字段：**

- 字段名：`OpenURL`
- 字段类型：**超链接**
- ⚠️ 名字必须一字不差（区分大小写），否则同步时报 `FieldNameNotFound`

> 如果你想起别的名字，改两个地方即可：
> 1. 飞书表的字段名
> 2. `ObSyncFeishu.js` 里 `prepareFeishuRecordData()` 中 `OpenURL:` 那个 key

---

## 排错

| 现象 | 原因 | 解决 |
|---|---|---|
| 点链接没反应 | 服务没开 | 双击 `start_bridge.bat` |
| 浏览器报"无法访问此网站" | 服务没开 / 端口被占 | 检查黑窗口是否活着；`netstat -ano \| findstr :8765` |
| 同步报 `FieldNameNotFound` | 飞书表没有 OpenURL 字段，或名字不对 | 按上面建字段，核对大小写 |
| 服务启动报"端口无法绑定" | 8765 被别的程序占了 | 改 `.py` 的 `PORT` + 配置的 `bridgePort`，两边一致 |
| 打开了 Obsidian 但笔记不对 | 路径不一致 | 检查笔记是否有特殊字符；`OpenURL` 和 `OBURI` 应指向同一篇 |

### 验证服务是否活着
浏览器打开：`http://127.0.0.1:8765/?ping=1` → 显示 `pong` 即正常。

---

## 可调参数

**`obsidian_bridge.py`：**
- `PORT = 8765` —— 服务端口
- `DEFAULT_VAULT = "MyIOTO"` —— 默认库名
- `DEBOUNCE_SECONDS = 1.0` —— 防抖窗口（同一笔记 1 秒内只开一次）

**`My-TP-OBSyncFeishu.md`：**
- `bridgePort: 8765` —— 必须和 `.py` 的 `PORT` 一致
