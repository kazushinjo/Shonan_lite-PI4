// 5インチLCDケース前面(ベゼル) 縁15mm版
// 窓は v18+2mm と同じ大きさ・位置。窓の縁から外形まで(前面から見た幅)を上下左右とも bezel にし、
// 4隅のボスに M3 インサートナット用の穴をあける。DFR0550 用に4隅の L 字ガイドを付ける。
// 裏蓋は 1mm のパネルを挟んでベゼルのインサートに M3 で締める。DFR0550 の裏に Pi4 を載せる前提。座標は元の STL と同じ(窓の中心 = (1.365, 1.49))

/* [出力] */
// 1: ベゼル(印刷用)  2: 裏蓋(印刷用、背面を下に置いた向き)  3: 組み立て確認(パネル・DFR0550・Pi4 は半透明)
// 4: 1mm パネルの切り抜き(2D、DXF 書き出し用)
mode = 1;

/* [ベゼル] */
bezel_x = 15;        // 左右の縁の幅 (窓の表面側の縁から外形まで)
bezel_y = 15;        // 上下の縁の幅

/* [取り付け穴] */
hole_d     = 5;      // 穴径 (M3 インサートナット用)
hole_depth = 5;      // 穴深さ (ボス上面から)
boss_d     = 6.62;   // ボス外径
wall_gap   = 0;      // 壁とボスのすき間 (0 で壁に接し、隅を四角く埋める)

/* [DFR0550 位置決めガイド] */
dfr_guide = true;            // DFR0550 (DFRobot 5" DSI) の位置決めガイドを付ける
dfr_size  = [120.8, 75.8];   // DFR0550 の外形
dfr_c     = [1.365, 3.85];   // DFR0550 の中心 (= 取付穴 113×68 の中心)。表示領域が窓の中央に来る位置
guide_gap = 0.3;             // DFR0550 とガイドのすき間 (片側)
guide_t   = 1.2;             // ガイドの厚さ
guide_len = 12;              // L字の腕の長さ (外側の角から)
guide_h   = 4;               // ガイドの高さ (板の上面から。液晶部の厚さ 5.7 より低くする)

/* [裏蓋 (1mm パネルを挟んで M3 で締める)] */
panel_t     = 1;       // 挟むパネルの厚さ
bc_wall     = 2;       // 裏蓋の壁厚
bc_plate    = 2;       // 裏蓋の背面の板の厚さ
bc_clear    = 2;       // Pi4 の一番高い部品(USB)と背面の板のすき間
m3_clear_d  = 3.4;     // M3 ネジの通し穴
m3_head_d   = 6.5;     // M3 ネジ頭の座ぐり
m3_seat     = 3;       // 座ぐりの底の厚さ (ネジは M3×8 くらい)
col_d       = 8;       // M3 ネジ用の柱の径
dfr_post    = true;    // DFR0550 の外側取付穴(113×68)の支柱を裏から押さえる柱を付ける
post_d      = 6;       // その柱の径
post_gap    = 0.2;     // 柱の先と DFR0550 の支柱の先のすき間
m25_clear_d = 2.7;     // M2.5 ネジの通し穴 (柱から DFR0550 の支柱にネジ止めもできる)
m25_head_d  = 5;       // M2.5 ネジ頭の座ぐり
vent        = true;    // 背面の板に通気用のスリットをあける
gpio_slot   = true;    // GPIO の配線を出すスリット (+Y の壁)
gpio_window = true;    // GPIO ヘッダーの真上の背面に窓をあけ、裏蓋を付けたまま外からコネクタを差せるようにする
usbc_direct = true;    // Pi4 の USB-C の正面に、外から普通のケーブルをまっすぐ差せる筒状の穴を作る
usbc_tunnel = [16, 11];// 筒の内側の幅・高さ (プラグの根元のモールドが通る大きさ)
usbc_tube_t = 1.5;     // 筒の壁厚
usbc_panel  = false;   // パネル取り付け型 USB-C 延長ケーブルのメス側を -Y の壁に付ける穴 (筒を使わないとき)
usbc_cut    = [11, 5]; // メス側の本体を通す穴 (角丸の長穴)。使う延長ケーブルに合わせて変える
usbc_pitch  = 28;      // 固定ネジの間隔 (0 でネジ穴なし)
usbc_screw  = 3.2;     // 固定ネジの穴径
usbc_x      = -42;     // 取り付け位置 X。Pi4 の USB-C の正面を避け、ケーブルを曲げて回せる位置にする

