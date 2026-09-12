#!/usr/bin/env python3
"""Aggregate approved-baseline 3D handoff regressions through an existing trusted CI gate."""
from __future__ import annotations

import unittest

from test_plan_handoff_core import *  # noqa: F401,F403
from test_plan_handoff_warehouse_dock_geometry import *  # noqa: F401,F403


if __name__ == "__main__":
    unittest.main(verbosity=2)
