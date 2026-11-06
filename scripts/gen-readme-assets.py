#!/usr/bin/env python3
"""Generate the dsh-primer README visuals (v5).

Outputs (idempotent overwrite):
  docs/assets/dsh-primer-hero-{zh,en}-{light,dark}.webp   1440x576  (Pillow)
  docs/assets/dsh-primer-flow-v5-{light,dark}.svg          1100x660  (hand-written SVG)

Both figures are derived from the actual package, not from a generic template:

  hero  - the progressive-disclosure drawer. index.js reads SKILL.md, splits its
          frontmatter and calls ctx.skills.register with a directory resourceBase.
          The host therefore keeps ONE catalog line resident (name + description),
          pulls the SKILL.md body when the description matches, and resolves the
          relative references (guide/*.md, references/official-docs/*.md) only
          when a loaded page points at them. The drawer draws exactly those three
          tiers, then the mechanical CLI strip that never enters context.

  flow  - dual-channel confluence. One read-only bundle splits into the cognitive
          layer (agent skill: bundle patch row -> ctx.skills.register -> catalog
          line -> on-demand page) and the mechanical layer (dsh-plugin-dev new /
          check / verify / seams). The two channels converge on one conclusion.
          The dashed "skillRef" link is real: every check item cites the skill
          section it enforces (src/cli/commands/check.ts).

Text is Chinese + code tokens because all five README languages share one pair of
SVG files; only the hero is localised (zh / en).

Fonts: msyh.ttc / msyhbd.ttc for Chinese, consola.ttf for code tokens,
segoeui(b).ttf for Latin. Run:  python scripts/gen-readme-assets.py
"""
from __future__ import annotations

import math
import os
import sys
from html import escape

from PIL import Image, ImageDraw, ImageFilter, ImageFont

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'docs', 'assets')

FONT_CJK = r'C:\Windows\Fonts\msyh.ttc'
FONT_CJK_BOLD = r'C:\Windows\Fonts\msyhbd.ttc'
FONT_MONO = r'C:\Windows\Fonts\consola.ttf'
FONT_EN = r'C:\Windows\Fonts\segoeui.ttf'
FONT_EN_BOLD = r'C:\Windows\Fonts\segoeuib.ttf'
for _p in (FONT_CJK, FONT_CJK_BOLD, FONT_MONO, FONT_EN, FONT_EN_BOLD):
    if not os.path.exists(_p):
        raise SystemExit(f'FATAL: font missing: {_p}')

# --- palette: family accent + the two sanctioned page backgrounds ------------
SKIN = {
    'light': dict(bg_from='#f9f6fd', bg_to='#e4eaf8', card='#ffffff',
                  card_edge='#e4e1ee', text='#141419', sub='#4d5261',
                  faint='#8f94a4', accent='#4B67B4', accent2='#16a34a',
                  pill='#ece7f9', grid='#e7e4f0', chip='#f5f2fb',
                  on_accent='#ffffff', shadow=(32, 26, 64)),
    'dark': dict(bg_from='#131a2a', bg_to='#0c1016', card='#1b2231',
                 card_edge='#2e374b', text='#f0f3f9', sub='#a8b1c4',
                 faint='#7c8598', accent='#8496f5', accent2='#3fb950',
                 pill='#242d42', grid='#1e2636', chip='#202839',
                 on_accent='#101528', shadow=(0, 0, 0)),
}

FAMILIES = {
    'mono': FONT_MONO,
    'cjk': FONT_CJK,
    'cjk_bold': FONT_CJK_BOLD,
    'en': FONT_EN,
    'en_bold': FONT_EN_BOLD,
}


def font(size: float, kind: str = 'cjk') -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FAMILIES[kind], int(round(size)))


