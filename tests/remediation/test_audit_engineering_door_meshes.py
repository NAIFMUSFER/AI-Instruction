"""باب مشترك واحد في glTF؛ سجلا الغرفتين يبقيان في النموذج والمصدر.

No geometry repair, model mutation or regulatory interpretation. Compare the
actual exported vertices, preserve different dimensions/materials/semantics,
and never merge same-face records or more than one reciprocal pair.
"""
import base64
import collections
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import subprocess
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import acs_compiler as C


def model():
    def room(name, x, edge):
        return {"id": name, "rect": [x, 0, 4, 4], "walls": [],
                "doors": [{"id": name + "-door", "edge": edge, "offset": 2,
                           "width": .9, "height": 2.1, "material": "wood"}],
                "windows": [], "points": [{"type": "light", "x": 2, "z": 2}]}
    return {"site": {"w": 8, "d": 4}, "wall_h": 3, "wall_t": .2,
            "floor_height": 3.2, "levels": [{"index": 0, "template": "g"}],
            "floors": {"g": {"rooms": [room("left", 0, "E"), room("right", 4, "W")]}}}


def rooms(m):
    return m["floors"]["g"]["rooms"]


def render(m):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "model.gltf"
        C.compile_building(m, path)
        return json.loads(path.read_text())


def doors(gltf):
    return [n for n in gltf["nodes"] if n["name"].startswith("DOOR|")]


class SharedDoorMeshes(unittest.TestCase):
    def test_reciprocal_door_has_one_mesh_and_both_source_records(self):
        m = model()
        import acs_validate
        self.assertEqual(acs_validate.validate_building(m)[0], [])
        before = copy.deepcopy(m)
        g = render(m)
        self.assertEqual(len(doors(g)), 1)
        sources = doors(g)[0]["extras"]["acs_opening_sources"]
        self.assertEqual({s["opening_id"] for s in sources}, {"left-door", "right-door"})
        self.assertEqual({s["node_name"] for s in sources}, {"DOOR|F0|left|0", "DOOR|F0|right|0"})
        self.assertEqual({s["edge"] for s in sources}, {"E", "W"})
        self.assertEqual(m, before)
        self.assertEqual(g, render(m))

    def test_north_south_reciprocal_pair_is_also_one_mesh(self):
        m = model()
        rooms(m)[1]["rect"] = [0, 4, 4, 4]
        rooms(m)[0]["doors"][0]["edge"] = "S"
        rooms(m)[1]["doors"][0]["edge"] = "N"
        self.assertEqual(len(doors(render(m))), 1)

    def test_different_geometry_and_semantics_are_preserved(self):
        for key, value in (("offset", 2.001), ("width", .91), ("height", 2.2),
                           ("material", "glass"), ("material", "steel"),
                           ("color", "#ff0000"), ("swing", "outward"),
                           ("hinge", "right")):
            with self.subTest(key=key, value=value):
                m = model()
                rooms(m)[1]["doors"][0][key] = value
                self.assertEqual(len(doors(render(m))), 2)

    def test_dimensions_differing_below_float32_resolution_are_preserved(self):
        m = model()
        rooms(m)[1]["doors"][0]["width"] += 1e-10
        self.assertEqual(len(doors(render(m))), 2)

    def test_distinct_centers_with_identical_written_vertices_are_preserved(self):
        m = model()
        rooms(m)[1]["rect"][0] += 1e-15
        self.assertEqual(len(doors(render(m))), 2)

    def test_same_face_records_are_not_silently_deleted(self):
        m = model()
        rooms(m)[1]["rect"] = list(rooms(m)[0]["rect"])
        rooms(m)[1]["doors"][0]["edge"] = "E"
        self.assertEqual(len(doors(render(m))), 2)

    def test_distinct_floor_identities_are_preserved_even_at_same_elevation(self):
        m = model()
        m["floor_height"] = 0
        m['floors']['upper'] = copy.deepcopy(m['floors']['g'])
        rooms(m)[1]['doors'] = []
        m['floors']['upper']['rooms'][0]['doors'] = []
        m["levels"].append({"index": 1, "template": "upper"})
        g = render(m)
        self.assertEqual(len(doors(g)), 2)
        self.assertEqual({n["name"].split("|")[1] for n in doors(g)}, {"F0", "F1"})

    def test_each_reciprocal_pair_can_be_consumed_only_once(self):
        for which in (0, 1):
            m = model()
            duplicate = copy.deepcopy(rooms(m)[which]["doors"][0])
            duplicate["id"] = "another-leaf"
            rooms(m)[which]["doors"].append(duplicate)
            g = render(m)
            self.assertEqual(len(doors(g)), 2)
            self.assertEqual(sum(len(n.get("extras", {}).get("acs_opening_sources", [None])) for n in doors(g)), 3)

    def test_ambiguous_room_ids_are_not_silently_combined(self):
        m = model()
        rooms(m)[1]['id'] = 'left'
        self.assertEqual(len(doors(render(m))), 2)

    def test_legacy_openings_without_ids_keep_index_sources(self):
        m = model()
        for r in rooms(m):
            del r['doors'][0]['id']
        sources = doors(render(m))[0]['extras']['acs_opening_sources']
        self.assertEqual(len(sources), 2)
        self.assertEqual({s['opening_index'] for s in sources}, {0})

    def test_nonpositive_leaf_remains_unrendered(self):
        m = model()
        rooms(m)[0]['doors'][0]['width'] = 0
        self.assertEqual(len(doors(render(m))), 1)

    def test_input_order_preserves_physical_geometry_and_source_set(self):
        m = model()
        first = render(m)
        rooms(m).reverse()
        second = render(m)
        def content(g):
            n = doors(g)[0]
            prim = g["meshes"][n["mesh"]]["primitives"][0]
            a = g["accessors"][prim["attributes"]["POSITION"]]
            v = g["bufferViews"][a["bufferView"]]
            raw = base64.b64decode(g["buffers"][0]["uri"].split(",")[1])
            return (raw[v["byteOffset"]:v["byteOffset"]+v["byteLength"]],
                    {s["opening_id"] for s in n["extras"]["acs_opening_sources"]})
        self.assertEqual(content(first), content(second))