/* [DFR0550・Pi4 の高さ (DFRobot 公式 CAD の値)] */
dfr_lcd_t = 5.7;       // 液晶部の厚さ (パネルに当たる面から基板まで)
dfr_pcb_t = 1.6;       // 基板の厚さ
dfr_so_h  = 5;         // 裏の支柱の長さ (M2.5)
pi_pcb_t  = 1.4;       // Pi4 の基板の厚さ
pi_tall   = 16;        // Pi4 の一番高い部品 (USB) の基板からの高さ
// Pi4 は DFR0550 の内側取付穴(58×49)に、部品面を裏蓋側に向けて付ける。
// DSI コネクタが DFR0550 の DISPLAY コネクタ(-X 側)に近い向きで、USB/LAN は +X、USB-C/HDMI は -Y を向く。
pi_org = [dfr_c[0] - 34.32, dfr_c[1] - 28.0];   // Pi4 の基板の角 (USB-C/HDMI 側・DSI 側) の位置

/* [固定値: 元形状] */
win_c     = [1.365, 1.49];     // 窓の中心
win_front = [111.552, 68.288]; // 窓 表面側 (Z=0)
win_cham  = 1;                 // 窓の面取り C1 (奥側は 109.552 × 66.288)
plate     = 1.5;               // 前面の板の厚さ
wall      = 1.5;               // 壁厚
height    = 8;                 // 全高 (ボス上面)
edge_cham = 1;                 // 前面外周の面取り C1
corner_r  = 1;                 // 外形の角 R
$fn = 72;

outer = [win_front[0] + 2*bezel_x, win_front[1] + 2*bezel_y];
inner = [outer[0] - 2*wall, outer[1] - 2*wall];
off   = boss_d/2 + wall_gap;
boss_pos = [for (sx=[1,-1], sy=[1,-1]) [win_c[0] + sx*(inner[0]/2 - off), win_c[1] + sy*(inner[1]/2 - off)]];
echo(str("外形 = ", outer[0], " x ", outer[1], " x ", height));
echo(str("穴ピッチ = ", inner[0] - 2*off, " x ", inner[1] - 2*off));
for (p=boss_pos) echo(str("ボス中心 = ", p));
if (dfr_guide) echo(str("DFR0550 ガイドの内側 = X ", dfr_c[0]-dfr_size[0]/2-guide_gap, " 〜 ", dfr_c[0]+dfr_size[0]/2+guide_gap,
                        "  Y ", dfr_c[1]-dfr_size[1]/2-guide_gap, " 〜 ", dfr_c[1]+dfr_size[1]/2+guide_gap));

module rrect(size, r) {
  if (r <= 0) square(size, center=true);
  else offset(r=r) square([size[0]-2*r, size[1]-2*r], center=true);
}

module outer_body() {   // 前面外周 C1、角 R1
  hull() {
    linear_extrude(0.01) rrect([outer[0]-2*edge_cham, outer[1]-2*edge_cham], max(corner_r-edge_cham, 0));
    translate([0,0,edge_cham]) linear_extrude(height-edge_cham) rrect(outer, corner_r);
  }
}

module window_cut() {   // 表面側が広い C1 の面取り
  hull() {
    translate([0,0,-0.01]) linear_extrude(0.01) square(win_front, center=true);
    translate([0,0,win_cham]) linear_extrude(0.01) square([win_front[0]-2*win_cham, win_front[1]-2*win_cham], center=true);
  }
  translate([0,0,win_cham]) linear_extrude(plate) square([win_front[0]-2*win_cham, win_front[1]-2*win_cham], center=true);
}

// DFR0550 の4隅に置く L 字のガイド。下側(+Y、FPC 側)の FPC・コネクタ(左端から 27〜94)を避けるため隅だけにする
module dfr_guides() {
  g = [dfr_size[0]/2 + guide_gap, dfr_size[1]/2 + guide_gap];
  for (sx=[1,-1], sy=[1,-1]) translate([dfr_c[0] + sx*g[0], dfr_c[1] + sy*g[1], plate-0.01])
    mirror([sx<0 ? 1 : 0, 0, 0]) mirror([0, sy<0 ? 1 : 0, 0]) {
      translate([-(guide_len-guide_t), 0, 0]) cube([guide_len, guide_t, guide_h+0.01]);
      translate([0, -(guide_len-guide_t), 0]) cube([guide_t, guide_len, guide_h+0.01]);
    }
}

