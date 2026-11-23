"""Read actual serialized stairs with Three's loader, then check explicit math.

Expected boxes, projected triangle clipping and plate coverage below do not call
the stair resolver/compiler geometry helpers. This is a second parser path, not
a second display engine. Supported exchange here is .gltf, not .glb or IFC stairs.
"""
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from stairs_delivery_fixture import canonical_fixture, approved_fixture
from acs_compiler import compile_building

TOL = 1e-5


def turn(x, z, degrees):
    return ((x, z), (-z, x), (-x, -z), (z, -x))[int(degrees / 90) % 4]


def rect_world(rect, obj, room):
    x, z, w, d = rect
    p = [turn(a, b, obj['rot']) for a, b in ((x,z),(x+w,z),(x+w,z+d),(x,z+d))]
    xs = [v[0]+room['rect'][0]+obj['x'] for v in p]
    zs = [v[1]+room['rect'][1]+obj['z'] for v in p]
    return [min(xs), min(zs), max(xs)-min(xs), max(zs)-min(zs)]


def expected_boxes(obj, room):
    # Independently specified fixture: 18 equal risers, 8 treads/flight.
    rise = obj['h']/18
    result = {}
    for flight in (1, 2):
        for i in range(1, 9):
            top = i*rise if flight == 1 else obj['h']/2+i*rise
            z = -1+(i-.5)*.25 if flight == 1 else 1-(i-.5)*.25
            result['f%d_t%02d' % (flight, i)] = ((-.5 if flight == 1 else .5, top-rise/2, z), (.9,rise,.25))
    result['mid_landing'] = ((0,obj['h']/2-.075,1.45),(1.9,.15,.9))
    output = {}
    for identity, (center, size) in result.items():
        points=[]
        for dx in (-.5,.5):
            for dy in (-.5,.5):
                for dz in (-.5,.5):
                    x,z=turn(center[0]+size[0]*dx,center[2]+size[2]*dz,obj['rot'])
                    points.append([room['rect'][0]+obj['x']+x,
                                   obj['stair']['source_elevation_m']+center[1]+size[1]*dy,
                                   room['rect'][1]+obj['z']+z])
        output[identity] = ([min(p[k] for p in points) for k in range(3)],
                            [max(p[k] for p in points) for k in range(3)], size)
    return output


def triangles(mesh):
    p=mesh['vertices']; idx=mesh['indices']
    assert len(idx)%3==0
    return [[p[idx[i+j]] for j in range(3)] for i in range(0,len(idx),3)]


def clipped_area(tri, rect):
    # Sutherland-Hodgman clipping of the decoded horizontal triangle in X/Z.
    points=[(p[0],p[2]) for p in tri]
    x,z,w,d=rect
    for axis, bound, sign in ((0,x,1),(0,x+w,-1),(1,z,1),(1,z+d,-1)):
        output=[]
        if not points:return 0
        for a,b in zip(points,points[1:]+points[:1]):
            ina=(a[axis]-bound)*sign>=0; inb=(b[axis]-bound)*sign>=0
            if ina:output.append(a)
            if ina!=inb:
                t=(bound-a[axis])/(b[axis]-a[axis])
                output.append(tuple(a[k]+t*(b[k]-a[k]) for k in range(2)))
        points=output
    return abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points,points[1:]+points[:1])))/2


def surface_area(meshes, height, region):
    return sum(clipped_area(t,region) for m in meshes for t in triangles(m)
               if all(abs(p[1]-height)<TOL for p in t))


def read_artifact(path):
    result=subprocess.run(['node',str(ROOT/'tests/remediation/stairs_gltf_reader.mjs'),str(path)],
                          cwd=ROOT,check=True,capture_output=True,text=True)
    return json.loads(result.stdout)


