from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn

OUT = 'Langstone-V2取扱説明書.docx'
BLUE = RGBColor(46, 116, 181)
DARK = RGBColor(31, 77, 120)
MUTED = RGBColor(90, 100, 110)

def font(run, size=11, color=None, bold=False):
    run.font.name = 'Calibri'; run.font.size = Pt(size); run.bold = bold
    run._element.get_or_add_rPr().rFonts.set(qn('w:ascii'), 'Calibri')
    run._element.get_or_add_rPr().rFonts.set(qn('w:hAnsi'), 'Calibri')
    run._element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'), 'Calibri')
    if color: run.font.color.rgb = color

def add_text(doc, text, style=None):
    p = doc.add_paragraph(style=style)
    p.paragraph_format.widow_control = True
    for i, line in enumerate(text.split('\n')):
        if i: p.add_run().add_break()
        font(p.add_run(line))
    return p

def bullet(doc, text):
    p = doc.add_paragraph(style='List Bullet'); p.paragraph_format.space_after = Pt(4)
    font(p.add_run(text)); return p

def number(doc, text):
    p = doc.add_paragraph(style='List Number'); p.paragraph_format.space_after = Pt(4)
    font(p.add_run(text)); return p

def table(doc, headers, rows, widths):
    t = doc.add_table(rows=1, cols=len(headers)); t.alignment = WD_TABLE_ALIGNMENT.LEFT; t.autofit = False
    for i, h in enumerate(headers):
        c = t.rows[0].cells[i]; c.width = Inches(widths[i]); c.paragraphs[0].paragraph_format.space_after = Pt(0)
        c.paragraphs[0].add_run(h).bold = True
        for r in c.paragraphs[0].runs: font(r, 10, DARK, True)
    for row in rows:
        cells = t.add_row().cells
        for i, value in enumerate(row):
            cells[i].width = Inches(widths[i]); p = cells[i].paragraphs[0]; p.paragraph_format.space_after = Pt(0)
            font(p.add_run(str(value)), 10)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t

doc = Document(); s = doc.sections[0]
s.top_margin = Inches(1); s.bottom_margin = Inches(1); s.left_margin = Inches(1); s.right_margin = Inches(1)
s.header_distance = Inches(.492); s.footer_distance = Inches(.492)
normal = doc.styles['Normal']; normal.font.name = 'Calibri'; normal.font.size = Pt(11); normal.paragraph_format.space_after = Pt(6); normal.paragraph_format.line_spacing = 1.25
for name, size, color, before, after in [('Heading 1',16,BLUE,18,10),('Heading 2',13,BLUE,14,7),('Heading 3',12,DARK,10,5)]:
    st = doc.styles[name]; st.font.name = 'Calibri'; st.font.size = Pt(size); st.font.bold = True; st.font.color.rgb = color
    st.paragraph_format.space_before = Pt(before); st.paragraph_format.space_after = Pt(after); st.paragraph_format.keep_with_next = True
hp = s.header.paragraphs[0]; hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT; font(hp.add_run('Langstone-V2 | DFR0550運用ガイド'), 9, MUTED)
fp = s.footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT; font(fp.add_run('取扱説明書  •  2026-08-16'), 9, MUTED)

p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(60); font(p.add_run('LANGSTONE-V2'), 16, BLUE, True)
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; font(p.add_run('取扱説明書'), 30, DARK, True)
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; font(p.add_run('Raspberry Pi 4 / DFR0550 5インチ / ADALM-Pluto'), 13, MUTED)
add_text(doc, '対象機器で動作確認済みの設定、起動、操作、更新、タッチパネル診断、復旧手順をまとめた現場向けマニュアルです。')
table(doc, ['項目','確定値'], [('対象Pi','Raspberry Pi 4 / Raspberry Pi OS'),('表示','DFRobot DFR0550、800×480、DSI/FPC接続'),('タッチ','raspberrypi-ts、/dev/input/event2'),('SDR','ADALM-Pluto'),('管理IP例','192.168.0.146')], [1.5,5.0])
add_text(doc, '重要：DFR0550はHDMIではなくDSI/FPC接続です。今回の正常構成はlegacy framebuffer（BCM2708 FB）とfirmware自動検出です。KMS/DSI overlayを追加しないでください。')
doc.add_page_break()

add_text(doc, '1. 安全と前提', 'Heading 1')
add_text(doc, '本機は送信機として動作します。アンテナ、フィルタ、増幅器、電源、接地を適切に構成し、免許・周波数・出力規則を守ってください。')
for x in ['送信前に適切なアンテナまたはダミーロードを接続する。','FPCケーブルは電源を切ってから抜き差しする。','GPIOは3.3V系のため、外部機器には必要に応じてバッファを入れる。','Pi、DFR0550、Pluto、USBオーディオ、マウスを接続してから電源を入れる。']: bullet(doc,x)
add_text(doc, '2. ハードウェア構成', 'Heading 1')
table(doc, ['機器','接続・用途'], [('Raspberry Pi 4','本体。EthernetまたはWi-Fiで管理'),('DFR0550','PiのDSI/FPCコネクタへ接続。HDMIではない'),('ADALM-Pluto','USB接続'),('USBオーディオ','マイク入力、スピーカー／ヘッドホン出力'),('USBマウス','スクロールでチューニング、左右クリックでステップ選択'),('PTT / CW / TX GPIO','GPIO 11 / 12 / 40。外部回路は3.3V対応')], [2.1,4.4])
add_text(doc, '3. 通常の起動と操作', 'Heading 1')
for x in ['機器を接続してPiの電源を入れる。','800×480のLangstone画面が表示されるまで待つ。','タッチパネルでバンド、モード、周波数、音量を操作する。','周波数の微調整はマウスホイール、左右ボタンはチューニングステップに使う。','送信時はPTT、CWキー、または画面操作を使い、アンテナ系を確認する。']: number(doc,x)
table(doc, ['入力','機能'], [('タッチパネル','画面上のボタン、周波数、モード操作'),('マウスホイール','周波数変更'),('マウス左／右','チューニングステップ'),('マウス中央','CWキー'),('GPIO 11','PTT。プルアップしGNDで送信'),('GPIO 12','CWキー。プルアップしGNDでキーイング')], [2.0,4.5])

