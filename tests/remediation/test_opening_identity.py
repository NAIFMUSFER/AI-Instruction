"""Identity lifecycle regression, including historical revision preservation.

No network, provider, filesystem migration or production mutation is performed.
"""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import acs_authoring as A
import acs_arch as AR
import acs_bim as B
import acs_workspace as W
import acs_understand as U
import acs_distance as DIST
import acs_relations as REL
import acs_opening_identity as OI


def fixture():
    return {"site": {"w": 10, "d": 10}, "floor_height": 4, "wall_h": 4, "wall_t": 0.2,
            "levels": [{"index": 0, "template": "g"}, {"index": 1, "template": "g"}],
            "floors": {"g": {"rooms": [{"id": "r", "rect": [0, 0, 10, 10],
                "doors": [{"edge": "N", "offset": 2, "width": 1, "height": 2.1},
                          {"edge": "S", "offset": 7, "width": 1, "height": 2.1}],
                "windows": [{"edge": "E", "offset": 2, "width": 1, "height": 1, "sill": 1},
                            {"edge": "W", "offset": 7, "width": 1, "height": 1, "sill": 1}]}]}}}


def room(m):
    return m["floors"]["g"]["rooms"][0]


def command(kind, target, parameters=None):
    return {"type": kind, "target_id": target, "parameters": parameters or {}}


def commit(p, cmd):
    v = A.validate_transaction(p, [cmd])
    result = A.commit_transaction(p, [cmd], confirm=v["transaction"]["confirmation_digest"],
                                  acknowledge_warnings=True, actor_id="test-user",
                                  created_at="2026-09-06T00:00:00Z")
    if not result["committed"]:
        raise AssertionError(result["issues"])
    return result["project"]


def snapshot():
    p = A.create_project(fixture())
    first = commit(p, command("DELETE_DOOR", "bld_0.g.r.door_0"))
    added = commit(first, command("ADD_DOOR", "bld_0.g.r",
                                {"edge": "E", "offset": 4, "width": 1, "height": 2.1}))
    aid = room(added["model"])["doors"][-1]["id"]
    moved = commit(added, command("MOVE_DOOR", aid, {"edge": "E", "offset": 5}))
    undone = A.undo(moved)["project"]
    redone = A.redo(undone)["project"]
    loaded = A.load_project(json.loads(json.dumps(A.serialise_project(redone, True, True))))["project"]
    arch = AR.compile_architecture(loaded["model"])
    return {"model": loaded["model"], "hash": loaded["model_hash"],
            "history": loaded["history"], "audit": loaded["audit_log"],
            "arch": arch, "tree": W.project_tree(loaded, arch),
            "relationships": REL.build_relationships(loaded["model"]),
            "exchange": B.build_exchange(loaded)["exchange"],
            "deleted": A.resolve_target(loaded["model"], "bld_0.g.r.door_0"),
            "surviving": A.resolve_target(loaded["model"], "bld_0.g.r.door_1"),
            "new_id": aid}


