"""Actual approved glTF read with pinned Three GLTFLoader; numeric geometry oracle.

The reader is independent from Python serialization, not a second display engine.
No IFC/full-BIM or GLB assertion is made for this context fixture.
"""
import copy,hashlib,json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from acs_context_details import get_actual_bounds
from acs_compiler import compile_building
from context_details_fixture import context_fixture,approved_context_fixture

class ContextReader(unittest.TestCase):
    def read(self,path):
        run=subprocess.run(['node','tests/remediation/stairs_gltf_reader.mjs',str(path)],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stderr);return json.loads(run.stdout)
    def test_exact_approved_sources_parts_and_real_extents(self):
        with tempfile.TemporaryDirectory() as temp:
            record=approved_context_fixture(temp);model=json.loads((Path(temp)/'context.canonical.json').read_text());scene=self.read(Path(temp)/record['gltf'])
            sources=[row['source'] for row in record['receipt']['source_map']]
            meshes=[m for m in scene['meshes'] if 'acs_object_source' in m['extras']]
            self.assertEqual(len(meshes),12) # 2 columns + 6 railing boxes + 2 pots + 2 foliage boxes
            grouped={}
            for mesh in meshes:
                source=mesh['extras']['acs_object_source'];self.assertIn(source,sources)
                self.assertEqual(mesh['extras']['acs_object_repeat_index'],0)
                self.assertEqual(len(mesh['indices']),36)
                grouped.setdefault(source['element_id'],[]).append(mesh)
            self.assertEqual(len(grouped),5)
            for room in model['floors']['g']['rooms']:
                for obj in room['objects']:
                    points=[p for mesh in grouped[obj['id']] for p in mesh['vertices']]
                    # Independent literal shape oracle, not helper dimensions.
                    width=obj['w']+.05 if obj['kind']=='railing' else obj['w']
                    height=1.13 if obj['kind']=='railing' else 1.164 if obj['kind']=='plant' else 3
                    expected_min=[room['rect'][0]+obj['x']-width/2,0,room['rect'][1]+obj['z']-obj['d']/2]
                    expected_max=[expected_min[0]+width,height,expected_min[2]+obj['d']]
                    for axis in range(3):
                        self.assertAlmostEqual(min(p[axis] for p in points),expected_min[axis],places=5)
                        self.assertAlmostEqual(max(p[axis] for p in points),expected_max[axis],places=5)
            self.assertEqual(record['receipt']['model_hash'],record['model_hash'])
    def test_cardinal_oblique_repetition_negative_level_bounds(self):
        from acs_compiler import Builder,build_objects
        with tempfile.TemporaryDirectory() as temp:
            for rot in (0,45,90,180,270):
                obj={'id':'authored','kind':'railing','x':0,'z':0,'y':-.2,'w':2.75,'d':.06,'h':1.1,'rot':rot,'count':2,'pitch':2,'dir':'z'}
                b=Builder();b._object_context={'template':'shared','level_index':-2}
                build_objects(b,{'id':'r','rect':[10,20,6,6],'objects':[obj]},'F-2',-3.2)
                path=Path(temp)/('rotation%s.gltf'%rot);b.export_gltf(path);scene=self.read(path);bounds=get_actual_bounds(obj)
                self.assertEqual(len(scene['meshes']),8)
                for index,mesh in enumerate(scene['meshes']):
                    self.assertEqual(mesh['extras']['acs_object_source']['level_index'],-2)
                    self.assertEqual(mesh['extras']['acs_object_repeat_index'],index//4)
                    for axis,offset in enumerate((10,-3.2,20)):
                        self.assertAlmostEqual(min(p[axis] for p in mesh['vertices']),bounds['parts'][index]['min'][axis]+offset,places=5)
                        self.assertAlmostEqual(max(p[axis] for p in mesh['vertices']),bounds['parts'][index]['max'][axis]+offset,places=5)
    def test_metadata_does_not_change_existing_python_geometry_bytes(self):
        # Captured by executing the unchanged compiler at ad45ef1992c85a4aa5309cd1adc12c265d55fff1.
        # This fixes the comparison target even after commit/shallow CI checkout.
        # Hash covers complete serialized buffer/accessor/mesh/material tables.
        baseline_geometry_hash='1ad84b5cbdef189cf55c84989d0245a1e65a0a54ed5e52f0b51c1fcddfe57aa9'
        with tempfile.TemporaryDirectory() as temp:
            model=context_fixture();before=copy.deepcopy(model)
            path=Path(temp)/'current.gltf';compile_building(model,path);doc=json.loads(path.read_text())
            geometry={key:doc[key] for key in ('buffers','bufferViews','accessors','meshes','materials')}
            self.assertEqual(hashlib.sha256(json.dumps(geometry,sort_keys=True,separators=(',',':')).encode()).hexdigest(),baseline_geometry_hash)
            self.assertEqual(model,before)

if __name__=='__main__':unittest.main()
