# -*- coding: utf-8 -*-
"""
生成 start_bridge.bat 的图标（飞书多维表 -> 跳转 -> 本地 Obsidian 笔记）
设计坐标系：1024 x 1024，用 4x 超采样渲染后降采样，保证边缘平滑。
输出：bridge.ico（多尺寸，含 256x256）+ 预览 PNG
"""
from PIL import Image, ImageDraw, ImageFilter
import os

# 输出目录 = 脚本所在目录（不放本地绝对路径，方便别人直接跑）
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
S = 4                      # 超采样倍数
DESIGN = 1024.0            # 设计坐标系边长

# ---------------- 设计常量（1024 坐标系） ----------------
BG_R = 224                 # 底板圆角
BG_TOP = (33, 35, 62)      # 底板渐变：上
BG_BOT = (13, 14, 26)      # 底板渐变：下

BLK_Y0, BLK_Y1 = 268, 756  # 元素块上下边界
BLK_R = 60                 # 元素块圆角
LEFT_X0, LEFT_X1 = 108, 440
RIGHT_X0, RIGHT_X1 = 584, 916

FS_TOP = (91, 140, 255)    # 飞书蓝：上
FS_BOT = (47, 98, 232)     # 飞书蓝：下
OB_TOP = (170, 132, 255)   # Obsidian 紫：上
OB_BOT = (109, 40, 217)    # Obsidian 紫：下

ARROW_COLOR = (255, 255, 255)
GLOW_COLOR = (34, 211, 238)


def lerp(a, b, t):
    return tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))


def vgrad_solid(size, box, radius, c_top, c_bot):
    """在给定 box 内生成垂直渐变的圆角矩形（RGBA）"""
    x0, y0, x1, y1 = box
    w, h = int(round(x1 - x0)), int(round(y1 - y0))
    g = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(g)
    for y in range(h):
        d.line([(0, y), (w, y)], fill=lerp(c_top, c_bot, y / max(1, h - 1)))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(g, (0, 0), mask)
    return out


def clip_to_rounded(layer, W, box, radius):
    """把图层 alpha 裁剪到圆角矩形内"""
    clip = Image.new("L", (W, W), 0)
    ImageDraw.Draw(clip).rounded_rectangle(box, radius=radius, fill=255)
    a = Image.composite(layer.getchannel("A"), Image.new("L", (W, W), 0), clip)
    layer.putalpha(a)
    return layer