class SerializedStairs(unittest.TestCase):
    def assert_model(self, model, decoded):
        meshes=decoded['meshes']; stair_meshes=[m for m in meshes if m['extras'].get('acs_stair')]
        physical_ids=[]; expected_count=0
        for level in model['levels']:
            for room in model['floors'][level['template']]['rooms']:
                for obj in room.get('objects',[]):
                    if obj.get('form')!='u_return':continue
                    expected=expected_boxes(obj,room); expected_count+=17
                    prefix='OBJ|F%d|%s|%s|'%(level['index'],room['id'],obj['id'])
                    actual={m['name'][len(prefix):]:m for m in meshes if m['name'].startswith(prefix)}
                    self.assertEqual(set(actual),set(expected),'all 16 treads and the mid landing must be serialized')
                    for identity,(lo,hi,size) in expected.items():
                        mesh=actual[identity]; physical_ids.append(mesh['name'])
                        self.assertEqual(len(triangles(mesh)),12)
                        self.assertEqual(mesh['extras']['acs_stair'],{
                            'source_level_index':level['index'],'target_level_index':obj['stair']['target_level_index'],
                            'room_id':room['id'],'object_id':obj['id'],'component_id':identity,
                            'role':'mid_landing' if identity=='mid_landing' else 'tread'})
                        for k in range(3):
                            self.assertAlmostEqual(min(p[k] for p in mesh['vertices']),lo[k],delta=TOL)
                            self.assertAlmostEqual(max(p[k] for p in mesh['vertices']),hi[k],delta=TOL)
                        area=0
                        for tri in triangles(mesh):
                            self.assertTrue(any(all(abs(p[k]-bound)<TOL for p in tri) for k in range(3) for bound in (lo[k],hi[k])), 'triangle must lie on an expected box face')
                            a,b,c=tri;u=[b[k]-a[k] for k in range(3)];v=[c[k]-a[k] for k in range(3)]
                            area+=math.sqrt(sum(q*q for q in (u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])))/2
                        self.assertAlmostEqual(area,2*(size[0]*size[1]+size[0]*size[2]+size[1]*size[2]),delta=TOL)
                    opening=rect_world([-.95,-1,1.9,2.9],obj,room)
                    arrival=rect_world([-.95,-1.9,1.9,.9],obj,room)
                    source=level['index']; target=obj['stair']['target_level_index']
                    for prefix,height in [
                        ('FLOOR|F%d|slab|'%target,obj['stair']['target_elevation_m']),
                        ('FLOOR|F%d|%s|plate_'%(target,room['id']),obj['stair']['target_elevation_m']+.024),
                        ('FLOOR|F%d|%s|ceil_'%(source,room['id']),obj['stair']['source_elevation_m']+2.995),
                    ]:
                        selected=[m for m in meshes if m['name'].startswith(prefix)]
                        self.assertTrue(selected,prefix+' must not be silently omitted')
                        self.assertAlmostEqual(surface_area(selected,height,opening),0,delta=TOL,msg=prefix+' blocks the physical opening')
                        self.assertAlmostEqual(surface_area(selected,height,arrival),1.71,delta=TOL,msg=prefix+' loses or duplicates the arrival/entry strip')
        self.assertEqual(len(stair_meshes),expected_count)
        self.assertEqual(len(set(physical_ids)),expected_count,'physical instance source IDs must be unique')

    def test_cardinal_rotations_exact_triangles_and_finish_openings(self):
        with tempfile.TemporaryDirectory() as directory:
            for edge in ('N','E','S','W'):
                with self.subTest(edge=edge):
                    model=canonical_fixture(edge=edge);path=Path(directory)/(edge+'.gltf')
                    compile_building(model,path);self.assert_model(model,read_artifact(path))

    def test_negative_nonuniform_repeated_instances_and_two_cores(self):
        levels=[{'index':9,'template':'shared','elevation':-3.2},
                {'index':-2,'template':'shared','elevation':0},
                {'index':3,'template':'shared','elevation':3.6}]
        model=canonical_fixture(levels=levels,two_cores=True,edge='E')
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'instances.gltf';compile_building(model,path)
            decoded=read_artifact(path);self.assert_model(model,decoded)
            self.assertEqual([(v['index'],v['elevation_m']) for v in decoded['scene']['acs_levels']],[(9,-3.2),(-2,0),(3,3.6)])

    def test_approved_artifact_hash_and_stairs_same_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            record=approved_fixture(directory)
            model=json.loads((Path(directory)/'stairs.canonical.json').read_text())
            decoded=read_artifact(Path(directory)/record['gltf'])
            self.assert_model(model,decoded)
            self.assertEqual(record['physical_traversal'],'NOT_VERIFIED')
            # Real handoff verification checks the embedded baseline hash; no
            # locally fabricated approval or custom geometry verifier is used.
            self.assertEqual(record['receipt']['model_hash'],record['model_hash'])

    def test_reader_detects_serialized_blocked_hole_and_missing_arrival(self):
        model=canonical_fixture()
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'mutated.gltf';compile_building(model,path)
            original=json.loads(path.read_text())
            # A serialized node transform copies the intact ground slab over
            # the intended upper opening. The external reader must apply that
            # transform, and triangle intersection must catch the obstruction.
            blocked=json.loads(json.dumps(original))
            source=next(node for node in blocked['nodes'] if node['name'].startswith('FLOOR|F0|slab|'))
            blocked['nodes'].append({'name':'FLOOR|F1|slab|injected','mesh':source['mesh'],'translation':[0,3.2,0]})
            blocked['scenes'][0]['nodes'].append(len(blocked['nodes'])-1)
            path.write_text(json.dumps(blocked))
            with self.assertRaisesRegex(AssertionError,'blocks the physical opening'):
                self.assert_model(model,read_artifact(path))
            path.write_text(json.dumps(original));decoded=read_artifact(path)
            arrival_names={m['name'] for m in decoded['meshes']
                           if m['name'].startswith('FLOOR|F1|slab|') and
                           surface_area([m],3.2,[1.05,.1,1.9,.9])>TOL}
            self.assertTrue(arrival_names)
            original['scenes'][0]['nodes']=[i for i in original['scenes'][0]['nodes']
                                           if original['nodes'][i]['name'] not in arrival_names]
            path.write_text(json.dumps(original))
            with self.assertRaisesRegex(AssertionError,'loses or duplicates the arrival'):
                self.assert_model(model,read_artifact(path))


if __name__=='__main__':unittest.main()
