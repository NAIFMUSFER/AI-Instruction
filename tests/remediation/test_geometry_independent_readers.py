"""Required external reader acceptance. No skip when IfcOpenShell is absent.

Test dependency: ifcopenshell==0.9.0.post1 (CI only); production stays unchanged.
IFC uses X/Y plan and Z up; canonical/glTF uses X/Z plan and Y up.
The declared 2D CAD projection maps canonical Z to negative CAD Y.
"""
import json,tempfile,unittest,sys
from pathlib import Path
import ifcopenshell, ifcopenshell.geom, ifcopenshell.validate
import ezdxf
from tools.generate_delivery_fixtures import main as generate, fixtures

def existing_apartment():
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'phase9_2'))
    from lib_ad_fixtures import apartment_model
    return apartment_model()

def apartment_reader_fixture():
    """New explicit synthetic design, not facts inferred from old placeholders.

    Reuses the existing two7x9m units and balcony footprints. Each unit now has
    declared rooms, reciprocal doors, lighting and0.2m wall thickness. Only one
    apartment floor is represented; stairs to another floor are not claimed.
    """
    b=existing_apartment(); b['meta']={'type':'residential','name':'Synthetic apartment floor — explicitly authored test variant'}
    b['wall_t']=.2;b['wall_h']=3.05;b['levels']=[{'index':0,'template':'t','elevation':0}]
    old=b['floors']['t']['rooms'];rooms=[]
    def door(edge,offset):return {'edge':edge,'offset':offset,'width':1,'height':2.1,'material':'wood'}
    for i in range(2):
        x=i*7
        rows=[('living','living',[x,0,4,5],[door('N',2),door('E',1.5),door('E',4),door('S',2)]),
              ('kitchen','kitchen',[x+4,0,3,3],[door('W',1.5),door('S',1.5)]),
              ('bath','bathroom',[x+4,3,3,2],[door('W',1),door('N',1.5),door('S',1.5)]),
              ('bed','bedroom',[x,5,4,4],[door('N',2),door('E',2),door('S',3.5)]),
              ('hall','corridor',[x+4,5,3,4],[door('N',1.5),door('W',2)])]
        for name,role,rect,doors in rows:
            rooms.append({'id':f'unit{i}_{name}','name':name,'role':role,'rect':rect,'doors':doors,'windows':[]})
        balcony=next(r for r in old if r['id']==f'bal{i}');balcony['doors']=[door('N',2)];balcony['windows']=[];rooms.append(balcony)
    for r in rooms:
        r['points']=[{'id':'fixture_light','type':'light','x':r['rect'][2]/2,'z':r['rect'][3]/2}]
        for collection in ('doors','windows','objects'):
            for i,element in enumerate(r.get(collection,[])):
                element['id']=r['id']+'_'+collection+'_'+str(i)
                if collection=='objects':element.update({'y':0,'count':1,'pitch':1,'dir':'x','rot':0})
    b['floors']['t']['rooms']=rooms
    return b

