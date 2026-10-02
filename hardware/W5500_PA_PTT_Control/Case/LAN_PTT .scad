// ==========================================
// パラメータ設定
// ==========================================

// --- ケースのパラメータ ---

//  - mode = 1：本体のみ
//  - mode = 2：蓋のみ
//  - mode = 3：組立状態
//  - mode = 4：分解図

mode = 2;            // 1:本体のみ 2:蓋のみ 3:組立状態 4:分解図
inner_x = 80;       // 内寸 X (幅)
inner_y = 120;      // 内寸 Y (奥行)
inner_z = 35;       // 内寸 Z (高さ)
thickness = 2.5;    // 肉厚
corner_r = 5.0;     // 外側の角丸の半径 (R)

// --- ボスのパラメータ ---
pitch_x = 66;       // ボス配置のX方向間隔
pitch_y = 109;      // ボス配置のY方向間隔
boss_od = 8.0;      // ボス外径
boss_id = 5.0;      // ボス内径（ビス穴）
boss_h  = 5.0;      // ボスの高さ

// --- 穴のパラメータ ---
hole_d  = 16.0;     // 丸穴の直径

// 1つ目の穴 (前面の丸穴)
hole1_x = 20.0;     // X座標 (内寸基準)
hole1_z = 17.5;     // Z座標 (内寸基準)

// 2つ目の穴 (背面の丸穴)
hole2_x = 20.0;     // X座標 (内寸基準)
hole2_y = 120.0;    // Y座標 (内寸基準・背面の壁)
hole2_z = 17.5;     // Z座標 (内寸基準)

// --- 角穴のパラメータ (前面の切り欠き) ---
notch_x_start = 45.0; // X開始位置
notch_z_start = 10.6; // Z開始位置 RJ45下端=基板面+5 → Z11.6、下に1.0mm余裕
notch_w       = 18.0; // 幅 (63 - 45)
notch_h       = 14.9; // 高さ (25.5 - 10.6) RJ45上端=基板面+18 → Z24.6、上に0.9mm余裕

// --- はめ込み蓋のパラメータ ---
lid_top_t       = 2.5; // 蓋の天板厚
lid_lip_h       = 9.0; // 差し込みリップの高さ
lid_lip_wall    = 1.5; // リップの壁厚
lid_clearance   = 0.0; // 本体との片側クリアランス
explode_offset  = 20.0; // 分解図で蓋を持ち上げる距離

// --- 蓋リップの切り欠き ---
lid_notch_x = 20.0;     // X中心座標（内寸基準）
lid_notch_w = 25.0;     // 横幅
lid_notch_h = 8.0;      // 高さ（リップ下端から上方向）

// --- 蓋のエンボス文字 ---
// [文字, X座標(左端), Y座標, 縦の揃え, 文字の大きさ] 座標は内寸基準。
// 縦の揃え "baseline"=Yが文字の下端、"top"=Yが文字の上端（背面の縁で外へはみ出さないように）
lid_labels = [
    ["+12V INPUT",         3.0,  10.0, "baseline", 4.0],  // 前面側 (+12V入力コネクタの上)
    ["PA/PTT Control",  5.0,  60.0, "baseline", 7.0],  // 中央
    ["+12V OUTPUT",        3.0, 115.0, "top",      4.0],  // 背面側 (12V出力コネクタの上)
];
// 文字の大きさはOpenSCADのtext()のsize (大文字の高さはその約0.7倍)
lid_text_h      = 1.0;    // 天板からの盛り上げ高さ
lid_text_font   = "Liberation Sans:style=Bold";

// 3つ目の穴 (背面の角丸長方形穴・中心座標)
hole3_x = 50.0;
hole3_y = 120.0;
hole3_z = 13.6;       // ボス5 + 基板1.6 + 基板面からType-C中心7 (旧7.0)
hole3_w = 15.0;       // 横幅
hole3_h = 6.0;        // 高さ
hole3_r = 1.5;        // 角丸半径

$fn = 60;           // 円や角丸の滑らかさ

// ==========================================
// 自動計算される値
// ==========================================
outer_x = inner_x + (thickness * 2);
outer_y = inner_y + (thickness * 2);
outer_z = inner_z + thickness;

inner_corner_r = max(0.1, corner_r - thickness);

// ボス群をケース中央に配置するためのX/Yオフセット量
offset_x = thickness + (inner_x - pitch_x) / 2;
offset_y = thickness + (inner_y - pitch_y) / 2;

// ==========================================
// モジュール定義
// ==========================================

// --- 角丸の直方体 ---
module rounded_box(w, d, h, r) {
    translate([r, r, 0])
    linear_extrude(height = h)
    offset(r = r)
    square([w - 2*r, d - 2*r]);
}

// --- ボス単体 ---
module mounting_boss() {
    difference() {
        cylinder(d=boss_od, h=boss_h);
        // 内側のくり抜き
        translate([0, 0, -0.5])
            cylinder(d=boss_id, h=boss_h + 1.0);
    }
}