def mutations():
    import inspect
    original = inspect.getsource(C.Builder.add_door_box)
    import textwrap
    original = textwrap.dedent(original)
    cases = [
        ('pairing disabled', 'sources.append(source)', 'return'),
        ('opposite face', "first['edge'] == opposite.get(edge)", 'True'),
        ('one pair only', 'len(sources) == 1', 'True'),
        ('distinct room sources', "first['room_id'] != room_id", 'True'),
        ('optional legacy identity', "if 'id' in opening:", 'if True:'),
        ('positive leaf', 'if ex <= 0 or ey <= 0 or ez <= 0:', 'if False:'),
        ('floor identity', '(fkey, cx, cy, cz, ex, ey, ez, mat, semantics)', '(cx, cy, cz, ex, ey, ez, mat, semantics)'),
        ('exact dimensions', '(fkey, cx, cy, cz, ex, ey, ez, mat, semantics)', '(fkey, cx, cy, cz, mat, semantics)'),
        ('semantic distinctions', '(fkey, cx, cy, cz, ex, ey, ez, mat, semantics)', '(fkey, cx, cy, cz, ex, ey, ez, mat)'),
        ('exact centers', '(fkey, cx, cy, cz, ex, ey, ez, mat, semantics)', '(fkey, p.tobytes(), ex, ey, ez, mat, semantics)'),
    ]
    for name, old, new in cases:
        assert original.count(old) == 1, name
        namespace = vars(C).copy()
        exec(original.replace(old, new), namespace)
        with patch.object(C.Builder, 'add_door_box', namespace['add_door_box']):
            result = unittest.TextTestRunner(stream=io.StringIO()).run(
                unittest.defaultTestLoader.loadTestsFromTestCase(SharedDoorMeshes))
        assert not result.wasSuccessful(), 'SURVIVED: ' + name
        print('KILLED', name)
    source = textwrap.dedent(inspect.getsource(C.Builder.export_gltf))
    assert source.count('if len(sources) > 1:') == 1
    namespace = vars(C).copy()
    exec(source.replace('if len(sources) > 1:', 'if False:'), namespace)
    with patch.object(C.Builder, 'export_gltf', namespace['export_gltf']):
        result = unittest.TextTestRunner(stream=io.StringIO()).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(SharedDoorMeshes))
    assert not result.wasSuccessful(), 'SURVIVED: exported source aliases'
    print('KILLED exported source aliases')
    print('MUTATIONS', len(cases)+1, 'killed')