class IndependentGeometryReaders(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)
        cls.models={**fixtures(),'apartment':apartment_reader_fixture()};generate(cls.root,cls.models)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def test_original_apartment_missing_dimension_is_not_approved(self):
        from acs_plan_lock_binding import PlanLockWorkspace
        from acs_plan_bridge import existing_geometry_verifier
        model=existing_apartment()
        area=sum(r['rect'][2]*r['rect'][3] for l in model['levels'] for r in model['floors'][l['template']]['rooms'])
        ws=PlanLockWorkspace(existing_geometry_verifier)
        rev=ws.propose(model,brief='Original synthetic apartment admission',requirements=[{'id':'area','metric':'building_target_area_m2','expected':area,'source':'requested','evidence':str(area)}],expected_head=None,note='Original unchanged negative fixture')
        review=ws.review(rev.id)
        self.assertFalse(review['can_approve'])
        self.assertIn({'code':'DIMENSION_NOT_SPECIFIED','path':'/wall_t','severity':'error'},review['issues'])
    def test_ifc_schema_world_bounds_and_instances(self):
        for name,model in self.models.items():
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
    def test_explicit_roof_with_non_prefixed_ids_in_ifc_dxf_pdf_and_gltf(self):
        import acs_roof
        from acs_plan_lock_binding import PlanLockWorkspace
        from acs_plan_bridge import existing_geometry_verifier
        from acs_plan_projection import project
        from tools.acs_plan_handoff import compile_approved_baseline
        from tools.acs_plan_ifc_export import export_approved_ifc
        from tools.acs_plan_cad_export import export_approved_cad
        from tools.acs_plan_pdf_export import export_approved_pdf
        from pypdf import PdfReader
        base=fixtures()['villa'];model,report=acs_roof.add_flat_roof_level(base)
        roof=model['levels'][-1];roof.pop('auto')
        rooms=model['floors'][roof['template']]['rooms']
        for i,room in enumerate(rooms):room['id']='declared_deck_'+str(i)
        area=sum(r['rect'][2]*r['rect'][3] for l in base['levels'] for r in base['floors'][l['template']]['rooms'])
        ws=PlanLockWorkspace(existing_geometry_verifier)
        rev=ws.propose(model,brief=f'Synthetic area {area}',requirements=[{'id':'area','metric':'building_target_area_m2','expected':area,'source':'requested','evidence':str(area)}],expected_head=None,note='Explicit roof export acceptance')
        self.assertTrue(ws.review(rev.id)['can_approve'])
        ws.approve(rev.id,expected_head=rev.id,confirmed=True,acknowledge_concept_only=True,actor_label='synthetic-reader')
        out=self.root/'roof-reader';out.mkdir()
        export_approved_ifc(ws,rev.id,out/'roof.ifc')
        export_approved_cad(ws,rev.id,roof['index'],out/'roof.dxf')
        export_approved_pdf(ws,rev.id,out/'roof.pdf')
        compile_approved_baseline(ws,rev.id,out/'roof.gltf')
        f=ifcopenshell.open(str(out/'roof.ifc'))
        logger=ifcopenshell.validate.json_logger();ifcopenshell.validate.validate(f,logger)
        self.assertEqual(logger.statements,[])
        spaces=[s for s in f.by_type('IfcSpace') if s.LongName.startswith('declared_deck_')]
        self.assertEqual(len(spaces),len(rooms))
        settings=ifcopenshell.geom.settings();settings.set(settings.USE_WORLD_COORDS,True)
        for space in spaces:
            shape=ifcopenshell.geom.create_shape(settings,space);v=shape.geometry.verts
            room=next(r for r in rooms if r['id']==space.LongName);x,z,w,d=room['rect']
            expected=((x,x+w),(z,z+d),(roof['elevation'],roof['elevation']+.9))
            for axis,(low,high) in enumerate(expected):
                self.assertAlmostEqual(min(v[axis::3]),low,places=6)
                self.assertAlmostEqual(max(v[axis::3]),high,places=6)
        cad=ezdxf.readfile(out/'roof.dxf');self.assertEqual(cad.audit().errors,[])
        polygons=list(cad.modelspace().query('LWPOLYLINE'));self.assertEqual(len(polygons),len(rooms))
        for poly,room in zip(polygons,rooms):
            xy=list(poly.get_points('xy'));xs=[p[0] for p in xy];ys=[p[1] for p in xy]
            self.assertTrue(poly.closed);x,z,w,d=room['rect']
            for actual,expected in zip((min(xs),max(xs),min(ys),max(ys)),(x,x+w,-z-d,-z)):
                self.assertAlmostEqual(actual,expected,places=6)
        text='\n'.join(page.extract_text() or '' for page in PdfReader(out/'roof.pdf').pages)
        self.assertIn('Roof deck, unoccupied - Level '+str(roof['index']),text)
        projection=project(rev.revision,roof['index']);self.assertEqual(projection['level_kind'],'roof');self.assertFalse(projection['level_auto'])
        gltf=json.loads((out/'roof.gltf').read_text());metadata=gltf['scenes'][0]['extras']['acs_levels']
        self.assertEqual([l['index'] for l in metadata if l['kind']=='roof'],[roof['index']])
        self.assertEqual(ws.get(rev.id).model_hash,rev.model_hash)

    def test_dxf_boundaries_match_declared_rectangles(self):
        for name,model in self.models.items():
            for l in model['levels']:
                f=ezdxf.readfile(self.root/(name+f"-F{l['index']}.dxf"));self.assertEqual(f.audit().errors,[])
                polylines=list(f.modelspace().query('LWPOLYLINE'))
                self.assertEqual(len(polylines),len(model['floors'][l['template']]['rooms']))
                expected=sorted((r['rect'][0],-r['rect'][1]-r['rect'][3],r['rect'][2],r['rect'][3]) for r in model['floors'][l['template']]['rooms'])
                actual=[]
                for pl in polylines:
                    self.assertTrue(pl.closed);pts=list(pl.get_points('xy'));xs=[v[0] for v in pts];ys=[v[1] for v in pts]
                    actual.append((min(xs),min(ys),max(xs)-min(xs),max(ys)-min(ys)))
                for actual_rect,expected_rect in zip(sorted(actual),expected):
                    for actual_value,expected_value in zip(actual_rect,expected_rect):
                        self.assertAlmostEqual(actual_value,expected_value,places=6)
if __name__=='__main__':unittest.main()
