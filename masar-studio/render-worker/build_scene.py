"""MASAR -> Blender. Run only this trusted script, never user Python/.blend files.
Usage: blender --background --factory-startup --disable-autoexec --offline-mode
  --python-exit-code 1 --python render-worker/build_scene.py -- --input scene.json --output job-dir
The caller supplies an isolated directory and enforces wall-time/memory/network limits.
"""
import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

SCHEMA = 'masar-render-scene-1'

def validate_scene(scene):
    if not isinstance(scene, dict) or scene.get('schema') != SCHEMA or scene.get('units') != 'm':
        raise ValueError('Unsupported MASAR render contract')
    if scene.get('pipeline') != 'blender-bridge-1.0.0' or scene.get('axes') != 'X-east Y-north Z-up':
        raise ValueError('Unsupported coordinate/pipeline contract')
    objects = scene.get('objects')
    if not isinstance(objects, list) or not 1 <= len(objects) <= 16000:
        raise ValueError('Render object limit exceeded')
    ids = set()
    materials = scene.get('materials', {})
    if set(materials) != {'exterior','interior','floor','frame','glass','wood','fabric','site','paving','water'}:
        raise ValueError('Unknown material catalog')
    for material in materials.values():
        if set(material) - {'color','roughness','metallic','alpha'}:
            raise ValueError('Unsupported material field')
        color = material.get('color')
        if not isinstance(color,str) or len(color) != 7 or color[0] != '#' or any(c not in '0123456789abcdefABCDEF' for c in color[1:]):
            raise ValueError('Invalid color')
        for k in ['roughness','metallic','alpha']:
            v=material.get(k,1)
            if type(v) not in (float,int) or not math.isfinite(v) or not 0 <= v <= 1:
                raise ValueError('Invalid material numeric value')
    for obj in objects:
        if set(obj)-{'id','shape','min','size','material','elementId','roomId','roomIds','levelId','hostWallId','category','displayOnly'}:
            raise ValueError('Unknown object field')
        oid=obj.get('id')
        if not isinstance(oid,str) or not oid or len(oid)>300 or oid in ids:
            raise ValueError('Duplicate/invalid object ID')
        ids.add(oid)
        if obj.get('shape')!='box' or obj.get('material') not in materials:
            raise ValueError('Unknown shape/material')
        for key in ['min','size']:
            value=obj.get(key)
            if not isinstance(value,list) or len(value)!=3 or not all(type(n) in (float,int) and math.isfinite(n) and abs(n)<1024 for n in value):
                raise ValueError('Invalid object geometry')
        if any(n<=0 for n in obj['size']): raise ValueError('Nonpositive size')
        for key in ['elementId','roomId','levelId','hostWallId','category']:
            if key in obj and (not isinstance(obj[key],str) or len(obj[key])>300): raise ValueError('Invalid element metadata')
        if 'roomIds' in obj and (not isinstance(obj['roomIds'],list) or len(obj['roomIds'])>16 or any(not isinstance(i,str) or len(i)>160 for i in obj['roomIds'])):
            raise ValueError('Invalid room links')
    settings=scene.get('settings',{})
    dimensions={'preview':{'width':640,'height':480,'samples':16},'standard':{'width':1280,'height':960,'samples':64}}
    if settings.get('quality') not in dimensions or scene.get('resolution')!=dimensions[settings['quality']]:
        raise ValueError('Unbounded render quality')
    if set(scene.get('cameras',{})) != {'exterior','interior'}: raise ValueError('Two fixed cameras required')
    for c in scene['cameras'].values():
        for key in ['position','target']:
            if not isinstance(c.get(key),list) or len(c[key])!=3 or not all(type(n) in (int,float) and math.isfinite(n) and abs(n)<2048 for n in c[key]):
                raise ValueError('Invalid camera')
        if c.get('lens') not in [20,45]: raise ValueError('Unsupported camera lens')
    return scene

