"""Required external reader acceptance. No skip when IfcOpenShell is absent.

Test dependency: ifcopenshell==0.9.0.post1 (CI only); production stays unchanged.
IFC uses X/Y plan and Z up; canonical/glTF uses X/Z plan and Y up.
The declared 2D CAD projection maps canonical Z to negative CAD Y.
"""
import json,tempfile,unittest
from pathlib import Path
import ifcopenshell, ifcopenshell.geom, ifcopenshell.validate
import ezdxf
from tools.generate_delivery_fixtures import main as generate, fixtures

class IndependentGeometryReaders(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name);generate(cls.root)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def test_ifc_schema_world_bounds_and_instances(self):
        for name,model in fixtures().items():
            f=ifcopenshell.open(str(self.root/(name+'.ifc')))
            logger=ifcopenshell.validate.json_logger();ifcopenshell.validate.validate(f,logger)
            self.assertEqual(logger.statements,[],str(logger.statements))
            self.assertEqual(f.schema,'IFC4');self.assertFalse(f.by_type('IfcWall'))
            spaces=f.by_type('IfcSpace');self.assertEqual(len(spaces),sum(len(model['floors'][l['template']]['rooms']) for l in model['levels']))
            self.assertEqual(len({s.GlobalId for s in spaces}),len(spaces))
            settings=ifcopenshell.geom.settings();settings.set(settings.USE_WORLD_COORDS,True)
            expected=[]
            for l in model['levels']:
                for r in model['floors'][l['template']]['rooms']:
                    x,z,w,d=r['rect'];h=r.get('wall_h',model['wall_h']);y=l.get('elevation',l['index']*model['floor_height'])
                    expected.append((r['id'],[[x,x+w],[z,z+d],[y,y+h]]))
            actual=[]
            for s in spaces:
                shape=ifcopenshell.geom.create_shape(settings,s);v=shape.geometry.verts
                bounds=[[round(min(v[i::3]),6),round(max(v[i::3]),6)] for i in range(3)]
                actual.append((s.LongName,bounds))
            self.assertEqual(sorted(actual),sorted(expected))
    def test_dxf_boundaries_match_declared_rectangles(self):
        for name,model in fixtures().items():
            for l in model['levels']:
                f=ezdxf.readfile(self.root/(name+f"-F{l['index']}.dxf"));self.assertEqual(f.audit().errors,[])
                polylines=list(f.modelspace().query('LWPOLYLINE'))
                self.assertEqual(len(polylines),len(model['floors'][l['template']]['rooms']))
                expected=sorted((r['rect'][0],-r['rect'][1]-r['rect'][3],r['rect'][2],r['rect'][3]) for r in model['floors'][l['template']]['rooms'])
                actual=[]
                for pl in polylines:
                    self.assertTrue(pl.closed);pts=list(pl.get_points('xy'));xs=[v[0] for v in pts];ys=[v[1] for v in pts]
                    actual.append((min(xs),min(ys),max(xs)-min(xs),max(ys)-min(ys)))
                self.assertEqual(sorted(actual),expected)
if __name__=='__main__':unittest.main()
