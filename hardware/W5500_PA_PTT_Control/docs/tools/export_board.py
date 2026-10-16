"""KiCad 付属の Python で実行: 基板の外形・部品（F.Fab 外形・パッド）を JSON に書き出す（make_parts_layout.py 用）。PSN_TRX・Serrasoid_TRX と同じもの"""
import pcbnew, sys, json
b = pcbnew.LoadBoard(sys.argv[1]); mm = pcbnew.ToMM
def shp(g):
    s = g.GetShape(); d = {'w': mm(g.GetWidth())}
    if s == pcbnew.SHAPE_T_SEGMENT: d.update(t='seg', a=mm(g.GetStart()), b=mm(g.GetEnd()))
    elif s == pcbnew.SHAPE_T_RECT: d.update(t='poly', p=[mm(c) for c in g.GetRectCorners()])
    elif s == pcbnew.SHAPE_T_CIRCLE: d.update(t='circ', c=mm(g.GetCenter()), r=mm(g.GetRadius()), fill=bool(g.IsSolidFill()))
    elif s == pcbnew.SHAPE_T_ARC: d.update(t='arc3', a=mm(g.GetStart()), m=mm(g.GetArcMid()), b=mm(g.GetEnd()))
    elif s == pcbnew.SHAPE_T_POLY:
        ps = g.GetPolyShape(); d.update(t='poly', p=[mm(ps.CVertex(i)) for i in range(ps.TotalVertices())], fill=bool(g.IsSolidFill()))
    else: return None
    return d
out = {'edge': [], 'fps': [], 'blocks': []}
for d in b.GetDrawings():
    if d.GetLayer() == pcbnew.Edge_Cuts:
        x = shp(d); x and out['edge'].append(x)
SH = {pcbnew.PAD_SHAPE_CIRCLE: 'circle', pcbnew.PAD_SHAPE_RECT: 'rect', pcbnew.PAD_SHAPE_OVAL: 'oval', pcbnew.PAD_SHAPE_ROUNDRECT: 'rrect'}
for f in b.GetFootprints():
    side = 'B' if f.GetLayer() == pcbnew.B_Cu else 'F'
    FAB = pcbnew.F_Fab if side == 'F' else pcbnew.B_Fab; SILK = pcbnew.F_SilkS if side == 'F' else pcbnew.B_SilkS
    CY = pcbnew.F_CrtYd if side == 'F' else pcbnew.B_CrtYd
    fab = [shp(g) for g in f.GraphicalItems() if g.GetLayer() == FAB and g.GetClass() == 'PCB_SHAPE']
    if not fab: fab = [shp(g) for g in f.GraphicalItems() if g.GetLayer() == SILK and g.GetClass() == 'PCB_SHAPE']
    pads = [{'n': p.GetNumber(), 'c': mm(p.GetPosition()), 'sz': mm(p.GetSize(pcbnew.F_Cu)), 'ang': p.GetOrientationDegrees(),
             'sh': SH.get(p.GetShape(pcbnew.F_Cu), 'rect'), 'drill': mm(p.GetDrillSize().x)} for p in f.Pads()]
    cy = f.GetCourtyard(CY); bb = cy.BBox() if cy.OutlineCount() else f.GetBoundingBox(False)
    out['fps'].append({'ref': f.GetReference(), 'val': f.GetValue(), 'side': side, 'pos': mm(f.GetPosition()),
                       'fab': [x for x in fab if x], 'pads': pads, 'bbox': [mm(bb.GetOrigin()), mm(bb.GetEnd())]})
texts = [(d.GetText(), mm(d.GetPosition())) for d in b.GetDrawings() if d.GetClass() == 'PCB_TEXT' and d.GetLayer() == pcbnew.Dwgs_User]
for d in b.GetDrawings():
    if d.GetLayer() == pcbnew.Dwgs_User and d.GetClass() == 'PCB_SHAPE':
        a, c = mm(d.GetStart()), mm(d.GetEnd())
        for t, p in texts:
            if abs(p[0] - (a[0] + 1)) < 2 and abs(p[1] - (a[1] + 1)) < 2: out['blocks'].append({'name': t, 'a': a, 'b': c})
json.dump(out, open(sys.argv[2], 'w'), ensure_ascii=False)
print(len(out['fps']), 'footprints')