def render(N):
    """渲染 N x N 的图标（内部超采样）"""
    W = int(N * S)
    k = W / DESIGN

    def s(v):
        return v * k

    def box4(x0, y0, x1, y1):
        return [s(x0), s(y0), s(x1), s(y1)]

    img = Image.new("RGBA", (W, W), (0, 0, 0, 0))

    # ---------- 1. 底板（垂直渐变圆角矩形） ----------
    bg = Image.new("RGB", (W, W))
    dbg = ImageDraw.Draw(bg)
    for y in range(W):
        dbg.line([(0, y), (W, y)], fill=lerp(BG_TOP, BG_BOT, y / (W - 1)))
    bmask = Image.new("L", (W, W), 0)
    ImageDraw.Draw(bmask).rounded_rectangle([0, 0, W - 1, W - 1], radius=int(s(BG_R)), fill=255)
    img.paste(bg, (0, 0), bmask)

    # 1b. 左上角柔和光晕（提升质感）
    halo = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    ImageDraw.Draw(halo).ellipse(
        [s(-260), s(-320), s(880), s(560)], fill=(120, 150, 255, 46))
    halo = halo.filter(ImageFilter.GaussianBlur(radius=s(180)))
    a = Image.composite(halo.getchannel("A"), Image.new("L", (W, W), 0), bmask)
    halo.putalpha(a)
    img.alpha_composite(halo)

    # ---------- 2. 元素块投影 ----------
    shadow = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    dsh = ImageDraw.Draw(shadow)
    off = int(s(16))
    for bx in (box4(LEFT_X0, BLK_Y0, LEFT_X1, BLK_Y1),
               box4(RIGHT_X0, BLK_Y0, RIGHT_X1, BLK_Y1)):
        dsh.rounded_rectangle([bx[0], bx[1] + off, bx[2], bx[3] + off],
                              radius=int(s(BLK_R)), fill=(0, 0, 0, 150))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=s(26)))
    img.alpha_composite(shadow)

    # ---------- 3. 左侧：飞书多维表格 ----------
    left = vgrad_solid(W, box4(LEFT_X0, BLK_Y0, LEFT_X1, BLK_Y1), int(s(BLK_R)), FS_TOP, FS_BOT)
    img.alpha_composite(left, (int(s(LEFT_X0)), int(s(BLK_Y0))))

    # 表格网格
    grid = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    dg = ImageDraw.Draw(grid)
    gx0, gx1 = s(164), s(384)
    gy0, gy1 = s(324), s(700)
    lw = max(1, int(s(11)))
    for i in (1, 2):
        x = gx0 + (gx1 - gx0) * i / 3.0
        dg.line([(x, gy0), (x, gy1)], fill=(255, 255, 255, 85), width=lw)
        y = gy0 + (gy1 - gy0) * i / 3.0
        dg.line([(gx0, y), (gx1, y)], fill=(255, 255, 255, 85), width=lw)
    clip_to_rounded(grid, W, box4(LEFT_X0, BLK_Y0, LEFT_X1, BLK_Y1), int(s(BLK_R)))
    img.alpha_composite(grid)

    # ---------- 4. 右侧：Obsidian 笔记 ----------
    right = vgrad_solid(W, box4(RIGHT_X0, BLK_Y0, RIGHT_X1, BLK_Y1), int(s(BLK_R)), OB_TOP, OB_BOT)
    img.alpha_composite(right, (int(s(RIGHT_X0)), int(s(BLK_Y0))))

    lines = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    dl = ImageDraw.Draw(lines)
    # 标题（短而粗）+ 两行正文
    dl.line([(s(640), s(420)), (s(778), s(420))], fill=(255, 255, 255, 118), width=max(1, int(s(26))))
    dl.line([(s(640), s(512)), (s(860), s(512))], fill=(255, 255, 255, 88), width=max(1, int(s(17))))
    dl.line([(s(640), s(598)), (s(828), s(598))], fill=(255, 255, 255, 88), width=max(1, int(s(17))))
    clip_to_rounded(lines, W, box4(RIGHT_X0, BLK_Y0, RIGHT_X1, BLK_Y1), int(s(BLK_R)))
    img.alpha_composite(lines)

    # ---------- 5. 中间箭头（带青色辉光） ----------
    arrow = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    da = ImageDraw.Draw(arrow)
    da.rectangle(box4(444, 489, 528, 535), fill=ARROW_COLOR + (255,))
    da.polygon([(s(576), s(512)), (s(522), s(452)), (s(522), s(572))], fill=ARROW_COLOR + (255,))

    glow_src = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    glow_src.putalpha(arrow.getchannel("A").point(lambda v: int(v * 0.85)))
    glow_col = Image.new("RGBA", (W, W), GLOW_COLOR + (0,))
    glow_col.putalpha(glow_src.getchannel("A"))
    glow = glow_col.filter(ImageFilter.GaussianBlur(radius=s(26)))
    img.alpha_composite(glow)
    img.alpha_composite(arrow)

    # ---------- 6. 底板内描边（边缘光） ----------
    edge = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    ImageDraw.Draw(edge).rounded_rectangle(
        [0, 0, W - 1, W - 1], radius=int(s(BG_R)),
        outline=(255, 255, 255, 46), width=max(1, int(s(2.5))))
    img.alpha_composite(edge)

    # 降采样
    return img.resize((N, N), Image.LANCZOS)


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)

    master = render(512)                 # 512 主图，用于生成 ICO
    preview = render(256)                # 预览图

    master.save(os.path.join(OUT_DIR, "icon_preview_512.png"))
    preview.save(os.path.join(OUT_DIR, "icon_preview_256.png"))

    # 生成多尺寸 ICO（从 512 主图降采样，质量最好）
    sizes = [256, 128, 64, 48, 32, 16]
    master.save(os.path.join(OUT_DIR, "bridge.ico"), format="ICO",
                sizes=[(n, n) for n in sizes])

    ico = os.path.join(OUT_DIR, "bridge.ico")
    print("OK")
    print("  bridge.ico          :", os.path.getsize(ico), "bytes")
    print("  icon_preview_512    :", os.path.getsize(os.path.join(OUT_DIR, "icon_preview_512.png")), "bytes")
    print("  icon_preview_256    :", os.path.getsize(os.path.join(OUT_DIR, "icon_preview_256.png")), "bytes")