add_text(doc, '4. ネットワーク接続と遠隔管理', 'Heading 1')
add_text(doc, 'ssh pi@192.168.0.146')
add_text(doc, '接続後の基本確認：')
add_text(doc, "cd ~/Langstone\nps -ax | grep -E 'Lang_TRX|GUI_Pluto'\ncat /sys/class/graphics/fb0/name")
add_text(doc, '正常時はGUI_Pluto、Lang_TRX_Pluto.py、BCM2708 FBが確認できます。')
add_text(doc, '5. インストールと更新', 'Heading 1')
add_text(doc, 'ローカルPCからPiへ配布：')
add_text(doc, 'cd ~/AppDev/Langstone-V2\n./deploy_to_pi.sh pi@192.168.0.146')
add_text(doc, '新規インストールまたは再構築：')
add_text(doc, 'ssh pi@192.168.0.146\ncd ~/Langstone\nchmod +x install_dfr0550.sh\n./install_dfr0550.sh')
add_text(doc, '既存環境の更新：')
add_text(doc, 'cd ~/Langstone\n./stop\n./update\nsudo reboot')
add_text(doc, 'インストーラはlegacy framebufferを設定し、最後に再起動します。KMS/DSI overlayを手動追加しないでください。')

add_text(doc, '6. タッチパネルの確認', 'Heading 1')
add_text(doc, 'タッチデバイス：')
add_text(doc, "for f in /sys/class/input/event*/device/name; do echo -n \"$f: \"; cat \"$f\"; done")
add_text(doc, '正常時： /sys/class/input/event2/device/name: raspberrypi-ts')
add_text(doc, 'GUIの接続先：')
add_text(doc, "pid=$(pgrep -x GUI_Pluto | head -1)\nls -l /proc/$pid/fd | grep input")
add_text(doc, '正常時は/dev/input/event2が表示されます。実イベント監視：')
add_text(doc, 'timeout 30s od -An -tx1 /dev/input/event2')
add_text(doc, '旧版・現行の正常構成では、BTN_TOUCH（code 330）、ABS_X（code 0）、ABS_Y（code 1）、EV_SYNが発生します。')

add_text(doc, '7. トラブルシューティング', 'Heading 1')
add_text(doc, '画面が表示されない', 'Heading 2')
for x in ['FPCケーブルの向き、ロック、電源を確認する。','HDMI用設定やKMS/DSI overlayが残っていないか確認する。','cat /sys/class/graphics/fb0/name を実行し、BCM2708 FBか確認する。','必要ならバックアップからconfig.txtを復元して再起動する。']: bullet(doc,x)
add_text(doc, 'タッチが動作しない', 'Heading 2')
for x in ['event2の名前がraspberrypi-tsか確認する。','GUIがevent2を開いているか確認する。','実機タップ中にodでイベントを監視する。イベント0件なら座標処理ではなく起動構成を疑う。','dtoverlay=vc4-kms-v3d、vc4-kms-dsi-7inch、rpi-ft5406を手動追加しない。']: bullet(doc,x)
add_text(doc, 'GUIまたはGNU Radioが起動しない', 'Heading 2')
add_text(doc, "ps -ax | grep -E 'Lang_TRX|GUI_Pluto'\ncd ~/Langstone\npython3 Lang_TRX_Pluto.py > /tmp/LangstoneTRX_Pluto.log 2>&1 &\ntail -f /tmp/LangstoneTRX_Pluto.log")
add_text(doc, 'ウォーターフォールが暗い／表示されない', 'Heading 2')
for x in ['アンテナ、Pluto、周波数、ゲインを確認する。','現行コードはlogpwrfft後にvector_to_streamを通して表示用UDPへ送る。変更後は再ビルドする。']: bullet(doc,x)

add_text(doc, '8. 復旧と保守記録', 'Heading 1')
add_text(doc, '設定変更前バックアップ：')
add_text(doc, '/boot/firmware/config.txt.before-legacy-touch\n/boot/firmware/cmdline.txt.before-legacy-touch')
add_text(doc, '復元する場合：')
add_text(doc, 'sudo cp /boot/firmware/config.txt.before-legacy-touch /boot/firmware/config.txt\nsudo cp /boot/firmware/cmdline.txt.before-legacy-touch /boot/firmware/cmdline.txt\nsudo reboot')
table(doc, ['確認項目','合格条件'], [('画面','800×480、BCM2708 FB'),('タッチ','raspberrypi-ts / event2'),('イベント','BTN_TOUCH、ABS_X、ABS_Y、EV_SYN'),('GUI','GUI_Plutoが起動しevent2を開く'),('GNU Radio','Lang_TRX_Pluto.pyが起動し音声・ウォーターフォールが動作')], [2.0,4.5])
add_text(doc, '関連ファイル', 'Heading 2')
for x in ['README.md：プロジェクト概要と簡易手順','install_dfr0550.sh：Piへのインストールとlegacy表示設定','deploy_to_pi.sh：ローカルPCからPiへの配布','LANGSTONE_TOUCH_DEBUG_STATUS.md：今回の調査記録']: bullet(doc,x)
doc.save(OUT); print(OUT)