def run(input_path, output):
    import bpy
    from mathutils import Vector
    started=time.monotonic()
    raw=input_path.read_bytes()
    if len(raw)>8_000_000: raise ValueError('Snapshot exceeds 8 MB')
    spec=validate_scene(json.loads(raw))
    if bpy.app.version[:2] != (4,5): raise RuntimeError('Use the pinned Blender 4.5 LTS line')
    output.mkdir(parents=True,exist_ok=True)
    if any((output/name).exists() for name in ['model.blend','model.glb','exterior.png','interior.png','manifest.json']):
        raise ValueError('Refusing to overwrite an existing result')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene
    scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
    scene.render.engine='CYCLES';scene.cycles.device='CPU'
    scene.cycles.samples=spec['resolution']['samples'];scene.cycles.use_denoising=True
    scene.render.resolution_x=spec['resolution']['width'];scene.render.resolution_y=spec['resolution']['height'];scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB'
    scene.render.threads_mode='FIXED';scene.render.threads=2
    scene.view_settings.view_transform='AgX'
    scene.world=bpy.data.worlds.new('MASAR environment');scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.72,.8,.9,1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.4
    source_hash=hashlib.sha256(raw).hexdigest()
    scene['masarSnapshotHash']=source_hash;scene['masarRevisionId']=spec['source']['revisionId']
    materials={}
    def linear(n): return n/12.92 if n<=.04045 else ((n+.055)/1.055)**2.4
    for name,data in spec['materials'].items():
        mat=bpy.data.materials.new(name);mat.use_nodes=True
        color=tuple(linear(int(data['color'][i:i+2],16)/255) for i in (1,3,5))
        bsdf=mat.node_tree.nodes.get('Principled BSDF')
        bsdf.inputs['Base Color'].default_value=(*color,1)
        bsdf.inputs['Roughness'].default_value=data['roughness'];bsdf.inputs['Metallic'].default_value=data['metallic']
        if name=='glass':
            bsdf.inputs['Alpha'].default_value=data.get('alpha',1)
            mat.surface_render_method='DITHERED'
        materials[name]=mat
    built=[]
    for i,entry in enumerate(spec['objects']):
        minimum=entry['min'];size=entry['size']
        # Explicit vertices, not default cubes with residual transforms.
        vertices=[(minimum[0]+x*size[0],minimum[1]+y*size[1],minimum[2]+z*size[2]) for x,y,z in [(0,0,0),(1,0,0),(1,1,0),(0,1,0),(0,0,1),(1,0,1),(1,1,1),(0,1,1)]]
        mesh=bpy.data.meshes.new('geometry-'+str(i));mesh.from_pydata(vertices,[],[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]);mesh.update()
        obj=bpy.data.objects.new('MASAR-'+str(i),mesh);scene.collection.objects.link(obj)
        obj.data.materials.append(materials[entry['material']])
        obj['objectId']=entry['id'];obj['elementId']=entry['elementId'];obj['category']=entry['category'];obj['displayOnly']=entry['displayOnly']
        obj['revisionId']=spec['source']['revisionId']
        for key in ['roomId','roomIds','levelId','hostWallId']:
            if key in entry:obj[key]=entry[key]
        built.append((obj,entry))
    # Read actual mesh coordinates back for every element before any artifact is accepted.
    geometry=[]
    for obj,entry in built:
        coords=[obj.matrix_world @ v.co for v in obj.data.vertices]
        actual_min=[min(v[k] for v in coords) for k in range(3)];actual_max=[max(v[k] for v in coords) for k in range(3)]
        expected_max=[entry['min'][k]+entry['size'][k] for k in range(3)]
        delta=max(abs(a-b) for a,b in zip(actual_min+actual_max,entry['min']+expected_max))
        if delta>0.00005: raise ValueError('Geometry differs from MASAR by more than 0.05 mm')
        geometry.append({'objectId':entry['id'],'elementId':entry['elementId'],'min':actual_min,'max':actual_max,'maxErrorM':delta})
    # Sun and interior area lights are explicit visualization assumptions, not MEP.
    sun=bpy.data.lights.new('Presentation daylight','SUN');sun.energy=2.2;sun.angle=.12
    sun_obj=bpy.data.objects.new('Presentation daylight',sun);scene.collection.objects.link(sun_obj);sun_obj.rotation_euler=(.55,-.45,-.5)
    for i,room in enumerate(spec['proofs']['rooms']):
        poly=room['polygon'];x=sum(p[0] for p in poly)/len(poly);y=sum(p[1] for p in poly)/len(poly)
        light=bpy.data.lights.new('Presentation fill '+str(i),'AREA');light.energy=room['area']*6;light.shape='DISK';light.size=2
        obj=bpy.data.objects.new(light.name,light);scene.collection.objects.link(obj);obj.location=(x,y,room['elevation']+2.6)
        obj['displayOnly']=True
    cameras={}
    for name,c in spec['cameras'].items():
        data=bpy.data.cameras.new(name);data.lens=c['lens'];data.clip_start=.05;data.clip_end=2000
        obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=c['position'];obj.rotation_euler=(Vector(c['target'])-obj.location).to_track_quat('-Z','Y').to_euler();cameras[name]=obj
    scene.camera=cameras['exterior']
    # No textures/downloads/scripts embedded. The generated .blend is operator-editable.
    bpy.ops.wm.save_as_mainfile(filepath=str(output/'model.blend'),check_existing=False)
    bpy.ops.object.select_all(action='DESELECT')
    for obj,_ in built:obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(output/'model.glb'),export_format='GLB',use_selection=True,export_extras=True,export_yup=True,export_animations=False,export_cameras=False,export_lights=False,export_apply=True)
    for name in ['exterior','interior']:
        scene.camera=cameras[name];scene.render.filepath=str(output/(name+'.png'))
        bpy.ops.render.render(write_still=True)
    manifest={'schema':'masar-render-result-1','pipeline':spec['pipeline'],'snapshotHash':source_hash,'source':spec['source'],'blenderVersion':bpy.app.version_string,'engine':'CYCLES','device':'CPU','units':'m','gltfAxes':'X-east Y-up Z-south','settings':spec['settings'],'elapsedSeconds':round(time.monotonic()-started,3),'geometry':geometry,'maxGeometryErrorM':max(g['maxErrorM'] for g in geometry),'disclaimer':spec['disclaimer'],'files':{}}
    for name in ['model.blend','model.glb','exterior.png','interior.png']:
        data=(output/name).read_bytes();manifest['files'][name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
    print('MASAR_RESULT '+json.dumps({'snapshotHash':source_hash,'objects':len(geometry),'maxGeometryErrorM':manifest['maxGeometryErrorM'],'seconds':manifest['elapsedSeconds']}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:])
    run(args.input.resolve(),args.output.resolve())
