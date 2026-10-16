"""
部品実装図（docs/W5500_PA_PTT_Control_部品実装図.pdf）を作る。PSN_TRX・Serrasoid_TRX の docs/tools/make_parts_layout.py が元。

  1) KiCad 付属の Python で基板データを書き出す（KiCad の Python は .kicad_pro を書き戻すことがあるので、kicad フォルダのコピーで実行する）
       cp -R hardware/W5500_PA_PTT_Control/kicad /tmp/w5k
       /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \
           hardware/W5500_PA_PTT_Control/docs/tools/export_board.py /tmp/w5k/w5500-esp32.kicad_pcb board.json
  2) matplotlib のある Python で作図する
       python3 hardware/W5500_PA_PTT_Control/docs/tools/make_parts_layout.py board.json \
           hardware/W5500_PA_PTT_Control/docs/W5500_PA_PTT_Control_部品実装図.pdf

部品表（ブロック・値・種類・注意）はこのファイルの BLOCKS。ブロックの順が組立順の目安。
"""
import json, math, os, sys, unicodedata
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Rectangle, Circle, Ellipse, Polygon
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.transforms as mtrans

FW3 = '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc'
FW6 = '/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc'
if not os.path.exists(FW3):   # Windows: 游ゴシック
    FW3, FW6 = 'C:/Windows/Fonts/YuGothM.ttc', 'C:/Windows/Fonts/YuGothB.ttc'
for f in (FW3, FW6):
    fm.fontManager.addfont(f)
plt.rcParams['font.family'] = fm.FontProperties(fname=FW3).get_name()
BOLD = fm.FontProperties(fname=FW6)

board = json.load(open(sys.argv[1]))
OUT = sys.argv[2]

TITLE = 'W5500 PA/PTT Control　部品実装図'
SUB = '基板 Rev.1.2（仕様書 Rev.2.8）/ 72 × 115 mm / 4 層 / リード部品のみ　2026-10-16'
COPPER = '#c8762f'
FAB = '#333333'
FAINT = '#c8c8c8'
NAVY = '#1f2d6b'

