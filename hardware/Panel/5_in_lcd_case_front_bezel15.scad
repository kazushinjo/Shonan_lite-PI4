// 5インチLCDケース前面(ベゼル) 縁15mm版
// 窓は v18+2mm と同じ大きさ・位置。窓の縁から外形まで(前面から見た幅)を上下左右とも bezel にし、
// 4隅のボスに M3 インサートナット用の穴をあける。座標は元の STL と同じ(窓の中心 = (1.365, 1.49))

/* [ベゼル] */
bezel_x = 15;        // 左右の縁の幅 (窓の表面側の縁から外形まで)
bezel_y = 15;        // 上下の縁の幅

/* [取り付け穴] */
hole_d     = 5;      // 穴径 (M3 インサートナット用)
hole_depth = 5;      // 穴深さ (ボス上面から)
boss_d     = 6.62;   // ボス外径
wall_gap   = 0;      // 壁とボスのすき間 (0 で壁に接し、隅を四角く埋める)

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

difference() {
  union() {
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
