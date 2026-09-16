#!/usr/bin/env python3
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
UI=ROOT/'public/app/ui/connected-workspace.mjs'

class ConnectedTypologyIsolation(unittest.TestCase):
    def test_generation_routes_residential_options_only_for_residential(self):
        src=UI.read_text(encoding='utf-8')
        expected="const program=source.source_id?briefProgram():($('cwType').value==='residential'?residentialOptions.program(briefProgram(),option):briefProgram());"
        self.assertIn(expected,src)
        self.assertNotIn("const program=source.source_id?briefProgram():residentialOptions.program(briefProgram(),option);",src)

    def test_warehouse_help_remains_typology_specific(self):
        src=UI.read_text(encoding='utf-8')
        self.assertIn("$('cwType').value==='residential'",src)
        self.assertIn("للمستودعات",src)

if __name__=='__main__': unittest.main()
