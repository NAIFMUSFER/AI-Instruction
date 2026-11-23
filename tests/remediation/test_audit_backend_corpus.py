"""مسح عقود المداخل على تجهيزات المباني الفعلية، لا على رقم محفوظ وحده."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import acs_bim as BIM
import acs_layout as LAYOUT
import acs_validate as VALIDATE
import acs_visual as VISUAL


def walk(value, path='$', depth=0):
    if depth > 6:
        return
    if isinstance(value, dict):
        if isinstance(value.get('floors'), dict) and 'levels' in value:
            yield path, value
        for key, child in value.items():
            yield from walk(child, path + '.' + key, depth + 1)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk(child, '%s[%d]' % (path, index), depth + 1)


def corpus():
    for file in sorted((ROOT / 'tests').rglob('*.json')):
        try:
            data = json.loads(file.read_text())
        except (ValueError, UnicodeError):
            continue
        for path, model in walk(data):
            yield str(file.relative_to(ROOT)) + '::' + path, model


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def observe(function, model):
    outputs, inputs, errors = [], [], []
    for _ in range(2):
        candidate = copy.deepcopy(model)
        try:
            outputs.append(function(candidate))
        except Exception as exc:
            errors.append(type(exc).__name__ + ': ' + str(exc))
            outputs.append({'error': errors[-1]})
        inputs.append(candidate)
    return {'errors': errors,
            'nondeterministic': digest(outputs[0]) != digest(outputs[1]) or digest(inputs[0]) != digest(inputs[1]),
            'mutates': digest(model) != digest(inputs[0])}


def audit():
    models = list(corpus())
    report = {'models': len(models), 'functions': {}, 'repair': {'worse': [], 'errors': [], 'nondeterministic': []}}
    functions = {
        'opening_identity_issues': BIM.opening_identity_issues,
        'autofix_propose': LAYOUT.autofix,
        'autofix_apply': lambda m: LAYOUT.autofix(m, authority=LAYOUT.AUTHORITY_APPLY),
        # وقت حقن ثابت: وقت بناء المشهد ليس لا حتمية هندسية.
        'compile_visual_scene': lambda m: VISUAL.compile_visual_scene(m, at='2026-09-26T00:00:00Z'),
        'validate_building': VALIDATE.validate_building,
    }
    for name, function in functions.items():
        findings = {'errors': [], 'nondeterministic': [], 'mutates': []}
        for label, model in models:
            observed = observe(function, model)
            for key in findings:
                if observed[key]:
                    findings[key].append({'fixture': label, 'value': observed[key]})
        report['functions'][name] = findings
    for label, model in models:
        try:
            before = VALIDATE.validate_building(copy.deepcopy(model))[0]
            outputs = []
            for _ in range(2):
                fixed = copy.deepcopy(model)
                changed = LAYOUT.autofix(fixed, authority=LAYOUT.AUTHORITY_APPLY)
                after = VALIDATE.validate_building(fixed)[0]
                outputs.append([fixed, changed, after])
            if len(after) > len(before):
                report['repair']['worse'].append({'fixture': label, 'before': len(before), 'after': len(after)})
            if digest(outputs[0]) != digest(outputs[1]):
                report['repair']['nondeterministic'].append(label)
        except Exception as exc:
            report['repair']['errors'].append({'fixture': label, 'error': type(exc).__name__ + ': ' + str(exc)})
    return report


class CorpusContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = audit()

    def test_corpus_does_not_silently_shrink(self):
        self.assertGreaterEqual(self.report['models'], 165)

    def test_entrypoints_never_raise_or_change_between_repeats(self):
        for name, findings in self.report['functions'].items():
            with self.subTest(function=name):
                self.assertEqual(findings['errors'], [])
                self.assertEqual(findings['nondeterministic'], [])

    def test_readonly_entrypoints_leave_the_caller_unchanged(self):
        for name in ('opening_identity_issues', 'compile_visual_scene', 'validate_building'):
            with self.subTest(function=name):
                self.assertEqual(self.report['functions'][name]['mutates'], [])
        # autofix writes by its declared contract; the existing
        # test_autofix_propose_boundary.py checks its SAFE_NORMALIZATION allowlist.

    def test_apply_never_increases_issue_count(self):
        self.assertEqual(self.report['repair'], {'worse': [], 'errors': [], 'nondeterministic': []})

    def test_sweep_detects_mutation_exception_and_nondeterminism(self):
        model = {'safe': True}
        calls = []
        def mutating(candidate):
            calls.append(None)
            candidate['injected'] = len(calls)
            return candidate
        bad = observe(mutating, model)
        self.assertTrue(bad['mutates'])
        self.assertTrue(bad['nondeterministic'])
        self.assertEqual(model, {'safe': True})
        def throwing(candidate):
            raise ValueError('synthetic failure')
        self.assertEqual(len(observe(throwing, model)['errors']), 2)
        self.assertEqual(observe(lambda candidate: dict(candidate), model),
                         {'errors': [], 'nondeterministic': False, 'mutates': False})


if __name__ == '__main__':
    if '--report' in sys.argv:
        report = audit()
        summary = {'models': report['models'], 'functions': {
            name: {key: len(values) for key, values in data.items()}
            for name, data in report['functions'].items()},
            'repair': {key: len(values) for key, values in report['repair'].items()}}
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        unittest.main(verbosity=2)
