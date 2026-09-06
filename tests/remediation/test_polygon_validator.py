"""C09h: the ACS validator evaluates the same straight polygon as the compiler."""
import copy
import unittest
from test_polygon_gltf import model, L
from test_polygon_architecture import adjacent_triangles
import acs_validate as V


def building(**fields):
    b = model()
    b['floors']['plan']['rooms'][0].update(fields)
    b['meta'] = {'strict': True}
    return b


class PolygonValidator(unittest.TestCase):
    def validate(self, b):
        before = copy.deepcopy(b)
        result = V.validate_building(b)
        self.assertEqual(b, before)
        return result

    def test_valid_polygon_door_has_no_false_alert_and_is_reachable(self):
        issues, stats = self.validate(building(doors=[{'edge_index': 0, 'offset': 2, 'width': 1}]))
        self.assertEqual(issues, [])
        self.assertEqual(stats['access']['status'], 'COMPLETED')
        self.assertEqual(stats['access']['reachable_rooms'], 1)

    def test_invalid_ring_and_conflicting_box_are_explicit(self):
        for points, code in (([[0, 0], [6, 6], [0, 6], [6, 0]], 'POLYGON_INVALID'),
                             ([[0, 0], [6, 0], [2, 2]], 'POLYGON_RECT_MISMATCH')):
            with self.subTest(code=code):
                b = building(walls='none')
                b['floors']['plan']['rooms'][0]['polygon'] = points
                issues, _ = self.validate(b)
                self.assertTrue(any(code in issue for issue in issues), issues)

    def test_point_in_the_missing_l_notch_is_outside(self):
        b = building(walls='none', points=[{'type': 'light', 'x': 4, 'z': 4}])
        issues, _ = self.validate(b)
        self.assertTrue(any('POINT_OUTSIDE_ROOM' in issue and 'points/0' in issue for issue in issues), issues)

    def test_shared_diagonal_is_not_an_overlap_and_transmits_access(self):
        b = adjacent_triangles()
        b['meta'] = {'strict': True}
        b['floors']['plan']['rooms'][0]['doors'].append({'edge_index': 0, 'offset': 2, 'width': 1})
        issues, stats = self.validate(b)
        self.assertEqual(issues, [])
        self.assertEqual(stats['access']['status'], 'COMPLETED')
        self.assertEqual(stats['access']['reachable_rooms'], 2)

    def test_real_polygon_overlap_is_still_detected(self):
        b = building(walls='none')
        other = copy.deepcopy(b['floors']['plan']['rooms'][0])
        other.update(id='other', polygon=[[x+1, z] for x, z in L], rect=[1, 0, 6, 6])
        b['floors']['plan']['rooms'].append(other)
        issues, _ = self.validate(b)
        self.assertTrue(any('تداخل' in issue and 'other' in issue for issue in issues), issues)

    def test_isolated_polygon_and_window_only_are_not_unevaluated(self):
        for windows in ([], [{'edge_index': 0, 'offset': 2, 'width': 1, 'height': 1, 'sill': 1}]):
            with self.subTest(windows=windows):
                issues, stats = self.validate(building(windows=windows))
                self.assertTrue(any('ROOM_UNREACHABLE' in issue for issue in issues), issues)
                self.assertEqual(stats['access']['status'], 'COMPLETED')

    def test_short_oblique_edge_bounds_the_opening_width(self):
        b = model([[0, 0], [6, 0], [0, 6]], doors=[{'edge_index': 1, 'offset': 8, 'width': 2}])
        b['meta'] = {'strict': True}
        issues, _ = self.validate(b)
        self.assertTrue(any('OPENING_OUTSIDE_WALL' in issue for issue in issues), issues)


if __name__ == '__main__':
    unittest.main(verbosity=2)
