"""Required independent reader for one approved computed residential stair case.

CI-only dependency: ifcopenshell==0.9.0.post1. Missing dependency is a hard
import failure, never a skip or an internal-parser substitute. The IFC artifact
contains spaces and unoccupied roof reference zones; no physical stair/roof BIM.
"""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element
import ifcopenshell.util.placement
import ifcopenshell.util.unit
import ifcopenshell.validate

from acs_plan_persisted_commands import execute_persisted_plan_command
from acs_plan_review import canonical, digest
from acs_plan_store import SQLitePlanStore
from acs_plan_store_port import SQLitePlanStoreAdapter
from acs_residential_layout import propose
import acs_workspace_service as workspace_service
from tools.acs_plan_ifc_export import export_approved_ifc
from test_connected_workspace import ACTOR, PROJECT, Runner, command
from test_residential_layout_fallback import program


def physical_ifc_id(model_hash, canonical_id):
    """Independent implementation of the repository's declared identity contract.

    The reader itself supplies schema, placement and solid interpretation; no
    exporter parser or geometry routine is used to inspect the serialized file.
    """
    alphabet = json.loads((ROOT / 'acs_bim.json').read_text())['global_id_alphabet']
    seed = json.dumps({'m': model_hash, 'id': canonical_id, 's': 'IFC4'},
                      ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    value = int(hashlib.sha256(seed.encode('utf-8')).hexdigest()[:32], 16)
    return ''.join(alphabet[(value >> shift) & 63] for shift in range(126, -1, -6))


class ConnectedStairIfcReader(unittest.TestCase):
    def test_approved_fallback_exports_exact_physical_spaces_only(self):
        brief = 'عمارة دورين، كل دور شقتين. جهة الشارع: جنوب'
        requirements = program()
        candidate = propose(brief, requirements)
        self.assertIsNotNone(candidate)
        runner = Runner(candidate)  # Deterministic synthetic reply; no provider.
        with tempfile.TemporaryDirectory(prefix='acs-stair-ifc-reader-') as directory:
            root = Path(directory)
            database = SQLitePlanStore(root / 'plans.sqlite3')
            database.create_project(PROJECT, owner_id=ACTOR)
            store = SQLitePlanStoreAdapter(database)
            revision_id = workspace_service.generate_and_save(
                store, PROJECT, ACTOR,
                dict(command(), brief=brief, requirements=requirements, max_provider_calls=6),
                runner=runner)
            approved = execute_persisted_plan_command(
                store, PROJECT,
                {'action': 'approve', 'expected_head': revision_id,
                 'confirmed': True, 'acknowledge_concept_only': True},
                actor_id=ACTOR, verifier=workspace_service.existing_geometry_verifier)
            self.assertEqual(approved['baseline'], revision_id)
            # Reopen through the persisted connected adapter before exporting.
            reopened_store = SQLitePlanStoreAdapter(SQLitePlanStore(root / 'plans.sqlite3'))
            workspace = workspace_service.workspace(reopened_store, PROJECT, ACTOR)
            revision = workspace.get(revision_id)
            model = revision.model
            before = canonical(model)
            self.assertEqual(digest(model), revision.model_hash)
            stairs = [o for f in model['floors'].values() for r in f['rooms']
                      for o in r.get('objects', []) if o.get('form') == 'u_return']
            self.assertTrue(stairs, 'the regression must exercise the new canonical stairs')
            self.assertTrue(any('stair_source_template' in level for level in model['levels']))

            path = root / 'approved-spaces.ifc'
            receipt = export_approved_ifc(workspace, revision_id, path)
            self.assertEqual(receipt['ifc_scope'], 'SPACES_ONLY')
            self.assertEqual(receipt['revision_id'], revision_id)
            self.assertEqual(receipt['model_hash'], revision.model_hash)
            self.assertEqual(receipt['artifact_sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
            parsed = ifcopenshell.open(str(path))
            self.assertEqual(parsed.schema, 'IFC4')
            logger = ifcopenshell.validate.json_logger()
            ifcopenshell.validate.validate(parsed, logger)
            self.assertEqual(logger.statements, [], str(logger.statements))
            self.assertEqual(ifcopenshell.util.unit.calculate_unit_scale(parsed), 1.0)

            expected_storeys, expected_spaces, expected_roofs = {}, {}, {}
            for level in model['levels']:
                elevation = level.get('elevation', level['index'] * model['floor_height'])
                level_source = 'bld_0.flr_' + str(level['index'])
                storey_id = physical_ifc_id(revision.model_hash, 'bld_0.flr_' + str(level['index']))
                is_roof = level.get('kind') == 'roof'
                if not is_roof:
                    expected_storeys[storey_id] = elevation
                for room in model['floors'][level['template']]['rooms']:
                    source = 'bld_0.flr_%s.%s.%s' % (level['index'], level['template'], room['id'])
                    space_id = physical_ifc_id(revision.model_hash, source)
                    self.assertNotIn(space_id, expected_spaces)
                    self.assertNotIn(space_id, expected_roofs)
                    x, z, width, depth = room['rect']
                    height = room.get('wall_h', room.get('height', model['wall_h']))
                    target = expected_roofs if is_roof else expected_spaces
                    target[space_id] = (level_source if is_roof else storey_id, room['id'],
                        ((x, x + width), (z, z + depth), (elevation, elevation + height)), source)

            storeys = parsed.by_type('IfcBuildingStorey')
            spaces = parsed.by_type('IfcSpace')
            roof_references = parsed.by_type('IfcSpatialZone')
            self.assertEqual({s.GlobalId for s in storeys}, set(expected_storeys))
            self.assertEqual({s.GlobalId for s in spaces}, set(expected_spaces))
            self.assertEqual({s.GlobalId for s in roof_references}, set(expected_roofs))
            self.assertEqual(receipt['ifc_content_scope'], 'SPACES_AND_UNOCCUPIED_ROOF_REFERENCES')
            manifest = receipt['ifc_manifest']
            self.assertEqual(manifest['level_count'], len(expected_storeys))
            self.assertEqual(manifest['space_count'], len(expected_spaces))
            self.assertEqual(manifest['roof_level_count'], sum(l.get('kind') == 'roof' for l in model['levels']))
            self.assertEqual(manifest['roof_reference_count'], len(expected_roofs))
            product_counts = Counter(product.is_a() for product in parsed.by_type('IfcProduct'))
            self.assertEqual(product_counts, Counter({'IfcSite': 1, 'IfcBuilding': 1,
                'IfcBuildingStorey': len(expected_storeys), 'IfcSpace': len(expected_spaces),
                'IfcSpatialZone': len(expected_roofs)}))
            for entity in ('IfcStair', 'IfcStairFlight', 'IfcDoor', 'IfcWindow',
                           'IfcWall', 'IfcSlab', 'IfcOpeningElement', 'IfcRoof', 'IfcElementQuantity'):
                # The pinned reader can return a tuple. Require zero entities,
                # independent of the concrete empty sequence representation.
                self.assertEqual(len(parsed.by_type(entity)), 0,
                                 entity + ' exceeds spaces-only scope')
            root_ids = [entity.GlobalId for entity in parsed.by_type('IfcRoot')]
            self.assertEqual(len(root_ids), len(set(root_ids)))

            containers = {}
            for relation in parsed.by_type('IfcRelContainedInSpatialStructure'):
                for element in relation.RelatedElements:
                    self.assertNotIn(element.GlobalId, containers)
                    containers[element.GlobalId] = relation.RelatingStructure.GlobalId
            references = {}
            for relation in parsed.by_type('IfcRelReferencedInSpatialStructure'):
                self.assertTrue(relation.RelatingStructure.is_a('IfcBuilding'))
                for element in relation.RelatedElements:
                    self.assertNotIn(element.GlobalId, references)
                    references[element.GlobalId] = relation.RelatingStructure.GlobalId
            self.assertEqual(set(references), set(expected_roofs))
            settings = ifcopenshell.geom.settings()
            settings.set(settings.USE_WORLD_COORDS, True)
            for storey in storeys:
                elevation = expected_storeys[storey.GlobalId]
                self.assertAlmostEqual(storey.Elevation, elevation, places=6)
                transform = ifcopenshell.util.placement.get_local_placement(storey.ObjectPlacement)
                self.assertAlmostEqual(float(transform[2, 3]), elevation, places=6)
            for space in list(spaces) + list(roof_references):
                is_roof = space.is_a('IfcSpatialZone')
                storey_id, room_id, bounds, source = (expected_roofs if is_roof else expected_spaces)[space.GlobalId]
                self.assertEqual(space.LongName, room_id)
                if is_roof:
                    self.assertNotIn(space.GlobalId, containers)
                    self.assertEqual(space.PredefinedType, 'USERDEFINED')
                    self.assertEqual(space.ObjectType, 'ACS_UNOCCUPIED_ROOF_REFERENCE')
                    props = ifcopenshell.util.element.get_psets(space)['ACS_RoofReference']
                    self.assertEqual(props['LevelKind'], 'roof')
                    self.assertIs(props['IsOccupied'], False)
                    self.assertIs(props['CountsInFloorArea'], False)
                    self.assertEqual(props['ReferenceGeometry'], 'EXTRUDED_REFERENCE_EXTENT')
                    self.assertIs(props['CanonicalHeightDeclared'], True)
                    self.assertEqual(props['CanonicalId'], source)
                    self.assertEqual(props['CanonicalLevelId'], storey_id)
                    metadata = next(r for r in receipt['roof_reference_metadata'] if r['canonical_id'] == source)
                    self.assertEqual(metadata['reference_geometry'], props['ReferenceGeometry'])
                    self.assertIs(metadata['canonical_height_declared'], True)
                else:
                    self.assertEqual(containers[space.GlobalId], storey_id)
                shape = ifcopenshell.geom.create_shape(settings, space)
                vertices = shape.geometry.verts
                self.assertTrue(vertices)
                self.assertTrue(all(math.isfinite(v) for v in vertices))
                for axis, (low, high) in enumerate(bounds):
                    self.assertAlmostEqual(min(vertices[axis::3]), low, places=6)
                    self.assertAlmostEqual(max(vertices[axis::3]), high, places=6)

            self.assertEqual(canonical(workspace.get(revision_id).model), before)
            self.assertEqual(workspace.get(revision_id).model_hash, revision.model_hash)
            self.assertEqual(len(runner.calls), 1)
            print(json.dumps({'fixture': 'computed residential fallback with canonical U stairs',
                'scope': receipt['ifc_scope'], 'schema': parsed.schema,
                'reader': 'IfcOpenShell', 'reader_version': ifcopenshell.version,
                'storeys': len(storeys), 'spaces': len(spaces),
                'unoccupied_roof_references': len(roof_references),
                'product_entities': dict(sorted(product_counts.items())),
                'exported_stairs': 0, 'canonical_hash_unchanged': True}, sort_keys=True))


if __name__ == '__main__':
    unittest.main()