module bezel() {
  difference() {
    union() {
      if (dfr_guide) dfr_guides();
      translate(win_c) difference() {
        outer_body();
        translate([0,0,plate]) linear_extrude(height) square(inner, center=true);   // 内側の空間
        window_cut();
      }
      for (p=boss_pos) translate([p[0],p[1],plate-0.01]) {
        cylinder(d=boss_d, h=height-plate+0.01);                                     // ボス
        if (wall_gap == 0)   // 隅側を四角く埋めて壁と一体にする
          let(sx=sign(p[0]-win_c[0]), sy=sign(p[1]-win_c[1]))
            translate([sx<0 ? -off-0.05 : 0, sy<0 ? -off-0.05 : 0, 0]) cube([off+0.05, off+0.05, height-plate+0.01]);
      }
    }
    for (p=boss_pos) translate([p[0],p[1],height-hole_depth]) cylinder(d=hole_d, h=hole_depth+0.1);  // M3 インサート穴
  }
}

// ---------------- 裏蓋 ----------------
z_panel  = height;                                   // パネルの表面 (ベゼルの縁)
z_bc     = height + panel_t;                         // 裏蓋がパネルに当たる面
z_dfr_so = plate + dfr_lcd_t + dfr_pcb_t + dfr_so_h; // DFR0550 の支柱の先 (Pi4 の基板の下面)
z_pi_top = z_dfr_so + pi_pcb_t + pi_tall;            // Pi4 の一番高い部品の上
z_bc_in  = z_pi_top + bc_clear;                      // 裏蓋の内側の天井
z_bc_top = z_bc_in + bc_plate;                       // 裏蓋の背面
dfr_holes = [for (sx=[1,-1], sy=[1,-1]) [dfr_c[0] + sx*56.5, dfr_c[1] + sy*34]];
echo(str("裏蓋の高さ = ", z_bc_top - z_bc, "  (パネル裏から背面まで)"));

// 開口 [x0, x1, y0, y1, z0, z1] (STL の座標)
pi_x1 = pi_org[0] + 85;
// プラグの根元のモールドが当たらないよう、壁の開口は下の縁(パネル側)まで切り欠く
op_usb   = [pi_x1 - 1, outer[0], pi_org[1] + 1, pi_org[1] + 55, z_bc - 1, z_pi_top + 1.3];                    // USB/LAN (+X)
op_power = [pi_org[0] + 21.5, pi_org[0] + 61, -outer[1], pi_org[1] + 1, z_bc - 1, z_dfr_so + pi_pcb_t + 8];      // HDMI・音声 (-Y)
z_usbc   = (z_bc + z_bc_in) / 2;                                                                               // USB-C 延長のメス側の高さ
usbc_c   = [pi_org[0] + 11.2, z_dfr_so + pi_pcb_t + 1.6];   // Pi4 の USB-C の中心 (X, Z)
usbc_y1  = pi_org[1] - 1.5;                                  // 筒の奥の端 (Pi4 の基板の縁の少し手前)
op_gpio  = [pi_org[0] + 18, pi_org[0] + 48, pi_org[1] + 40, outer[1], z_pi_top - 8, z_pi_top - 1];          // GPIO の配線 (+Y)

module box_cut(o) { translate([o[0], o[2], o[4]]) cube([o[1]-o[0], o[3]-o[2], o[5]-o[4]]); }