# (ブロック名, 色, メモ, 部品 [部品番号, 値/型番, 種類, 注意])
# 組立順の目安: 背の低い抵抗から付けたくなるが、ブロックごとに付けて確かめる。電源を先に付けて電圧を確かめ、ESP32・W5500 は最後にはんだ付けする
BLOCKS = [
    ('電源', '#f6c27a', [
        'U2 L7805（+12V→+5V）と U1 LM2940T-3.3（+5V→+3.3V、W5500 用）。どちらも足は 1=IN・2=GND・3=OUT で形も同じなので取り違えない',
        'TO-220 は本体の下端を基板から約 6mm 浮かせ、タブの穴を放熱器の M3 穴（基板から 19mm）に合わせてねじ止めしてからはんだ付け',
        '放熱器の金属ピンはめっき無し穴に差すだけ（はんだ付けしない）。U1・U2 はタブが GND なので放熱器も GND。タブと放熱器の間に放熱グリス',
        '付け終わったら J2 に 12V を入れ、U2 の 3 番（J1 の 1 番）で +5V、U1 の 3 番（A1 の VCC）で +3.3V を確かめる（ESP32・W5500 はまだ付けない）',
    ], [
        ['J2', 'DC_IN_13V8', '電線パッド', '1mm² 線を直付け。□= +12V、○= GND'],
        ['C3', '0.33µF', 'コンデンサ', '25V 以上。U2 の入力（+12V）'],
        ['U2', 'L7805', 'レギュレータ', '□= 1 番（IN）。放熱器 HS2'],
        ['HS2', '105054', '放熱器', '秋月 20×20×25mm。U2 をねじ止め'],
        ['C1', '0.47µF', 'コンデンサ', '16V 以上。U2 出力・U1 入力（+5V）'],
        ['U1', 'LM2940T-3.3', 'レギュレータ', '□= 1 番（IN）。放熱器 HS1'],
        ['HS1', '105054', '放熱器', '秋月 20×20×25mm。U1 をねじ止め'],
        ['C2', '33µF', '電解コンデンサ', '10V 以上。□が＋（+3.3V）。22µF 以上必須'],
    ]),
    ('12V 出力スイッチ', '#f2aaa8', [
        'GPIO26 → R6 → Q1（2SC1815）→ Q5（2SJ334、P-ch MOSFET のハイサイドスイッチ）→ J5（12V 出力）',
        'Q5 2SJ334 は TO-220NIS（絶縁型）。U1・U2 と同じく本体を約 6mm 浮かせて放熱器 HS3 にねじ止め、放熱グリスを塗る（目安 7A まで）',
        'R8 は 1kΩ 1/2W（他の抵抗より太い）。J5 は 1mm² 線を直付け。12V 出力は表裏 4mm 幅のパターン',
    ], [
        ['R6', '510', '抵抗', 'Q1 のベース抵抗。縦置き'],
        ['R12', '10k', '抵抗', 'Q1 のベース → GND。縦置き'],
        ['R8', '1k 1/2W', '抵抗', '1/2W（φ3.2×9mm）。Q5 ゲート → +12V'],
        ['Q1', '2SC1815', 'トランジスタ', '□= 1 番（E）、2 = C、3 = B'],
        ['Q5', '2SJ334', 'P-ch MOSFET', '□= 1 番（G）、2 = D、3 = S。放熱器 HS3'],
        ['HS3', '105054', '放熱器', '秋月 20×20×25mm。Q5 をねじ止め'],
        ['J5', 'Power', '電線パッド', '1mm² 線を直付け。□= 12V 出力、○= GND'],
    ]),
    ('PTT 出力', '#a9c8ef', [
        'GPIO27 → R7 → Q3（2SC1815）。Q3 が ON で J6 の 1 番（PTT_ON）を GND へ落とす（オープンコレクタ）',
        'R13 は起動中・書き込み中に PTT が勝手に ON にならないためのプルダウン。省略しない',
    ], [
        ['R7', '510', '抵抗', 'Q3 のベース抵抗。縦置き'],
        ['R13', '10k', '抵抗', 'Q3 のベース → GND。縦置き'],
        ['Q3', '2SC1815', 'トランジスタ', '□= 1 番（E）、2 = C、3 = B'],
        ['J6', 'PTT_ON', 'XH コネクタ', 'B2B-XH-A。1 = PTT_ON、2 = GND'],
    ]),
    ('表示 LED（外付け）', '#d6e6a4', [
        'LED は基板に載せず、ケースのパネルに付けて JST XH（J7・J8）でつなぐ。どちらも 1 番 = アノード、2 番 = カソード（GND）',
        'J7 + R10 = Power（12V 出力）表示の赤 LED、J8 + R11 = +12V（入力）表示の緑 LED',
    ], [
        ['R10', '10k', '抵抗', 'J7 の LED の電流制限。縦置き'],
        ['J7', 'LED_PWR', 'XH コネクタ', 'B2B-XH-A。赤 LED（12V 出力）'],
        ['R11', '10k', '抵抗', 'J8 の LED の電流制限。縦置き'],
        ['J8', 'LED_12V', 'XH コネクタ', 'B2B-XH-A。緑 LED（+12V 入力）'],
    ]),
    ('ESP32・W5500', '#b9b2ec', [
        'J1 = Freenove ESP32 WROOM（FNK0090）を基板に直接はんだ付けする（ピンソケットは使わない）。USB-C が基板の下端（背面）側。列の間隔 25.4mm',
        'A1 = W5500 Lite（USR-ES1 互換、2×6 ピン）も直接はんだ付けする。RJ45 が基板の上端（前面）側。どちらも付けると外しにくいので向きを確かめてから',
        'ESP32・W5500 を付ける前に電源ブロックの電圧を確かめる。付けた後 LAN をつなぎ、仕様書 4 章の HTTP API で POWER・PTT の ON/OFF を確かめる',
    ], [
        ['R9', '10k', '抵抗', 'W5500 の RST → +3.3V プルアップ。縦置き'],
        ['J1', 'ESP32 WROOM', 'マイコンボード', 'FNK0090。直接はんだ付け、USB-C が背面側'],
        ['A1', 'W5500 Lite', 'モジュール', '□= 1 番。直接はんだ付け、RJ45 が上端（前面）側'],
    ]),
]
BCOL = {n: c for n, c, _, _ in BLOCKS}
BLOCK_OF = {r[0]: n for n, _, _, rows in BLOCKS for r in rows}
TCOL = {'#f6c27a': '#d9922f', '#f2aaa8': '#d0605c', '#a9c8ef': '#5b8fd0', '#d6e6a4': '#8aa63e', '#b9b2ec': '#7d73c9'}

