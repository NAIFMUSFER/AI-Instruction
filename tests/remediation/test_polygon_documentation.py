"""C09d: document the same real polygon as architecture, including its voids."""
import copy
import json
import re
import sys
import unittest
import xml.etree.ElementTree as ET
from test_polygon_gltf import model, L
import acs_authoring as AU
import acs_docs as D
import acs_polygon as G


def bundle(b=None, section=None, upper=False):
    b = model() if b is None else b
    project = AU.create_project(b)
    src = D.sources(project)
    spec = {"view_type":"FLOOR_PLAN", "level_id":src["arch"]["levels"][-1 if upper else 0]["id"],
            "discipline":"ARCHITECTURE", "scale":"1:100", "dimension_policy":"FULL_CHAIN",
            "annotation_policy":"TAGS_ONLY"}
    if section is not None:
        spec.update(view_type="SECTION", cut_plane=section)
    r = D.build_view(project, spec, src)
    assert r["valid"], r
    ops = D.draw_ops(r["view"],r["geometry"],r["dimensions"],r["annotations"],420,297)
    sheet = {"sheet_id":"test", "paper_mm":[420,297], "viewports":[
        {"view_id":r["view"]["view_id"],"x":0,"y":0,"width":420,"height":297}]}
    pdf = D.sheet_pdf([sheet],{r["view"]["view_id"]:ops})
    return {"project":project,"spec":spec,"result":r,"ops":ops,"sheet":sheet,
            "quantities":D.quantities(project,src=src),"pdf_streams":pdf["content_streams"]}


class PolygonDocumentation(unittest.TestCase):
    def test_svg_fill_has_actual_area_and_no_notch(self):
        b=model();before=copy.deepcopy(b);p=bundle(b);r=p["result"]
        s=D.view_svg(r["view"],r["geometry"],r["dimensions"],r["annotations"])["svg"]
        polys=ET.fromstring(s).findall('{http://www.w3.org/2000/svg}polygon')
        filled=[e for e in polys if e.get('fill')!='none']
        self.assertEqual(len(filled),1)
        ring=[[float(v) for v in pair.split(',')] for pair in filled[0].get('points').split()]
        self.assertEqual(len(ring),6)
        self.assertAlmostEqual(abs(G.signed_area(ring)),20*100,places=5)
        self.assertEqual(b,before)

    def test_slab_void_geometry_and_real_quantity(self):
        b=model(objects=[{"kind":"stairs","core_id":"A","x":1,"z":3,"w":1,"d":1}])
        b['levels'].append({"index":1,"template":"plan","elevation":10.2})
        p=bundle(b,upper=True)
        slab=next(e for e in p['result']['geometry']['elements'] if e['category']=='SLAB')
        cells=slab.get('cells',[])
        self.assertAlmostEqual(sum(abs(G.signed_area(c)) for c in cells),19,places=5)
        self.assertFalse(any(G.contains_point(c,[1,3]) for c in cells))
        quantity=next(q for q in p['quantities']['report']['quantities'] if q['quantity_type']=='FLOOR_AREA')
        self.assertEqual(quantity['quantity'],39)

    def test_section_intersects_polygon_not_its_bounding_box(self):
        for axis in ('x','z'):
            with self.subTest(axis=axis):
                p=bundle(section={"axis":axis,"at":4})
                slabs=[e for e in p['result']['geometry']['elements'] if e['category']=='SLAB']
                self.assertEqual([(e['u0'],e['u1']) for e in slabs],[(0,2)])

    def test_room_tag_stays_inside_concave_room(self):
        p=bundle();tags=[a for a in p['result']['annotations']['annotations'] if a['annotation_type']=='ROOM_TAG']
        self.assertEqual(len(tags),1)
        self.assertTrue(G.contains_point(L,[tags[0]['x'],tags[0]['y']]))

    def test_pdf_contains_closed_six_vertex_vector_path(self):
        p=bundle()
        # Inspect the generated PDF stream: a closed six-vertex path, not a bbox re.
        paths=[line for line in p['pdf_streams'][0].splitlines() if ' h S' in line]
        self.assertTrue(paths)
        six=[line for line in paths if len(re.findall(r'\bl\b',line))==5]
        self.assertEqual(len(six),1)
        numbers=[float(n) for n in re.findall(r'-?\d+(?:\.\d+)?',six[0])]
        ring=[numbers[i:i+2] for i in range(0,len(numbers),2)]
        self.assertAlmostEqual(abs(G.signed_area(ring)),2000,places=5)

    def test_slab_has_no_internal_sweep_partition_as_a_boundary(self):
        p=bundle();g=p['result']['geometry'];slab=next(e for e in g['elements'] if e['category']=='SLAB')
        self.assertEqual(slab.get('shape'),'cells')
        ops=D.draw_ops(p['result']['view'],{**g,'elements':[slab]},{},{},420,297)['ops']
        self.assertTrue(ops)
        # No line may cross the room interior; sweep partitions are not physical edges.
        t=p['ops']['transform']
        for op in ops:
            self.assertEqual(op['op'],'line')
            x=(op['x1']+op['x2'])/2; y=(op['y1']+op['y2'])/2
            point=[(x-12)/t['k']+t['ox'],(297-12-y)/t['k']+t['oy']]
            self.assertFalse(G.contains_point(L,point) and not any(G.on_segment(point,a,b) for a,b in G.edges(L)),point)


if __name__=='__main__':
    if '--cases' in sys.argv:
        print(json.dumps([bundle(),bundle(section={'axis':'x','at':4})]))
    else:unittest.main(verbosity=2)