def load_baseline(revision, filename):
    source = subprocess.check_output(['git', 'show', revision + ':' + filename], cwd=ROOT).decode()
    mod = types.ModuleType('audit_old_' + filename.removesuffix('.py'))
    mod.__file__ = str(ROOT / filename)
    sys.modules[mod.__name__] = mod
    exec(compile(source, mod.__file__, 'exec'), mod.__dict__)
    return mod


def corpus(revision):
    from test_validate_against_real_models import _walk
    import acs_plan_bridge as bridge
    old = load_baseline(revision, 'acs_compiler.py')
    old_bridge = load_baseline(revision, 'acs_plan_bridge.py')
    counts = collections.Counter()
    old_errors = []
    def parts(compiler, m):
        captured = []
        def capture(builder, path):
            captured.extend(builder.parts)
            return len(builder.parts), 0
        try:
            with patch.object(compiler.Builder, 'export_gltf', capture), contextlib.redirect_stdout(io.StringIO()):
                compiler.compile_building(m, 'unused')
        except Exception as exc:
            return (type(exc).__name__, str(exc)), []
        return None, [tuple(a.tobytes() for a in part[:4]) + part[4:] for part in captured]
    for path in sorted((ROOT / 'tests').rglob('*.json')):
        try:
            data = json.loads(path.read_text())
        except Exception:
            continue
        for pointer, m in _walk(data):
            counts['models'] += 1
            label = str(path.relative_to(ROOT)) + '::' + pointer
            before = copy.deepcopy(m)
            old_error, old_parts = parts(old, m)
            error, new_parts = parts(C, m)
            assert (error, new_parts) == parts(C, m), ('nondeterminism', label)
            assert m == before, ('input mutation', label)
            assert error == old_error, ('new exception', label, error, old_error)
            if error:
                old_errors.append([label, error])
            else:
                counts['compiled'] += 1
                old_other = collections.Counter(p for p in old_parts if not p[-1].startswith('DOOR|'))
                new_other = collections.Counter(p for p in new_parts if not p[-1].startswith('DOOR|'))
                assert old_other == new_other, ('non-door change', label)
                old_doors = collections.Counter(p for p in old_parts if p[-1].startswith('DOOR|'))
                new_doors = collections.Counter(p for p in new_parts if p[-1].startswith('DOOR|'))
                assert not new_doors - old_doors, ('changed/new leaf geometry', label)
                for removed in (old_doors-new_doors):
                    assert any(removed[:-1] == p[:-1] for p in new_doors), ('lost distinct geometry', label)
                removed = sum((old_doors-new_doors).values())
                counts['removed_reciprocal_door_meshes'] += removed
                counts['models_with_pairs'] += bool(removed)
            def review(fn):
                try:
                    r = fn(m)
                    return r['scopes'], r['issues']
                except Exception as exc:
                    return type(exc).__name__, str(exc)
            assert review(bridge.existing_geometry_verifier) == review(old_bridge.existing_geometry_verifier), ('review invariant', label)
            assert m == before, ('review mutation', label)
    assert counts['models'] >= 165, counts
    print(json.dumps({'counts': counts, 'unchanged_compiler_exceptions': old_errors}, ensure_ascii=False, indent=2))