def hx(value: str) -> tuple[int, int, int]:
    value = value.lstrip('#')
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def gradient(w: int, h: int, c1: str, c2: str) -> Image.Image:
    img = Image.new('RGB', (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = 0.18 * (y / h) + 0.82 * (y / h) ** 1.6
        d.line([(0, y), (w, y)],
               fill=tuple(int(p + (q - p) * t) for p, q in zip(hx(c1), hx(c2))))
    return img


def glow(img: Image.Image, cx: float, cy: float, r: float, color: tuple[int, int, int],
         alpha: int) -> Image.Image:
    layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i in range(10, 0, -1):
        rr = r * i / 10
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
                  fill=color + (int(alpha * (1 - i / 11)),))
    return Image.alpha_composite(img.convert('RGBA'),
                                 layer.filter(ImageFilter.GaussianBlur(26))).convert('RGB')


def soft_card(img: Image.Image, box, radius: float, fill: str, edge: str,
              shadow: tuple[int, int, int], alpha: int = 30, blur: int = 16,
              dy: int = 10, width: int = 1) -> Image.Image:
    x0, y0, x1, y1 = box
    layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.rounded_rectangle([x0, y0 + dy, x1, y1 + dy], radius=radius,
                         fill=shadow + (alpha,))
    layer = layer.filter(ImageFilter.GaussianBlur(blur))
    base = Image.alpha_composite(img.convert('RGBA'), layer)
    d = ImageDraw.Draw(base)
    d.rounded_rectangle(box, radius=radius, fill=hx(fill), outline=hx(edge),
                        width=width)
    return base.convert('RGB')


def dashed_line(d: ImageDraw.ImageDraw, x1: float, y1: float, x2: float, y2: float,
                color, width: int = 2, on: int = 6, off: int = 6) -> None:
    length = math.hypot(x2 - x1, y2 - y1)
    if length == 0:
        return
    ux, uy = (x2 - x1) / length, (y2 - y1) / length
    pos = 0.0
    while pos < length:
        end = min(pos + on, length)
        d.line([(x1 + ux * pos, y1 + uy * pos), (x1 + ux * end, y1 + uy * end)],
               fill=color, width=width)
        pos += on + off


def pill(img: Image.Image, xy, text: str, s: dict, size: float = 17,
         kind: str = 'cjk_bold', fg: str | None = None, bg: str | None = None,
         border: str | None = None) -> Image.Image:
    d = ImageDraw.Draw(img)
    f = font(size, kind)
    tw = d.textlength(text, font=f)
    x, y = xy
    h = int(size + 18)
    box = (x, y, x + tw + 32, y + h)
    d.rounded_rectangle(box, radius=h / 2, fill=hx(bg or s['pill']),
                        outline=hx(border) if border else None,
                        width=1 if border else 0)
    d.text((x + 16, y + h / 2), text, font=f, fill=hx(fg or s['accent']),
           anchor='lm')
    return img


def fit_font(d: ImageDraw.ImageDraw, text: str, kind: str, size: float, maxw: float,
             min_size: float = 10.5) -> ImageFont.FreeTypeFont:
    while size > min_size:
        f = font(size, kind)
        if d.textlength(text, font=f) <= maxw:
            return f
        size -= 0.5
    return font(size, kind)


def runs_width(d: ImageDraw.ImageDraw, runs, size: float, body_kind: str) -> float:
    total = 0.0
    for text, kind in runs:
        f = font(size, 'mono' if kind == 'mono' else body_kind)
        total += d.textlength(text, font=f)
    return total


def runs_text(img: Image.Image, x: float, baseline: float, runs, color: str,
              size: float, body_kind: str) -> None:
    """Draw mixed mono/body runs on one shared baseline (no CJK tofu)."""
    d = ImageDraw.Draw(img)
    cx = x
    for text, kind in runs:
        f = font(size, 'mono' if kind == 'mono' else body_kind)
        d.text((cx, baseline), text, font=f, fill=hx(color), anchor='ls')
        cx += d.textlength(text, font=f)


def tag(img: Image.Image, right: float, top: float, text: str, s: dict,
        fg: str, bg: str | None, border: str | None = None,
        size: float = 11.5, kind: str = 'mono') -> Image.Image:
    d = ImageDraw.Draw(img)
    f = font(size, kind)
    tw = d.textlength(text, font=f)
    h = int(size + 12)
    box = (right - tw - 22, top, right, top + h)
    d.rounded_rectangle(box, radius=h / 2, fill=hx(bg) if bg else None,
                        outline=hx(border) if border else None,
                        width=1 if border else 0)
    d.text(((box[0] + box[2]) / 2, top + h / 2), text, font=f, fill=hx(fg),
           anchor='mm')
    return img


# ---------------------------------------------------------------------------
# Hero copy. Both languages describe the same mechanism; only wording changes.
# ---------------------------------------------------------------------------
HERO = {
    'zh': dict(
        kicker='DeepSeek Harness · 插件开发知识库',
        title='dsh-primer',
        values=['先问版本，再写插件', '按需加载，条条有出处'],
        value_size=40, value_kind='cjk_bold',
        sub='官方镜像 · 版本矩阵 · 迁移 seam · 16 项检查',
        sub_size=25, meta_size=20.5,
        meta='1 条常驻 · 19 篇 guide · 481 页镜像 · 26 条 seam',
        foot='Apache-2.0 · PerryLink DSH plugin family',
        caption=[('SESSION CONTEXT', 'mono'), (' · 渐进披露', 'body')],
        tiers=[
            dict(y=100, h=78, w=340, title='会话技能目录', fill='accent',
                 lines=[[('name + description', 'mono'), (' · 1 条', 'body')]],
                 tag='常驻', tag_style='outline'),
            dict(y=210, h=100, w=470, title='SKILL.md 正文', fill='tint',
                 lines=[[('frontmatter 决定宿主何时加载', 'body')],
                        [('正文按任务类型指向该读的页', 'body')]],
                 tag='触发时', tag_style='chip'),
            dict(y=342, h=100, w=570, title='相对引用 → 按需取页', fill='tint',
                 lines=[[('resourceBase: directory', 'mono')],
                        [('guide/ · references/official-docs/（481 页 · 687f282e）', 'body')]],
                 tag='引用时', tag_style='chip'),
        ],
        cli=('dsh-plugin-dev new · check · verify', '机械层 · 不进上下文'),
    ),
    'en': dict(
        kicker='DeepSeek Harness · plugin-dev knowledge base',
        title='dsh-primer',
        values=['Version first, then build', 'Load on demand, cite the page'],
        value_size=36, value_kind='en_bold',
        sub='verbatim mirror · version matrix · 16 checks',
        sub_size=24, meta_size=20.5,
        meta='1 catalog entry · 19 guide docs · 481 pages · 26 seams',
        foot='Apache-2.0 · PerryLink DSH plugin family',
        caption=[('SESSION CONTEXT', 'mono'), (' · progressive disclosure', 'body')],
        tiers=[
            dict(y=100, h=78, w=340, title='session catalog', fill='accent',
                 lines=[[('name + description', 'mono'), (' · 1 entry', 'body')]],
                 tag='resident', tag_style='outline'),
            dict(y=210, h=100, w=470, title='SKILL.md body', fill='tint',
                 lines=[[('its frontmatter decides when to load', 'body')],
                        [('the body points a task at the right page', 'body')]],
                 tag='on trigger', tag_style='chip'),
            dict(y=342, h=100, w=570, title='relative refs, on demand', fill='tint',
                 lines=[[('resourceBase: directory', 'mono')],
                        [('guide/ · references/official-docs/ (481 pages · 687f282e)', 'body')]],
                 tag='on cite', tag_style='chip'),
        ],
        cli=('dsh-plugin-dev new · check · verify', 'mechanical layer · never in context'),
    ),
}


def hero(lang: str, skin: str) -> None:
    s = SKIN[skin]
    H = HERO[lang]
    w, h = 1440, 576
    img = gradient(w, h, s['bg_from'], s['bg_to'])
    img = glow(img, 1290, 30, 460, hx(s['accent']),
               22 if skin == 'light' else 36)
    img = glow(img, 170, 570, 300, hx(s['accent2']),
               8 if skin == 'light' else 14)

    # ---- left column: kicker / title / two value lines / sub / meta / foot ---
    img = pill(img, (64, 58), H['kicker'], s, size=17,
               kind='cjk_bold' if lang == 'zh' else 'en_bold')
    d = ImageDraw.Draw(img)
    title_size = 82
    tf = fit_font(d, H['title'], 'mono', title_size, 570)
    d.text((64, 112), H['title'], font=tf, fill=hx(s['text']))

    y = 246
    for line in H['values']:
        vf = fit_font(d, line, H['value_kind'], H['value_size'], 574, 30)
        d.text((66, y), line, font=vf, fill=hx(s['text']))
        y += 56

    sf = fit_font(d, H['sub'], 'cjk' if lang == 'zh' else 'en',
                  H['sub_size'], 574, 18)
    d.text((66, 368), H['sub'], font=sf, fill=hx(s['sub']))
    mf = fit_font(d, H['meta'], 'cjk' if lang == 'zh' else 'en',
                  H['meta_size'], 574, 14)
    d.text((66, 414), H['meta'], font=mf, fill=hx(s['faint']))
    d.line([66, 452, 640, 452], fill=hx(s['grid']), width=2)
    d.text((66, 470), H['foot'], font=font(16, 'en'), fill=hx(s['faint']))

    body_kind = 'cjk' if lang == 'zh' else 'en'

    # ---- right: the progressive-disclosure drawer ---------------------------
    img = soft_card(img, (690, 40, 1376, 536), 22, s['card'], s['card_edge'],
                    s['shadow'], alpha=34 if skin == 'light' else 90,
                    blur=20, dy=14)
    d = ImageDraw.Draw(img)
    runs_text(img, 718, 71, H['caption'], s['faint'], 13, body_kind)
    d.line([718, 88, 1348, 88], fill=hx(s['grid']), width=1)

    # spine + numbered tier dots
    dashed_line(d, 726, 100, 726, 442, hx(s['accent']),
                width=2, on=5, off=7)
    for i, tier in enumerate(H['tiers']):
        cy = tier['y'] + tier['h'] / 2 - 4
        d.line([739, cy, 756, cy], fill=hx(s['accent']), width=2)
        d.ellipse([726 - 14, cy - 14, 726 + 14, cy + 14],
                  fill=hx(s['accent']))
        d.text((726, cy), str(i + 1), font=font(14, 'mono'),
               fill=hx(s['on_accent']), anchor='mm')

    for tier in H['tiers']:
        y0, hh, ww = tier['y'], tier['h'], tier['w']
        box = (756, y0, 756 + ww, y0 + hh)
        if tier['fill'] == 'accent':
            img = soft_card(img, box, 18, s['accent'], s['accent'],
                            s['shadow'], alpha=40 if skin == 'light' else 80,
                            blur=18, dy=12)
            d = ImageDraw.Draw(img)
            title_color = s['on_accent']
            line_color = s['on_accent']
        else:
            img = soft_card(img, box, 18, s['card'], s['card_edge'],
                            s['shadow'], alpha=22 if skin == 'light' else 70,
                            blur=14, dy=8)
            d = ImageDraw.Draw(img)
            title_color = s['text']
            line_color = s['sub']

        d.text((778, y0 + 31), tier['title'],
               font=font(21, 'cjk_bold' if lang == 'zh' else 'en_bold'),
               fill=hx(title_color), anchor='ls')
        ly = y0 + 60
        for runs in tier['lines']:
            size = 17.5
            maxw = ww - 46
            while size > 11 and runs_width(d, runs, size, body_kind) > maxw:
                size -= 0.5
            runs_text(img, 778, ly, runs, line_color, size, body_kind)
            ly += 24
            d = ImageDraw.Draw(img)

        right = 756 + ww - 16
        if tier['tag_style'] == 'outline':
            tag(img, right, y0 + 14, tier['tag'], s, fg=s['on_accent'],
                bg=None, border=s['on_accent'], size=12.5,
                kind='mono' if lang == 'en' else 'cjk')
        else:
            tag(img, right, y0 + 14, tier['tag'], s, fg=s['accent'],
                bg=s['pill'], border=None, size=12.5,
                kind='mono' if lang == 'en' else 'cjk')

    # ---- mechanical layer strip --------------------------------------------
    strip = (718, 466, 1348, 510)
    img = soft_card(img, strip, 14, s['chip'], s['card_edge'], s['shadow'],
                    alpha=0, blur=2, dy=0)
    d = ImageDraw.Draw(img)
    d.text((736, 488), H['cli'][0], font=font(14, 'mono'), fill=hx(s['sub']))
    d.text((1332, 488), H['cli'][1],
           font=font(12.5, 'cjk' if lang == 'zh' else 'en'), fill=hx(s['faint']),
           anchor='ra')

    path = os.path.join(OUT, f'dsh-primer-hero-{lang}-{skin}.webp')
    img.save(path, 'WEBP', quality=92, method=6)
    print(f'wrote docs/assets/dsh-primer-hero-{lang}-{skin}.webp')


# ---------------------------------------------------------------------------
# Flow SVG: dual-channel confluence, 1100x660
# ---------------------------------------------------------------------------
FLOW = {
    'light': dict(bg_from='#f9f6fd', bg_to='#e4eaf8', card='#ffffff',
                  edge='#e4e1ee', text='#141419', sub='#4d5261',
                  faint='#8f94a4', accent='#4B67B4', accent2='#16a34a',
                  pill='#ece7f9', grid='#e7e4f0', chip='#f5f2fb',
                  shadow='#1b1735', shadow_op='0.13'),
    'dark': dict(bg_from='#131a2a', bg_to='#0c1016', card='#1b2231',
                 edge='#2e374b', text='#f0f3f9', sub='#a8b1c4',
                 faint='#7c8598', accent='#8496f5', accent2='#3fb950',
                 pill='#242d42', grid='#1e2636', chip='#202839',
                 shadow='#000000', shadow_op='0.55'),
}

MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
SANS = ("ui-sans-serif, system-ui, -apple-system, 'Segoe UI', "
        "'Microsoft YaHei', sans-serif")

# (title, body, footnote) for each lane, top to bottom.
LANES = [
    dict(x=50, tag='认知层 · agent 技能', note='按需进上下文', cards=[
        ('cordis.patch.yml → ctx.skills.register',
         'insert 一行 → apply() 读 SKILL.md、拆 frontmatter',
         '注册即 effect，停用或热重载即撤销'),
        ('description → 会话技能目录',
         'description 决定宿主何时把技能放进上下文',
         'agent 自行判断是否加载，正文 116 行'),
        ('resourceBase → 按需取页',
         'guide/ 19 篇 · version-matrix.md · migration-0.2.md',
         '仅引用时读取，无网络、无写入、无模型调用'),
    ]),
    dict(x=596, tag='机械层 · dsh-plugin-dev', note='终端 / CI 可跑', cards=[
        ('new <name> --lang ts|js',
         '契约模板 · Config · tests · 五语 README',
         '幂等；无 --force 拒绝覆盖非空目录'),
        ('check [--json] [--strict]',
         '16 项：patch 2 · manifest 6 · 展示 1 · README 2 · 红线 5',
         '每项带 skillRef，指回技能章节'),
        ('verify → pack → 干净 profile',
         '临时 DSH_HOME：安装 / 启动 / 卸载冒烟',
         'seams：26 条记录，未知即退出码 3'),
    ]),
]

FLOW_CARDS = [
    dict(y=222, h=78),
    dict(y=312, h=78),
    dict(y=402, h=78),
]


def flow_svg(skin: str) -> str:
    s = FLOW[skin]
    W, H = 1100, 660
    p = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="figtitle figdesc">
<title id="figtitle">dsh-primer 双通道汇流结构图</title>
<desc id="figdesc">只读 bundle 分成两条通道。认知层：cordis.patch.yml 插一行、index.js 的 apply 调 ctx.skills.register 注册技能，会话技能目录常驻 name + description，SKILL.md 正文与 guide/、references/ 按需读取。机械层：dsh-plugin-dev 的 new 生成脚手架，check 跑 16 项静态检查（每项带 skillRef），verify 打包后在干净 profile 冒烟，seams 查询 26 条破坏性变更。两条通道汇成同一个结论：插件对目标宿主成立。</desc>
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="0.28" y2="1">
    <stop offset="0" stop-color="{s['bg_from']}"/><stop offset="1" stop-color="{s['bg_to']}"/>
  </linearGradient>
  <filter id="soft" x="-25%" y="-25%" width="150%" height="170%">
    <feDropShadow dx="0" dy="8" stdDeviation="11" flood-color="{s['shadow']}" flood-opacity="{s['shadow_op']}"/>
  </filter>
  <pattern id="dots" width="26" height="26" patternUnits="userSpaceOnUse">
    <circle cx="1.2" cy="1.2" r="1.2" fill="{s['grid']}"/>
  </pattern>
  <marker id="mkA" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
    <path d="M0 0 L10 5 L0 10 z" fill="{s['accent']}"/>
  </marker>
  <marker id="mkG" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
    <path d="M0 0 L10 5 L0 10 z" fill="{s['accent2']}"/>
  </marker>
</defs>
<rect width="{W}" height="{H}" fill="url(#bg)"/>
<rect width="{W}" height="{H}" fill="url(#dots)" opacity=".45"/>

<!-- header -->
<text x="48" y="58" fill="{s['text']}" font-family="{MONO}" font-size="30" font-weight="700">dsh-primer</text>
<text x="48" y="88" fill="{s['sub']}" font-family="{SANS}" font-size="14.5">一个 bundle，两条通道：知识按需进上下文，检查逐条留证据</text>
<text x="1052" y="86" text-anchor="end" fill="{s['faint']}" font-family="{SANS}" font-size="12.5">inject: skills · 不注册工具 / 命令 / slot</text>
<line x1="40" y1="100" x2="1060" y2="100" stroke="{s['grid']}" stroke-width="1.4"/>

<!-- shared source: the read-only package -->
<rect x="44" y="110" width="1012" height="72" rx="18" fill="{s['card']}" stroke="{s['edge']}" filter="url(#soft)"/>
<text x="66" y="133" fill="{s['accent']}" font-family="{MONO}" font-size="11.5" font-weight="700" letter-spacing="1.1">PACKAGE · filesystem:read · 只读</text>
<text x="66" y="162" fill="{s['text']}" font-family="{SANS}" font-size="15">bundle 内容：一份知识库（技能）+ 一个零依赖 CLI</text>
<line x1="524" y1="124" x2="524" y2="168" stroke="{s['edge']}" stroke-width="1.2"/>''']
    # the four artifacts that make up the package, as chips
    cx = 531
    for label, width in (('SKILL.md', 84), ('guide/ · 19', 104),
                         ('official-docs · 481', 152), ('data/seams · 26', 134)):
        p.append(f'''<g><rect x="{cx}" y="126" width="{width}" height="32" rx="9" fill="{s['chip']}" stroke="{s['edge']}"/>
<text x="{cx + width / 2}" y="147" text-anchor="middle" fill="{s['sub']}" font-family="{MONO}" font-size="11.5">{escape(label)}</text></g>''')
        cx += width + 9

    # split bus from the source into the two lanes
    p.append(f'''
<!-- split -->
<path d="M550 182 V192" fill="none" stroke="{s['accent']}" stroke-width="1.6"/>
<path d="M90 192 H1010" fill="none" stroke="{s['accent']}" stroke-width="1.6"/>
<circle cx="550" cy="192" r="3.6" fill="{s['accent']}"/>
<path d="M90 192 V216" fill="none" stroke="{s['accent']}" stroke-width="1.8" marker-end="url(#mkA)"/>
<path d="M1010 192 V216" fill="none" stroke="{s['accent']}" stroke-width="1.8" marker-end="url(#mkA)"/>
<text x="112" y="212" font-family="{SANS}" font-size="13"><tspan fill="{s['accent']}" font-weight="700">认知层 · agent 技能</tspan><tspan fill="{s['faint']}" font-size="11.5"> · 按需进上下文</tspan></text>
<text x="988" y="212" text-anchor="end" font-family="{SANS}" font-size="13"><tspan fill="{s['accent']}" font-weight="700">机械层 · dsh-plugin-dev</tspan><tspan fill="{s['faint']}" font-size="11.5"> · 终端 / CI 可跑</tspan></text>''')

    # lane cards
    for lane in LANES:
        for step, ((title, body, foot), geo) in enumerate(
                zip(lane['cards'], FLOW_CARDS), 1):
            x, y, hh = lane['x'], geo['y'], geo['h']
            p.append(f'''
<g>
  <rect x="{x}" y="{y}" width="454" height="{hh}" rx="16" fill="{s['card']}" stroke="{s['edge']}" stroke-width="1.2" filter="url(#soft)"/>
  <circle cx="{x + 30}" cy="{y + 34}" r="13" fill="{s['pill']}"/>
  <text x="{x + 30}" y="{y + 38.5}" text-anchor="middle" fill="{s['accent']}" font-family="{MONO}" font-size="12.5" font-weight="700">{step}</text>
  <text x="{x + 54}" y="{y + 32}" fill="{s['text']}" font-family="{MONO}" font-size="15.5" font-weight="700">{escape(title)}</text>
  <text x="{x + 54}" y="{y + 55}" fill="{s['sub']}" font-family="{SANS}" font-size="13">{escape(body)}</text>
  <text x="{x + 54}" y="{y + 72}" fill="{s['faint']}" font-family="{SANS}" font-size="12">{escape(foot)}</text>
</g>''')

    # cross-link: every check cites the skill section it enforces
    p.append(f'''
<!-- skillRef: check item -> skill section -->
<text x="550" y="341" text-anchor="middle" fill="{s['accent']}" font-family="{MONO}" font-size="11">skillRef ×16</text>
<path d="M596 351 H512" fill="none" stroke="{s['accent']}" stroke-width="1.6" stroke-dasharray="5 5" marker-end="url(#mkA)"/>''')

    # confluence band
    p.append(f'''
<!-- merge -->
<path d="M277 480 V500" fill="none" stroke="{s['accent2']}" stroke-width="2.4" marker-end="url(#mkG)"/>
<path d="M823 480 V500" fill="none" stroke="{s['accent2']}" stroke-width="2.4" marker-end="url(#mkG)"/>
<rect x="44" y="504" width="1012" height="90" rx="20" fill="{s['card']}" stroke="{s['accent2']}" stroke-width="2.2" filter="url(#soft)"/>
<rect x="68" y="520" width="4" height="58" rx="2" fill="{s['accent2']}"/>
<text x="88" y="530" fill="{s['accent2']}" font-family="{MONO}" font-size="11.5" font-weight="700" letter-spacing="1.2">CONFLUENCE · 两条通道，一个结论</text>
<text x="88" y="558" fill="{s['text']}" font-family="{SANS}" font-size="18" font-weight="700">插件对目标宿主成立，才算交付</text>
<text x="88" y="582" fill="{s['sub']}" font-family="{SANS}" font-size="12.5">知识给出处（guide/ · references/），CLI 给结果（16 项检查 · pack 冒烟）；两边都能复述，结论才站得住。</text>

<!-- footer -->
<text x="48" y="622" fill="{s['faint']}" font-family="{MONO}" font-size="11.5">只读 · 无网络 · 无模型调用 · filesystem:read · 卸载即撤销</text>
<text x="1052" y="622" text-anchor="end" fill="{s['faint']}" font-family="{MONO}" font-size="11.5">26 条 seam（19 L · 6 S · 1 B）· 16 项检查</text>
</svg>''')
    return '\n'.join(p) + '\n'


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    for skin in ('light', 'dark'):
        for lang in ('zh', 'en'):
            hero(lang, skin)
        path = os.path.join(OUT, f'dsh-primer-flow-v5-{skin}.svg')
        with open(path, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(flow_svg(skin))
        print(f'wrote docs/assets/dsh-primer-flow-v5-{skin}.svg')


if __name__ == '__main__':
    main()