# 足の名前（ブロック別の図だけに出す）
PINLAB = {'U1': ['IN', 'GND', 'OUT'], 'U2': ['IN', 'GND', 'OUT'], 'Q5': ['G', 'D', 'S'],
          'Q1': ['E', 'C', 'B'], 'Q3': ['E', 'C', 'B'], 'C2': ['＋', ''],
          'J2': ['+12V', 'GND'], 'J5': ['12V', 'GND'], 'J6': ['1', '2'], 'J7': ['A', 'K'], 'J8': ['A', 'K']}
NAME = {'J1': 'J1 (ESP32)', 'A1': 'A1 (W5500)'}

FP = {f['ref']: f for f in board['fps']}
xs = [p[0] for e in board['edge'] for p in (e.get('p') or [e.get('a'), e.get('b')]) if p]
ys = [p[1] for e in board['edge'] for p in (e.get('p') or [e.get('a'), e.get('b')]) if p]
BX0, BX1, BY0, BY1 = min(xs), max(xs), min(ys), max(ys)
missing = [r for r in BLOCK_OF if r not in FP] + [r for r in FP if r not in BLOCK_OF and not r.startswith('H') or r.startswith('HS') and r not in BLOCK_OF]
if missing:
    sys.exit('部品表と基板が合わない: %s' % missing)


# ---------------------------------------------------------------- 描画
def draw_shape(ax, s, col, lw):
    t = s['t']
    if t == 'seg':
        ax.plot([s['a'][0], s['b'][0]], [s['a'][1], s['b'][1]], color=col, lw=lw, solid_capstyle='round')
    elif t == 'poly':
        ax.add_patch(Polygon(s['p'], closed=True, fill=bool(s.get('fill')), fc=col if s.get('fill') else 'none', ec=col, lw=lw))
    elif t == 'circ':
        ax.add_patch(Circle(s['c'], s['r'], fill=bool(s.get('fill')), fc=col if s.get('fill') else 'none', ec=col, lw=lw))
    elif t == 'arc3':
        (x1, y1), (x2, y2), (x3, y3) = s['a'], s['m'], s['b']
        d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
        if abs(d) < 1e-9:
            return
        ux = ((x1 * x1 + y1 * y1) * (y2 - y3) + (x2 * x2 + y2 * y2) * (y3 - y1) + (x3 * x3 + y3 * y3) * (y1 - y2)) / d
        uy = ((x1 * x1 + y1 * y1) * (x3 - x2) + (x2 * x2 + y2 * y2) * (x1 - x3) + (x3 * x3 + y3 * y3) * (x2 - x1)) / d
        r = math.hypot(x1 - ux, y1 - uy)
        a1, a2, am = (math.atan2(y - uy, x - ux) for x, y in ((x1, y1), (x3, y3), (x2, y2)))
        def norm(a, ref):
            while a < ref:
                a += 2 * math.pi
            return a
        e1 = norm(a2, a1); m1 = norm(am, a1)
        if m1 > e1:
            e1 -= 2 * math.pi
        n = 30
        pts = [(ux + r * math.cos(a1 + (e1 - a1) * k / n), uy + r * math.sin(a1 + (e1 - a1) * k / n)) for k in range(n + 1)]
        ax.plot([x for x, y in pts], [y for x, y in pts], color=col, lw=lw)


def draw_pad(ax, p, fc, ec):
    x, y = p['c']
    w, h = p['sz']
    tr = mtrans.Affine2D().rotate_deg_around(x, y, -p['ang']) + ax.transData
    if p['sh'] == 'circle':
        ax.add_patch(Circle((x, y), w / 2, fc=fc, ec=ec, lw=0.3))
    elif p['sh'] == 'oval':
        ax.add_patch(Ellipse((x, y), w, h, fc=fc, ec=ec, lw=0.3, transform=tr))
    else:
        ax.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, fc=fc, ec=ec, lw=0.3, transform=tr))
    if p['drill'] > 0:
        ax.add_patch(Circle((x, y), p['drill'] / 2, fc='white', ec='none'))