def live_evidence(directory):
    """Read authorized synthetic captures; raw downloads stay outside git."""
    import hashlib
    import xml.etree.ElementTree as ET
    import numpy as np
    import acs_arch
    import acs_bim
    import acs_validate
    import ezdxf
    from acs_plan_bridge import existing_geometry_verifier
    root = Path(directory)
    report = {'capture_directory': str(root), 'artifacts': {}}
    for kind in ('ifc', 'gltf', 'dxf', 'svg'):
        raw = (root / ('apartment-approved.' + kind)).read_bytes()
        manifest = json.loads((root / ('apartment-' + kind + '-manifest.json')).read_text())
        digest = hashlib.sha256(raw).hexdigest()
        assert (len(raw), digest) == (manifest['artifact_bytes'], manifest['artifact_sha256'])
        report['artifacts'][kind] = {'bytes': len(raw), 'sha256': digest,
            'model_hash': manifest['model_hash'], 'revision_id': manifest['revision_id'],
            'scope': manifest.get('ifc_scope', manifest.get('projection_scope', '3D')),
            'approval_scope': manifest['approval_scope'],
            'regulatory_compliance': manifest['regulatory_compliance'],
            'structural_safety': manifest['structural_safety']}
    parsed = acs_bim.parse_step((root / 'apartment-approved.ifc').read_text())
    assert parsed['valid']
    ents = list(parsed['step']['entities'].values())
    report['ifc'] = {'parser_valid': parsed['valid'], 'issues': parsed['issues'],
        'units': acs_bim.resolve_units(parsed['step']),
        'entities': collections.Counter(e['type'] for e in ents),
        'storey_elevations': [e['args'][-1] for e in ents if e['type'] == 'IFCBUILDINGSTOREY']}
    drawing = ezdxf.readfile(root / 'apartment-approved.dxf')
    audit = drawing.audit()
    report['dxf'] = {'units': drawing.units, 'errors': len(audit.errors), 'fixes': len(audit.fixes),
                     'entities': collections.Counter(e.dxftype() for e in drawing.modelspace())}
    svg = ET.parse(root / 'apartment-approved.svg').getroot()
    report['svg'] = dict(collections.Counter(e.tag.split('}')[-1] for e in svg.iter()))
    def gltf_census(g):
        raw = base64.b64decode(g['buffers'][0]['uri'].split(',')[1])
        assert len(raw) == g['buffers'][0]['byteLength']
        arrays = []
        for a in g['accessors']:
            v = g['bufferViews'][a['bufferView']]
            dtype = {5126: '<f4', 5125: '<u4'}[a['componentType']]
            dims = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3}[a['type']]
            offset = v.get('byteOffset', 0) + a.get('byteOffset', 0)
            size = a['count'] * dims * 4
            assert 0 <= offset and offset + size <= len(raw)
            assert a.get('byteOffset', 0) + size <= v['byteLength']
            arr = np.frombuffer(raw, dtype=dtype, count=a['count']*dims, offset=offset).reshape(-1, dims)
            assert np.isfinite(arr).all()
            for op in ('min', 'max'):
                if op in a:
                    assert getattr(arr, op)(axis=0).tolist() == a[op]
            arrays.append(arr)
        positions = []
        for n in doors(g):
            p = g['meshes'][n['mesh']]['primitives'][0]
            positions.append(arrays[p['attributes']['POSITION']].tobytes())
        for mesh in g['meshes']:
            for p in mesh['primitives']:
                indices = arrays[p['indices']]
                assert len(indices) % 3 == 0
                assert indices.max() < len(arrays[p['attributes']['POSITION']])
        return {'node_types': collections.Counter(n['name'].split('|')[0] for n in g['nodes']),
                'nodes': len(g['nodes']), 'buffer_bytes': len(raw), 'accessors': len(arrays),
                'buffer_index_errors': 0, 'distinct_door_vertex_sets': len(set(positions)),
                'door_meshes': len(positions), 'duplicate_vertex_excess': len(positions)-len(set(positions)),
                'paired_source_records': sum(len(n.get('extras', {}).get('acs_opening_sources', [])) for n in doors(g))}
    report['downloaded_gltf'] = gltf_census(json.loads((root / 'apartment-approved.gltf').read_text()))
    for name in ('apartment', 'multilevel'):
        revision = json.loads((root / (name + '-revision.json')).read_text())[0]['revision_json']
        m = revision['model']
        before = copy.deepcopy(m)
        arch = acs_arch.compile_architecture(m, 'bld_0', None, 0)
        report[name] = {'site': m['site'], 'levels': m['levels'],
            'template_rooms': {t: len(f['rooms']) for t, f in m['floors'].items()},
            'validator': acs_validate.validate_building(m),
            'coverage': existing_geometry_verifier(m)['coverage'],
            'architecture_core_count': len(arch['cores']), 'architecture_void_count': len(arch['voids']),
            'architecture_issues': arch['issues'], 'local_recompiled_gltf': gltf_census(render(m))}
        assert m == before
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if '--mutations' in sys.argv:
        mutations()
    elif '--corpus' in sys.argv:
        corpus(sys.argv[sys.argv.index('--corpus')+1])
    elif '--evidence' in sys.argv:
        live_evidence(sys.argv[sys.argv.index('--evidence')+1])
    else:
        unittest.main(verbosity=2)