class OpeningIdentityTests(unittest.TestCase):
    def test_reserved_projection_names_match_authoring_contract(self):
        self.assertEqual(OI.DERIVED_NS, A.DERIVED_NS)

    def test_deleted_target_cannot_retarget_survivor(self):
        for kind in ("DOOR", "WINDOW"):
            with self.subTest(kind=kind):
                p = commit(A.create_project(fixture()), command("DELETE_" + kind, "bld_0.g.r." + kind.lower() + "_0"))
                self.assertIsNone(A.resolve_target(p["model"], "bld_0.g.r." + kind.lower() + "_0")["kind"])
                self.assertEqual(A.resolve_target(p["model"], "bld_0.g.r." + kind.lower() + "_1")["opening_index"], 0)

    def test_migration_is_idempotent_and_geometry_unchanged(self):
        m = fixture()
        before = AR.compile_architecture(m)
        self.assertTrue(A.stabilise_opening_ids(m))
        self.assertEqual(A.stabilise_opening_ids(m), [])
        self.assertEqual(AR.compile_architecture(m), before)

    def test_preview_cancel_and_old_revision_are_unchanged(self):
        p = A.create_project(fixture())
        before = copy.deepcopy(p)
        A.preview_command(p["model"], command("DELETE_DOOR", "bld_0.g.r.door_0"))
        self.assertEqual(p, before)
        q = commit(p, command("DELETE_DOOR", "bld_0.g.r.door_0"))
        self.assertEqual(p, before)
        self.assertEqual(q["revision_models"][p["current_revision"]], before["model"])
        self.assertIn("_opening_identity", q["audit_log"][-1]["changed_paths"])

    def test_add_move_save_undo_redo_preserve_identity(self):
        out = snapshot()
        self.assertEqual(out["surviving"]["opening_index"], 0)
        self.assertIsNone(out["deleted"]["kind"])
        self.assertEqual(room(out["model"])["doors"][-1]["id"], out["new_id"])
        self.assertEqual(room(out["model"])["doors"][-1]["offset"], 5)
        self.assertTrue(any(x["opening_ref"] == out["new_id"] for x in out["arch"]["openings"]))
        self.assertTrue(any(x["canonical_id"] == out["new_id"] + "@0" for x in out["exchange"]["doors"]))

    def test_reordering_keeps_identity_and_invalidates_positional_alias(self):
        m = fixture()
        A.stabilise_opening_ids(m)
        room(m)["doors"].reverse()
        self.assertEqual(A.resolve_target(m, "bld_0.g.r.door_0")["opening_index"], 1)
        self.assertEqual(A.resolve_target(m, "bld_0.g.r.door_1@1")["opening_index"], 0)
        self.assertIsNone(A.resolve_target(m, "bld_0.g.r.door_1@99")["kind"])

    def test_duplicate_and_reserved_identities_rejected(self):
        for identity in ("bld_0.g.r.door_0", "bld_0.g.r", "bld_0.flr_0", "__proto__"):
            with self.subTest(identity=identity):
                m = fixture()
                room(m)["windows"][0]["id"] = identity
                self.assertIn("ID_COLLISION", [i["code"] for i in A.opening_identity_issues(m)])
                with self.assertRaises(ValueError):
                    A.stabilise_opening_ids(m)

    def test_invalid_identities_and_marker_fail_closed(self):
        for value in (None, "", [], 12, "door@0", "door\nscript", "x" * 257, "<svg/onload=1>"):
            m = fixture()
            room(m)["doors"][0]["id"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                A.stabilise_opening_ids(m)
        for state in ({"schema": "future", "next": 0}, {"schema": A.OPENING_IDENTITY_SCHEMA, "next": True}):
            m = fixture()
            m["_opening_identity"] = state
            self.assertTrue(A.opening_identity_issues(m))

    def test_missing_identity_in_migrated_model_is_not_regenerated(self):
        m = fixture()
        A.stabilise_opening_ids(m)
        del room(m)["doors"][0]["id"]
        before = copy.deepcopy(m)
        with self.assertRaises(ValueError):
            A.stabilise_opening_ids(m)
        self.assertEqual(m, before)

    def test_new_ids_are_not_reused_after_delete(self):
        p = A.create_project(fixture())
        add = command("ADD_WINDOW", "bld_0.g.r", {"edge": "E", "offset": 5, "width": 1})
        p = commit(p, add)
        oid = room(p["model"])["windows"][-1]["id"]
        p = commit(p, command("DELETE_WINDOW", oid))
        p = commit(p, add)
        self.assertNotEqual(room(p["model"])["windows"][-1]["id"], oid)

    def test_source_lock_cannot_be_bypassed_with_level_suffix(self):
        m = fixture()
        A.stabilise_opening_ids(m)
        m["_authoring_locks"] = {"bld_0.g.r.door_1": {"reason": "USER_LOCKED"}}
        result = A.preview_command(m, command("MOVE_DOOR", "bld_0.g.r.door_1@0", {"offset": 6}))
        self.assertFalse(result["valid"])
        self.assertIn("TARGET_LOCKED", [i["code"] for i in result["issues"]])

    def test_workspace_host_matches_selected_opening(self):
        p = A.create_project(fixture())
        A.stabilise_opening_ids(p["model"])
        arch = AR.compile_architecture(p["model"])
        oid = "bld_0.g.r.door_1"
        expected = next(o["host_wall_id"] for o in arch["openings"] if o["opening_ref"] == oid)
        rel = W._relationships(p["model"], A.resolve_target(p["model"], oid), arch, "bld_0")
        self.assertEqual(next(r["target_id"] for r in rel if r["relation"] == "HOSTED_BY_WALL"), expected)

    def test_new_generation_admission_assigns_ids_without_changing_unknown_thickness(self):
        m = fixture()
        m["wall_t"] = 0
        out = U.validate(m)
        self.assertEqual(out["wall_t"], 0)  # separate known uncertainty defect
        self.assertTrue(all(o.get("id") for k in ("doors", "windows") for o in room(out)[k]))

    def test_distance_uses_identity_after_reorder(self):
        m = fixture()
        A.stabilise_opening_ids(m)
        room(m)["doors"].reverse()
        idx = DIST._rooms_index(m, "bld_0")
        self.assertEqual(DIST._via_door("bld_0.g.r.door_0", idx), ("bld_0.g.r", 1))
        room(m)["doors"].pop()
        self.assertEqual(DIST._via_door("bld_0.g.r.door_0", idx), (None, None))

    def test_missing_distance_reference_is_not_a_legacy_door(self):
        rooms = {"r": {"doors": [{"edge": "N"}]}}
        for via in (None, "", 0):
            self.assertEqual(DIST._via_door(via, rooms), (None, None))

    def test_import_and_export_reject_broken_migrated_identity(self):
        m = fixture()
        A.stabilise_opening_ids(m)
        del room(m)["doors"][0]["id"]
        p = A.create_project(m)
        loaded = A.load_project(A.serialise_project(p))
        self.assertFalse(loaded["valid"])
        self.assertIsNone(loaded["project"])
        exported = B.build_exchange(p)
        self.assertFalse(exported["valid"])
        self.assertIsNone(exported["exchange"])

    def test_ai_edit_cannot_drop_identity_version_or_records(self):
        for omit in ("marker", "id"):
            m = fixture()
            before = copy.deepcopy(m)
            response = copy.deepcopy(m)
            A.stabilise_opening_ids(response)
            if omit == "marker":
                del response["_opening_identity"]
            else:
                del room(response)["doors"][0]["id"]
            with self.subTest(omit=omit), patch.object(U, "call_llm", return_value=json.dumps(response)):
                with self.assertRaises((U.E.AcsApiError, ValueError)):
                    U.apply_notes(m, [])
            self.assertEqual(m, before)


if __name__ == "__main__":
    if "--snapshot" in sys.argv:
        print(json.dumps(snapshot(), ensure_ascii=False, sort_keys=True))
    else:
        unittest.main(verbosity=2)