def draw_fp(ax, f, mode, pins=False):
    """mode: 'normal' / 'faint'"""
    col = FAB if mode != 'faint' else FAINT
    for s in f['fab']:
        draw_shape(ax, s, col, 0.6 if mode != 'faint' else 0.4)
    for p in f['pads']:
        if mode == 'faint':
            draw_pad(ax, p, 'white', FAINT)
        else:
            draw_pad(ax, p, COPPER if p['n'] else '#eeeeee', '#7a4a1c' if p['n'] else '#888888')
    if mode == 'faint' or f['ref'].startswith('H') and not f['ref'].startswith('HS'):
        return
    (x0, y0), (x1, y1) = f['bbox']
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if f['ref'].startswith('R'):   # 縦置き抵抗は細長いので番号を横に（左の列は左側、右の列は右側）
        left = cx < 70
        cx, ha = (x0 - 0.2, 'right') if left else (x1 + 0.2, 'left')
    else:
        ha = 'center'
    if f['ref'].startswith('HS'):
        cx, cy = x1 - 5, y0 + 3
    elif f['ref'] in ('U1', 'U2', 'Q5'):   # TO-220 は足の名前の左に
        cx, cy, ha = x0 - 3.2, f['pads'][0]['c'][1] + 2.5, 'right'
    elif f['ref'] == 'J8':                 # 縦向きの XH は右に
        cx, ha = x1 + 0.3, 'left'
    elif f['ref'] in ('Q1', 'Q3', 'J6', 'J7'):   # TO-92・横向きの XH は上に
        cy = y0 - 1.6
    ax.text(cx, cy, NAME.get(f['ref'], f['ref']), ha=ha, va='center', fontsize=6.0, color=NAVY, fontproperties=BOLD,
            zorder=20, bbox=dict(fc='white', ec='none', alpha=0.7, pad=0.15))
    if f['val'] and not f['ref'].startswith(('J', 'A')):
        ax.text(cx, cy + 2.0, f['val'][:14], ha=ha, va='center', fontsize=4.2, color='#555555', zorder=20)
    if pins and f['ref'] in PINLAB:
        for p, lab in zip(sorted(f['pads'], key=lambda p: int(p['n'])), PINLAB[f['ref']]):
            px, py = p['c']
            if f['ref'] == 'J8':
                ax.text(px + 1.6, py, lab, ha='left', va='center', fontsize=4.6, color='#a03010', zorder=21)
            elif f['ref'] in ('U1', 'U2', 'Q5'):
                ax.text(px - 1.6, py, lab, ha='right', va='center', fontsize=4.6, color='#a03010', zorder=21)
            else:
                ax.text(px, py + 1.7, lab, ha='center', va='top', fontsize=4.4, color='#a03010', zorder=21)


def board_axes(fig, rect):
    ax = fig.add_axes(rect)
    ax.set_xlim(BX0 - 3, BX1 + 3)
    ax.set_ylim(BY1 + 6, BY0 - 8)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.add_patch(Rectangle((BX0, BY0), BX1 - BX0, BY1 - BY0, fill=False, ec='black', lw=1.4, zorder=30))
    ax.text((BX0 + BX1) / 2, BY0 - 3.2, '↑ 前面（RJ45・+12V 入力の丸型コネクタ）', ha='center', va='bottom', fontsize=6.5, color='#555555')
    ax.text((BX0 + BX1) / 2, BY1 + 1.2, '↓ 背面（USB-C・12V 出力 / PTT の丸型コネクタ）', ha='center', va='top', fontsize=6.5, color='#555555')
    return ax


def header(fig, sub_title, page, total):
    fig.text(0.015, 0.965, f'{TITLE}（部品面）', fontsize=13, fontproperties=BOLD, va='top')
    fig.text(0.015, 0.932, SUB, fontsize=7.5, color='#444444', va='top')
    if sub_title:
        fig.text(0.015, 0.905, sub_title, fontsize=11, fontproperties=BOLD, va='top', color=NAVY)
    fig.text(0.985, 0.012, f'{page} / {total}', fontsize=7, ha='right', color='#666666')


def shade(ax, refs, col, alpha):
    """ブロックの部品の外形（コートヤード）を色で塗る"""
    for r in refs:
        (a, b), (c, d) = FP[r]['bbox']
        ax.add_patch(Rectangle((a, b), c - a, d - b, fc=col, ec='none', alpha=alpha, zorder=0))


