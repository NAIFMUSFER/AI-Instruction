"""C13: use canonical host coordinates once, in real SVG and its source views."""
import copy
import math
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import acs_arch as A
import acs_docs as D
import acs_authoring as AU


def model(edge="N",width=1):
    opening={"edge":edge,"offset":3,"height":2.1}
    if width is not None:opening["width"]=width
    return {"site":{"w":30,"d":25},"wall_h":3,"wall_t":.15,"floor_height":3.2,
            "levels":[{"index":0,"template":"g","elevation":0}],
            "floors":{"g":{"rooms":[{"id":"offset-room","rect":[10,5,6,6],"doors":[opening]}]}}}


def fixture_views():
    project=AU.create_project(model())
    src=D.sources(project);level=src["arch"]["levels"][0]["id"]
    common={"discipline":"ARCHITECTURE","scale":"1:100","dimension_policy":"NONE","annotation_policy":"NONE"}
    views={}
    for key,spec in {"plan":{"view_type":"FLOOR_PLAN","level_id":level},
                     "elevation":{"view_type":"ELEVATION","orientation":"NORTH"},
                     "section":{"view_type":"SECTION","cut_plane":{"axis":"x","at":13}}}.items():
        views[key]=D.build_view(project,{**common,**spec},src)
        if not views[key]["valid"]:raise AssertionError(views[key])
    return project,src,views


class SvgOpeningOrigin(unittest.TestCase):
    def test_four_edges_keep_canonical_opening_centres(self):
        for edge,expected in [("N",[13,5]),("S",[13,11]),("E",[16,8]),("W",[10,8])]:
            with self.subTest(edge=edge):
                b=model(edge);before=copy.deepcopy(b);arch=A.compile_architecture(b)
                g=D._opening_plan(arch["openings"][0],arch)
                centre=[(g["start"][i]+g["end"][i])/2 for i in (0,1)]
                self.assertEqual(centre,expected)
                self.assertEqual(b,before)

    def test_split_wall_start_is_subtracted_instead_of_room_origin(self):
        b=model("S");b["floors"]["g"]["rooms"][0]["rect"]=[0,0,10,4]
        b["floors"]["g"]["rooms"][0]["doors"][0]["offset"]=5
        b["floors"]["g"]["rooms"].append({"id":"neighbour","rect":[3,4,4,4]})
        arch=A.compile_architecture(b);op=arch["openings"][0]
        host=A.element_by_id(arch,op["host_wall_id"]);self.assertEqual(host["u0"],3)
        g=D._opening_plan(op,arch)
        self.assertEqual(g["start"],[4.5,4]);self.assertEqual(g["end"],[5.5,4])

    def test_oblique_host_and_unknown_width_point(self):
        from test_polygon_architecture import adjacent_triangles
        arch=A.compile_architecture(adjacent_triangles());g=D._opening_plan(arch["openings"][0],arch)
        for i in (0,1):self.assertAlmostEqual((g["start"][i]+g["end"][i])/2,3,places=5)
        arch=A.compile_architecture(model(width=None));g=D._opening_plan(arch["openings"][0],arch)
        self.assertEqual((g["shape"],g["x"],g["z"],g["width"]),("point",13,5,None))

    def test_svg_door_remains_centred_in_its_host(self):
        _,_,views=fixture_views();r=views["plan"]
        svg=D.view_svg(r["view"],r["geometry"],r["dimensions"],r["annotations"])["svg"]
        lines=ET.fromstring(svg).findall('{http://www.w3.org/2000/svg}line')
        walls=[line for line in lines if line.get('data-cls')=='CUT' and line.get('y1')==line.get('y2')]
        self.assertEqual(len(walls),2)
        north=max(walls,key=lambda line:float(line.get('y1')))
        doors=[line for line in lines if line.get('data-cls')=='ANNOTATION']
        self.assertEqual(len(doors),1)
        centre=lambda line:(float(line.get('x1'))+float(line.get('x2')))/2
        self.assertAlmostEqual(centre(doors[0]),centre(north),places=5)
        self.assertEqual(doors[0].get('y1'),north.get('y1'))

    def test_elevation_and_section_use_the_correct_door_projection(self):
        _,_,views=fixture_views()
        door=next(e for e in views['elevation']['geometry']['elements'] if e['category']=='DOOR')
        self.assertEqual((door['u0'],door['u1']),(12.5,13.5))
        door=next(e for e in views['section']['geometry']['elements'] if e['category']=='DOOR')
        self.assertEqual(door['geometry_class'],'CUT')
        self.assertEqual((door['u0'],door['u1']),(4.95,5.05))


if __name__=="__main__":unittest.main(verbosity=2)