module back_cover() {
  difference() {
    union() {
      translate([win_c[0], win_c[1], z_bc]) difference() {
        linear_extrude(z_bc_top - z_bc) rrect(outer, corner_r);
        translate([0, 0, -0.01]) linear_extrude(z_bc_in - z_bc + 0.01) square([outer[0]-2*bc_wall, outer[1]-2*bc_wall], center=true);
      }
      for (p=boss_pos) translate([p[0], p[1], z_bc]) {                 // M3 ネジ用の柱 (ベゼルのボスと同じ位置)
        cylinder(d=col_d, h=z_bc_in - z_bc + 0.01);
        let(sx=sign(p[0]-win_c[0]), sy=sign(p[1]-win_c[1]))
          translate([sx<0 ? -col_d/2-1 : 0, sy<0 ? -col_d/2-1 : 0, 0]) cube([col_d/2+1, col_d/2+1, z_bc_in - z_bc + 0.01]);
      }
      if (dfr_post) for (p=dfr_holes) translate([p[0], p[1], z_dfr_so + post_gap]) cylinder(d=post_d, h=z_bc_in - z_dfr_so - post_gap + 0.01);
      if (usbc_direct)   // USB-C へまっすぐ通る筒
        translate([usbc_c[0] - usbc_tunnel[0]/2 - usbc_tube_t, win_c[1] - outer[1]/2, z_bc])
          cube([usbc_tunnel[0] + 2*usbc_tube_t, usbc_y1 - (win_c[1] - outer[1]/2), usbc_c[1] + usbc_tunnel[1]/2 + usbc_tube_t - z_bc]);
    }
    // 外に出る部分を外形で切りそろえる
    translate([win_c[0], win_c[1], z_bc - 1]) difference() {
      cube([outer[0] + 20, outer[1] + 20, 200], center=true);
      linear_extrude(100) rrect(outer, corner_r);
    }
    for (p=boss_pos) translate([p[0], p[1], 0]) {
      translate([0, 0, z_bc - 1]) cylinder(d=m3_clear_d, h=100);
      translate([0, 0, z_bc + m3_seat]) cylinder(d=m3_head_d, h=100);
    }
    if (dfr_post) for (p=dfr_holes) translate([p[0], p[1], 0]) {
      translate([0, 0, z_dfr_so]) cylinder(d=m25_clear_d, h=100);
      translate([0, 0, z_dfr_so + post_gap + 3]) cylinder(d=m25_head_d, h=100);
    }
    box_cut(op_usb);
    box_cut(op_power);
    if (gpio_slot) box_cut(op_gpio);
    if (gpio_window) translate([pi_org[0] + 4, pi_org[1] + 47.5, z_bc_in - 1]) cube([57, 10, bc_plate + 2]);   // GPIO の窓 (40ピンのフラットケーブル用コネクタも通る幅)
    if (usbc_direct)
      translate([usbc_c[0] - usbc_tunnel[0]/2, win_c[1] - outer[1]/2 - 1, usbc_c[1] - usbc_tunnel[1]/2])
        cube([usbc_tunnel[0], usbc_y1 - (win_c[1] - outer[1]/2) + 1.1, usbc_tunnel[1]]);
    if (usbc_panel) translate([usbc_x, win_c[1] - outer[1]/2 - 1, z_usbc]) rotate([-90, 0, 0]) {
      hull() for (s=[-1,1]) translate([s*(usbc_cut[0]-usbc_cut[1])/2, 0, 0]) cylinder(d=usbc_cut[1], h=bc_wall + 2);
      if (usbc_pitch > 0) for (s=[-1,1]) translate([s*usbc_pitch/2, 0, 0]) cylinder(d=usbc_screw, h=bc_wall + 2);
    }
    if (vent) for (i=[0:6]) translate([pi_org[0] + 12 + i*9, pi_org[1] + 6, z_bc_in - 1]) cube([3, 36, bc_plate + 2]);
  }
}

// ---------------- パネル (1mm) の切り抜き ----------------
panel_cut = [dfr_size[0] + 1.6, dfr_size[1] + 1.6];   // DFR0550 の外形 + 片側 0.8
module panel_2d() {
  difference() {
    translate(win_c) rrect([outer[0] + 20, outer[1] + 20], 2);        // パネル (図示用の範囲)
    translate(dfr_c) square(panel_cut, center=true);
    translate([dfr_c[0] - 34, dfr_c[1] + dfr_size[1]/2]) square([71, 2]); // +Y 辺の FPC・コネクタ逃げ
    for (p=boss_pos) translate(p) circle(d=m3_clear_d);
  }
}

// ---------------- 組み立て確認用の部品 ----------------
module dfr_dummy() {
  translate([dfr_c[0], dfr_c[1], plate]) {
    translate([0, 0, dfr_lcd_t/2]) cube([dfr_size[0], dfr_size[1], dfr_lcd_t], center=true);
    translate([0, 0, dfr_lcd_t + dfr_pcb_t/2]) cube([dfr_size[0], dfr_size[1], dfr_pcb_t], center=true);
  }
  for (p=dfr_holes) translate([p[0], p[1], z_dfr_so - dfr_so_h]) cylinder(d=4.5, h=dfr_so_h, $fn=6);
}
module pi_dummy() {
  translate([pi_org[0], pi_org[1], z_dfr_so]) {
    cube([85, 56, pi_pcb_t]);
    translate([85 - 21, 2, pi_pcb_t]) cube([21 + 2, 52, pi_tall]);      // USB/LAN
    translate([7, 50, pi_pcb_t]) cube([51, 5, 8.5]);                     // GPIO
  }
}

if (mode == 1) bezel();
else if (mode == 2) translate([0, 0, z_bc_top]) rotate([180, 0, 0]) back_cover();
else if (mode == 3) {
  bezel();
  back_cover();
  %translate([0, 0, z_panel]) linear_extrude(panel_t) panel_2d();
  %dfr_dummy();
  %pi_dummy();
}
else if (mode == 4) panel_2d();