def fit(v, width_pt, fs):
    """列幅（pt）に収まるよう末尾を「…」で切る（全角 1.0、半角 0.62 文字幅で概算）"""
    w = lambda c: 1.0 if unicodedata.east_asian_width(c) in 'WFA' else 0.62
    if sum(w(c) for c in v) * fs <= width_pt:
        return v
    out = ''
    for c in v:
        if (sum(w(x) for x in out) + w(c) + 1.0) * fs > width_pt:
            return out + '…'
        out += c
    return out


A4 = (11.69, 8.27)


def table(fig, rect, rows, color, widths=(0.12, 0.22, 0.19, 0.47), fs=7.0, rh_in=0.27):
    """rows: [[部品番号, 値, 種類, 注意]]"""
    cols = ['部品番号', '値/型番', '種類', '注意']
    x0, y0, w, h = rect
    ax = fig.add_axes([x0, y0, w, h])
    ax.axis('off')
    rh = min(rh_in / (h * A4[1]), 1.0 / (len(rows) + 1))
    xs_ = [sum(widths[:i]) for i in range(4)]
    ax.add_patch(Rectangle((0, 1 - rh), 1, rh, fc=color, ec='#888888', lw=0.4))
    for i, c in enumerate(cols):
        ax.text(xs_[i] + 0.01, 1 - rh / 2, c, fontsize=fs, va='center', color='white', fontproperties=BOLD)
    for r, row in enumerate(rows):
        yy = 1 - rh * (r + 2)
        ax.add_patch(Rectangle((0, yy), 1, rh, fc='#f3f3f3' if r % 2 else 'white', ec='#bbbbbb', lw=0.3))
        for i, v in enumerate(row):
            f_i = fs if i < 3 else fs - 0.6
            v = fit(str(v), widths[i] * w * A4[0] * 72 - 3, f_i)
            ax.text(xs_[i] + 0.01, yy + rh / 2, v, fontsize=f_i, va='center',
                    fontproperties=BOLD if i == 0 else None, color=NAVY if i == 0 else 'black', clip_on=True)
    for xv in xs_[1:]:
        ax.plot([xv, xv], [1 - rh * (len(rows) + 1), 1], color='#bbbbbb', lw=0.3)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)


pages_total = 2 + len(BLOCKS)
pdf = PdfPages(OUT, metadata={'Title': 'W5500 PA/PTT Control 部品実装図 Rev.1.2', 'Author': 'JA6FUF'})
n_parts = sum(len(rows) for _, _, _, rows in BLOCKS)

# ---- 1. 全体図
fig = plt.figure(figsize=A4)
header(fig, f'全体図（{n_parts} 点、取付穴 H1〜H4 を除く）', 1, pages_total)
ax = board_axes(fig, [0.01, 0.05, 0.50, 0.84])
for name, col, _, rows in BLOCKS:
    shade(ax, [r[0] for r in rows], col, 0.45)
for f in board['fps']:
    draw_fp(ax, f, 'normal')
notes = [
    '□（四角）パッド = 1 番ピン / 電解コンデンサの＋ / 電線パッドの電源側。',
    'H1〜H4 = M3 取付穴（ケースのボスに M3 ねじで固定）。穴の周りに部品の足を置いていない。',
    '抵抗はすべて縦置き（足の間隔 5.08mm）。R8 だけ 1/2W。',
    '放熱器 HS1〜HS3（秋月 105054）の 2 本の金属ピンはめっき無し穴。はんだ付けしない。',
    'J2・J5 は電線（1mm²）を直接はんだ付けするパッド。J6〜J8 は JST XH 2 ピン。',
    '4 層基板（内層 1 = GND、内層 2 = +12V）。GND・+12V の足ははんだが',
    '　流れにくいので、こてを長めに当てる。',
]
fig.text(0.53, 0.86, '全体の注意', fontsize=9, fontproperties=BOLD, va='top', color=NAVY)
for k, line in enumerate(notes):
    fig.text(0.53, 0.83 - k * 0.026, ('' if line.startswith('　') else '・') + line, fontsize=7.4, va='top')
fig.text(0.53, 0.64, '組み立ての順番（ページ 3〜）', fontsize=9, fontproperties=BOLD, va='top', color=NAVY)
for i, (name, col, _, rows) in enumerate(BLOCKS):
    yy = 0.605 - i * 0.034
    fig.patches.append(Rectangle((0.535, yy - 0.008), 0.018, 0.016, transform=fig.transFigure, fc=col, ec='#888888', lw=0.4, alpha=0.9))
    fig.text(0.56, yy, f'{i + 1}. {name}', fontsize=8, va='center', fontproperties=BOLD)
    fig.text(0.70, yy, '・'.join(r[0] for r in rows), fontsize=7, va='center', color='#333333')