// --- XZ面の角丸長方形をY方向に押し出した穴あけ用形状 ---
module rounded_hole_xz(w, depth, h, r) {
    hull() {
        for (x = [r, w - r])
            for (z = [r, h - r])
                translate([x, 0, z])
                    rotate([-90, 0, 0])
                    cylinder(r = r, h = depth);
    }
}

// --- 4隅のボスレイアウト ---
module boss_layout() {
    translate([0,       0,       0]) mounting_boss(); // 左下
    translate([pitch_x, 0,       0]) mounting_boss(); // 右下
    translate([pitch_x, pitch_y, 0]) mounting_boss(); // 右上
    translate([0,       pitch_y, 0]) mounting_boss(); // 左上
}

// ==========================================
// 本体
// ==========================================
module body() {
    union() {
    // 1. ケース本体
    difference() {
        // 外形
        rounded_box(outer_x, outer_y, outer_z, corner_r);
        
        // 内側のくり抜き
        translate([thickness, thickness, thickness])
            rounded_box(inner_x, inner_y, inner_z + 1, inner_corner_r); 
            
        // --- 1つ目の穴あけ (前面の丸穴) ---
        translate([thickness + hole1_x, -1, thickness + hole1_z])
            rotate([-90, 0, 0])
            cylinder(d=hole_d, h=thickness + 2);
            
        // --- 2つ目の穴あけ (背面の丸穴) ---
        translate([thickness + hole2_x, thickness + hole2_y - 1, thickness + hole2_z])
            rotate([-90, 0, 0])
            cylinder(d=hole_d, h=thickness + 2);

        // --- 3つ目の穴あけ (背面の角丸長方形穴) ---
        translate([
            thickness + hole3_x - hole3_w / 2,
            thickness + hole3_y - 1,
            thickness + hole3_z - hole3_h / 2
        ])
            rounded_hole_xz(hole3_w, thickness + 2, hole3_h, hole3_r);

        // --- 4つ目の穴あけ (前面の角穴) ---
        translate([thickness + notch_x_start, -1, thickness + notch_z_start])
            cube([notch_w, thickness + 2, notch_h]);
    }
    
        // 2. ボス部品の配置
        translate([offset_x, offset_y, thickness]) {
            boss_layout();
        }
    }
}

// ==========================================
// はめ込み蓋
// ==========================================
module lid() {
    lid_outer_x = outer_x + lid_clearance * 2;
    lid_outer_y = outer_y + lid_clearance * 2;
    lid_outer_r = corner_r + lid_clearance;

    // 差し込みリップは本体の内側に入るリング状の形状
    lip_outer_x = inner_x - lid_clearance * 2;
    lip_outer_y = inner_y - lid_clearance * 2;
    lip_outer_r = max(0.1, inner_corner_r - lid_clearance);

    difference() {
        union() {
            // 蓋の天板（z=0から上向き）
            rounded_box(lid_outer_x, lid_outer_y, lid_top_t, lid_outer_r);

            // 天板の上面に盛り上げた文字（前面側から読める向き）
            for (label = lid_labels)
                translate([thickness + label[1], thickness + label[2], lid_top_t - 0.01])
                    linear_extrude(height = lid_text_h + 0.01)
                    text(label[0], size = label[4], font = lid_text_font,
                         halign = "left", valign = label[3]);

            // 蓋の裏側へ伸びる差し込みリップ（z=0より下）
            translate([lid_clearance + (outer_x - inner_x) / 2,
                       lid_clearance + (outer_y - inner_y) / 2,
                       -lid_lip_h])
                difference() {
                    rounded_box(lip_outer_x, lip_outer_y, lid_lip_h, lip_outer_r);
                    translate([lid_lip_wall, lid_lip_wall, -0.5])
                        rounded_box(lip_outer_x - lid_lip_wall * 2,
                                    lip_outer_y - lid_lip_wall * 2,
                                    lid_lip_h + 1,
                                    max(0.1, lip_outer_r - lid_lip_wall));
                }
        }

        // 前面リップの切り欠き（X=20、Y=0）
        translate([thickness + lid_notch_x - lid_notch_w / 2,
                   -1,
                   -lid_lip_h])
            cube([lid_notch_w, lid_lip_wall + 4, lid_notch_h]);

        // 背面リップの切り欠き（X=20、Y=120）
        translate([thickness + lid_notch_x - lid_notch_w / 2,
                   lid_outer_y - lid_lip_wall - 4,
                   -lid_lip_h])
            cube([lid_notch_w, lid_lip_wall + 4, lid_notch_h]);
    }
}

// ==========================================
// 表示モード
// ==========================================
if (mode == 1) {
    body();
} else if (mode == 2) {
    // 蓋だけを正のZ範囲に表示
    translate([0, 0, lid_lip_h])
        lid();
} else if (mode == 3) {
    // 組立状態
    body();
    translate([0, 0, outer_z])
        lid();
} else if (mode == 4) {
    // 分解図：蓋を本体の上方へ移動
    body();
    translate([0, 0, outer_z + explode_offset])
        lid();
}
