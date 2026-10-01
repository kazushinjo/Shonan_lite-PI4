# JLCPCB 発注データ (W5500 PA/PTT 制御基板 Rev.1.1)

基板 Rev.1.1 は仕様書 Rev.2.7 に対応する(版数の対応表は `docs/W5500_PA_PTT_Control_仕様書.md` を参照)。

KiCad 10 の `kicad/w5500-esp32.kicad_pcb` から出力した JLCPCB 向けの製造データ。
部品はスルーホールだけなので、基板のみを発注して手はんだで組み立てる想定(PCBA は使わない)。

## ファイル

| ファイル | 内容 |
|---|---|
| `w5500-esp32_jlcpcb_gerber.zip` | **JLCPCB にアップロードするファイル**(下記 `gerber/` の中身をまとめたもの) |
| `gerber/*.gtl` / `*.gbl` | 銅箔 表(F.Cu) / 裏(B.Cu) |
| `gerber/*.g1` / `*.g2` | 内層1(GND 全面ベタ) / 内層2(+12V 全面ベタ) |
| `gerber/*.gts` / `*.gbs` | レジスト 表 / 裏 |
| `gerber/*.gto` / `*.gbo` | シルク 表 / 裏 |
| `gerber/*.gm1` | 基板外形(Edge.Cuts) |
| `gerber/*-PTH.drl` / `*-NPTH.drl` | ドリル(Excellon、mm)。スルーホール103穴(部品99+ビア4) / めっきなし10穴(取付穴φ3.2が4穴、放熱器ピン用φ1.8が6穴) |
| `w5500-esp32_BOM.csv` | 部品表(手配用。JLCPCB の部品実装には使わない) |

## 発注時の設定

| 項目 | 設定 |
|---|---|
| Base Material | FR-4 |
| Layers | **4** |
| Dimensions | 72 × 115 mm(自動で読み取られる値を確認) |
| PCB Qty | 任意(最小5枚) |
| Product Type | Industrial/Consumer electronics |
| Different Design | 1 |
| Delivery Format | Single PCB |
| PCB Thickness | 1.6 mm |
| PCB Color | 任意(緑が最安・最短) |
| Silkscreen | 白 |
| Surface Finish | HASL(with lead) または LeadFree HASL |
| Outer Copper Weight | **1 oz**(12V出力は表裏とも幅4mmのパターン。1ozで5A以上に対応) |
| Inner Copper Weight | 0.5 oz(標準)。+12V/GND は全面ベタなので標準で足りる。余裕を持たせるなら 1 oz |
| Impedance Control | 不要 |
| Layer Stackup | 標準(JLC04161H-7628 など、既定のもの) |
| Via Covering | Tented(ビアは4個だけ、すべて信号・電源の細い配線用) |
| Min via hole size/diameter | 0.3mm/(0.4/0.45mm)(設計のビアは穴0.4mm・外径0.8mm) |
| Board Outline Tolerance | ±0.2mm(標準) |
| Confirm Production file | 任意 |
| Remove Order Number | **Specify a location**(シルクの `JLCJLCJLCJLC` の位置に注文番号が入る。背面側の空き領域) |
| Castellated Holes / Edge Plating など | 不要 |

## 設計ルール(JLCPCB の4層の製造能力内)

- 配線幅 最小 0.3mm(信号) / 0.8mm(+5V・+3.3V) / 2〜4mm(12V出力)
- クリアランス 最小 0.25mm、ベタとのクリアランス 0.4mm
- ビア 穴0.4mm / 外径0.8mm(4個)、最小の部品穴 0.8mm(抵抗・トランジスタ等)
- 基板端から銅箔まで 0.5mm以上
- 放熱器(秋月 105054)の取付ピン(φ1.4mm、間隔12.5mm)用の穴はφ1.8mmのめっき無しで、穴の縁から1mm以内は全層で銅箔なし(ピンと内層ベタのショート防止)
- KiCad の DRC(回路図との照合を含む)で違反0件・未接続0件を確認済み

## 発注前に確認すること(未確認の項目)

- **Freenove ESP32 WROOM ボードの外形と USB-C の位置**は公式ピン配置図から読み取った推定値(約27×58.5mm)。実物を測って、ケースの USB 開口と合うか確認すること。
- **W5500 Lite モジュールの寸法**もデータシートからの値。RJ45 がケース前面の角穴に合うか実物で確認すること。
- ESP32 ソケット(ピンソケット)の高さと、ケースの USB 開口の高さ(z=7mm)が合うか確認すること。