fig.text(0.53, 0.40, '用意するもの（基板に付けない部品）', fontsize=9, fontproperties=BOLD, va='top', color=NAVY)
extra = [
    'Freenove ESP32 WROOM（FNK0090、USB-C）',
    'W5500 Lite（USR-ES1 互換）',
    '放熱器 秋月 105054 × 3、M3 ねじ・ナット × 3、放熱グリス',
    '赤・緑の LED（パネル取付）と JST XH 2 ピンのハウジング・コンタクト × 3（J6〜J8 用）',
    '1mm² の電線（J2・J5）、丸型コネクタ WTN-11-1253 8P × 2、ケース（LAN_PTT.scad）',
]
for k, line in enumerate(extra):
    fig.text(0.53, 0.37 - k * 0.026, '・' + line, fontsize=7.4, va='top')
fig.text(0.53, 0.20, '仕様書: docs/W5500_PA_PTT_Control_仕様書.pdf（回路・放熱・HTTP API）', fontsize=6.8, va='top', color='#555555')
fig.text(0.53, 0.18, '接続一覧: docs/MCU1_J1_W5500_接続一覧.pdf', fontsize=6.8, va='top', color='#555555')
pdf.savefig(fig); plt.close(fig)

# ---- 2. 部品表（全部）
fig = plt.figure(figsize=A4)
header(fig, f'部品表（{n_parts} 点、組み立ての順）', 2, pages_total)
allrows, cols = [], []
for name, col, _, rows in BLOCKS:
    for r in rows:
        allrows.append(r); cols.append(col)
ax = fig.add_axes([0.03, 0.05, 0.94, 0.83]); ax.axis('off'); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
rh = 1.0 / (len(allrows) + 1)
widths = [0.05, 0.10, 0.14, 0.12, 0.59]
xs_ = [sum(widths[:i]) for i in range(5)]
ax.add_patch(Rectangle((0, 1 - rh), 1, rh, fc=NAVY, ec='#888888', lw=0.4))
for i, c in enumerate(['部品番号', '値/型番', 'ブロック', '種類', '注意']):
    ax.text(xs_[i] + 0.004, 1 - rh / 2, c, fontsize=7.5, va='center', color='white', fontproperties=BOLD)
for k, (r, col) in enumerate(zip(allrows, cols)):
    yy = 1 - rh * (k + 2)
    ax.add_patch(Rectangle((0, yy), 1, rh, fc='white', ec='#bbbbbb', lw=0.3))
    ax.add_patch(Rectangle((xs_[2], yy), widths[2], rh, fc=col, ec='none', alpha=0.45))
    for i, v in enumerate([r[0], r[1], BLOCK_OF[r[0]], r[2], r[3]]):
        ax.text(xs_[i] + 0.004, yy + rh / 2, v, fontsize=7.2, va='center',
                fontproperties=BOLD if i == 0 else None, color=NAVY if i == 0 else 'black')
for xv in xs_[1:]:
    ax.plot([xv, xv], [1 - rh * (len(allrows) + 1), 1], color='#bbbbbb', lw=0.3)
pdf.savefig(fig); plt.close(fig)

# ---- ブロック別
for bi, (name, col, memo, rows) in enumerate(BLOCKS):
    fig = plt.figure(figsize=A4)
    header(fig, f'{bi + 1}. {name}（{len(rows)} 点）', bi + 3, pages_total)
    top = 0.878 - len(memo) * 0.021
    ax = board_axes(fig, [0.01, 0.03, 0.46, top - 0.03])
    refs = set(r[0] for r in rows)
    shade(ax, refs, col, 0.5)
    for f in board['fps']:
        draw_fp(ax, f, 'normal' if f['ref'] in refs else 'faint', pins=True)
    for k, line in enumerate(memo):
        fig.text(0.015, 0.878 - k * 0.021, '・' + line, fontsize=7.6, va='top', color='#333333')
    table(fig, [0.49, 0.06, 0.495, top - 0.08], rows, TCOL[col])
    pdf.savefig(fig); plt.close(fig)
pdf.close()
print('pages', pages_total, 'parts', n_parts, OUT)
