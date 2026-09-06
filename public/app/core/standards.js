/* ============================================================
   public/app/core/standards.js
   مُستخرَج من public/index.html بـ tools/frontend_split.js (F-09).
   لا تحرّره يدوياً إن كان مولَّداً — حرّر المولّد وأعِد التوليد.
   ============================================================ */
import { __ACS_SHARED } from '../shared-state.js';
import { __ACS_LATE } from '../late-bindings.js';
import { _dsRooms, _pyRound, ensureElementIds, extractExits, findEgress, findPath, measurePath, usableExits } from './viewer.js';

const ACS_RULES_REGISTRY = {
  "schema": "acs.rules/1",
  "engine_version": "acs-rule-engine/1.0.0",
  "note": "REGISTRY ONLY. Contains ZERO regulatory rules. Every ruleset here is synthetic (regulatory=false, namespace=TEST_ONLY) and exists solely to exercise engine mechanics. No SBC / IBC / NFPA / ADA / Civil-Defense value is encoded anywhere in this file. Real regulatory content may only be added from an authoritative supplied source, with full evidence, in a later approved phase.",
  "evaluation_states": [
    "PASS",
    "FAIL",
    "NOT_APPLICABLE",
    "NOT_EVALUATED",
    "INSUFFICIENT_DATA",
    "INVALID_RULE_DEFINITION",
    "UNSUPPORTED"
  ],
  "applicability_states": [
    "APPLICABLE",
    "NOT_APPLICABLE",
    "UNDETERMINED"
  ],
  "data_quality_states": [
    "COMPLETE",
    "INCOMPLETE",
    "MISSING",
    "NOT_REQUIRED"
  ],
  "severities": [
    "info",
    "advisory",
    "major",
    "critical"
  ],
  "completeness_states": [
    "partial",
    "complete_for_declared_scope",
    "unknown"
  ],
  "provenance_values": [
    "user",
    "ai_inference",
    "system_default",
    "geometry_inference",
    "rule"
  ],
  "subject_types": [
    "PROJECT",
    "SITE",
    "BUILDING",
    "LEVEL",
    "SPACE",
    "DOOR",
    "WINDOW",
    "STAIR",
    "ELEVATOR",
    "ROUTE",
    "EXIT",
    "EGRESS",
    "OBJECT",
    "SYSTEM"
  ],
  "dimensions": [
    "length",
    "area",
    "angle",
    "time",
    "count",
    "ratio",
    "dimensionless",
    "enum",
    "boolean"
  ],
  "units": {
    "m": {
      "dim": "length",
      "mul": 1
    },
    "cm": {
      "dim": "length",
      "div": 100
    },
    "mm": {
      "dim": "length",
      "div": 1000
    },
    "km": {
      "dim": "length",
      "mul": 1000
    },
    "m2": {
      "dim": "area",
      "mul": 1
    },
    "cm2": {
      "dim": "area",
      "div": 10000
    },
    "mm2": {
      "dim": "area",
      "div": 1000000
    },
    "deg": {
      "dim": "angle",
      "mul": 1
    },
    "rad": {
      "dim": "angle",
      "mul": 57.29577951308232
    },
    "s": {
      "dim": "time",
      "mul": 1
    },
    "min": {
      "dim": "time",
      "mul": 60
    },
    "h": {
      "dim": "time",
      "mul": 3600
    },
    "count": {
      "dim": "count",
      "mul": 1
    },
    "ratio": {
      "dim": "ratio",
      "mul": 1
    },
    "percent": {
      "dim": "ratio",
      "div": 100
    },
    "none": {
      "dim": "dimensionless",
      "mul": 1
    }
  },
  "operators": {
    "numeric_max": {
      "value_type": "number",
      "needs_unit": true,
      "dim": "numeric"
    },
    "numeric_min": {
      "value_type": "number",
      "needs_unit": true,
      "dim": "numeric"
    },
    "numeric_range": {
      "value_type": "range",
      "needs_unit": true,
      "dim": "numeric"
    },
    "count_min": {
      "value_type": "number",
      "needs_unit": false,
      "dim": "count"
    },
    "count_max": {
      "value_type": "number",
      "needs_unit": false,
      "dim": "count"
    },
    "boolean_required": {
      "value_type": "boolean",
      "needs_unit": false,
      "dim": "boolean"
    },
    "existence": {
      "value_type": "boolean",
      "needs_unit": false,
      "dim": "any"
    },
    "enumeration": {
      "value_type": "list",
      "needs_unit": false,
      "dim": "enum"
    },
    "all_of": {
      "value_type": "clauses",
      "needs_unit": false,
      "dim": "composite"
    },
    "any_of": {
      "value_type": "clauses",
      "needs_unit": false,
      "dim": "composite"
    }
  },
  "input_contracts": {
    "route.walking_distance_m": {
      "subject": "ROUTE",
      "dim": "length",
      "unit": "m"
    },
    "route.distance_status": {
      "subject": "ROUTE",
      "dim": "enum"
    },
    "route.hops": {
      "subject": "ROUTE",
      "dim": "count",
      "unit": "count"
    },
    "route.door_count": {
      "subject": "ROUTE",
      "dim": "count",
      "unit": "count"
    },
    "route.vertical_transition_count": {
      "subject": "ROUTE",
      "dim": "count",
      "unit": "count"
    },
    "route.levels_crossed": {
      "subject": "ROUTE",
      "dim": "count",
      "unit": "count"
    },
    "route.uses_stairs": {
      "subject": "ROUTE",
      "dim": "boolean"
    },
    "route.uses_elevator": {
      "subject": "ROUTE",
      "dim": "boolean"
    },
    "route.resolution": {
      "subject": "ROUTE",
      "dim": "enum"
    },
    "egress.status": {
      "subject": "EGRESS",
      "dim": "enum"
    },
    "egress.walking_distance_m": {
      "subject": "EGRESS",
      "dim": "length",
      "unit": "m"
    },
    "egress.distance_status": {
      "subject": "EGRESS",
      "dim": "enum"
    },
    "egress.exit_count": {
      "subject": "EGRESS",
      "dim": "count",
      "unit": "count"
    },
    "egress.usable_exit_count": {
      "subject": "EGRESS",
      "dim": "count",
      "unit": "count"
    },
    "door.clear_width": {
      "subject": "DOOR",
      "dim": "length",
      "unit": "m"
    },
    "door.edge": {
      "subject": "DOOR",
      "dim": "enum"
    },
    "space.area": {
      "subject": "SPACE",
      "dim": "area",
      "unit": "m2"
    },
    "space.level": {
      "subject": "SPACE",
      "dim": "count",
      "unit": "count"
    },
    "building.program": {
      "subject": "BUILDING",
      "dim": "enum"
    },
    "building.levels_count": {
      "subject": "BUILDING",
      "dim": "count",
      "unit": "count"
    },
    "building.wall_thickness": {
      "subject": "BUILDING",
      "dim": "length",
      "unit": "m"
    },
    "occupancy.status": {
      "subject": "ANY",
      "dim": "enum"
    },
    "occupancy.group": {
      "subject": "ANY",
      "dim": "enum"
    },
    "occupancy.subgroup": {
      "subject": "ANY",
      "dim": "enum"
    },
    "occupancy.standard": {
      "subject": "ANY",
      "dim": "enum"
    },
    "occupancy.edition": {
      "subject": "ANY",
      "dim": "enum"
    },
    "occupancy.jurisdiction_country": {
      "subject": "ANY",
      "dim": "enum"
    }
  },
  "sources": [
    {
      "source_id": "SBC",
      "name": "Saudi Building Code",
      "standard": "SBC",
      "edition": null,
      "jurisdiction": {
        "country": null,
        "region": null,
        "authority": null
      },
      "document": null,
      "verified": false,
      "status": "NOT_LOADED"
    },
    {
      "source_id": "IBC",
      "name": "International Building Code",
      "standard": "IBC",
      "edition": null,
      "jurisdiction": {
        "country": null,
        "region": null,
        "authority": null
      },
      "document": null,
      "verified": false,
      "status": "NOT_LOADED"
    },
    {
      "source_id": "NFPA",
      "name": "National Fire Protection Association standards",
      "standard": "NFPA",
      "edition": null,
      "jurisdiction": {
        "country": null,
        "region": null,
        "authority": null
      },
      "document": null,
      "verified": false,
      "status": "NOT_LOADED"
    },
    {
      "source_id": "ADA",
      "name": "Americans with Disabilities Act accessibility standards",
      "standard": "ADA",
      "edition": null,
      "jurisdiction": {
        "country": null,
        "region": null,
        "authority": null
      },
      "document": null,
      "verified": false,
      "status": "NOT_LOADED"
    },
    {
      "source_id": "CIVIL_DEFENSE",
      "name": "Civil Defense requirements",
      "standard": "CIVIL_DEFENSE",
      "edition": null,
      "jurisdiction": {
        "country": null,
        "region": null,
        "authority": null
      },
      "document": null,
      "verified": false,
      "status": "NOT_LOADED"
    },
    {
      "source_id": "MUNICIPALITY",
      "name": "Municipality requirements",
      "standard": "MUNICIPALITY",
      "edition": null,
      "jurisdiction": {
        "country": null,
        "region": null,
        "authority": null
      },
      "document": null,
      "verified": false,
      "status": "NOT_LOADED"
    },
    {
      "source_id": "HEALTH_FACILITY",
      "name": "Health-facility regulations",
      "standard": "HEALTH_FACILITY",
      "edition": null,
      "jurisdiction": {
        "country": null,
        "region": null,
        "authority": null
      },
      "document": null,
      "verified": false,
      "status": "NOT_LOADED"
    },
    {
      "source_id": "EDUCATION",
      "name": "Education-facility regulations",
      "standard": "EDUCATION",
      "edition": null,
      "jurisdiction": {
        "country": null,
        "region": null,
        "authority": null
      },
      "document": null,
      "verified": false,
      "status": "NOT_LOADED"
    },
    {
      "source_id": "synthetic_test",
      "name": "Synthetic engine-test source (NOT a regulation)",
      "standard": "TEST_STANDARD",
      "edition": null,
      "jurisdiction": {
        "country": null,
        "region": null,
        "authority": null
      },
      "document": null,
      "verified": false,
      "status": "SYNTHETIC"
    }
  ],
  "rulesets": [
    {
      "ruleset_id": "TEST_ONLY.CORE",
      "ruleset_version": "1",
      "standard": "TEST_STANDARD",
      "edition": "0",
      "jurisdiction": {
        "country": null,
        "region": null,
        "authority": null
      },
      "coverage_scope": "engine primitives only",
      "completeness": "partial",
      "regulatory": false,
      "rules": [
        {
          "rule_id": "TEST_ONLY.NUMERIC_MAX_001",
          "namespace": "TEST_ONLY",
          "regulatory": false,
          "title": "synthetic: route walking distance not above a synthetic ceiling",
          "category": "synthetic",
          "severity": "info",
          "enabled": true,
          "revision": 1,
          "standard": "TEST_STANDARD",
          "edition": "0",
          "section": "§T.MAX",
          "jurisdiction_required": false,
          "jurisdiction": {
            "country": null,
            "region": null,
            "authority": null
          },
          "source": {
            "type": "synthetic_test",
            "source_id": "synthetic_test",
            "document_id": null,
            "page": null,
            "clause": null,
            "url": null,
            "verified": false
          },
          "subject_type": "ROUTE",
          "applies_to": {
            "subject_type": "ROUTE",
            "conditions": []
          },
          "inputs": [
            {
              "key": "route.walking_distance_m",
              "unit": "m",
              "required": true,
              "quality": {
                "status_key": "route.distance_status",
                "accept": [
                  "COMPLETE"
                ],
                "reasons": {
                  "PARTIAL": "INCOMPLETE_DISTANCE_MEASUREMENT",
                  "GEOMETRY_NOT_SUPPORTED": "GEOMETRY_NOT_SUPPORTED",
                  "NOT_MEASURED": "DISTANCE_NOT_MEASURED",
                  "INVALID_PATH": "INVALID_PATH"
                }
              }
            }
          ],
          "operator": "numeric_max",
          "expected": {
            "value": 30,
            "unit": "m"
          }
        },
        {
          "rule_id": "TEST_ONLY.NUMERIC_MIN_001",
          "namespace": "TEST_ONLY",
          "regulatory": false,
          "title": "synthetic: door clear width not below a synthetic floor (unit-conversion probe)",
          "category": "synthetic",
          "severity": "info",
          "enabled": true,
          "revision": 1,
          "standard": "TEST_STANDARD",
          "edition": "0",
          "section": "§T.MIN",
          "jurisdiction_required": false,
          "jurisdiction": {
            "country": null,
            "region": null,
            "authority": null
          },
          "source": {
            "type": "synthetic_test",
            "source_id": "synthetic_test",
            "document_id": null,
            "page": null,
            "clause": null,
            "url": null,
            "verified": false
          },
          "subject_type": "DOOR",
          "applies_to": {
            "subject_type": "DOOR",
            "conditions": []
          },
          "inputs": [
            {
              "key": "door.clear_width",
              "unit": "m",
              "required": true
            }
          ],
          "operator": "numeric_min",
          "expected": {
            "value": 900,
            "unit": "mm"
          }
        },
        {
          "rule_id": "TEST_ONLY.EXISTS_001",
          "namespace": "TEST_ONLY",
          "regulatory": false,
          "title": "synthetic: an exit is represented for this origin",
          "category": "synthetic",
          "severity": "info",
          "enabled": true,
          "revision": 1,
          "standard": "TEST_STANDARD",
          "edition": "0",
          "section": "§T.EXISTS",
          "jurisdiction_required": false,
          "jurisdiction": {
            "country": null,
            "region": null,
            "authority": null
          },
          "source": {
            "type": "synthetic_test",
            "source_id": "synthetic_test",
            "document_id": null,
            "page": null,
            "clause": null,
            "url": null,
            "verified": false
          },
          "subject_type": "EGRESS",
          "applies_to": {
            "subject_type": "EGRESS",
            "conditions": []
          },
          "inputs": [
            {
              "key": "egress.exit_count",
              "unit": "count",
              "required": true
            }
          ],
          "operator": "existence",
          "expected": {
            "value": true
          }
        },
        {
          "rule_id": "TEST_ONLY.COUNT_MIN_001",
          "namespace": "TEST_ONLY",
          "regulatory": false,
          "title": "synthetic: at least one usable exit is represented",
          "category": "synthetic",
          "severity": "info",
          "enabled": true,
          "revision": 1,
          "standard": "TEST_STANDARD",
          "edition": "0",
          "section": "§T.COUNT",
          "jurisdiction_required": false,
          "jurisdiction": {
            "country": null,
            "region": null,
            "authority": null
          },
          "source": {
            "type": "synthetic_test",
            "source_id": "synthetic_test",
            "document_id": null,
            "page": null,
            "clause": null,
            "url": null,
            "verified": false
          },
          "subject_type": "EGRESS",
          "applies_to": {
            "subject_type": "EGRESS",
            "conditions": []
          },
          "inputs": [
            {
              "key": "egress.usable_exit_count",
              "unit": "count",
              "required": true
            }
          ],
          "operator": "count_min",
          "expected": {
            "value": 1
          }
        },
        {
          "rule_id": "TEST_ONLY.ENUM_001",
          "namespace": "TEST_ONLY",
          "regulatory": false,
          "title": "synthetic: measurement status is one of an accepted set",
          "category": "synthetic",
          "severity": "info",
          "enabled": true,
          "revision": 1,
          "standard": "TEST_STANDARD",
          "edition": "0",
          "section": "§T.ENUM",
          "jurisdiction_required": false,
          "jurisdiction": {
            "country": null,
            "region": null,
            "authority": null
          },
          "source": {
            "type": "synthetic_test",
            "source_id": "synthetic_test",
            "document_id": null,
            "page": null,
            "clause": null,
            "url": null,
            "verified": false
          },
          "subject_type": "ROUTE",
          "applies_to": {
            "subject_type": "ROUTE",
            "conditions": []
          },
          "inputs": [
            {
              "key": "route.distance_status",
              "required": true
            }
          ],
          "operator": "enumeration",
          "expected": {
            "values": [
              "COMPLETE",
              "PARTIAL"
            ]
          }
        },
        {
          "rule_id": "TEST_ONLY.BOOL_001",
          "namespace": "TEST_ONLY",
          "regulatory": false,
          "title": "synthetic: route is recorded as using stairs",
          "category": "synthetic",
          "severity": "info",
          "enabled": true,
          "revision": 1,
          "standard": "TEST_STANDARD",
          "edition": "0",
          "section": "§T.BOOL",
          "jurisdiction_required": false,
          "jurisdiction": {
            "country": null,
            "region": null,
            "authority": null
          },
          "source": {
            "type": "synthetic_test",
            "source_id": "synthetic_test",
            "document_id": null,
            "page": null,
            "clause": null,
            "url": null,
            "verified": false
          },
          "subject_type": "ROUTE",
          "applies_to": {
            "subject_type": "ROUTE",
            "conditions": []
          },
          "inputs": [
            {
              "key": "route.uses_stairs",
              "required": true
            }
          ],
          "operator": "boolean_required",
          "expected": {
            "value": true
          }
        },
        {
          "rule_id": "TEST_ONLY.RANGE_001",
          "namespace": "TEST_ONLY",
          "regulatory": false,
          "title": "synthetic: route walking distance inside a synthetic band",
          "category": "synthetic",
          "severity": "info",
          "enabled": true,
          "revision": 1,
          "standard": "TEST_STANDARD",
          "edition": "0",
          "section": "§T.RANGE",
          "jurisdiction_required": false,
          "jurisdiction": {
            "country": null,
            "region": null,
            "authority": null
          },
          "source": {
            "type": "synthetic_test",
            "source_id": "synthetic_test",
            "document_id": null,
            "page": null,
            "clause": null,
            "url": null,
            "verified": false
          },
          "subject_type": "ROUTE",
          "applies_to": {
            "subject_type": "ROUTE",
            "conditions": []
          },
          "inputs": [
            {
              "key": "route.walking_distance_m",
              "unit": "m",
              "required": true,
              "quality": {
                "status_key": "route.distance_status",
                "accept": [
                  "COMPLETE"
                ],
                "reasons": {
                  "PARTIAL": "INCOMPLETE_DISTANCE_MEASUREMENT",
                  "GEOMETRY_NOT_SUPPORTED": "GEOMETRY_NOT_SUPPORTED",
                  "NOT_MEASURED": "DISTANCE_NOT_MEASURED",
                  "INVALID_PATH": "INVALID_PATH"
                }
              }
            }
          ],
          "operator": "numeric_range",
          "expected": {
            "min": 1,
            "max": 100,
            "unit": "m"
          }
        },
        {
          "rule_id": "TEST_ONLY.ALL_OF_001",
          "namespace": "TEST_ONLY",
          "regulatory": false,
          "title": "synthetic: composite all_of over two primitives",
          "category": "synthetic",
          "severity": "info",
          "enabled": true,
          "revision": 1,
          "standard": "TEST_STANDARD",
          "edition": "0",
          "section": "§T.ALL",
          "jurisdiction_required": false,
          "jurisdiction": {
            "country": null,
            "region": null,
            "authority": null
          },
          "source": {
            "type": "synthetic_test",
            "source_id": "synthetic_test",
            "document_id": null,
            "page": null,
            "clause": null,
            "url": null,
            "verified": false
          },
          "subject_type": "ROUTE",
          "applies_to": {
            "subject_type": "ROUTE",
            "conditions": []
          },
          "inputs": [
            {
              "key": "route.walking_distance_m",
              "unit": "m",
              "required": true,
              "quality": {
                "status_key": "route.distance_status",
                "accept": [
                  "COMPLETE"
                ],
                "reasons": {
                  "PARTIAL": "INCOMPLETE_DISTANCE_MEASUREMENT",
                  "GEOMETRY_NOT_SUPPORTED": "GEOMETRY_NOT_SUPPORTED",
                  "NOT_MEASURED": "DISTANCE_NOT_MEASURED",
                  "INVALID_PATH": "INVALID_PATH"
                }
              }
            },
            {
              "key": "route.hops",
              "unit": "count",
              "required": true
            }
          ],
          "operator": "all_of",
          "expected": {
            "clauses": [
              {
                "operator": "numeric_max",
                "input": "route.walking_distance_m",
                "expected": {
                  "value": 100,
                  "unit": "m"
                }
              },
              {
                "operator": "count_min",
                "input": "route.hops",
                "expected": {
                  "value": 1
                }
              }
            ]
          }
        },
        {
          "rule_id": "TEST_ONLY.ANY_OF_001",
          "namespace": "TEST_ONLY",
          "regulatory": false,
          "title": "synthetic: composite any_of over two primitives",
          "category": "synthetic",
          "severity": "info",
          "enabled": true,
          "revision": 1,
          "standard": "TEST_STANDARD",
          "edition": "0",
          "section": "§T.ANY",
          "jurisdiction_required": false,
          "jurisdiction": {
            "country": null,
            "region": null,
            "authority": null
          },
          "source": {
            "type": "synthetic_test",
            "source_id": "synthetic_test",
            "document_id": null,
            "page": null,
            "clause": null,
            "url": null,
            "verified": false
          },
          "subject_type": "ROUTE",
          "applies_to": {
            "subject_type": "ROUTE",
            "conditions": []
          },
          "inputs": [
            {
              "key": "route.walking_distance_m",
              "unit": "m",
              "required": true,
              "quality": {
                "status_key": "route.distance_status",
                "accept": [
                  "COMPLETE"
                ],
                "reasons": {
                  "PARTIAL": "INCOMPLETE_DISTANCE_MEASUREMENT",
                  "GEOMETRY_NOT_SUPPORTED": "GEOMETRY_NOT_SUPPORTED",
                  "NOT_MEASURED": "DISTANCE_NOT_MEASURED",
                  "INVALID_PATH": "INVALID_PATH"
                }
              }
            },
            {
              "key": "route.hops",
              "unit": "count",
              "required": true
            }
          ],
          "operator": "any_of",
          "expected": {
            "clauses": [
              {
                "operator": "numeric_max",
                "input": "route.walking_distance_m",
                "expected": {
                  "value": 0.001,
                  "unit": "m"
                }
              },
              {
                "operator": "count_min",
                "input": "route.hops",
                "expected": {
                  "value": 1
                }
              }
            ]
          }
        },
        {
          "rule_id": "TEST_ONLY.PROGRAM_APPLICABILITY_001",
          "namespace": "TEST_ONLY",
          "regulatory": false,
          "title": "synthetic: applies only when the building program is a specific value",
          "category": "synthetic",
          "severity": "info",
          "enabled": true,
          "revision": 1,
          "standard": "TEST_STANDARD",
          "edition": "0",
          "section": "§T.APPLY",
          "jurisdiction_required": false,
          "jurisdiction": {
            "country": null,
            "region": null,
            "authority": null
          },
          "source": {
            "type": "synthetic_test",
            "source_id": "synthetic_test",
            "document_id": null,
            "page": null,
            "clause": null,
            "url": null,
            "verified": false
          },
          "subject_type": "ROUTE",
          "applies_to": {
            "subject_type": "ROUTE",
            "conditions": [
              {
                "input": "building.program",
                "op": "in",
                "value": [
                  "hotel"
                ]
              }
            ]
          },
          "inputs": [
            {
              "key": "route.hops",
              "unit": "count",
              "required": true
            }
          ],
          "operator": "count_min",
          "expected": {
            "value": 1
          }
        },
        {
          "rule_id": "TEST_ONLY.OCC_ENUM_001",
          "namespace": "TEST_ONLY",
          "regulatory": false,
          "title": "synthetic: occupancy-dependent probe",
          "category": "synthetic",
          "severity": "info",
          "enabled": true,
          "revision": 1,
          "standard": "TEST_STANDARD",
          "edition": "0",
          "section": "§T.OCC",
          "jurisdiction_required": false,
          "jurisdiction": {
            "country": null,
            "region": null,
            "authority": null
          },
          "source": {
            "type": "synthetic_test",
            "source_id": "synthetic_test",
            "document_id": null,
            "page": null,
            "clause": null,
            "url": null,
            "verified": false
          },
          "subject_type": "BUILDING",
          "applies_to": {
            "subject_type": "BUILDING",
            "conditions": []
          },
          "inputs": [
            {
              "key": "occupancy.group",
              "required": true,
              "quality": {
                "status_key": "occupancy.status",
                "accept": [
                  "VERIFIED"
                ],
                "reasons": {
                  "UNCLASSIFIED": "OCCUPANCY_NOT_CLASSIFIED",
                  "CANDIDATE": "OCCUPANCY_NOT_VERIFIED",
                  "NEEDS_INFORMATION": "OCCUPANCY_NEEDS_INFORMATION",
                  "CONFLICT": "OCCUPANCY_CLASSIFICATION_CONFLICT",
                  "NOT_APPLICABLE": "OCCUPANCY_NOT_APPLICABLE"
                }
              },
              "alignment": [
                {
                  "input": "occupancy.standard",
                  "rule_field": "standard",
                  "reason": "OCCUPANCY_STANDARD_MISMATCH"
                },
                {
                  "input": "occupancy.edition",
                  "rule_field": "edition",
                  "reason": "OCCUPANCY_EDITION_MISMATCH"
                },
                {
                  "input": "occupancy.jurisdiction_country",
                  "rule_field": "jurisdiction.country",
                  "reason": "OCCUPANCY_JURISDICTION_MISMATCH"
                }
              ]
            }
          ],
          "operator": "enumeration",
          "expected": {
            "values": [
              "TEST_OCC_A"
            ]
          }
        },
        {
          "rule_id": "TEST_ONLY.OCC_REQUIRED_001",
          "namespace": "TEST_ONLY",
          "regulatory": false,
          "title": "synthetic: occupancy-dependent probe",
          "category": "synthetic",
          "severity": "info",
          "enabled": true,
          "revision": 1,
          "standard": "TEST_STANDARD",
          "edition": "0",
          "section": "§T.OCCREQ",
          "jurisdiction_required": false,
          "jurisdiction": {
            "country": null,
            "region": null,
            "authority": null
          },
          "source": {
            "type": "synthetic_test",
            "source_id": "synthetic_test",
            "document_id": null,
            "page": null,
            "clause": null,
            "url": null,
            "verified": false
          },
          "subject_type": "BUILDING",
          "applies_to": {
            "subject_type": "BUILDING",
            "conditions": []
          },
          "inputs": [
            {
              "key": "occupancy.group",
              "required": true
            }
          ],
          "operator": "existence",
          "expected": {
            "value": true
          }
        },
        {
          "rule_id": "TEST_ONLY.OCC_JUR_001",
          "namespace": "TEST_ONLY",
          "regulatory": false,
          "title": "synthetic: occupancy-dependent probe",
          "category": "synthetic",
          "severity": "info",
          "enabled": true,
          "revision": 1,
          "standard": "TEST_STANDARD",
          "edition": "0",
          "section": "§T.OCCJUR",
          "jurisdiction_required": true,
          "jurisdiction": {
            "country": "TESTLAND",
            "region": null,
            "authority": null
          },
          "source": {
            "type": "synthetic_test",
            "source_id": "synthetic_test",
            "document_id": null,
            "page": null,
            "clause": null,
            "url": null,
            "verified": false
          },
          "subject_type": "BUILDING",
          "applies_to": {
            "subject_type": "BUILDING",
            "conditions": []
          },
          "inputs": [
            {
              "key": "occupancy.group",
              "required": true,
              "quality": {
                "status_key": "occupancy.status",
                "accept": [
                  "VERIFIED"
                ],
                "reasons": {
                  "UNCLASSIFIED": "OCCUPANCY_NOT_CLASSIFIED",
                  "CANDIDATE": "OCCUPANCY_NOT_VERIFIED",
                  "NEEDS_INFORMATION": "OCCUPANCY_NEEDS_INFORMATION",
                  "CONFLICT": "OCCUPANCY_CLASSIFICATION_CONFLICT",
                  "NOT_APPLICABLE": "OCCUPANCY_NOT_APPLICABLE"
                }
              },
              "alignment": [
                {
                  "input": "occupancy.standard",
                  "rule_field": "standard",
                  "reason": "OCCUPANCY_STANDARD_MISMATCH"
                },
                {
                  "input": "occupancy.edition",
                  "rule_field": "edition",
                  "reason": "OCCUPANCY_EDITION_MISMATCH"
                },
                {
                  "input": "occupancy.jurisdiction_country",
                  "rule_field": "jurisdiction.country",
                  "reason": "OCCUPANCY_JURISDICTION_MISMATCH"
                }
              ]
            }
          ],
          "operator": "existence",
          "expected": {
            "value": true
          }
        }
      ]
    },
    {
      "ruleset_id": "TEST_ONLY.STD_ED1",
      "ruleset_version": "1",
      "standard": "TEST_STANDARD",
      "edition": "1",
      "jurisdiction": {
        "country": null,
        "region": null,
        "authority": null
      },
      "coverage_scope": "edition-isolation probe only",
      "completeness": "partial",
      "regulatory": false,
      "rules": [
        {
          "rule_id": "TEST_ONLY.EDITION_MAX_001",
          "namespace": "TEST_ONLY",
          "regulatory": false,
          "title": "synthetic edition 1 ceiling",
          "category": "synthetic",
          "severity": "info",
          "enabled": true,
          "revision": 1,
          "standard": "TEST_STANDARD",
          "edition": "1",
          "section": "§T.ED",
          "jurisdiction_required": false,
          "jurisdiction": {
            "country": null,
            "region": null,
            "authority": null
          },
          "source": {
            "type": "synthetic_test",
            "source_id": "synthetic_test",
            "document_id": null,
            "page": null,
            "clause": null,
            "url": null,
            "verified": false
          },
          "subject_type": "ROUTE",
          "applies_to": {
            "subject_type": "ROUTE",
            "conditions": []
          },
          "inputs": [
            {
              "key": "route.walking_distance_m",
              "unit": "m",
              "required": true,
              "quality": {
                "status_key": "route.distance_status",
                "accept": [
                  "COMPLETE"
                ],
                "reasons": {
                  "PARTIAL": "INCOMPLETE_DISTANCE_MEASUREMENT",
                  "GEOMETRY_NOT_SUPPORTED": "GEOMETRY_NOT_SUPPORTED",
                  "NOT_MEASURED": "DISTANCE_NOT_MEASURED",
                  "INVALID_PATH": "INVALID_PATH"
                }
              }
            }
          ],
          "operator": "numeric_max",
          "expected": {
            "value": 30,
            "unit": "m"
          }
        }
      ]
    },
    {
      "ruleset_id": "TEST_ONLY.STD_ED2",
      "ruleset_version": "1",
      "standard": "TEST_STANDARD",
      "edition": "2",
      "jurisdiction": {
        "country": null,
        "region": null,
        "authority": null
      },
      "coverage_scope": "edition-isolation probe only",
      "completeness": "partial",
      "regulatory": false,
      "rules": [
        {
          "rule_id": "TEST_ONLY.EDITION_MAX_001",
          "namespace": "TEST_ONLY",
          "regulatory": false,
          "title": "synthetic edition 2 ceiling",
          "category": "synthetic",
          "severity": "info",
          "enabled": true,
          "revision": 1,
          "standard": "TEST_STANDARD",
          "edition": "2",
          "section": "§T.ED",
          "jurisdiction_required": false,
          "jurisdiction": {
            "country": null,
            "region": null,
            "authority": null
          },
          "source": {
            "type": "synthetic_test",
            "source_id": "synthetic_test",
            "document_id": null,
            "page": null,
            "clause": null,
            "url": null,
            "verified": false
          },
          "subject_type": "ROUTE",
          "applies_to": {
            "subject_type": "ROUTE",
            "conditions": []
          },
          "inputs": [
            {
              "key": "route.walking_distance_m",
              "unit": "m",
              "required": true,
              "quality": {
                "status_key": "route.distance_status",
                "accept": [
                  "COMPLETE"
                ],
                "reasons": {
                  "PARTIAL": "INCOMPLETE_DISTANCE_MEASUREMENT",
                  "GEOMETRY_NOT_SUPPORTED": "GEOMETRY_NOT_SUPPORTED",
                  "NOT_MEASURED": "DISTANCE_NOT_MEASURED",
                  "INVALID_PATH": "INVALID_PATH"
                }
              }
            }
          ],
          "operator": "numeric_max",
          "expected": {
            "value": 25,
            "unit": "m"
          }
        }
      ]
    },
    {
      "ruleset_id": "TEST_ONLY.JURISDICTION",
      "ruleset_version": "1",
      "standard": "TEST_STANDARD",
      "edition": "0",
      "jurisdiction": {
        "country": null,
        "region": null,
        "authority": null
      },
      "coverage_scope": "jurisdiction-gate probe only",
      "completeness": "partial",
      "regulatory": false,
      "rules": [
        {
          "rule_id": "TEST_ONLY.JURISDICTION_001",
          "namespace": "TEST_ONLY",
          "regulatory": false,
          "title": "synthetic: requires a declared jurisdiction before it may be evaluated",
          "category": "synthetic",
          "severity": "info",
          "enabled": true,
          "revision": 1,
          "standard": "TEST_STANDARD",
          "edition": "0",
          "section": "§T.JUR",
          "jurisdiction_required": true,
          "jurisdiction": {
            "country": "TESTLAND",
            "region": null,
            "authority": null
          },
          "source": {
            "type": "synthetic_test",
            "source_id": "synthetic_test",
            "document_id": null,
            "page": null,
            "clause": null,
            "url": null,
            "verified": false
          },
          "subject_type": "ROUTE",
          "applies_to": {
            "subject_type": "ROUTE",
            "conditions": []
          },
          "inputs": [
            {
              "key": "route.hops",
              "unit": "count",
              "required": true
            }
          ],
          "operator": "count_min",
          "expected": {
            "value": 1
          }
        }
      ]
    }
  ]
};
const RULE_ENGINE_VERSION = ACS_RULES_REGISTRY.engine_version;
const RULE_STATES = ACS_RULES_REGISTRY.evaluation_states;
const RULE_SUBJECT_TYPES = ACS_RULES_REGISTRY.subject_types;
const RULE_UNITS = ACS_RULES_REGISTRY.units;
const RULE_OPERATORS = ACS_RULES_REGISTRY.operators;
const RULE_CONTRACTS = ACS_RULES_REGISTRY.input_contracts;
const RULE_SEVERITIES = ACS_RULES_REGISTRY.severities;
const RULE_COMPLETENESS = ACS_RULES_REGISTRY.completeness_states;
const RULE_FORBIDDEN_KEYS = ['script','code','js','eval','exec','expression','fn','function',
                             '__proto__','constructor','prototype'];
function unitDim(u){ const d=RULE_UNITS[u]; return d?d.dim:null; }
function toBase(v,unit){ if(v===null||v===undefined) return null;
  const u=RULE_UNITS[unit]; if(!u) return null;
  return u.div?Number(v)/Number(u.div):Number(v)*Number(u.mul===undefined?1:u.mul); }
function fromBase(v,unit){ if(v===null||v===undefined) return null;
  const u=RULE_UNITS[unit]; if(!u) return null;
  return u.div?Number(v)*Number(u.div):Number(v)/Number(u.mul===undefined?1:u.mul); }
/* قيمة العرض فقط — لا تُستعمل أبداً في المقارنة */
function ruleDisplay(v,unit,digits){ if(v===null||v===undefined) return null;
  digits=(digits===undefined)?3:digits;
  const x=(unit in RULE_UNITS)?fromBase(v,unit):v;
  return (typeof x==='number')?_pyRound(x,digits):x; }
function _ruleForbidden(o,depth){ depth=depth||0; if(depth>12) return true;
  if(Array.isArray(o)){ for(const v of o) if(_ruleForbidden(v,depth+1)) return true; return false; }
  if(o&&typeof o==='object'){ for(const k of Object.keys(o)){
      if(RULE_FORBIDDEN_KEYS.indexOf(String(k).toLowerCase())>=0) return true;
      if(_ruleForbidden(o[k],depth+1)) return true; } return false; }
  if(typeof o==='string'){ const t=o.trim().toLowerCase();
    if(t.indexOf('javascript:')===0||t.indexOf('data:')===0) return true; }
  return false; }
function _isNum(v){ return typeof v==='number'&&isFinite(v); }
function _checkExpected(op,expected,issues,prefix){ prefix=prefix||'';
  const spec=RULE_OPERATORS[op];
  if(!spec){ issues.push(prefix+'unknown operator: '+op); return; }
  const vt=spec.value_type;
  if(vt==='number'){
    if(!_isNum(expected.value)) issues.push(prefix+'operator '+op+' requires a numeric expected.value');
    if(spec.needs_unit&&!(expected.unit in RULE_UNITS)) issues.push(prefix+'operator '+op+' requires a known unit');
  } else if(vt==='range'){
    ['min','max'].forEach(k=>{ if(!_isNum(expected[k])) issues.push(prefix+'numeric_range requires numeric '+k); });
    if(!(expected.unit in RULE_UNITS)) issues.push(prefix+'numeric_range requires a known unit');
  } else if(vt==='boolean'){
    if(typeof expected.value!=='boolean') issues.push(prefix+'operator '+op+' requires a boolean expected.value');
  } else if(vt==='list'){
    if(!Array.isArray(expected.values)||!expected.values.length) issues.push(prefix+'operator '+op+' requires a non-empty expected.values list');
  } else if(vt==='clauses'){
    const cl=expected.clauses;
    if(!Array.isArray(cl)||!cl.length){ issues.push(prefix+'operator '+op+' requires expected.clauses'); return; }
    cl.forEach((c,i)=>{ const sub=c.operator;
      if(sub==='all_of'||sub==='any_of'){ issues.push(prefix+'clause '+i+': nested composite operators are not supported'); return; }
      if(!c.input) issues.push(prefix+'clause '+i+': missing input key');
      _checkExpected(sub,c.expected||{},issues,prefix+'clause '+i+': '); }); } }
/* فحص بنيوي + فحص دليل. قائمة فارغة = تعريف صالح */
function validateRule(rule){
  const issues=[];
  if(!rule||typeof rule!=='object'||Array.isArray(rule)) return ['rule is not an object'];
  if(_ruleForbidden(rule)) issues.push('rule contains a forbidden executable/script field or URL scheme');
  ['rule_id','operator','expected','subject_type','applies_to','inputs'].forEach(k=>{
    const v=rule[k];
    const empty=(v===null||v===undefined||v===''||(Array.isArray(v)&&!v.length)||
                 (v&&typeof v==='object'&&!Array.isArray(v)&&!Object.keys(v).length));
    if(empty&&!(k==='inputs'&&Array.isArray(v))) issues.push('missing mandatory field: '+k); });
  if(RULE_SUBJECT_TYPES.indexOf(rule.subject_type)<0) issues.push('unknown subject_type: '+rule.subject_type);
  if(rule.severity!==null&&rule.severity!==undefined&&RULE_SEVERITIES.indexOf(rule.severity)<0)
    issues.push('unknown severity: '+rule.severity);
  const inputs=rule.inputs||[];
  if(!Array.isArray(inputs)||!inputs.length) issues.push('rule declares no inputs');
  else inputs.forEach(i=>{ const key=(i||{}).key;
    if(!(key in RULE_CONTRACTS)) issues.push('input outside the declared contract: '+key);
    const u=(i||{}).unit;
    if(u!==null&&u!==undefined&&!(u in RULE_UNITS)) issues.push('unknown input unit: '+u); });
  _checkExpected(rule.operator,rule.expected||{},issues);
  const src=rule.source||{};
  if(src.url&&String(src.url).indexOf('https://')!==0) issues.push('source.url must be https');
  if(rule.regulatory===true){
    ['standard','edition','section'].forEach(k=>{ if(!rule[k]) issues.push('regulatory rule missing evidence field: '+k); });
    if(!(src.document_id||src.url)) issues.push('regulatory rule missing source document reference');
    if(src.verified!==true) issues.push('regulatory rule source is not verified');
    if(src.type==='synthetic_test') issues.push('regulatory rule may not use a synthetic_test source');
    if(rule.namespace==='TEST_ONLY') issues.push('regulatory rule may not live in the TEST_ONLY namespace');
  } else {
    if(rule.namespace!=='TEST_ONLY') issues.push('non-regulatory rule must declare namespace TEST_ONLY');
    if(src.type!=='synthetic_test') issues.push('non-regulatory rule must declare source.type synthetic_test');
    if(String(rule.rule_id||'').indexOf('TEST_ONLY.')!==0) issues.push('synthetic rule_id must be namespaced TEST_ONLY.');
  }
  return issues; }
/* هوية القاعدة تشمل المعيار والإصدار والبند والمراجعة — لا يتغيّر معناها بصمت */
function ruleUid(rule){ return [rule.standard,rule.edition,rule.section,rule.rule_id,
  'r'+rule.revision].map(x=>String(x)).join('|'); }
function ruleSources(){ return ACS_RULES_REGISTRY.sources.map(s=>Object.assign({},s)); }
function ruleSourceById(id){ const s=ACS_RULES_REGISTRY.sources.find(x=>x.source_id===id); return s?Object.assign({},s):null; }
/* أمن الاستيراد: يُرفض الملف كاملاً عند مخالفة بنيوية/أمنية */
function validateRuleSet(rs){
  const issues=[];
  if(!rs||typeof rs!=='object'||Array.isArray(rs)) return ['ruleset is not an object'];
  ['ruleset_id','ruleset_version','standard','edition','rules'].forEach(k=>{
    if(rs[k]===null||rs[k]===undefined||rs[k]==='') issues.push('ruleset missing field: '+k); });
  if(RULE_COMPLETENESS.indexOf(rs.completeness)<0) issues.push('unknown completeness: '+rs.completeness);
  if(rs.completeness==='complete_for_declared_scope'&&!rs.coverage_scope)
    issues.push('completeness=complete_for_declared_scope requires a declared coverage_scope');
  if(_ruleForbidden(rs)) issues.push('ruleset contains a forbidden executable/script field or URL scheme');
  const seen={};
  (rs.rules||[]).forEach(r=>{ const uid=ruleUid(r);
    if(seen[uid]) issues.push('duplicate rule identity: '+uid); seen[uid]=1;
    if(!RULE_OPERATORS[r.operator]) issues.push('unknown operator in '+r.rule_id+': '+r.operator); });
  return issues; }
function ruleSets(){ return ACS_RULES_REGISTRY.rulesets.map(r=>Object.assign({},r)); }
function ruleSetById(id,extra){ let rs=ACS_RULES_REGISTRY.rulesets.find(r=>r.ruleset_id===id);
  if(!rs) rs=(extra||[]).find(r=>r.ruleset_id===id); return rs||null; }
function allRules(extra){ const out=[];
  ACS_RULES_REGISTRY.rulesets.concat(extra||[]).forEach(rs=>(rs.rules||[]).forEach(r=>out.push([rs,r])));
  return out; }
/* كل القواعد التي تحمل هذا المعرّف — قد تتعدّد عبر الإصدارات */
function ruleMatches(id,extra){ return allRules(extra).filter(p=>p[1].rule_id===id); }
function ruleById(id,extra,ruleSetId){ let hits=ruleMatches(id,extra);
  if(ruleSetId!==null&&ruleSetId!==undefined) hits=hits.filter(h=>h[0].ruleset_id===ruleSetId);
  return hits.length?hits[0]:[null,null]; }
function regulatoryRuleCount(extra){ let n=0;
  allRules(extra).forEach(p=>{ if(p[1].regulatory===true&&!validateRule(p[1]).length) n++; }); return n; }
/* بوّابة CODE_REQUIRED: قاعدة تنظيمية محمّلة، مصدرها موثّق، وتعريفها صالح */
function codeRequiredAllowed(ruleId,extra){
  const hits=ruleMatches(ruleId,extra);
  if(hits.length!==1) return false;      // غير موجودة، أو ملتبسة عبر الإصدارات
  const r=hits[0][1];
  if(r.regulatory!==true) return false;
  if(((r.source||{}).verified)!==true) return false;
  return !validateRule(r).length; }
/* ---------------------------------------------------------- المواضيع --- */
function _ruleRoomOf(building,spaceId,bid){
  const idx=_dsRooms(building,bid);
  return Object.prototype.hasOwnProperty.call(idx,spaceId)?idx[spaceId]:null; }
function resolveSubject(building,rels,subjectId,bid,occupancyIndex){
  bid=bid||'bld_0';
  const sid=String(subjectId===null||subjectId===undefined?'':subjectId);
  const p=sid.indexOf(':'); if(p<0) return null;
  const kind=sid.slice(0,p).toUpperCase(), ref=sid.slice(p+1);
  if(RULE_SUBJECT_TYPES.indexOf(kind)<0) return null;
  const data={building:building,relationships:rels,building_id:bid};
  if(occupancyIndex) data.occupancy=occupancyIndex[sid];
  if(kind==='BUILDING') return {type:kind,id:sid,data:data};
  if(kind==='SPACE'){ const room=_ruleRoomOf(building,ref,bid); if(room===null) return null;
    data.space_id=ref; data.room=room; return {type:kind,id:sid,data:data}; }
  if(kind==='DOOR'){ const q=ref.lastIndexOf('.door_'); if(q<0) return null;
    const sp=ref.slice(0,q), tail=ref.slice(q+6);
    if(!/^\d+$/.test(tail)) return null;
    const room=_ruleRoomOf(building,sp,bid); if(room===null) return null;
    const doors=room.doors||[], di=parseInt(tail,10); if(di>=doors.length) return null;
    data.space_id=sp; data.room=room; data.door=doors[di]; data.door_index=di;
    return {type:kind,id:sid,data:data}; }
  if(kind==='ROUTE'){ const q=ref.indexOf('>'); if(q<0) return null;
    const a=ref.slice(0,q), b=ref.slice(q+1);
    const path=findPath(building,rels,a,b,bid);
    data.path=path; data.measurement=measurePath(building,path,bid);
    return {type:kind,id:sid,data:data}; }
  if(kind==='EGRESS'){ data.egress=findEgress(building,rels,ref,bid);
    data.exits=extractExits(building,rels,bid); data.usable_exits=usableExits(data.exits);
    return {type:kind,id:sid,data:data}; }
  return {type:kind,id:sid,data:data}; }
/* ---------------------------------------------------------- المدخلات --- */
function _ruleMissing(reason,ev){ return {present:false,value:null,unit:null,provenance:null,
  evidence:ev||[],reason:reason}; }
/* أضعف مصدر على المسار — لا تُرقّى البيانات المستنتجة إلى مؤكَّدة */
function _routeProvenance(path){
  const srcs={}; (path.edges||[]).forEach(e=>{ if(e.source) srcs[String(e.source)]=1; });
  const weak=['system_generated','geometry_inference','ai_inference'];
  for(const w of weak) if(srcs[w]) return w;
  return Object.keys(srcs).length?'user':'system_default'; }
function resolveInput(key,subject){
  if(!(key in RULE_CONTRACTS)) return _ruleMissing('INPUT_NOT_IN_CONTRACT');
  const d=(subject||{}).data||{}, t=(subject||{}).type, c=RULE_CONTRACTS[key];
  if(c.subject!==t&&c.subject!=='ANY') return _ruleMissing('SUBJECT_TYPE_MISMATCH');
  if(key.indexOf('occupancy.')===0){
    const occ=d.occupancy, field=key.slice(10);
    const _pn=v=>(v===undefined||v===null)?'None':v;   // تنسيق مطابق لـ %s في بايثون
    const ev=[{type:'occupancy',ref:(subject||{}).id,
      detail:'status='+_pn((occ||{}).status)+' records='+_pn((occ||{}).records)}];
    if(!occ) return _ruleMissing('OCCUPANCY_NOT_RESOLVED',ev);
    const val=occ[field];
    // المجموعة لا تُنشر إلا من تصنيف متحقَّق منه فعلاً
    if(['group','subgroup','standard','edition','jurisdiction_country'].indexOf(field)>=0&&
       occ.status!=='VERIFIED') return _ruleMissing('OCCUPANCY_NOT_VERIFIED',ev);
    const provMap={USER_DECLARED:'user',MANUAL_VERIFIED:'user',
                   AUTHORITATIVE_MAPPING:'rule',AI_SUGGESTED:'ai_inference'};
    const prov=provMap[occ.source||'']||'system_default';
    return {present:val!==null&&val!==undefined,value:(val===undefined?null:val),
            unit:null,provenance:prov,evidence:ev}; }
  const ok=(v,unit,prov,ev)=>({present:v!==null&&v!==undefined,value:(v===undefined?null:v),
    unit:(unit===undefined?null:unit),provenance:prov||'geometry_inference',evidence:ev||[]});
  if(t==='ROUTE'){
    const p=d.path||{}, m=d.measurement||{}, prov=_routeProvenance(p);
    const ev=[{type:'path',ref:(p.from===undefined?null:p.from),detail:(p.hops===undefined?null:p.hops)+' hops'}];
    if(key==='route.walking_distance_m')
      return ok(m.walking_distance_exact_m,'m',prov,ev.concat([{type:'measurement',
        ref:(m.distance_status===undefined?null:m.distance_status),
        detail:(m.segments||[]).length+' segments'}]));
    if(key==='route.distance_status') return ok(m.distance_status,null,prov,ev);
    if(key==='route.hops') return ok(p.hops,'count',prov,ev);
    if(key==='route.resolution') return ok(p.resolution,null,prov,ev);
    const tr=p.transitions||[], verts=tr.filter(x=>x.type==='vertical');
    if(key==='route.door_count') return ok(tr.filter(x=>x.type==='door').length,'count',prov,ev);
    if(key==='route.vertical_transition_count') return ok(verts.length,'count',prov,ev);
    if(key==='route.levels_crossed'){ const lv={}; let n=0;
      verts.forEach(x=>{ [x.from_level,x.to_level].forEach(l=>{ const k=String(l);
        if(!lv[k]){lv[k]=1;n++;} }); });
      return ok(n?Math.max(0,n-1):0,'count',prov,ev); }
    if(key==='route.uses_stairs') return ok(verts.some(x=>x.kind==='stairs'),null,prov,ev);
    if(key==='route.uses_elevator') return ok(verts.some(x=>x.kind==='elevator'),null,prov,ev);
  }
  if(t==='EGRESS'){
    const e=d.egress||{};
    const ev=[{type:'egress',ref:(e.status===undefined?null:e.status),
               detail:'selection_basis='+(e.selection_basis===undefined?null:e.selection_basis)}];
    if(key==='egress.status') return ok(e.status,null,'geometry_inference',ev);
    if(key==='egress.walking_distance_m'){ const dm=e.distance_measurement||{};
      return ok(dm.walking_distance_exact_m,'m','geometry_inference',ev); }
    if(key==='egress.distance_status') return ok(e.distance_status,null,'geometry_inference',ev);
    if(key==='egress.exit_count') return ok((d.exits||[]).length,'count','geometry_inference',ev);
    if(key==='egress.usable_exit_count') return ok((d.usable_exits||[]).length,'count','geometry_inference',ev);
  }
  if(t==='DOOR'){
    const door=d.door||{};
    const ev=[{type:'door',ref:(subject||{}).id,detail:'edge='+(door.edge===undefined?null:door.edge)}];
    if(key==='door.clear_width'){
      // حقل مصرَّح فقط — لا يُشتق العرض الحرّ من عرض فتحة أو أي قيمة أخرى
      const v=door.clear_width_m;
      if(v===null||v===undefined) return _ruleMissing('FIELD_NOT_PRESENT_IN_MODEL',ev);
      return ok(v,'m',String(door.source||'user'),ev); }
    if(key==='door.edge') return ok(door.edge,null,String(door.source||'user'),ev);
  }
  if(t==='SPACE'){
    const room=d.room||{}, rc=room.rect||[];
    const ev=[{type:'space',ref:(d.space_id===undefined?null:d.space_id),
               detail:'rect='+(rc.length?JSON.stringify(rc.slice(0,4)):'None')}];
    if(key==='space.area') return ok(rc.length>=4?Number(rc[2])*Number(rc[3]):null,'m2','geometry_inference',ev);
    if(key==='space.level') return _ruleMissing('FIELD_NOT_PRESENT_IN_MODEL',ev);
  }
  if(t==='BUILDING'){
    const b=d.building||{};
    const ev=[{type:'building',ref:(d.building_id===undefined?null:d.building_id),
               detail:'levels='+(b.levels||[]).length}];
    if(key==='building.program'){ const meta=b.meta||{};
      return ok(meta.type,null,meta.type_source||'ai_inference',ev); }
    if(key==='building.levels_count') return ok((b.levels||[]).length,'count','system_default',ev);
    if(key==='building.wall_thickness') return ok(b.wall_t,'m','system_default',ev);
  }
  return _ruleMissing('UNRESOLVED_INPUT'); }
function _ruleField(rule,path){ let cur=rule;
  for(const part of String(path===null||path===undefined?'':path).split('.')){
    if(!cur||typeof cur!=='object') return null;
    cur=cur[part]; }
  return (cur===undefined)?null:cur; }
function _contextInput(key,subject,context){
  const r=resolveInput(key,subject);
  if(r.present) return r;
  const c=RULE_CONTRACTS[key]||{};
  const alt=((context||{}).subjects||{})[c.subject];
  return (alt!==null&&alt!==undefined)?resolveInput(key,alt):r; }
/* ---------------------------------------------------------- المقيِّمات --- */
function _cmpNumeric(op,ab,expected){
  if(op==='numeric_max') return ab<=toBase(expected.value,expected.unit);
  if(op==='numeric_min') return ab>=toBase(expected.value,expected.unit);
  if(op==='numeric_range') return toBase(expected.min,expected.unit)<=ab&&ab<=toBase(expected.max,expected.unit);
  return null; }
function _evalPrimitive(op,value,unit,expected){
  if(op==='numeric_max'||op==='numeric_min'||op==='numeric_range'){
    if(!_isNum(value)) return [null,null,null];
    const eu=expected.unit;
    if(unitDim(unit)!==unitDim(eu)) return [null,null,null];
    const ab=toBase(value,unit);
    const rb=(op==='numeric_range')?[toBase(expected.min,eu),toBase(expected.max,eu)]
                                   :toBase(expected.value,eu);
    return [_cmpNumeric(op,ab,expected),ab,rb]; }
  if(op==='count_min'||op==='count_max'){
    if(!_isNum(value)) return [null,null,null];
    const rv=expected.value;
    return [(op==='count_min')?(value>=rv):(value<=rv),value,rv]; }
  if(op==='boolean_required'){
    if(typeof value!=='boolean') return [null,null,null];
    return [value===expected.value,value,expected.value]; }
  if(op==='existence'){
    const want=expected.value!==false;
    const present=value!==null&&value!==undefined&&value!==0&&value!==false;
    return [present===want,present,want]; }
  if(op==='enumeration') return [(expected.values||[]).indexOf(value)>=0,value,(expected.values||[]).slice()];
  return [null,null,null]; }
/* ---------------------------------------------------------- التقييم --- */
function evaluateRule(rule,subject,context,ruleset,extra){
  context=context||{};
  const isObj=rule&&typeof rule==='object'&&!Array.isArray(rule);
  const res={rule_id:isObj?rule.rule_id:null, rule_uid:isObj?ruleUid(rule):null,
    rule_revision:isObj?(rule.revision===undefined?null:rule.revision):null,
    namespace:isObj?(rule.namespace===undefined?null:rule.namespace):null,
    regulatory:!!(isObj&&rule.regulatory===true),
    ruleset_id:(ruleset||{}).ruleset_id===undefined?null:(ruleset||{}).ruleset_id,
    ruleset_version:(ruleset||{}).ruleset_version===undefined?null:(ruleset||{}).ruleset_version,
    standard:isObj?(rule.standard===undefined?null:rule.standard):null,
    edition:isObj?(rule.edition===undefined?null:rule.edition):null,
    section:isObj?(rule.section===undefined?null:rule.section):null,
    severity:isObj?(rule.severity===undefined?null:rule.severity):null,
    status:null, subject_type:(subject||{}).type===undefined?null:(subject||{}).type,
    subject_id:(subject||{}).id===undefined?null:(subject||{}).id,
    applicability:'UNDETERMINED', data_quality:'NOT_REQUIRED', reason:null,
    actual:null, required:null, input_provenance:{}, inputs:{}, evidence:[],
    applicability_trace:[],
    engine_version:RULE_ENGINE_VERSION,
    evaluated_at:(context.evaluated_at===undefined?null:context.evaluated_at),
    code_required_eligible:false, definition_issues:[]};
  const issues=isObj?validateRule(rule):['rule is not an object'];
  if(issues.length){ res.status='INVALID_RULE_DEFINITION'; res.reason='RULE_EVIDENCE_INCOMPLETE';
    res.definition_issues=issues; return res; }
  if(rule.enabled===false){ res.status='NOT_APPLICABLE'; res.applicability='NOT_APPLICABLE';
    res.reason='RULE_DISABLED'; return res; }
  if(subject===null||subject===undefined){ res.status='NOT_EVALUATED'; res.reason='SUBJECT_NOT_RESOLVED'; return res; }
  res.evidence.push({type:'rule_source',ref:(rule.source||{}).source_id===undefined?null:(rule.source||{}).source_id,
    detail:rule.standard+' '+rule.edition+' '+rule.section+' (verified='+
      (((rule.source||{}).verified===true)?'True':'False')+')'});
  const pin=context.edition_pin||{};
  const pinned=pin[rule.standard];
  if(pinned!==null&&pinned!==undefined&&pinned!==rule.edition){
    res.applicability_trace.push({factor:'edition_pin',expected:rule.edition,actual:pinned,satisfied:false});
    res.status='NOT_APPLICABLE'; res.applicability='NOT_APPLICABLE'; res.reason='EDITION_NOT_PINNED'; return res; }
  res.applicability_trace.push({factor:'edition_pin',expected:rule.edition,
    actual:(pinned===undefined?null:pinned),satisfied:true});
  if(rule.jurisdiction_required===true){
    const j=context.jurisdiction||{};
    if(!j.country){ res.status='NOT_EVALUATED'; res.reason='JURISDICTION_NOT_SET'; return res; }
    const rj=rule.jurisdiction||{};
    if(rj.country&&rj.country!==j.country){
      res.applicability_trace.push({factor:'jurisdiction.country',expected:rj.country,
        actual:(j.country===undefined?null:j.country),satisfied:false});
      res.status='NOT_APPLICABLE';
      res.applicability='NOT_APPLICABLE'; res.reason='JURISDICTION_MISMATCH'; return res; }
    res.applicability_trace.push({factor:'jurisdiction.country',
      expected:(rj.country===undefined?null:rj.country),
      actual:(j.country===undefined?null:j.country),satisfied:true});
    res.evidence.push({type:'jurisdiction',ref:j.country,detail:'declared by project context'}); }
  const at=rule.applies_to||{};
  if(at.subject_type&&at.subject_type!==subject.type){
    res.applicability_trace.push({factor:'subject_type',expected:at.subject_type,
      actual:subject.type,satisfied:false});
    res.status='NOT_APPLICABLE'; res.applicability='NOT_APPLICABLE'; res.reason='SUBJECT_TYPE_MISMATCH'; return res; }
  res.applicability_trace.push({factor:'subject_type',
    expected:(at.subject_type===undefined?null:at.subject_type),actual:subject.type,satisfied:true});
  for(const cond of (at.conditions||[])){
    const got=_contextInput(cond.input,subject,context);
    if(!got.present){ res.status='INSUFFICIENT_DATA'; res.applicability='UNDETERMINED';
      res.data_quality='MISSING'; res.reason='APPLICABILITY_INPUT_MISSING: '+cond.input; return res; }
    const v=got.value, op=cond.op, want=cond.value;
    let okc=null;
    if(op==='in') okc=(want||[]).indexOf(v)>=0;
    else if(op==='equals') okc=(v===want);
    else if(op==='not_in') okc=(want||[]).indexOf(v)<0;
    if(okc===null){ res.status='UNSUPPORTED'; res.reason='UNSUPPORTED_APPLICABILITY_OPERATOR: '+op; return res; }
    res.applicability_trace.push({factor:cond.input,op:op,expected:want,value:undefined,
      actual:(v===undefined?null:v),satisfied:!!okc});
    delete res.applicability_trace[res.applicability_trace.length-1].value;
    if(!okc){ res.status='NOT_APPLICABLE'; res.applicability='NOT_APPLICABLE';
      res.reason='CONDITION_NOT_MET: '+cond.input; return res; } }
  res.applicability='APPLICABLE';
  /* الترتيب مقصود: "الجودة غير كافية" تفسّر غياب القيمة، فهي أصدق من "قيمة مفقودة" */
  const vals={};
  for(const spec of (rule.inputs||[])){
    const key=spec.key, got=resolveInput(key,subject);
    vals[key]=got;
    res.inputs[key]={present:got.present,value:got.value,
      unit:(spec.unit===undefined||spec.unit===null)?(got.unit===undefined?null:got.unit):spec.unit};
    if(got.provenance) res.input_provenance[key]=got.provenance;
    (got.evidence||[]).forEach(e=>{ if(!res.evidence.some(x=>JSON.stringify(x)===JSON.stringify(e))) res.evidence.push(e); }); }
  for(const spec of (rule.inputs||[])){
    const q=spec.quality; if(!q) continue;
    const st=resolveInput(q.status_key,subject);
    res.inputs[q.status_key]={present:st.present,value:st.value,unit:null};
    if(!st.present){ res.status='INSUFFICIENT_DATA'; res.data_quality='MISSING';
      res.reason='MISSING_QUALITY_STATUS: '+q.status_key; return res; }
    if((q.accept||[]).indexOf(st.value)<0){
      res.status='NOT_EVALUATED'; res.data_quality='INCOMPLETE';
      res.reason=(q.reasons||{})[st.value]||'INPUT_QUALITY_INSUFFICIENT';
      res.evidence.push({type:'data_quality',ref:q.status_key,
        detail:'actual='+st.value+' accept='+_pyList(q.accept||[])});
      return res; } }
  // محاذاة معلَنة: قيمة مدخل يجب أن تطابق حقلاً في القاعدة نفسها
  for(const spec of (rule.inputs||[])){
    for(const al of (spec.alignment||[])){
      const want=_ruleField(rule,al.rule_field);
      if(want===null||want===undefined) continue;
      const got=resolveInput(al.input,subject);
      res.inputs[al.input]={present:got.present,value:got.value,unit:null};
      if(!got.present){ res.status='INSUFFICIENT_DATA'; res.data_quality='MISSING';
        res.reason='MISSING_ALIGNMENT_INPUT: '+al.input; return res; }
      if(got.value!==want){ res.status='NOT_EVALUATED'; res.data_quality='INCOMPLETE';
        res.reason=al.reason||'ALIGNMENT_MISMATCH';
        res.evidence.push({type:'alignment',ref:al.input,
          detail:'actual='+got.value+' rule='+want});
        return res; } } }
  for(const spec of (rule.inputs||[])){
    const key=spec.key;
    if(spec.required&&!vals[key].present){ res.status='INSUFFICIENT_DATA'; res.data_quality='MISSING';
      res.reason='MISSING_REQUIRED_INPUT: '+key+' ('+(vals[key].reason===undefined?'None':vals[key].reason)+')';
      return res; } }
  res.data_quality='COMPLETE';
  const op=rule.operator, expected=rule.expected||{};
  if(op==='all_of'||op==='any_of'){
    const sub=[];
    for(const c of (expected.clauses||[])){
      const spec=(rule.inputs||[]).find(s=>s.key===c.input)||null;
      const got=vals[c.input]||{};
      const unit=(spec&&spec.unit!==undefined&&spec.unit!==null)?spec.unit:(got.unit===undefined?null:got.unit);
      const pr=_evalPrimitive(c.operator,got.value,unit,c.expected||{});
      if(pr[0]===null){ res.status='UNSUPPORTED';
        res.reason='UNSUPPORTED_CLAUSE: '+c.operator+'/'+c.input; return res; }
      const du=((c.expected||{}).unit)||unit;
      sub.push({input:c.input,operator:c.operator,satisfied:!!pr[0],
        actual:ruleDisplay(pr[1],du),required:ruleDisplay(pr[2],du)}); }
    const satisfied=(op==='all_of')?sub.every(s=>s.satisfied):sub.some(s=>s.satisfied);
    res.actual={clauses:sub}; res.required={operator:op,clauses:sub.length};
    res.status=satisfied?'PASS':'FAIL';
  } else {
    const spec=(rule.inputs||[])[0], got=vals[spec.key]||{};
    const unit=(spec.unit===undefined||spec.unit===null)?(got.unit===undefined?null:got.unit):spec.unit;
    const pr=_evalPrimitive(op,got.value,unit,expected);
    if(pr[0]===null){ res.status='UNSUPPORTED'; res.reason='UNSUPPORTED_OPERATOR_FOR_INPUT: '+op; return res; }
    const du=RULE_OPERATORS[op].needs_unit?expected.unit:null;
    res.actual={value:pr[1],unit:(du||unit),
      display_value:du?ruleDisplay(pr[1],du):pr[1],display_unit:du||unit,input:spec.key};
    if(op==='numeric_range')
      res.required={operator:op,min:pr[2][0],max:pr[2][1],unit:du,
        display_min:ruleDisplay(pr[2][0],du),display_max:ruleDisplay(pr[2][1],du),display_unit:du};
    else
      res.required={operator:op,value:pr[2],unit:du,
        display_value:du?ruleDisplay(pr[2],du):pr[2],display_unit:du};
    res.status=pr[0]?'PASS':'FAIL'; }
  res.code_required_eligible=!!(res.regulatory&&(res.status==='PASS'||res.status==='FAIL')&&
    ((rule.source||{}).verified===true));
  return res; }
function _pyList(a){ return '['+a.map(x=>"'"+x+"'").join(', ')+']'; }
function evaluateRuleSet(ruleSetId,subjects,context,extra){
  const rs=ruleSetById(ruleSetId,extra);
  if(!rs) return {ruleset_id:ruleSetId,results:[],error:'RULESET_NOT_FOUND'};
  const issues=validateRuleSet(rs);
  if(issues.length) return {ruleset_id:ruleSetId,results:[],error:'INVALID_RULESET',issues:issues};
  const results=[];
  (rs.rules||[]).forEach(r=>subjects.forEach(s=>results.push(evaluateRule(r,s,context,rs,extra))));
  return {ruleset_id:rs.ruleset_id,ruleset_version:rs.ruleset_version,standard:rs.standard,
    edition:rs.edition,completeness:(rs.completeness===undefined?null:rs.completeness),
    coverage_scope:(rs.coverage_scope===undefined?null:rs.coverage_scope),results:results}; }
/* تجميع محافظ: لا يقول "المبنى مطابق" أبداً في هذه المرحلة */
function aggregateRuleResults(results,ruleset){
  const counts={PASS:0,FAIL:0,NOT_APPLICABLE:0,NOT_EVALUATED:0,INSUFFICIENT_DATA:0,
                INVALID_RULE_DEFINITION:0,UNSUPPORTED:0};
  let reg=0, syn=0;
  (results||[]).forEach(r=>{ counts[r.status]=(counts[r.status]||0)+1;
    if(r.regulatory) reg++; else syn++; });
  const rsv=ruleset||{};
  const completeness=rsv.completeness||'unknown';
  const out={ruleset_id:rsv.ruleset_id===undefined?null:rsv.ruleset_id,
    ruleset_version:rsv.ruleset_version===undefined?null:rsv.ruleset_version,
    standard:rsv.standard===undefined?null:rsv.standard,
    edition:rsv.edition===undefined?null:rsv.edition,
    coverage_scope:rsv.coverage_scope===undefined?null:rsv.coverage_scope,
    completeness:completeness, rules_evaluated:(results||[]).length,
    pass:counts.PASS, fail:counts.FAIL, not_applicable:counts.NOT_APPLICABLE,
    not_evaluated:counts.NOT_EVALUATED, insufficient_data:counts.INSUFFICIENT_DATA,
    invalid_rules:counts.INVALID_RULE_DEFINITION, unsupported:counts.UNSUPPORTED,
    regulatory_results:reg, synthetic_results:syn,
    regulatory_rules_loaded:regulatoryRuleCount(),
    overall_compliance:'NOT_DETERMINED', engine_version:RULE_ENGINE_VERSION};
  const determinable=(reg>0&&completeness==='complete_for_declared_scope'&&
    out.not_evaluated===0&&out.insufficient_data===0&&out.invalid_rules===0&&out.unsupported===0);
  if(determinable) out.overall_compliance=(out.fail===0)?'COMPLIANT_WITHIN_DECLARED_SCOPE'
                                                        :'NON_COMPLIANT_WITHIN_DECLARED_SCOPE';
  out.statement='تم التقييم مقابل '+out.rules_evaluated+' قاعدة مُهيّأة ('+reg+
    ' تنظيمية، '+syn+' اصطناعية للاختبار). لا يوجد حكم مطابقة: '+out.overall_compliance+'.';
  return out; }
function ruleIssues(extra){
  const issues=[];
  ACS_RULES_REGISTRY.rulesets.concat(extra||[]).forEach(rs=>{
    validateRuleSet(rs).forEach(i=>issues.push('['+rs.ruleset_id+'] '+i));
    (rs.rules||[]).forEach(r=>validateRule(r).forEach(i=>issues.push('['+rs.ruleset_id+'/'+r.rule_id+'] '+i))); });
  return issues; }
/* ==================================================================
   المرحلة 2 — أساس استيراد المصادر الرسمية والتحقّق من حِزَم القواعد.
   نسخة مطابقة لـ acs_ingest.py، والتجهيزات منسوخة حرفياً من acs_ingest.json.
   الاستخراج ليس تحقّقاً • لا تفعيل تلقائي • الذكاء الاصطناعي يساعد ولا يوثّق •
   كل وثيقة مثبَّتة ببصمة SHA-256 • مقتطفات قصيرة فقط (لا استنساخ معايير) •
   المستندات بيانات لا شيفرة • التعارض غير المحسوم ⇒ NOT_EVALUATED.
   ================================================================== */
const ACS_INGEST_FIXTURES = {
 "schema": "acs.ingest/1",
 "pipeline_version": "acs-ingest/1.0.0",
 "note": "SYNTHETIC FIXTURES ONLY. No official standard text, clause number, edition, page or URL appears in this file. Every document is synthetic=true and official=false, every rule is regulatory=false / namespace TEST_ONLY. Real regulatory content may only enter through the documented ingestion pipeline with authoritative supplied source material and explicit approval. Real (non-synthetic) source documents live in acs_sources.json, never here.",
 "excerpt_max_chars": 300,
 "document_states": [
  "UNVERIFIED",
  "SOURCE_IDENTIFIED",
  "OFFICIAL_SOURCE_VERIFIED",
  "CONTENT_VERIFIED",
  "SUPERSEDED",
  "REVOKED",
  "INVALID"
 ],
 "document_transitions": {
  "UNVERIFIED": [
   "SOURCE_IDENTIFIED",
   "INVALID"
  ],
  "SOURCE_IDENTIFIED": [
   "OFFICIAL_SOURCE_VERIFIED",
   "CONTENT_VERIFIED",
   "INVALID",
   "REVOKED"
  ],
  "OFFICIAL_SOURCE_VERIFIED": [
   "CONTENT_VERIFIED",
   "SUPERSEDED",
   "REVOKED",
   "INVALID"
  ],
  "CONTENT_VERIFIED": [
   "SUPERSEDED",
   "REVOKED",
   "INVALID"
  ],
  "SUPERSEDED": [
   "REVOKED"
  ],
  "REVOKED": [],
  "INVALID": []
 },
 "fragment_states": [
  "EXTRACTED",
  "REVIEWED",
  "SUPERSEDED",
  "INVALID"
 ],
 "fragment_kinds": [
  "clause",
  "table_row",
  "table_cell",
  "definition",
  "exception",
  "footnote",
  "toc_locator"
 ],
 "candidate_states": [
  "EXTRACTED",
  "NEEDS_INTERPRETATION",
  "NEEDS_CROSS_REFERENCE",
  "NEEDS_EXCEPTION_REVIEW",
  "READY_FOR_VERIFICATION",
  "REJECTED",
  "VERIFIED"
 ],
 "candidate_transitions": {
  "EXTRACTED": [
   "NEEDS_INTERPRETATION",
   "NEEDS_CROSS_REFERENCE",
   "NEEDS_EXCEPTION_REVIEW",
   "READY_FOR_VERIFICATION",
   "REJECTED"
  ],
  "NEEDS_INTERPRETATION": [
   "NEEDS_CROSS_REFERENCE",
   "NEEDS_EXCEPTION_REVIEW",
   "READY_FOR_VERIFICATION",
   "REJECTED"
  ],
  "NEEDS_CROSS_REFERENCE": [
   "NEEDS_INTERPRETATION",
   "NEEDS_EXCEPTION_REVIEW",
   "READY_FOR_VERIFICATION",
   "REJECTED"
  ],
  "NEEDS_EXCEPTION_REVIEW": [
   "NEEDS_INTERPRETATION",
   "NEEDS_CROSS_REFERENCE",
   "READY_FOR_VERIFICATION",
   "REJECTED"
  ],
  "READY_FOR_VERIFICATION": [
   "VERIFIED",
   "REJECTED",
   "NEEDS_INTERPRETATION",
   "NEEDS_CROSS_REFERENCE",
   "NEEDS_EXCEPTION_REVIEW"
  ],
  "REJECTED": [
   "NEEDS_INTERPRETATION"
  ],
  "VERIFIED": [
   "REJECTED",
   "NEEDS_INTERPRETATION"
  ]
 },
 "pack_states": [
  "DRAFT",
  "UNDER_REVIEW",
  "VERIFIED_PARTIAL",
  "VERIFIED_FOR_DECLARED_SCOPE",
  "SUPERSEDED",
  "REVOKED"
 ],
 "pack_transitions": {
  "DRAFT": [
   "UNDER_REVIEW",
   "REVOKED"
  ],
  "UNDER_REVIEW": [
   "VERIFIED_PARTIAL",
   "VERIFIED_FOR_DECLARED_SCOPE",
   "DRAFT",
   "REVOKED"
  ],
  "VERIFIED_PARTIAL": [
   "VERIFIED_FOR_DECLARED_SCOPE",
   "SUPERSEDED",
   "REVOKED",
   "UNDER_REVIEW"
  ],
  "VERIFIED_FOR_DECLARED_SCOPE": [
   "SUPERSEDED",
   "REVOKED",
   "UNDER_REVIEW"
  ],
  "SUPERSEDED": [
   "REVOKED"
  ],
  "REVOKED": []
 },
 "pipeline_stages": [
  "SOURCE_ADDED",
  "SOURCE_VERIFIED",
  "CLAUSES_EXTRACTED",
  "CANDIDATE_RULES",
  "REVIEW",
  "VERIFIED_RULES",
  "DRAFT_RULE_PACK",
  "VERIFIED_RULE_PACK",
  "PROJECT_ACTIVATION"
 ],
 "origin_types": [
  "uploaded_file",
  "official_url",
  "manual_reference"
 ],
 "extraction_methods": [
  "manual_transcription",
  "text_layer_extraction",
  "ocr",
  "ai_assisted_extraction",
  "structured_import"
 ],
 "verification_methods": [
  "explicit_manual_approval",
  "dual_manual_approval",
  "authority_attestation",
  "ai_suggestion"
 ],
 "relation_types": [
  "supersedes",
  "superseded_by",
  "amends",
  "amended_by",
  "references",
  "depends_on"
 ],
 "exception_resolutions": [
  "open",
  "resolved",
  "declared_unsupported"
 ],
 "store": {
  "documents": [
   {
    "document_id": "SYNDOC-ED1",
    "source_id": "synthetic_test",
    "title": "TEST_STANDARD_001 synthetic fixture, Edition 1",
    "standard": "TEST_STANDARD_001",
    "edition": "1",
    "jurisdiction": {
     "country": null,
     "region": null,
     "authority": null
    },
    "document_type": "synthetic_fixture",
    "official": false,
    "synthetic": true,
    "origin": {
     "type": "manual_reference",
     "url": null,
     "filename": null
    },
    "integrity": {
     "sha256": "0105f93da68dfc03abd9a396de9bf761f6bdbd22ecceda71372fb353f9bdafb9",
     "size_bytes": 295
    },
    "verification": {
     "status": "UNVERIFIED",
     "method": null,
     "evidence": null,
     "verified_at": null,
     "verified_by": null
    },
    "relations": [],
    "synthetic_content": "TEST_STANDARD_001 (SYNTHETIC FIXTURE) — Edition 1\nT.1 A measured route shall not exceed the synthetic ceiling stated in Table T-1.\nT.2 Except as permitted by Section T.9, a synthetic opening shall meet Table T-2.\nT.3 Definitions: 'synthetic route' means a route produced by this fixture only.\n"
   },
   {
    "document_id": "SYNDOC-ED2",
    "source_id": "synthetic_test",
    "title": "TEST_STANDARD_001 synthetic fixture, Edition 2",
    "standard": "TEST_STANDARD_001",
    "edition": "2",
    "jurisdiction": {
     "country": null,
     "region": null,
     "authority": null
    },
    "document_type": "synthetic_fixture",
    "official": false,
    "synthetic": true,
    "origin": {
     "type": "manual_reference",
     "url": null,
     "filename": null
    },
    "integrity": {
     "sha256": "7e55ebca47e2936ee889bbed4fedc75d75bc4a6d21d9687df10d5f991e5d490b",
     "size_bytes": 134
    },
    "verification": {
     "status": "UNVERIFIED",
     "method": null,
     "evidence": null,
     "verified_at": null,
     "verified_by": null
    },
    "relations": [
     {
      "type": "supersedes",
      "document_id": "SYNDOC-ED1"
     }
    ],
    "synthetic_content": "TEST_STANDARD_001 (SYNTHETIC FIXTURE) — Edition 2\nT.1 A measured route shall not exceed the revised synthetic ceiling in Table T-1.\n"
   },
   {
    "document_id": "SYNDOC-LOOKS-OFFICIAL",
    "source_id": "synthetic_test",
    "title": "TEST_NATIONAL_STANDARD synthetic fixture (title looks official, source is not)",
    "standard": "TEST_NATIONAL_STANDARD",
    "edition": "A",
    "jurisdiction": {
     "country": null,
     "region": null,
     "authority": null
    },
    "document_type": "synthetic_fixture",
    "official": false,
    "synthetic": true,
    "origin": {
     "type": "manual_reference",
     "url": null,
     "filename": null
    },
    "integrity": {
     "sha256": "cbe3d6348bc714cb82c3c8954549ecb6dd4cf622ea466b71d4aafe666b578df2",
     "size_bytes": 134
    },
    "verification": {
     "status": "UNVERIFIED",
     "method": null,
     "evidence": null,
     "verified_at": null,
     "verified_by": null
    },
    "relations": [],
    "synthetic_content": "TEST_NATIONAL_STANDARD (SYNTHETIC FIXTURE, NOT OFFICIAL) — Edition A\nN.1 A synthetic placeholder clause with no regulatory meaning.\n"
   }
  ],
  "fragments": [
   {
    "fragment_id": "SYNFRAG-ED1-T1",
    "document_id": "SYNDOC-ED1",
    "document_hash": "0105f93da68dfc03abd9a396de9bf761f6bdbd22ecceda71372fb353f9bdafb9",
    "section": "T.1",
    "clause": "T.1",
    "page": null,
    "kind": "clause",
    "text_reference": "SYNDOC-ED1 §T.1 line 2",
    "excerpt": "A measured route shall not exceed the synthetic ceiling stated in Table T-1.",
    "normalized_meaning": "measured route length has a stated synthetic ceiling",
    "location": {
     "start": 52,
     "end": 133
    },
    "extraction_method": "manual_transcription",
    "status": "EXTRACTED"
   },
   {
    "fragment_id": "SYNFRAG-ED1-T1-TABLE",
    "document_id": "SYNDOC-ED1",
    "document_hash": "0105f93da68dfc03abd9a396de9bf761f6bdbd22ecceda71372fb353f9bdafb9",
    "section": "T.1",
    "clause": "Table T-1",
    "page": null,
    "kind": "table_row",
    "text_reference": "SYNDOC-ED1 Table T-1 row 'synthetic-A'",
    "excerpt": null,
    "normalized_meaning": "row synthetic-A carries the ceiling value",
    "location": {
     "start": 0,
     "end": 0
    },
    "extraction_method": "manual_transcription",
    "status": "EXTRACTED"
   },
   {
    "fragment_id": "SYNFRAG-ED1-T2",
    "document_id": "SYNDOC-ED1",
    "document_hash": "0105f93da68dfc03abd9a396de9bf761f6bdbd22ecceda71372fb353f9bdafb9",
    "section": "T.2",
    "clause": "T.2",
    "page": null,
    "kind": "clause",
    "text_reference": "SYNDOC-ED1 §T.2 line 3",
    "excerpt": "Except as permitted by Section T.9, a synthetic opening shall meet Table T-2.",
    "normalized_meaning": "opening requirement with an unresolved exception reference",
    "location": {
     "start": 134,
     "end": 210
    },
    "extraction_method": "manual_transcription",
    "status": "EXTRACTED"
   },
   {
    "fragment_id": "SYNFRAG-ED1-DEF",
    "document_id": "SYNDOC-ED1",
    "document_hash": "0105f93da68dfc03abd9a396de9bf761f6bdbd22ecceda71372fb353f9bdafb9",
    "section": "T.3",
    "clause": "T.3",
    "page": null,
    "kind": "definition",
    "text_reference": "SYNDOC-ED1 §T.3 definitions",
    "excerpt": "'synthetic route' means a route produced by this fixture only.",
    "normalized_meaning": "term definition for the synthetic fixture",
    "location": {
     "start": 211,
     "end": 280
    },
    "extraction_method": "manual_transcription",
    "status": "EXTRACTED"
   },
   {
    "fragment_id": "SYNFRAG-ED2-T1",
    "document_id": "SYNDOC-ED2",
    "document_hash": "7e55ebca47e2936ee889bbed4fedc75d75bc4a6d21d9687df10d5f991e5d490b",
    "section": "T.1",
    "clause": "T.1",
    "page": null,
    "kind": "clause",
    "text_reference": "SYNDOC-ED2 §T.1 line 2",
    "excerpt": "A measured route shall not exceed the revised synthetic ceiling in Table T-1.",
    "normalized_meaning": "edition 2 revises the synthetic ceiling",
    "location": {
     "start": 52,
     "end": 130
    },
    "extraction_method": "manual_transcription",
    "status": "EXTRACTED"
   }
  ],
  "candidates": [
   {
    "candidate_id": "SYNCAND-ED1-T1",
    "document_id": "SYNDOC-ED1",
    "document_hash": "0105f93da68dfc03abd9a396de9bf761f6bdbd22ecceda71372fb353f9bdafb9",
    "fragment_ids": [
     "SYNFRAG-ED1-T1",
     "SYNFRAG-ED1-T1-TABLE"
    ],
    "section": "T.1",
    "clause": "T.1",
    "page": null,
    "extraction_method": "manual_transcription",
    "interpretation_method": "manual_structured_mapping",
    "ai_assisted": false,
    "proposed_rule": {
     "rule_id": "TEST_ONLY.SYN_ED1_MAX",
     "namespace": "TEST_ONLY",
     "regulatory": false,
     "title": "synthetic rule derived from a synthetic fixture document",
     "category": "synthetic",
     "severity": "info",
     "enabled": true,
     "revision": 1,
     "standard": "TEST_STANDARD_001",
     "edition": "1",
     "section": "T.1",
     "jurisdiction_required": false,
     "jurisdiction": {
      "country": null,
      "region": null,
      "authority": null
     },
     "source": {
      "type": "synthetic_test",
      "source_id": "synthetic_test",
      "document_id": null,
      "page": null,
      "clause": null,
      "url": null,
      "verified": false
     },
     "subject_type": "ROUTE",
     "applies_to": {
      "subject_type": "ROUTE",
      "conditions": []
     },
     "inputs": [
      {
       "key": "route.walking_distance_m",
       "unit": "m",
       "required": true,
       "quality": {
        "status_key": "route.distance_status",
        "accept": [
         "COMPLETE"
        ],
        "reasons": {
         "PARTIAL": "INCOMPLETE_DISTANCE_MEASUREMENT",
         "GEOMETRY_NOT_SUPPORTED": "GEOMETRY_NOT_SUPPORTED",
         "NOT_MEASURED": "DISTANCE_NOT_MEASURED",
         "INVALID_PATH": "INVALID_PATH"
        }
       }
      }
     ],
     "operator": "numeric_max",
     "expected": {
      "value": 30,
      "unit": "m"
     },
     "exceptions": []
    },
    "exceptions": [],
    "cross_references": [],
    "definition_refs": [
     {
      "term": "synthetic route",
      "fragment_id": "SYNFRAG-ED1-DEF"
     }
    ],
    "table_context": {
     "table_id": "Table T-1",
     "row": "synthetic-A",
     "column": "ceiling",
     "conditions": [
      {
       "factor": "synthetic_category",
       "value": "A"
      }
     ]
    },
    "status": "EXTRACTED",
    "status_detail": [],
    "verification": null,
    "history": []
   },
   {
    "candidate_id": "SYNCAND-ED2-T1",
    "document_id": "SYNDOC-ED2",
    "document_hash": "7e55ebca47e2936ee889bbed4fedc75d75bc4a6d21d9687df10d5f991e5d490b",
    "fragment_ids": [
     "SYNFRAG-ED2-T1"
    ],
    "section": "T.1",
    "clause": "T.1",
    "page": null,
    "extraction_method": "manual_transcription",
    "interpretation_method": "manual_structured_mapping",
    "ai_assisted": false,
    "proposed_rule": {
     "rule_id": "TEST_ONLY.SYN_ED2_MAX",
     "namespace": "TEST_ONLY",
     "regulatory": false,
     "title": "synthetic rule derived from a synthetic fixture document",
     "category": "synthetic",
     "severity": "info",
     "enabled": true,
     "revision": 1,
     "standard": "TEST_STANDARD_001",
     "edition": "2",
     "section": "T.1",
     "jurisdiction_required": false,
     "jurisdiction": {
      "country": null,
      "region": null,
      "authority": null
     },
     "source": {
      "type": "synthetic_test",
      "source_id": "synthetic_test",
      "document_id": null,
      "page": null,
      "clause": null,
      "url": null,
      "verified": false
     },
     "subject_type": "ROUTE",
     "applies_to": {
      "subject_type": "ROUTE",
      "conditions": []
     },
     "inputs": [
      {
       "key": "route.walking_distance_m",
       "unit": "m",
       "required": true,
       "quality": {
        "status_key": "route.distance_status",
        "accept": [
         "COMPLETE"
        ],
        "reasons": {
         "PARTIAL": "INCOMPLETE_DISTANCE_MEASUREMENT",
         "GEOMETRY_NOT_SUPPORTED": "GEOMETRY_NOT_SUPPORTED",
         "NOT_MEASURED": "DISTANCE_NOT_MEASURED",
         "INVALID_PATH": "INVALID_PATH"
        }
       }
      }
     ],
     "operator": "numeric_max",
     "expected": {
      "value": 25,
      "unit": "m"
     },
     "exceptions": []
    },
    "exceptions": [],
    "cross_references": [],
    "definition_refs": [],
    "table_context": null,
    "status": "EXTRACTED",
    "status_detail": [],
    "verification": null,
    "history": []
   },
   {
    "candidate_id": "SYNCAND-EXC",
    "document_id": "SYNDOC-ED1",
    "document_hash": "0105f93da68dfc03abd9a396de9bf761f6bdbd22ecceda71372fb353f9bdafb9",
    "fragment_ids": [
     "SYNFRAG-ED1-T2"
    ],
    "section": "T.2",
    "clause": "T.2",
    "page": null,
    "extraction_method": "manual_transcription",
    "interpretation_method": "manual_structured_mapping",
    "ai_assisted": false,
    "proposed_rule": {
     "rule_id": "TEST_ONLY.SYN_OPENING_MIN",
     "namespace": "TEST_ONLY",
     "regulatory": false,
     "title": "synthetic rule derived from a synthetic fixture document",
     "category": "synthetic",
     "severity": "info",
     "enabled": true,
     "revision": 1,
     "standard": "TEST_STANDARD_001",
     "edition": "1",
     "section": "T.2",
     "jurisdiction_required": false,
     "jurisdiction": {
      "country": null,
      "region": null,
      "authority": null
     },
     "source": {
      "type": "synthetic_test",
      "source_id": "synthetic_test",
      "document_id": null,
      "page": null,
      "clause": null,
      "url": null,
      "verified": false
     },
     "subject_type": "DOOR",
     "applies_to": {
      "subject_type": "DOOR",
      "conditions": []
     },
     "inputs": [
      {
       "key": "door.clear_width",
       "unit": "m",
       "required": true
      }
     ],
     "operator": "numeric_min",
     "expected": {
      "value": 900,
      "unit": "mm"
     },
     "exceptions": []
    },
    "exceptions": [
     {
      "condition": "as permitted by Section T.9",
      "source_reference": "SYNDOC-ED1 §T.9",
      "resolution": "open"
     }
    ],
    "cross_references": [],
    "definition_refs": [],
    "table_context": null,
    "status": "EXTRACTED",
    "status_detail": [],
    "verification": null,
    "history": []
   },
   {
    "candidate_id": "SYNCAND-XREF",
    "document_id": "SYNDOC-ED1",
    "document_hash": "0105f93da68dfc03abd9a396de9bf761f6bdbd22ecceda71372fb353f9bdafb9",
    "fragment_ids": [
     "SYNFRAG-ED1-T2"
    ],
    "section": "T.2",
    "clause": "T.2",
    "page": null,
    "extraction_method": "manual_transcription",
    "interpretation_method": "manual_structured_mapping",
    "ai_assisted": false,
    "proposed_rule": {
     "rule_id": "TEST_ONLY.SYN_XREF",
     "namespace": "TEST_ONLY",
     "regulatory": false,
     "title": "synthetic rule derived from a synthetic fixture document",
     "category": "synthetic",
     "severity": "info",
     "enabled": true,
     "revision": 1,
     "standard": "TEST_STANDARD_001",
     "edition": "1",
     "section": "T.2",
     "jurisdiction_required": false,
     "jurisdiction": {
      "country": null,
      "region": null,
      "authority": null
     },
     "source": {
      "type": "synthetic_test",
      "source_id": "synthetic_test",
      "document_id": null,
      "page": null,
      "clause": null,
      "url": null,
      "verified": false
     },
     "subject_type": "ROUTE",
     "applies_to": {
      "subject_type": "ROUTE",
      "conditions": []
     },
     "inputs": [
      {
       "key": "route.hops",
       "unit": "count",
       "required": true
      }
     ],
     "operator": "count_min",
     "expected": {
      "value": 1
     },
     "exceptions": []
    },
    "exceptions": [],
    "cross_references": [
     {
      "label": "Section T.9",
      "resolution": "open",
      "fragment_id": null
     }
    ],
    "definition_refs": [],
    "table_context": null,
    "status": "EXTRACTED",
    "status_detail": [],
    "verification": null,
    "history": []
   },
   {
    "candidate_id": "SYNCAND-AI",
    "document_id": "SYNDOC-ED1",
    "document_hash": "0105f93da68dfc03abd9a396de9bf761f6bdbd22ecceda71372fb353f9bdafb9",
    "fragment_ids": [
     "SYNFRAG-ED1-T1"
    ],
    "section": "T.1",
    "clause": "T.1",
    "page": null,
    "extraction_method": "manual_transcription",
    "interpretation_method": "ai_assisted_structured_mapping",
    "ai_assisted": true,
    "proposed_rule": {
     "rule_id": "TEST_ONLY.SYN_AI_DRAFT",
     "namespace": "TEST_ONLY",
     "regulatory": false,
     "title": "synthetic rule derived from a synthetic fixture document",
     "category": "synthetic",
     "severity": "info",
     "enabled": true,
     "revision": 1,
     "standard": "TEST_STANDARD_001",
     "edition": "1",
     "section": "T.1",
     "jurisdiction_required": false,
     "jurisdiction": {
      "country": null,
      "region": null,
      "authority": null
     },
     "source": {
      "type": "synthetic_test",
      "source_id": "synthetic_test",
      "document_id": null,
      "page": null,
      "clause": null,
      "url": null,
      "verified": false
     },
     "subject_type": "ROUTE",
     "applies_to": {
      "subject_type": "ROUTE",
      "conditions": []
     },
     "inputs": [
      {
       "key": "route.hops",
       "unit": "count",
       "required": true
      }
     ],
     "operator": "count_min",
     "expected": {
      "value": 1
     },
     "exceptions": []
    },
    "exceptions": [],
    "cross_references": [],
    "definition_refs": [],
    "table_context": null,
    "status": "EXTRACTED",
    "status_detail": [],
    "verification": null,
    "history": []
   },
   {
    "candidate_id": "SYNCAND-BROKEN",
    "document_id": "SYNDOC-ED1",
    "document_hash": "0105f93da68dfc03abd9a396de9bf761f6bdbd22ecceda71372fb353f9bdafb9",
    "fragment_ids": [
     "SYNFRAG-MISSING-4.2"
    ],
    "section": "4.2",
    "clause": "4.2",
    "page": null,
    "extraction_method": "manual_transcription",
    "interpretation_method": "manual_structured_mapping",
    "ai_assisted": false,
    "proposed_rule": {
     "rule_id": "TEST_ONLY.SYN_BROKEN",
     "namespace": "TEST_ONLY",
     "regulatory": false,
     "title": "synthetic rule derived from a synthetic fixture document",
     "category": "synthetic",
     "severity": "info",
     "enabled": true,
     "revision": 1,
     "standard": "TEST_STANDARD_001",
     "edition": "1",
     "section": "4.2",
     "jurisdiction_required": false,
     "jurisdiction": {
      "country": null,
      "region": null,
      "authority": null
     },
     "source": {
      "type": "synthetic_test",
      "source_id": "synthetic_test",
      "document_id": null,
      "page": null,
      "clause": null,
      "url": null,
      "verified": false
     },
     "subject_type": "ROUTE",
     "applies_to": {
      "subject_type": "ROUTE",
      "conditions": []
     },
     "inputs": [
      {
       "key": "route.hops",
       "unit": "count",
       "required": true
      }
     ],
     "operator": "count_min",
     "expected": {
      "value": 1
     },
     "exceptions": []
    },
    "exceptions": [],
    "cross_references": [],
    "definition_refs": [],
    "table_context": null,
    "status": "EXTRACTED",
    "status_detail": [],
    "verification": null,
    "history": []
   },
   {
    "candidate_id": "SYNCAND-STALEHASH",
    "document_id": "SYNDOC-ED1",
    "document_hash": "0000000000000000000000000000000000000000000000000000000000000000",
    "fragment_ids": [
     "SYNFRAG-ED1-T1"
    ],
    "section": "T.1",
    "clause": "T.1",
    "page": null,
    "extraction_method": "manual_transcription",
    "interpretation_method": "manual_structured_mapping",
    "ai_assisted": false,
    "proposed_rule": {
     "rule_id": "TEST_ONLY.SYN_STALE",
     "namespace": "TEST_ONLY",
     "regulatory": false,
     "title": "synthetic rule derived from a synthetic fixture document",
     "category": "synthetic",
     "severity": "info",
     "enabled": true,
     "revision": 1,
     "standard": "TEST_STANDARD_001",
     "edition": "1",
     "section": "T.1",
     "jurisdiction_required": false,
     "jurisdiction": {
      "country": null,
      "region": null,
      "authority": null
     },
     "source": {
      "type": "synthetic_test",
      "source_id": "synthetic_test",
      "document_id": null,
      "page": null,
      "clause": null,
      "url": null,
      "verified": false
     },
     "subject_type": "ROUTE",
     "applies_to": {
      "subject_type": "ROUTE",
      "conditions": []
     },
     "inputs": [
      {
       "key": "route.hops",
       "unit": "count",
       "required": true
      }
     ],
     "operator": "count_min",
     "expected": {
      "value": 1
     },
     "exceptions": []
    },
    "exceptions": [],
    "cross_references": [],
    "definition_refs": [],
    "table_context": null,
    "status": "EXTRACTED",
    "status_detail": [],
    "verification": null,
    "history": []
   }
  ],
  "rulepacks": [
   {
    "rulepack_id": "TEST_ONLY.SYNPACK",
    "version": "1",
    "standard": "TEST_STANDARD_001",
    "edition": "1",
    "jurisdiction": {
     "country": null,
     "region": null,
     "authority": null
    },
    "source_documents": [
     "SYNDOC-ED1"
    ],
    "candidate_ids": [],
    "verification": {
     "status": "DRAFT",
     "method": null,
     "verified_at": null,
     "verified_by": null,
     "notes": null
    },
    "coverage_scope": [
     "synthetic.route_ceiling"
    ],
    "completeness": "partial",
    "regulatory": false,
    "synthetic": true,
    "history": []
   },
   {
    "rulepack_id": "TEST_ONLY.SYNPACK_ED2",
    "version": "1",
    "standard": "TEST_STANDARD_001",
    "edition": "2",
    "jurisdiction": {
     "country": null,
     "region": null,
     "authority": null
    },
    "source_documents": [
     "SYNDOC-ED2"
    ],
    "candidate_ids": [],
    "verification": {
     "status": "DRAFT",
     "method": null,
     "verified_at": null,
     "verified_by": null,
     "notes": null
    },
    "coverage_scope": [
     "synthetic.route_ceiling"
    ],
    "completeness": "partial",
    "regulatory": false,
    "synthetic": true,
    "history": []
   }
  ]
 },
 "origin_authorities": [
  "issuing_authority",
  "authorized_distributor",
  "third_party_redistribution",
  "unknown"
 ]
};
/* سجلّ الوثائق الحقيقية — بيانات وصفية وبصمات ومواضع فهرس فقط، بلا نصّ بنود */
const ACS_REAL_SOURCES = {
 "schema": "acs.sources/1",
 "note": "REAL source documents. Metadata, integrity hashes and table-of-contents locators only. No clause text, table, exception or definition from any standard is stored here. Candidates and rule packs remain empty until clause-bearing pages are supplied and verified. Documents whose origin_authority is third_party_redistribution can never reach OFFICIAL_SOURCE_VERIFIED, regardless of how authentic their content looks.",
 "documents": [
  {
   "document_id": "SBC201-CC-2024",
   "source_id": "SBC",
   "title": "The Saudi General Building Code — SBC 201 - CC — Code & Commentaries",
   "standard": "SBC 201",
   "edition": "2024",
   "jurisdiction": {
    "country": "Kingdom of Saudi Arabia",
    "region": null,
    "authority": null
   },
   "document_type": "excerpt_front_matter_and_table_of_contents",
   "official": true,
   "synthetic": false,
   "origin": {
    "type": "uploaded_file",
    "url": null,
    "filename": "SBC201_CC_241224FA.pdf",
    "origin_authority": "issuing_authority"
   },
   "integrity": {
    "sha256": "5b3ec5063f48bc1e2351396f38b4ff2ba4d5c23af80533f203d0e10480acfb06",
    "size_bytes": 3270898
   },
   "verification": {
    "status": "OFFICIAL_SOURCE_VERIFIED",
    "method": "explicit_manual_approval",
    "evidence": {
     "self_identification": "document identifies itself as SBC 201-CC-2024 on the cover and in the running footer of every page",
     "jurisdiction_evidence": "cover carries KINGDOM OF SAUDI ARABIA and the Saudi Building Code emblem",
     "limits": "issuing body's full legal name is not printed in the supplied 10 pages; authority field left null",
     "content_verification_withheld": "supplied file contains no clause text, so CONTENT_VERIFIED is not claimed"
    },
    "verified_at": "2026-08-08",
    "verified_by": "unattributed_operator"
   },
   "relations": [],
   "content_inventory": {
    "pages": 10,
    "pdf_producer": "iLovePDF",
    "pdf_moddate": "D:20241231090308Z",
    "contains_cover": true,
    "contains_table_of_contents": true,
    "toc_roman_pages": "xiii-xxi",
    "contains_normative_clause_text": false,
    "occurrences_of_shall": 0,
    "printed_running_footer": "SBC 201-CC-2024",
    "note": "Supplied file is front matter plus the table of contents only. It carries no clause text, no table, no exception and no definition, so no CandidateRule can be extracted from it."
   },
   "completeness": "excerpt",
   "history": [
    {
     "from": "UNVERIFIED",
     "to": "SOURCE_IDENTIFIED",
     "method": "explicit_manual_approval",
     "at": "2026-08-08",
     "evidence": {
      "cover_page": "SBC / The Saudi General Building Code / SBC 201 - CC / Code & Commentaries / 2024",
      "cover_marks": "Saudi Building Code emblem; KINGDOM OF SAUDI ARABIA (Vision 2030 mark)",
      "running_footer": "SBC 201-CC-2024 on every table-of-contents page",
      "stated_origin": "user states the file came from the official Saudi Building Code website (origin claim, not independently checked offline)"
     }
    },
    {
     "from": "SOURCE_IDENTIFIED",
     "to": "OFFICIAL_SOURCE_VERIFIED",
     "method": "explicit_manual_approval",
     "at": "2026-08-08",
     "evidence": {
      "self_identification": "document identifies itself as SBC 201-CC-2024 on the cover and in the running footer of every page",
      "jurisdiction_evidence": "cover carries KINGDOM OF SAUDI ARABIA and the Saudi Building Code emblem",
      "limits": "issuing body's full legal name is not printed in the supplied 10 pages; authority field left null",
      "content_verification_withheld": "supplied file contains no clause text, so CONTENT_VERIFIED is not claimed"
     }
    }
   ]
  },
  {
   "document_id": "SBC201-CR-2018-THIRDPARTY-COPY",
   "source_id": "SBC",
   "title": "Saudi Building Code-General — SBC 201 - CR — Code Requirements",
   "standard": "SBC 201",
   "edition": "2018",
   "variant": "CR (Code Requirements without commentary)",
   "jurisdiction": {
    "country": "Kingdom of Saudi Arabia",
    "region": null,
    "authority": "Saudi Building Code National Committee (SBCNC)"
   },
   "document_type": "excerpt_front_matter_toc_chapter1_and_partial_chapter2",
   "official": false,
   "synthetic": false,
   "origin": {
    "type": "uploaded_file",
    "url": null,
    "filename": "toaz.infosaudibuildingcodegeneralsbc201crpr_5daf4a8db0e2506dc9b5773eb2844ca4.pdf",
    "origin_authority": "third_party_redistribution",
    "origin_note": "filename and provenance indicate a third-party document-sharing site, not the issuing authority"
   },
   "integrity": {
    "sha256": "e8f3afc4064a5eaa6ee6f4809a4d3357b0dc20bcfcd93afcf4db51ee6843b972",
    "size_bytes": 7469728
   },
   "verification": {
    "status": "SOURCE_IDENTIFIED",
    "method": "explicit_manual_approval",
    "evidence": {
     "self_identification": "cover reads 'Saudi Building Code-General / SBC 201 - CR / Code Requirements / 2018'; running footer 'SBC 201-CR-18' on every page",
     "issuing_authority_evidence": "copyright page names 'The Saudi Building Code National Committee (SBCNC)' as owner of the code's intellectual property",
     "edition_evidence": "COPYRIGHT © 2018 on the copyright page; footer SBC 201-CR-18",
     "provenance_concern": "supplied filename indicates a third-party document-sharing site; this is not a chain of custody from the issuing authority",
     "licensing_concern": "the document's own notice prohibits redistribution without written permission"
    },
    "verified_at": "2026-08-08",
    "verified_by": "unattributed_operator"
   },
   "relations": [],
   "licensing": {
    "copyright_holder": "The Saudi Building Code National Committee (SBCNC)",
    "copyright_year": "2018",
    "notice_summary": "document states all rights reserved and prohibits reproduction, distribution or leasing in any form, including publishing on cloud sites or networks, without prior written permission",
    "redistribution_permitted": false,
    "permission_evidence": null,
    "pdf_permissions": "encrypted (RC4); copy and print flags set to no"
   },
   "content_inventory": {
    "pages": 50,
    "pdf_producer": "iTextSharp 5.5.13",
    "pdf_creationdate": "D:20181101135559+03'00'",
    "printed_running_footer": "SBC 201-CR-18",
    "contains_cover": true,
    "contains_key_list": true,
    "contains_copyright_page": true,
    "contains_committee_pages": true,
    "contains_preface": true,
    "contains_table_of_contents": true,
    "chapters_present": [
     "Chapter 1 (complete)",
     "Chapter 2 Definitions (partial, ends mid-D)"
    ],
    "means_of_egress_body_text_present": false,
    "means_of_egress_toc_start_printed_page": 372,
    "section_1017_toc_printed_page": 403,
    "occurrences_of_shall": 236,
    "note": "Chapter 10 appears in the table of contents only; its clause text is absent. No egress requirement can be extracted from this file."
   },
   "completeness": "excerpt",
   "history": [
    {
     "from": "UNVERIFIED",
     "to": "SOURCE_IDENTIFIED",
     "method": "explicit_manual_approval",
     "at": "2026-08-08",
     "evidence": {
      "self_identification": "cover reads 'Saudi Building Code-General / SBC 201 - CR / Code Requirements / 2018'; running footer 'SBC 201-CR-18' on every page",
      "issuing_authority_evidence": "copyright page names 'The Saudi Building Code National Committee (SBCNC)' as owner of the code's intellectual property",
      "edition_evidence": "COPYRIGHT © 2018 on the copyright page; footer SBC 201-CR-18",
      "provenance_concern": "supplied filename indicates a third-party document-sharing site; this is not a chain of custody from the issuing authority",
      "licensing_concern": "the document's own notice prohibits redistribution without written permission"
     }
    }
   ],
   "base_code": {
    "standard": "IBC",
    "edition": "2015",
    "publisher": "International Code Council (ICC)",
    "relationship": "base code used in developing SBC 201, modified by SBCNC for Saudi conditions",
    "evidence_quote_short": "2015 International Building Code (IBC 2015) ... is the base code in the development of this Code",
    "evidence_location": "SBC 201-CR-18 preface",
    "implication": "IBC text is not evidence for an SBC requirement: the SBCNC states that many changes and modifications were made to the base code, and those modifications are not quantified anywhere in the supplied pages"
   }
  }
 ],
 "fragments": [
  {
   "fragment_id": "SBC201-TOC-CH10",
   "document_id": "SBC201-CC-2024",
   "document_hash": "5b3ec5063f48bc1e2351396f38b4ff2ba4d5c23af80533f203d0e10480acfb06",
   "section": "Chapter 10",
   "clause": null,
   "page": 996,
   "kind": "toc_locator",
   "text_reference": "SBC 201-CC-2024 table of contents, chapter entry",
   "excerpt": "MEANS OF EGRESS",
   "normalized_meaning": "chapter locator for means of egress",
   "location": {
    "start": 0,
    "end": 0
   },
   "extraction_method": "text_layer_extraction",
   "status": "EXTRACTED"
  },
  {
   "fragment_id": "SBC201-TOC-1001",
   "document_id": "SBC201-CC-2024",
   "document_hash": "5b3ec5063f48bc1e2351396f38b4ff2ba4d5c23af80533f203d0e10480acfb06",
   "section": "1001",
   "clause": null,
   "page": 997,
   "kind": "toc_locator",
   "text_reference": "SBC 201-CC-2024 table of contents, entry for SECTION 1001",
   "excerpt": "ADMINISTRATION",
   "normalized_meaning": "section locator only — no requirement text is present in the supplied file",
   "location": {
    "start": 0,
    "end": 0
   },
   "extraction_method": "text_layer_extraction",
   "status": "EXTRACTED"
  },
  {
   "fragment_id": "SBC201-TOC-1002",
   "document_id": "SBC201-CC-2024",
   "document_hash": "5b3ec5063f48bc1e2351396f38b4ff2ba4d5c23af80533f203d0e10480acfb06",
   "section": "1002",
   "clause": null,
   "page": 998,
   "kind": "toc_locator",
   "text_reference": "SBC 201-CC-2024 table of contents, entry for SECTION 1002",
   "excerpt": "MAINTENANCE AND PLANS",
   "normalized_meaning": "section locator only — no requirement text is present in the supplied file",
   "location": {
    "start": 0,
    "end": 0
   },
   "extraction_method": "text_layer_extraction",
   "status": "EXTRACTED"
  },
  {
   "fragment_id": "SBC201-TOC-1003",
   "document_id": "SBC201-CC-2024",
   "document_hash": "5b3ec5063f48bc1e2351396f38b4ff2ba4d5c23af80533f203d0e10480acfb06",
   "section": "1003",
   "clause": null,
   "page": 998,
   "kind": "toc_locator",
   "text_reference": "SBC 201-CC-2024 table of contents, entry for SECTION 1003",
   "excerpt": "GENERAL MEANS OF EGRESS",
   "normalized_meaning": "section locator only — no requirement text is present in the supplied file",
   "location": {
    "start": 0,
    "end": 0
   },
   "extraction_method": "text_layer_extraction",
   "status": "EXTRACTED"
  },
  {
   "fragment_id": "SBC201-TOC-1004",
   "document_id": "SBC201-CC-2024",
   "document_hash": "5b3ec5063f48bc1e2351396f38b4ff2ba4d5c23af80533f203d0e10480acfb06",
   "section": "1004",
   "clause": null,
   "page": 1003,
   "kind": "toc_locator",
   "text_reference": "SBC 201-CC-2024 table of contents, entry for SECTION 1004",
   "excerpt": "OCCUPANT LOAD",
   "normalized_meaning": "section locator only — no requirement text is present in the supplied file",
   "location": {
    "start": 0,
    "end": 0
   },
   "extraction_method": "text_layer_extraction",
   "status": "EXTRACTED"
  },
  {
   "fragment_id": "SBC201-TOC-1005",
   "document_id": "SBC201-CC-2024",
   "document_hash": "5b3ec5063f48bc1e2351396f38b4ff2ba4d5c23af80533f203d0e10480acfb06",
   "section": "1005",
   "clause": null,
   "page": 1008,
   "kind": "toc_locator",
   "text_reference": "SBC 201-CC-2024 table of contents, entry for SECTION 1005",
   "excerpt": "MEANS OF EGRESS SIZING",
   "normalized_meaning": "section locator only — no requirement text is present in the supplied file",
   "location": {
    "start": 0,
    "end": 0
   },
   "extraction_method": "text_layer_extraction",
   "status": "EXTRACTED"
  },
  {
   "fragment_id": "SBC201-TOC-1006",
   "document_id": "SBC201-CC-2024",
   "document_hash": "5b3ec5063f48bc1e2351396f38b4ff2ba4d5c23af80533f203d0e10480acfb06",
   "section": "1006",
   "clause": null,
   "page": 1013,
   "kind": "toc_locator",
   "text_reference": "SBC 201-CC-2024 table of contents, entry for SECTION 1006",
   "excerpt": "NUMBER OF EXITS AND EXIT ACCESS DOORWAYS",
   "normalized_meaning": "section locator only — no requirement text is present in the supplied file",
   "location": {
    "start": 0,
    "end": 0
   },
   "extraction_method": "text_layer_extraction",
   "status": "EXTRACTED"
  },
  {
   "fragment_id": "SBC201-TOC-1007",
   "document_id": "SBC201-CC-2024",
   "document_hash": "5b3ec5063f48bc1e2351396f38b4ff2ba4d5c23af80533f203d0e10480acfb06",
   "section": "1007",
   "clause": null,
   "page": 1022,
   "kind": "toc_locator",
   "text_reference": "SBC 201-CC-2024 table of contents, entry for SECTION 1007",
   "excerpt": "EXIT AND EXIT ACCESS DOORWAY CONFIGURATION",
   "normalized_meaning": "section locator only — no requirement text is present in the supplied file",
   "location": {
    "start": 0,
    "end": 0
   },
   "extraction_method": "text_layer_extraction",
   "status": "EXTRACTED"
  },
  {
   "fragment_id": "SBC201-TOC-1008",
   "document_id": "SBC201-CC-2024",
   "document_hash": "5b3ec5063f48bc1e2351396f38b4ff2ba4d5c23af80533f203d0e10480acfb06",
   "section": "1008",
   "clause": null,
   "page": 1024,
   "kind": "toc_locator",
   "text_reference": "SBC 201-CC-2024 table of contents, entry for SECTION 1008",
   "excerpt": "MEANS OF EGRESS ILLUMINATION",
   "normalized_meaning": "section locator only — no requirement text is present in the supplied file",
   "location": {
    "start": 0,
    "end": 0
   },
   "extraction_method": "text_layer_extraction",
   "status": "EXTRACTED"
  },
  {
   "fragment_id": "SBC201-TOC-1009",
   "document_id": "SBC201-CC-2024",
   "document_hash": "5b3ec5063f48bc1e2351396f38b4ff2ba4d5c23af80533f203d0e10480acfb06",
   "section": "1009",
   "clause": null,
   "page": 1027,
   "kind": "toc_locator",
   "text_reference": "SBC 201-CC-2024 table of contents, entry for SECTION 1009",
   "excerpt": "ACCESSIBLE MEANS OF EGRESS",
   "normalized_meaning": "section locator only — no requirement text is present in the supplied file",
   "location": {
    "start": 0,
    "end": 0
   },
   "extraction_method": "text_layer_extraction",
   "status": "EXTRACTED"
  },
  {
   "fragment_id": "SBC201-TOC-1010",
   "document_id": "SBC201-CC-2024",
   "document_hash": "5b3ec5063f48bc1e2351396f38b4ff2ba4d5c23af80533f203d0e10480acfb06",
   "section": "1010",
   "clause": null,
   "page": 1043,
   "kind": "toc_locator",
   "text_reference": "SBC 201-CC-2024 table of contents, entry for SECTION 1010",
   "excerpt": "DOORS, GATES AND TURNSTILES",
   "normalized_meaning": "section locator only — no requirement text is present in the supplied file",
   "location": {
    "start": 0,
    "end": 0
   },
   "extraction_method": "text_layer_extraction",
   "status": "EXTRACTED"
  },
  {
   "fragment_id": "SBC201-TOC-1011",
   "document_id": "SBC201-CC-2024",
   "document_hash": "5b3ec5063f48bc1e2351396f38b4ff2ba4d5c23af80533f203d0e10480acfb06",
   "section": "1011",
   "clause": null,
   "page": 1076,
   "kind": "toc_locator",
   "text_reference": "SBC 201-CC-2024 table of contents, entry for SECTION 1011",
   "excerpt": "STAIRWAYS",
   "normalized_meaning": "section locator only — no requirement text is present in the supplied file",
   "location": {
    "start": 0,
    "end": 0
   },
   "extraction_method": "text_layer_extraction",
   "status": "EXTRACTED"
  },
  {
   "fragment_id": "SBC201-TOC-1012",
   "document_id": "SBC201-CC-2024",
   "document_hash": "5b3ec5063f48bc1e2351396f38b4ff2ba4d5c23af80533f203d0e10480acfb06",
   "section": "1012",
   "clause": null,
   "page": 1091,
   "kind": "toc_locator",
   "text_reference": "SBC 201-CC-2024 table of contents, entry for SECTION 1012",
   "excerpt": "RAMPS",
   "normalized_meaning": "section locator only — no requirement text is present in the supplied file",
   "location": {
    "start": 0,
    "end": 0
   },
   "extraction_method": "text_layer_extraction",
   "status": "EXTRACTED"
  },
  {
   "fragment_id": "SBC201-TOC-1013",
   "document_id": "SBC201-CC-2024",
   "document_hash": "5b3ec5063f48bc1e2351396f38b4ff2ba4d5c23af80533f203d0e10480acfb06",
   "section": "1013",
   "clause": null,
   "page": 1095,
   "kind": "toc_locator",
   "text_reference": "SBC 201-CC-2024 table of contents, entry for SECTION 1013",
   "excerpt": "EXIT SIGNS",
   "normalized_meaning": "section locator only — no requirement text is present in the supplied file",
   "location": {
    "start": 0,
    "end": 0
   },
   "extraction_method": "text_layer_extraction",
   "status": "EXTRACTED"
  },
  {
   "fragment_id": "SBC201-TOC-1014",
   "document_id": "SBC201-CC-2024",
   "document_hash": "5b3ec5063f48bc1e2351396f38b4ff2ba4d5c23af80533f203d0e10480acfb06",
   "section": "1014",
   "clause": null,
   "page": 1099,
   "kind": "toc_locator",
   "text_reference": "SBC 201-CC-2024 table of contents, entry for SECTION 1014",
   "excerpt": "HANDRAILS",
   "normalized_meaning": "section locator only — no requirement text is present in the supplied file",
   "location": {
    "start": 0,
    "end": 0
   },
   "extraction_method": "text_layer_extraction",
   "status": "EXTRACTED"
  },
  {
   "fragment_id": "SBC201-TOC-1015",
   "document_id": "SBC201-CC-2024",
   "document_hash": "5b3ec5063f48bc1e2351396f38b4ff2ba4d5c23af80533f203d0e10480acfb06",
   "section": "1015",
   "clause": null,
   "page": 1104,
   "kind": "toc_locator",
   "text_reference": "SBC 201-CC-2024 table of contents, entry for SECTION 1015",
   "excerpt": "GUARDS",
   "normalized_meaning": "section locator only — no requirement text is present in the supplied file",
   "location": {
    "start": 0,
    "end": 0
   },
   "extraction_method": "text_layer_extraction",
   "status": "EXTRACTED"
  },
  {
   "fragment_id": "SBC201-TOC-1016",
   "document_id": "SBC201-CC-2024",
   "document_hash": "5b3ec5063f48bc1e2351396f38b4ff2ba4d5c23af80533f203d0e10480acfb06",
   "section": "1016",
   "clause": null,
   "page": 1109,
   "kind": "toc_locator",
   "text_reference": "SBC 201-CC-2024 table of contents, entry for SECTION 1016",
   "excerpt": "EXIT ACCESS",
   "normalized_meaning": "section locator only — no requirement text is present in the supplied file",
   "location": {
    "start": 0,
    "end": 0
   },
   "extraction_method": "text_layer_extraction",
   "status": "EXTRACTED"
  },
  {
   "fragment_id": "SBC201-TOC-1017",
   "document_id": "SBC201-CC-2024",
   "document_hash": "5b3ec5063f48bc1e2351396f38b4ff2ba4d5c23af80533f203d0e10480acfb06",
   "section": "1017",
   "clause": null,
   "page": 1111,
   "kind": "toc_locator",
   "text_reference": "SBC 201-CC-2024 table of contents, entry for SECTION 1017",
   "excerpt": "EXIT ACCESS TRAVEL DISTANCE",
   "normalized_meaning": "section locator only — no requirement text is present in the supplied file",
   "location": {
    "start": 0,
    "end": 0
   },
   "extraction_method": "text_layer_extraction",
   "status": "EXTRACTED"
  },
  {
   "fragment_id": "SBC201-TOC-1018",
   "document_id": "SBC201-CC-2024",
   "document_hash": "5b3ec5063f48bc1e2351396f38b4ff2ba4d5c23af80533f203d0e10480acfb06",
   "section": "1018",
   "clause": null,
   "page": 1115,
   "kind": "toc_locator",
   "text_reference": "SBC 201-CC-2024 table of contents, entry for SECTION 1018",
   "excerpt": "AISLES",
   "normalized_meaning": "section locator only — no requirement text is present in the supplied file",
   "location": {
    "start": 0,
    "end": 0
   },
   "extraction_method": "text_layer_extraction",
   "status": "EXTRACTED"
  },
  {
   "fragment_id": "SBC201-TOC-1019",
   "document_id": "SBC201-CC-2024",
   "document_hash": "5b3ec5063f48bc1e2351396f38b4ff2ba4d5c23af80533f203d0e10480acfb06",
   "section": "1019",
   "clause": null,
   "page": 1116,
   "kind": "toc_locator",
   "text_reference": "SBC 201-CC-2024 table of contents, entry for SECTION 1019",
   "excerpt": "EXIT ACCESS STAIRWAYS AND RAMPS",
   "normalized_meaning": "section locator only — no requirement text is present in the supplied file",
   "location": {
    "start": 0,
    "end": 0
   },
   "extraction_method": "text_layer_extraction",
   "status": "EXTRACTED"
  },
  {
   "fragment_id": "SBC201-TOC-1020",
   "document_id": "SBC201-CC-2024",
   "document_hash": "5b3ec5063f48bc1e2351396f38b4ff2ba4d5c23af80533f203d0e10480acfb06",
   "section": "1020",
   "clause": null,
   "page": 1119,
   "kind": "toc_locator",
   "text_reference": "SBC 201-CC-2024 table of contents, entry for SECTION 1020",
   "excerpt": "CORRIDORS",
   "normalized_meaning": "section locator only — no requirement text is present in the supplied file",
   "location": {
    "start": 0,
    "end": 0
   },
   "extraction_method": "text_layer_extraction",
   "status": "EXTRACTED"
  },
  {
   "fragment_id": "SBC201-TOC-1021",
   "document_id": "SBC201-CC-2024",
   "document_hash": "5b3ec5063f48bc1e2351396f38b4ff2ba4d5c23af80533f203d0e10480acfb06",
   "section": "1021",
   "clause": null,
   "page": 1128,
   "kind": "toc_locator",
   "text_reference": "SBC 201-CC-2024 table of contents, entry for SECTION 1021",
   "excerpt": "EGRESS BALCONIES",
   "normalized_meaning": "section locator only — no requirement text is present in the supplied file",
   "location": {
    "start": 0,
    "end": 0
   },
   "extraction_method": "text_layer_extraction",
   "status": "EXTRACTED"
  },
  {
   "fragment_id": "SBC201-TOC-1022",
   "document_id": "SBC201-CC-2024",
   "document_hash": "5b3ec5063f48bc1e2351396f38b4ff2ba4d5c23af80533f203d0e10480acfb06",
   "section": "1022",
   "clause": null,
   "page": 1129,
   "kind": "toc_locator",
   "text_reference": "SBC 201-CC-2024 table of contents, entry for SECTION 1022",
   "excerpt": "EXITS",
   "normalized_meaning": "section locator only — no requirement text is present in the supplied file",
   "location": {
    "start": 0,
    "end": 0
   },
   "extraction_method": "text_layer_extraction",
   "status": "EXTRACTED"
  },
  {
   "fragment_id": "SBC201-TOC-1023",
   "document_id": "SBC201-CC-2024",
   "document_hash": "5b3ec5063f48bc1e2351396f38b4ff2ba4d5c23af80533f203d0e10480acfb06",
   "section": "1023",
   "clause": null,
   "page": 1130,
   "kind": "toc_locator",
   "text_reference": "SBC 201-CC-2024 table of contents, entry for SECTION 1023",
   "excerpt": "INTERIOR EXIT STAIRWAYS AND RAMPS",
   "normalized_meaning": "section locator only — no requirement text is present in the supplied file",
   "location": {
    "start": 0,
    "end": 0
   },
   "extraction_method": "text_layer_extraction",
   "status": "EXTRACTED"
  },
  {
   "fragment_id": "SBC201-TOC-1024",
   "document_id": "SBC201-CC-2024",
   "document_hash": "5b3ec5063f48bc1e2351396f38b4ff2ba4d5c23af80533f203d0e10480acfb06",
   "section": "1024",
   "clause": null,
   "page": 1139,
   "kind": "toc_locator",
   "text_reference": "SBC 201-CC-2024 table of contents, entry for SECTION 1024",
   "excerpt": "EXIT PASSAGEWAYS",
   "normalized_meaning": "section locator only — no requirement text is present in the supplied file",
   "location": {
    "start": 0,
    "end": 0
   },
   "extraction_method": "text_layer_extraction",
   "status": "EXTRACTED"
  },
  {
   "fragment_id": "SBC201-TOC-1025",
   "document_id": "SBC201-CC-2024",
   "document_hash": "5b3ec5063f48bc1e2351396f38b4ff2ba4d5c23af80533f203d0e10480acfb06",
   "section": "1025",
   "clause": null,
   "page": 1143,
   "kind": "toc_locator",
   "text_reference": "SBC 201-CC-2024 table of contents, entry for SECTION 1025",
   "excerpt": "LUMINOUS EGRESS PATH MARKINGS",
   "normalized_meaning": "section locator only — no requirement text is present in the supplied file",
   "location": {
    "start": 0,
    "end": 0
   },
   "extraction_method": "text_layer_extraction",
   "status": "EXTRACTED"
  },
  {
   "fragment_id": "SBC201-TOC-1026",
   "document_id": "SBC201-CC-2024",
   "document_hash": "5b3ec5063f48bc1e2351396f38b4ff2ba4d5c23af80533f203d0e10480acfb06",
   "section": "1026",
   "clause": null,
   "page": 1147,
   "kind": "toc_locator",
   "text_reference": "SBC 201-CC-2024 table of contents, entry for SECTION 1026",
   "excerpt": "HORIZONTAL EXITS",
   "normalized_meaning": "section locator only — no requirement text is present in the supplied file",
   "location": {
    "start": 0,
    "end": 0
   },
   "extraction_method": "text_layer_extraction",
   "status": "EXTRACTED"
  },
  {
   "fragment_id": "SBC201-TOC-1027",
   "document_id": "SBC201-CC-2024",
   "document_hash": "5b3ec5063f48bc1e2351396f38b4ff2ba4d5c23af80533f203d0e10480acfb06",
   "section": "1027",
   "clause": null,
   "page": 1150,
   "kind": "toc_locator",
   "text_reference": "SBC 201-CC-2024 table of contents, entry for SECTION 1027",
   "excerpt": "EXTERIOR EXIT STAIRWAYS AND RAMPS",
   "normalized_meaning": "section locator only — no requirement text is present in the supplied file",
   "location": {
    "start": 0,
    "end": 0
   },
   "extraction_method": "text_layer_extraction",
   "status": "EXTRACTED"
  },
  {
   "fragment_id": "SBC201-TOC-1028",
   "document_id": "SBC201-CC-2024",
   "document_hash": "5b3ec5063f48bc1e2351396f38b4ff2ba4d5c23af80533f203d0e10480acfb06",
   "section": "1028",
   "clause": null,
   "page": 1153,
   "kind": "toc_locator",
   "text_reference": "SBC 201-CC-2024 table of contents, entry for SECTION 1028",
   "excerpt": "EXIT DISCHARGE",
   "normalized_meaning": "section locator only — no requirement text is present in the supplied file",
   "location": {
    "start": 0,
    "end": 0
   },
   "extraction_method": "text_layer_extraction",
   "status": "EXTRACTED"
  },
  {
   "fragment_id": "SBC201-TOC-1029",
   "document_id": "SBC201-CC-2024",
   "document_hash": "5b3ec5063f48bc1e2351396f38b4ff2ba4d5c23af80533f203d0e10480acfb06",
   "section": "1029",
   "clause": null,
   "page": 1156,
   "kind": "toc_locator",
   "text_reference": "SBC 201-CC-2024 table of contents, entry for SECTION 1029",
   "excerpt": "EGRESS COURTS",
   "normalized_meaning": "section locator only — no requirement text is present in the supplied file",
   "location": {
    "start": 0,
    "end": 0
   },
   "extraction_method": "text_layer_extraction",
   "status": "EXTRACTED"
  },
  {
   "fragment_id": "SBC201-TOC-1030",
   "document_id": "SBC201-CC-2024",
   "document_hash": "5b3ec5063f48bc1e2351396f38b4ff2ba4d5c23af80533f203d0e10480acfb06",
   "section": "1030",
   "clause": null,
   "page": 1157,
   "kind": "toc_locator",
   "text_reference": "SBC 201-CC-2024 table of contents, entry for SECTION 1030",
   "excerpt": "ASSEMBLY",
   "normalized_meaning": "section locator only — no requirement text is present in the supplied file",
   "location": {
    "start": 0,
    "end": 0
   },
   "extraction_method": "text_layer_extraction",
   "status": "EXTRACTED"
  },
  {
   "fragment_id": "SBC201-TOC-1031",
   "document_id": "SBC201-CC-2024",
   "document_hash": "5b3ec5063f48bc1e2351396f38b4ff2ba4d5c23af80533f203d0e10480acfb06",
   "section": "1031",
   "clause": null,
   "page": 1179,
   "kind": "toc_locator",
   "text_reference": "SBC 201-CC-2024 table of contents, entry for SECTION 1031",
   "excerpt": "EMERGENCY ESCAPE AND RESCUE",
   "normalized_meaning": "section locator only — no requirement text is present in the supplied file",
   "location": {
    "start": 0,
    "end": 0
   },
   "extraction_method": "text_layer_extraction",
   "status": "EXTRACTED"
  }
 ],
 "candidates": [],
 "rulepacks": [],
 "chapter_bounds": {
  "means_of_egress_starts_page": 996,
  "next_chapter_accessibility_starts_page": 1287
 }
};
function ingestRealStore(){ return {documents:JSON.parse(JSON.stringify(ACS_REAL_SOURCES.documents||[])),
  fragments:JSON.parse(JSON.stringify(ACS_REAL_SOURCES.fragments||[])),
  candidates:JSON.parse(JSON.stringify(ACS_REAL_SOURCES.candidates||[])),
  rulepacks:JSON.parse(JSON.stringify(ACS_REAL_SOURCES.rulepacks||[]))}; }
const INGEST_SCHEMA = ACS_INGEST_FIXTURES.schema;
const INGEST_PIPELINE_VERSION = ACS_INGEST_FIXTURES.pipeline_version;
const ING_DOC_STATES = ACS_INGEST_FIXTURES.document_states;
const ING_DOC_TRANSITIONS = ACS_INGEST_FIXTURES.document_transitions;
const ING_FRAGMENT_STATES = ACS_INGEST_FIXTURES.fragment_states;
const ING_FRAGMENT_KINDS = ACS_INGEST_FIXTURES.fragment_kinds;
const ING_CANDIDATE_STATES = ACS_INGEST_FIXTURES.candidate_states;
const ING_CANDIDATE_TRANSITIONS = ACS_INGEST_FIXTURES.candidate_transitions;
const ING_PACK_STATES = ACS_INGEST_FIXTURES.pack_states;
const ING_PACK_TRANSITIONS = ACS_INGEST_FIXTURES.pack_transitions;
const ING_PIPELINE_STAGES = ACS_INGEST_FIXTURES.pipeline_stages;
const ING_ORIGIN_TYPES = ACS_INGEST_FIXTURES.origin_types;
const ING_EXTRACTION_METHODS = ACS_INGEST_FIXTURES.extraction_methods;
const ING_VERIFICATION_METHODS = ACS_INGEST_FIXTURES.verification_methods;
const ING_RELATION_TYPES = ACS_INGEST_FIXTURES.relation_types;
const ING_EXCEPTION_RESOLUTIONS = ACS_INGEST_FIXTURES.exception_resolutions;
const ING_ORIGIN_AUTHORITIES = ACS_INGEST_FIXTURES.origin_authorities;
/* سلسلة الحيازة المقبولة لوسم وثيقة بأنها رسمية */
const ING_OFFICIAL_CHAIN = ['issuing_authority','authorized_distributor'];
const EXCERPT_MAX_CHARS = ACS_INGEST_FIXTURES.excerpt_max_chars;
const ING_FORBIDDEN = ['javascript:','data:text/html','<script','eval(','exec(',
                       'new function(','system(','subprocess.','os.popen'];
const ING_FORBIDDEN_KEYS = ['script','code','eval','exec','function','__proto__'];
/* ---- SHA-256 (تطبيق نقي، بلا اعتماد على أي واجهة خارجية) ---- */
const _SHA_K=[0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2];
function _rotr32(x,n){ return ((x>>>n)|(x<<(32-n)))>>>0; }
function _utf8Bytes(str){ const b=[];
  for(let i=0;i<str.length;i++){ const c=str.charCodeAt(i);
    if(c<0x80) b.push(c);
    else if(c<0x800) b.push(0xC0|(c>>6),0x80|(c&63));
    else if(c>=0xD800&&c<=0xDBFF){ const c2=str.charCodeAt(++i);
      const cp=0x10000+((c-0xD800)<<10)+(c2-0xDC00);
      b.push(0xF0|(cp>>18),0x80|((cp>>12)&63),0x80|((cp>>6)&63),0x80|(cp&63)); }
    else b.push(0xE0|(c>>12),0x80|((c>>6)&63),0x80|(c&63)); }
  return b; }
function sha256Hex(text){
  if(text===null||text===undefined) return null;
  const m=_utf8Bytes(String(text)), ml=m.length*8;
  m.push(0x80); while(m.length%64!==56) m.push(0);
  const hi=Math.floor(ml/4294967296), lo=ml>>>0;
  m.push((hi>>>24)&255,(hi>>>16)&255,(hi>>>8)&255,hi&255,
         (lo>>>24)&255,(lo>>>16)&255,(lo>>>8)&255,lo&255);
  let H=[0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19];
  const w=new Array(64);
  for(let i=0;i<m.length;i+=64){
    for(let t=0;t<16;t++) w[t]=((m[i+t*4]<<24)|(m[i+t*4+1]<<16)|(m[i+t*4+2]<<8)|m[i+t*4+3])>>>0;
    for(let t=16;t<64;t++){
      const s0=(_rotr32(w[t-15],7)^_rotr32(w[t-15],18)^(w[t-15]>>>3))>>>0;
      const s1=(_rotr32(w[t-2],17)^_rotr32(w[t-2],19)^(w[t-2]>>>10))>>>0;
      w[t]=(((w[t-16]+s0)>>>0)+((w[t-7]+s1)>>>0))>>>0; }
    let a=H[0],b=H[1],c=H[2],d=H[3],e=H[4],f=H[5],g=H[6],h=H[7];
    for(let t=0;t<64;t++){
      const S1=(_rotr32(e,6)^_rotr32(e,11)^_rotr32(e,25))>>>0;
      const ch=((e&f)^((~e)&g))>>>0;
      const t1=(((h+S1)>>>0)+((ch+_SHA_K[t])>>>0)+w[t])>>>0;
      const S0=(_rotr32(a,2)^_rotr32(a,13)^_rotr32(a,22))>>>0;
      const maj=((a&b)^(a&c)^(b&c))>>>0;
      const t2=(S0+maj)>>>0;
      h=g;g=f;f=e;e=(d+t1)>>>0;d=c;c=b;b=a;a=(t1+t2)>>>0; }
    H=[(H[0]+a)>>>0,(H[1]+b)>>>0,(H[2]+c)>>>0,(H[3]+d)>>>0,
       (H[4]+e)>>>0,(H[5]+f)>>>0,(H[6]+g)>>>0,(H[7]+h)>>>0]; }
  return H.map(x=>('0000000'+x.toString(16)).slice(-8)).join(''); }
/* يعيد صياغة أقصر تمثيل عشري إلى صورة علمية موحّدة — تنسيق الأرقام يختلف بين
   اللغتين (5e-07 مقابل 5e-7، و1e-05 مقابل 0.00001) فنوحّده بدل الاتّكال عليه */
function _ingSci(s){
  s=String(s).trim();
  const neg=s.charAt(0)==='-'; if(neg) s=s.slice(1);
  const low=s.toLowerCase();
  let mant, exp;
  const ei=low.indexOf('e');
  if(ei>=0){ mant=low.slice(0,ei); exp=parseInt(low.slice(ei+1),10); }
  else { mant=low; exp=0; }
  const di=mant.indexOf('.');
  const ip=(di>=0)?mant.slice(0,di):mant, fp=(di>=0)?mant.slice(di+1):'';
  const alld=ip+fp;
  let digits=alld.replace(/^0+/,'');
  if(digits==='') return '0';
  const leadZeros=alld.length-digits.length;
  const e10=exp+(ip.length-1)-leadZeros;
  digits=digits.replace(/0+$/,''); if(digits==='') digits='0';
  const out=digits.charAt(0)+(digits.length>1?('.'+digits.slice(1)):'')+'e'+String(e10);
  return (neg?'-':'')+out; }
/* رمز رقمي موحّد عبر اللغتين. البادئة تمنع تصادم رقم مع نصّ يشبهه */
function _ingNumToken(v){
  if(!isFinite(v)) throw new Error('non-finite number cannot be canonicalised');
  if(Number.isInteger(v)&&Math.abs(v)<1e16) return '#n:'+String(Math.trunc(v));
  return '#n:'+_ingSci(String(v)); }
function _ingCanon(v){ if(typeof v==='boolean') return v;
  if(typeof v==='number') return _ingNumToken(v);
  if(Array.isArray(v)) return v.map(_ingCanon);
  if(v&&typeof v==='object'){ const o={}; Object.keys(v).sort().forEach(k=>{o[k]=_ingCanon(v[k]);}); return o; }
  return v; }
function ingestCanonicalJson(o){ return JSON.stringify(_ingCanon(o)); }
const ING_MEANING_FIELDS=['rule_id','standard','edition','section','applies_to','inputs',
  'operator','expected','exceptions','revision','subject_type','jurisdiction','jurisdiction_required'];
/* بصمة المعنى التنظيمي — أي تغيير في المعنى يوجب مراجعة جديدة لا تعديلاً صامتاً */
function ruleDefinitionHash(rule){
  if(!rule||typeof rule!=='object'||Array.isArray(rule)) return null;
  const o={}; ING_MEANING_FIELDS.forEach(k=>{o[k]=(rule[k]===undefined?null:rule[k]);});
  return sha256Hex(ingestCanonicalJson(o)); }
function _isHex64(h){ return typeof h==='string'&&h.length===64&&/^[0-9a-f]{64}$/.test(h.toLowerCase()); }
function _ingExecutable(o,depth){ depth=depth||0; if(depth>12) return true;
  if(Array.isArray(o)){ for(const v of o) if(_ingExecutable(v,depth+1)) return true; return false; }
  if(o&&typeof o==='object'){ for(const k of Object.keys(o)){
      if(ING_FORBIDDEN_KEYS.indexOf(String(k).toLowerCase())>=0) return true;
      if(_ingExecutable(o[k],depth+1)) return true; } return false; }
  if(typeof o==='string'){ const low=o.toLowerCase();
    for(const bad of ING_FORBIDDEN) if(low.indexOf(bad)>=0) return true; }
  return false; }
/* ---------------------------------------------------------- المخزن ---- */
function ingestEmptyStore(){ return {documents:[],fragments:[],candidates:[],rulepacks:[]}; }
function ingestFixtureStore(){ return JSON.parse(JSON.stringify(ACS_INGEST_FIXTURES.store)); }
function _ingBy(items,key,val){ for(const it of (items||[])) if(it[key]===val) return it; return null; }
function ingDocument(store,id){ return _ingBy(store.documents,'document_id',id); }
function ingFragment(store,id){ return _ingBy(store.fragments,'fragment_id',id); }
function ingCandidate(store,id){ return _ingBy(store.candidates,'candidate_id',id); }
function ingRulePack(store,id,version){ for(const p of (store.rulepacks||[]))
  if(p.rulepack_id===id&&(version===undefined||version===null||p.version===version)) return p; return null; }
/* ------------------------------------------------------ وثيقة المصدر ---- */
function validateDocument(doc){
  const issues=[];
  if(!doc||typeof doc!=='object'||Array.isArray(doc)) return ['document is not an object'];
  if(_ingExecutable(doc)) issues.push('document metadata contains executable/script-like content');
  ['document_id','source_id','title','standard','document_type'].forEach(k=>{
    if(!doc[k]) issues.push('document missing field: '+k); });
  const st=(doc.verification||{}).status;
  if(ING_DOC_STATES.indexOf(st)<0) issues.push('unknown document verification status: '+st);
  const origin=doc.origin||{};
  if(ING_ORIGIN_TYPES.indexOf(origin.type)<0) issues.push('unknown origin type: '+origin.type);
  if(origin.url&&String(origin.url).indexOf('https://')!==0) issues.push('official source url must be https');
  if(origin.type==='official_url'&&!origin.url) issues.push('origin official_url requires a url');
  if(origin.type==='uploaded_file'&&!origin.filename) issues.push('origin uploaded_file requires a filename');
  const integ=doc.integrity||{};
  if(!_isHex64(integ.sha256)) issues.push('document integrity.sha256 must be a 64-hex digest');
  if(integ.size_bytes!==null&&integ.size_bytes!==undefined&&!Number.isInteger(integ.size_bytes))
    issues.push('integrity.size_bytes must be an integer or null');
  if(doc.official===true&&doc.synthetic===true) issues.push('a document cannot be both official and synthetic');
  const oa=origin.origin_authority;
  if(oa!==null&&oa!==undefined&&ING_ORIGIN_AUTHORITIES.indexOf(oa)<0)
    issues.push('unknown origin_authority: '+oa);
  // نسخة معاد نشرها من طرف ثالث ليست مصدراً رسمياً مهما بدا محتواها صحيحاً
  if(doc.official===true&&ING_OFFICIAL_CHAIN.indexOf(oa)<0)
    issues.push('a document may not be marked official unless its origin_authority is '+
                'issuing_authority or authorized_distributor (got: '+oa+')');
  if(st==='OFFICIAL_SOURCE_VERIFIED'||st==='CONTENT_VERIFIED'){
    const v=doc.verification||{};
    if(ING_VERIFICATION_METHODS.indexOf(v.method)<0) issues.push('verified document requires a known verification method');
    if(!v.evidence) issues.push('verified document requires recorded verification evidence'); }
  (doc.relations||[]).forEach(rel=>{
    if(ING_RELATION_TYPES.indexOf(rel.type)<0) issues.push('unknown document relation: '+rel.type);
    if(!rel.document_id) issues.push('document relation without a target document_id'); });
  return issues; }
function canTransitionDocument(frm,to){ return (ING_DOC_TRANSITIONS[frm]||[]).indexOf(to)>=0; }
/* انتقال حالة صريح فقط. الانتقال غير المسموح يُرفض ولا يُنفَّذ */
function transitionDocument(doc,to,method,evidence,at,by){
  if(!doc.verification) doc.verification={status:'UNVERIFIED'};
  const v=doc.verification, frm=v.status;
  if(ING_DOC_STATES.indexOf(to)<0) return [false,'UNKNOWN_TARGET_STATE'];
  if(!canTransitionDocument(frm,to)) return [false,'INVALID_TRANSITION: '+frm+' -> '+to];
  if(to==='SOURCE_IDENTIFIED'||to==='OFFICIAL_SOURCE_VERIFIED'||to==='CONTENT_VERIFIED'){
    if(ING_VERIFICATION_METHODS.indexOf(method)<0) return [false,'VERIFICATION_METHOD_REQUIRED'];
    if(!evidence) return [false,'VERIFICATION_EVIDENCE_REQUIRED'];
    // الرسمية لا تُستنتج من عنوان يبدو رسمياً
    if(to==='OFFICIAL_SOURCE_VERIFIED'){
      if(doc.official!==true) return [false,'DOCUMENT_NOT_MARKED_OFFICIAL_BY_EVIDENCE'];
      if(ING_OFFICIAL_CHAIN.indexOf((doc.origin||{}).origin_authority)<0)
        return [false,'ORIGIN_NOT_IN_OFFICIAL_CHAIN']; } }
  v.status=to; v.method=(method===undefined?null:method); v.evidence=(evidence===undefined?null:evidence);
  v.verified_at=(at===undefined?null:at); v.verified_by=(by===undefined?null:by);
  if(!doc.history) doc.history=[];
  // الدليل يُحفظ مع كل انتقال أيضاً، فلا يضيع دليل خطوة سابقة عند تحديث الحالة
  doc.history.push({from:frm,to:to,method:(method===undefined?null:method),
    at:(at===undefined?null:at),evidence:(evidence===undefined?null:evidence)});
  return [true,null]; }
function verifyDocumentBytes(doc,content){
  const h=sha256Hex(content);
  return [h===((doc.integrity||{}).sha256), h]; }
function documentUsable(doc){ return ((doc.verification||{}).status)==='CONTENT_VERIFIED'; }
/* ---------------------------------------------------------- الشذرات ---- */
function validateFragment(frag,store){
  const issues=[];
  if(!frag||typeof frag!=='object'||Array.isArray(frag)) return ['fragment is not an object'];
  if(_ingExecutable(frag)) issues.push('fragment contains executable/script-like content');
  ['fragment_id','document_id','extraction_method'].forEach(k=>{
    if(!frag[k]) issues.push('fragment missing field: '+k); });
  if(ING_FRAGMENT_STATES.indexOf(frag.status)<0) issues.push('unknown fragment status: '+frag.status);
  if(ING_FRAGMENT_KINDS.indexOf(frag.kind)<0) issues.push('unknown fragment kind: '+frag.kind);
  if(ING_EXTRACTION_METHODS.indexOf(frag.extraction_method)<0)
    issues.push('unknown extraction method: '+frag.extraction_method);
  const doc=ingDocument(store,frag.document_id);
  if(doc===null) issues.push('fragment references a missing document: '+frag.document_id);
  else if(frag.document_hash&&frag.document_hash!==((doc.integrity||{}).sha256))
    issues.push('fragment document_hash does not match the stored document');
  const ex=frag.excerpt;
  if(ex!==null&&ex!==undefined){
    if(typeof ex!=='string') issues.push('excerpt must be text');
    else if(ex.length>EXCERPT_MAX_CHARS)
      issues.push('excerpt exceeds the permitted '+EXCERPT_MAX_CHARS+
                  '-character limit (copyright-safe storage)'); }
  if(!frag.text_reference&&(ex===null||ex===undefined))
    issues.push('fragment needs at least a text_reference pointer');
  const loc=frag.location||{};
  if(loc.start!==null&&loc.start!==undefined&&loc.end!==null&&loc.end!==undefined){
    if(!Number.isInteger(loc.start)||!Number.isInteger(loc.end)||loc.end<loc.start)
      issues.push('invalid fragment location range'); }
  return issues; }
function fragmentsOf(store,documentId){ return (store.fragments||[]).filter(f=>f.document_id===documentId); }
/* -------------------------------------------------------- المرشّحون ---- */
function _ingUnresolvedRefs(cand,store){ const out=[];
  (cand.cross_references||[]).forEach(ref=>{
    if(ref.resolution==='resolved'&&ref.fragment_id){
      if(ingFragment(store,ref.fragment_id)===null)
        out.push({ref:(ref.label===undefined?null:ref.label),reason:'BROKEN_SOURCE_REFERENCE'});
      return; }
    out.push({ref:(ref.label===undefined?null:ref.label),reason:'UNRESOLVED_CROSS_REFERENCE'}); });
  return out; }
function _ingOpenExceptions(cand){ const out=[];
  (cand.exceptions||[]).forEach(ex=>{
    if(ex.resolution!=='resolved'&&ex.resolution!=='declared_unsupported')
      out.push({condition:(ex.condition===undefined?null:ex.condition),reason:'EXCEPTION_NOT_REVIEWED'}); });
  return out; }
function _ingMissingDefs(cand,store){ const out=[];
  (cand.definition_refs||[]).forEach(d=>{
    if(!d.fragment_id||ingFragment(store,d.fragment_id)===null)
      out.push({term:(d.term===undefined?null:d.term),reason:'DEFINITION_FRAGMENT_MISSING'}); });
  return out; }
/* فحص بنيوي/دليلي للمرشّح — لا يجعله متحقَّقاً بحال */
function validateCandidate(cand,store){
  const issues=[];
  if(!cand||typeof cand!=='object'||Array.isArray(cand)) return ['candidate is not an object'];
  if(_ingExecutable(cand)) issues.push('candidate contains executable/script-like content');
  ['candidate_id','document_id','extraction_method','proposed_rule'].forEach(k=>{
    if(!cand[k]) issues.push('candidate missing field: '+k); });
  if(ING_CANDIDATE_STATES.indexOf(cand.status)<0) issues.push('unknown candidate status: '+cand.status);
  if(ING_EXTRACTION_METHODS.indexOf(cand.extraction_method)<0)
    issues.push('unknown extraction method: '+cand.extraction_method);
  if(cand.ai_assisted!==true&&cand.ai_assisted!==false)
    issues.push('candidate must state ai_assisted explicitly');
  const doc=ingDocument(store,cand.document_id);
  if(doc===null) issues.push('candidate references a missing document: '+cand.document_id);
  else { const rec=(doc.integrity||{}).sha256;
    if(cand.document_hash!==rec)
      issues.push('SOURCE_HASH_MISMATCH: candidate pinned '+cand.document_hash+', document is '+rec); }
  (cand.fragment_ids||[]).forEach(fid=>{
    if(ingFragment(store,fid)===null) issues.push('BROKEN_SOURCE_REFERENCE: '+fid); });
  // لا يُستشهد بوثيقة معيار لتبرير قاعدة معيار آخر أو إصدار آخر
  const pr0=cand.proposed_rule||{};
  if(doc!==null){
    if(pr0.standard&&doc.standard&&pr0.standard!==doc.standard)
      issues.push('STANDARD_MISMATCH: rule cites '+pr0.standard+' but the source document is '+doc.standard);
    if(pr0.edition&&doc.edition&&String(pr0.edition)!==String(doc.edition))
      issues.push('EDITION_MISMATCH: rule cites edition '+pr0.edition+
                  ' but the source document is edition '+doc.edition); }
  if(!(cand.fragment_ids||[]).length) issues.push('candidate cites no source fragment');
  if(cand.status==='VERIFIED'&&!cand.verification)
    issues.push('candidate claims VERIFIED without a verification record');
  const pr=cand.proposed_rule||{};
  validateRule(pr).forEach(i=>issues.push('proposed_rule: '+i));
  if(pr.regulatory===true&&(doc===null||!documentUsable(doc)))
    issues.push('regulatory candidate references a document that is not CONTENT_VERIFIED');
  if(pr.regulatory===true&&doc!==null&&doc.official!==true)
    issues.push('regulatory candidate requires an official source document');
  const tbl=cand.table_context;
  if(tbl!==null&&tbl!==undefined){
    if(typeof tbl!=='object'||!tbl.table_id) issues.push('table_context requires a table_id');
    else if((tbl.row===null||tbl.row===undefined)&&(tbl.column===null||tbl.column===undefined)&&
            !(tbl.conditions||[]).length)
      issues.push('table-derived candidate must keep its row/column/condition context'); }
  return issues; }
/* يحسب الحالة المستحقّة من الأدلّة — لا يرفع الحالة إلى VERIFIED أبداً */
function assessCandidate(cand,store){
  const blocking=validateCandidate(cand,store);
  const refs=_ingUnresolvedRefs(cand,store);
  const exc=_ingOpenExceptions(cand);
  const defs=_ingMissingDefs(cand,store);
  if(blocking.some(i=>i.indexOf('BROKEN_SOURCE_REFERENCE')>=0||i.indexOf('SOURCE_HASH_MISMATCH')>=0))
    return ['REJECTED',blocking];
  if(blocking.length) return ['NEEDS_INTERPRETATION',blocking];
  if(refs.length) return ['NEEDS_CROSS_REFERENCE',refs];
  if(exc.length) return ['NEEDS_EXCEPTION_REVIEW',exc];
  if(defs.length) return ['NEEDS_INTERPRETATION',defs];
  if(!cand.interpretation_method) return ['NEEDS_INTERPRETATION',[{reason:'INTERPRETATION_METHOD_MISSING'}]];
  return ['READY_FOR_VERIFICATION',[]]; }
function canTransitionCandidate(frm,to){ return (ING_CANDIDATE_TRANSITIONS[frm]||[]).indexOf(to)>=0; }
function advanceCandidate(cand,store){
  const a=assessCandidate(cand,store), state=a[0], detail=a[1], frm=cand.status;
  if(state===frm) return [frm,detail];
  if(!canTransitionCandidate(frm,state)) return [frm,[{reason:'INVALID_TRANSITION: '+frm+' -> '+state}]];
  cand.status=state; cand.status_detail=detail;
  if(!cand.history) cand.history=[];
  cand.history.push({from:frm,to:state});
  return [state,detail]; }
/* بوّابة التحقّق الصريحة الوحيدة. الذكاء الاصطناعي لا يستطيع استدعاءها نيابةً عن إنسان */
function verifyCandidate(cand,store,verifier,at,method,notes){
  method=(method===undefined||method===null)?'explicit_manual_approval':method;
  if(ING_VERIFICATION_METHODS.indexOf(method)<0) return [false,'UNKNOWN_VERIFICATION_METHOD',null];
  if(method==='ai_suggestion') return [false,'AI_MAY_NOT_VERIFY',null];
  const a=assessCandidate(cand,store), state=a[0], detail=a[1];
  if(state!=='READY_FOR_VERIFICATION') return [false,state,detail];
  const doc=ingDocument(store,cand.document_id);
  if(doc===null) return [false,'REJECTED',[{reason:'BROKEN_SOURCE_REFERENCE'}]];
  if(!documentUsable(doc)) return [false,'SOURCE_NOT_VERIFIED',
    [{reason:'DOCUMENT_STATUS_'+((doc.verification||{}).status)}]];
  if(cand.document_hash!==((doc.integrity||{}).sha256)) return [false,'SOURCE_HASH_MISMATCH',null];
  const pr=cand.proposed_rule||{};
  if(pr.regulatory===true&&doc.official!==true) return [false,'SOURCE_NOT_OFFICIAL',null];
  // الأنبوب لا يُختصر: يُنقل المرشّح أولاً إلى الحالة التي تستحقّها أدلّته ثم يُوثَّق
  if(cand.status!=='READY_FOR_VERIFICATION'){
    const moved=advanceCandidate(cand,store)[0];
    if(moved!=='READY_FOR_VERIFICATION')
      return [false,'INVALID_TRANSITION: '+cand.status+' -> READY_FOR_VERIFICATION',null]; }
  if(!canTransitionCandidate(cand.status,'VERIFIED'))
    return [false,'INVALID_TRANSITION: '+cand.status+' -> VERIFIED',null];
  const rec={verifier:(verifier===undefined?null:verifier),method:method,
    verified_at:(at===undefined?null:at),document_id:doc.document_id,
    document_hash:(doc.integrity||{}).sha256,rule_definition_hash:ruleDefinitionHash(pr),
    fragment_ids:(cand.fragment_ids||[]).slice(),ai_assisted:cand.ai_assisted===true,
    notes:(notes===undefined?null:notes)};
  const frm=cand.status;
  cand.status='VERIFIED'; cand.verification=rec;
  if(!cand.history) cand.history=[];
  cand.history.push({from:frm,to:'VERIFIED',method:method,at:(at===undefined?null:at)});
  return [true,null,rec]; }
/* التحقّق مثبَّت على بايتات الوثيقة: تغيّرها يُبطل التحقّق ولا يُحدَّث بصمت */
function verificationStillValid(cand,store){
  const rec=cand.verification;
  if(!rec) return [false,'NOT_VERIFIED'];
  const doc=ingDocument(store,rec.document_id);
  if(doc===null) return [false,'BROKEN_SOURCE_REFERENCE'];
  if(((doc.integrity||{}).sha256)!==rec.document_hash) return [false,'SOURCE_HASH_MISMATCH'];
  const st=(doc.verification||{}).status;
  if(st==='SUPERSEDED'||st==='REVOKED'||st==='INVALID') return [false,'SOURCE_'+st];
  if(ruleDefinitionHash(cand.proposed_rule)!==rec.rule_definition_hash) return [false,'RULE_DEFINITION_CHANGED'];
  for(const fid of (rec.fragment_ids||[])) if(ingFragment(store,fid)===null) return [false,'BROKEN_SOURCE_REFERENCE'];
  return [true,null]; }
/* ------------------------------------------------------ حِزَم القواعد ---- */
function validatePack(pack,store){
  const issues=[];
  if(!pack||typeof pack!=='object'||Array.isArray(pack)) return ['rulepack is not an object'];
  if(_ingExecutable(pack)) issues.push('rulepack contains executable/script-like content');
  ['rulepack_id','version','standard','edition'].forEach(k=>{
    if(!pack[k]) issues.push('rulepack missing field: '+k); });
  const st=(pack.verification||{}).status;
  if(ING_PACK_STATES.indexOf(st)<0) issues.push('unknown rulepack status: '+st);
  if(RULE_COMPLETENESS.indexOf(pack.completeness)<0) issues.push('unknown completeness: '+pack.completeness);
  const scope=pack.coverage_scope;
  if(!Array.isArray(scope)||!scope.length) issues.push('rulepack must declare a coverage_scope list');
  if(pack.completeness==='complete_for_declared_scope'&&(!Array.isArray(scope)||!scope.length))
    issues.push('complete_for_declared_scope requires a declared coverage_scope');
  const seen={};
  (pack.candidate_ids||[]).forEach(cid=>{
    const c=ingCandidate(store,cid);
    if(c===null){ issues.push('rulepack references a missing candidate: '+cid); return; }
    if(c.status!=='VERIFIED'){
      issues.push('rulepack contains a candidate that is not VERIFIED: '+cid+' ('+c.status+')'); return; }
    const v=verificationStillValid(c,store);
    if(!v[0]){ issues.push('rulepack candidate verification is no longer valid: '+cid+' ('+v[1]+')'); return; }
    const uid=ruleUid(c.proposed_rule||{});
    if(seen[uid]) issues.push('duplicate rule identity inside rulepack: '+uid);
    seen[uid]=1; });
  (pack.source_documents||[]).forEach(did=>{
    if(ingDocument(store,did)===null) issues.push('rulepack references a missing source document: '+did); });
  if(st==='VERIFIED_PARTIAL'||st==='VERIFIED_FOR_DECLARED_SCOPE'){
    if(!(pack.verification||{}).method) issues.push('verified rulepack requires a verification method');
    if(!(pack.candidate_ids||[]).length) issues.push('verified rulepack contains no verified rules'); }
  return issues; }
function canTransitionPack(frm,to){ return (ING_PACK_TRANSITIONS[frm]||[]).indexOf(to)>=0; }
function verifyPack(pack,store,to,verifier,at,method,notes){
  to=(to===undefined||to===null)?'VERIFIED_PARTIAL':to;
  method=(method===undefined||method===null)?'explicit_manual_approval':method;
  if(ING_PACK_STATES.indexOf(to)<0) return [false,'UNKNOWN_TARGET_STATE'];
  if(!pack.verification) pack.verification={status:'DRAFT'};
  const v=pack.verification, frm=v.status;
  if(!canTransitionPack(frm,to)) return [false,'INVALID_TRANSITION: '+frm+' -> '+to];
  if(ING_VERIFICATION_METHODS.indexOf(method)<0||method==='ai_suggestion')
    return [false,method==='ai_suggestion'?'AI_MAY_NOT_VERIFY':'UNKNOWN_VERIFICATION_METHOD'];
  const issues=validatePack(pack,store);
  if(issues.length) return [false,'PACK_INVALID: '+issues[0]];
  if(to==='VERIFIED_FOR_DECLARED_SCOPE'&&pack.completeness!=='complete_for_declared_scope')
    return [false,'SCOPE_COMPLETENESS_NOT_DECLARED'];
  v.status=to; v.method=method; v.verified_at=(at===undefined?null:at);
  v.verified_by=(verifier===undefined?null:verifier); v.notes=(notes===undefined?null:notes);
  if(!pack.history) pack.history=[];
  pack.history.push({from:frm,to:to,method:method,at:(at===undefined?null:at)});
  return [true,null]; }
/* يحوّل حزمة متحقَّقاً منها إلى الشكل الذي يفهمه محرّك القواعد — بلا تعديل معنى */
function packToRuleSet(pack,store){
  const rules=[];
  (pack.candidate_ids||[]).forEach(cid=>{
    const c=ingCandidate(store,cid);
    if(c===null||c.status!=='VERIFIED') return;
    if(!verificationStillValid(c,store)[0]) return;
    rules.push(JSON.parse(JSON.stringify(c.proposed_rule))); });
  return {ruleset_id:pack.rulepack_id+'@'+pack.version, ruleset_version:pack.version,
    standard:pack.standard, edition:pack.edition,
    jurisdiction:(pack.jurisdiction===undefined?null:pack.jurisdiction),
    coverage_scope:(pack.coverage_scope||[]).join(', '),
    completeness:pack.completeness, regulatory:pack.regulatory===true, rules:rules}; }
const ING_PACK_ACTIVE_STATES=['VERIFIED_PARTIAL','VERIFIED_FOR_DECLARED_SCOPE'];
/* لا تفعيل ضمني: الحزمة تعمل فقط إن ربطها المشروع صراحةً وكانت متحقَّقاً منها */
function resolveActiveRules(project,store){
  const out={rulesets:[],activated:[],rejected:[],conflicts:[]};
  ((project||{}).rulepacks||[]).forEach(ref=>{
    if(ref.enabled!==true){ out.rejected.push({rulepack_id:(ref.rulepack_id===undefined?null:ref.rulepack_id),
      version:(ref.version===undefined?null:ref.version),reason:'NOT_ENABLED'}); return; }
    const p=ingRulePack(store,ref.rulepack_id,ref.version);
    if(p===null){ out.rejected.push({rulepack_id:(ref.rulepack_id===undefined?null:ref.rulepack_id),
      version:(ref.version===undefined?null:ref.version),reason:'RULEPACK_NOT_FOUND'}); return; }
    const st=(p.verification||{}).status;
    if(ING_PACK_ACTIVE_STATES.indexOf(st)<0){
      out.rejected.push({rulepack_id:p.rulepack_id,version:p.version,
        reason:'RULEPACK_NOT_VERIFIED ('+st+')'}); return; }
    const issues=validatePack(p,store);
    if(issues.length){ out.rejected.push({rulepack_id:p.rulepack_id,version:p.version,
      reason:'RULEPACK_INVALID',detail:issues[0]}); return; }
    const rs=packToRuleSet(p,store);
    out.rulesets.push(rs);
    out.activated.push({rulepack_id:p.rulepack_id,version:p.version,ruleset_id:rs.ruleset_id,
      rules:rs.rules.length,completeness:p.completeness,
      coverage_scope:(p.coverage_scope||[]).slice()}); });
  // تعارض غير محسوم: نفس المعرّف بمعنيين مختلفين ⇒ لا اختيار عشوائي
  const seen={};
  out.rulesets.forEach(rs=>rs.rules.forEach(r=>{
    const rid=r.rule_id, h=ruleDefinitionHash(r), prev=seen[rid];
    if(prev===undefined) seen[rid]=[h,rs.ruleset_id];
    else if(prev[0]!==h) out.conflicts.push({rule_id:rid,rulesets:[prev[1],rs.ruleset_id],
      reason:'RULE_CONFLICT'}); }));
  return out; }
/* تقييم مشروع مقابل حزمه المفعَّلة صراحةً فقط. التعارض ⇒ NOT_EVALUATED */
function evaluateProject(project,subjects,store,context){
  const ctx=Object.assign({},context||{});
  if(ctx.jurisdiction===undefined) ctx.jurisdiction=((project||{}).jurisdiction===undefined?null:(project||{}).jurisdiction);
  const active=resolveActiveRules(project,store);
  const conflicted={}; active.conflicts.forEach(c=>{conflicted[c.rule_id]=1;});
  const results=[], packs=[];
  active.rulesets.forEach(rs=>{
    rs.rules.forEach(r=>{
      if(conflicted[r.rule_id]){
        results.push({rule_id:r.rule_id,rule_uid:ruleUid(r),ruleset_id:rs.ruleset_id,
          status:'NOT_EVALUATED',reason:'RULE_CONFLICT',regulatory:r.regulatory===true,
          applicability:'UNDETERMINED',data_quality:'NOT_REQUIRED',
          engine_version:RULE_ENGINE_VERSION,
          evaluated_at:(ctx.evaluated_at===undefined?null:ctx.evaluated_at),
          code_required_eligible:false});
        return; }
      subjects.forEach(s=>results.push(evaluateRule(r,s,ctx,rs,active.rulesets))); });
    packs.push(rs); });
  const agg=aggregateRuleResults(results,{
    ruleset_id:packs.map(p=>p.ruleset_id).join(',')||null, ruleset_version:null,
    standard:packs.length?packs[0].standard:null, edition:packs.length?packs[0].edition:null,
    coverage_scope:packs.map(p=>p.coverage_scope).join('; ')||null,
    completeness:packs.length?packs[0].completeness:'unknown'});
  agg.activated_rulepacks=active.activated;
  agg.rejected_rulepacks=active.rejected;
  agg.conflicts=active.conflicts;
  return {results:results,summary:agg,activation:active}; }
/* ------------------------------------------------------- الاستيراد ---- */
function validateImport(bundle){
  const issues=[];
  if(!bundle||typeof bundle!=='object'||Array.isArray(bundle)) return ['import bundle is not an object'];
  if(_ingExecutable(bundle)) issues.push('import bundle contains executable/script-like content');
  const store={documents:bundle.documents||[],fragments:bundle.fragments||[],
               candidates:bundle.candidates||[],rulepacks:bundle.rulepacks||[]};
  [['documents','document_id'],['fragments','fragment_id'],['candidates','candidate_id']].forEach(pair=>{
    const seen={};
    store[pair[0]].forEach(it=>{ const i=it[pair[1]];
      if(seen[i]) issues.push('duplicate '+pair[1]+': '+i); seen[i]=1; }); });
  const seenP={};
  store.rulepacks.forEach(p=>{ const k=p.rulepack_id+'@'+p.version;
    if(seenP[k]) issues.push('duplicate rulepack id/version: '+k); seenP[k]=1; });
  store.documents.forEach(d=>validateDocument(d).forEach(i=>issues.push('['+d.document_id+'] '+i)));
  store.fragments.forEach(f=>validateFragment(f,store).forEach(i=>issues.push('['+f.fragment_id+'] '+i)));
  store.candidates.forEach(c=>validateCandidate(c,store).forEach(i=>issues.push('['+c.candidate_id+'] '+i)));
  store.rulepacks.forEach(p=>validatePack(p,store).forEach(i=>issues.push('['+p.rulepack_id+'] '+i)));
  return issues; }
function ingestStoreIssues(store){ return validateImport({documents:store.documents,
  fragments:store.fragments,candidates:store.candidates,rulepacks:store.rulepacks}); }
/* بيانات تدقيق فقط — لا نصّ مصدر كامل ولا محتوى محمي */
function ingestAuditExport(store,project){
  const docs=(store.documents||[]).map(d=>({document_id:d.document_id,standard:d.standard,
    edition:(d.edition===undefined?null:d.edition),sha256:(d.integrity||{}).sha256,
    status:(d.verification||{}).status,official:d.official===true,synthetic:d.synthetic===true}));
  const cands=(store.candidates||[]).map(c=>{ const rec=c.verification||null;
    return {candidate_id:c.candidate_id,status:c.status,document_id:c.document_id,
      document_hash:c.document_hash,fragment_ids:(c.fragment_ids||[]).slice(),
      ai_assisted:c.ai_assisted===true,rule_id:(c.proposed_rule||{}).rule_id,
      rule_revision:((c.proposed_rule||{}).revision===undefined?null:(c.proposed_rule||{}).revision),
      rule_definition_hash:ruleDefinitionHash(c.proposed_rule),
      verification:rec?{method:rec.method,verified_at:rec.verified_at,verified_by:rec.verifier,
        document_hash:rec.document_hash,rule_definition_hash:rec.rule_definition_hash}:null}; });
  const packs=(store.rulepacks||[]).map(p=>({rulepack_id:p.rulepack_id,version:p.version,
    status:(p.verification||{}).status,completeness:p.completeness,
    coverage_scope:(p.coverage_scope||[]).slice(),regulatory:p.regulatory===true,
    candidate_ids:(p.candidate_ids||[]).slice()}));
  const out={pipeline_version:INGEST_PIPELINE_VERSION,engine_version:RULE_ENGINE_VERSION,
    documents:docs,candidates:cands,rulepacks:packs,
    copyright_note:'metadata, hashes and references only — no full source text is exported'};
  if(project!==null&&project!==undefined){
    out.activation=resolveActiveRules(project,store).activated;
    out.jurisdiction=(project.jurisdiction===undefined?null:project.jurisdiction); }
  return out; }
/* قواعد تنظيمية متحقَّق منها فعلاً داخل خط الاستيراد — يجب أن تكون صفراً */
function ingestRegulatoryRuleCount(store){ let n=0;
  (store.candidates||[]).forEach(c=>{ const pr=c.proposed_rule||{};
    if(c.status==='VERIFIED'&&pr.regulatory===true) n++; });
  return n; }
__ACS_SHARED.ACS_INGEST_STORE = ingestFixtureStore();   // تجهيزات اصطناعية فقط، بلا تفعيل
/* ==================================================================
   المرحلة 2 — أساس التصنيف النظامي للإشغال وسياق الكود (نسخة مطابقة لـ acs_occupancy.py).
   BUILDING PROGRAM ≠ REGULATORY OCCUPANCY ≠ JURISDICTION ≠ RULESET ACTIVATION.
   البرنامج يقترح ولا يُثبت • الذكاء الاصطناعي يقترح ولا يوثّق • إعلان المستخدم
   ليس تحقّقاً • لا اسم مجموعة يُخترع خارج حزمة محمّلة • لا غسيل عبر الإصدارات •
   تعارض متحقَّقَين ⇒ CONFLICT ⇒ القاعدة NOT_EVALUATED بلا ترجيح صامت.
   ================================================================== */
const ACS_OCCUPANCY_REGISTRY = {
 "schema": "acs.occupancy/1",
 "layer_version": "acs-occupancy/1.0.0",
 "note": "SYNTHETIC classification system only. No SBC, IBC or any real occupancy group name appears in this file. Every classification is regulatory=false / synthetic=true and exists solely to exercise the classification machinery. Real occupancy classes may only enter through a verified OccupancyClassificationPack built from authoritative supplied source material.",
 "classification_states": [
  "UNCLASSIFIED",
  "CANDIDATE",
  "NEEDS_INFORMATION",
  "READY_FOR_VERIFICATION",
  "VERIFIED",
  "CONFLICT",
  "NOT_APPLICABLE"
 ],
 "classification_transitions": {
  "UNCLASSIFIED": [
   "CANDIDATE",
   "NEEDS_INFORMATION",
   "NOT_APPLICABLE"
  ],
  "CANDIDATE": [
   "NEEDS_INFORMATION",
   "READY_FOR_VERIFICATION",
   "UNCLASSIFIED",
   "NOT_APPLICABLE"
  ],
  "NEEDS_INFORMATION": [
   "CANDIDATE",
   "READY_FOR_VERIFICATION",
   "UNCLASSIFIED",
   "NOT_APPLICABLE"
  ],
  "READY_FOR_VERIFICATION": [
   "VERIFIED",
   "CANDIDATE",
   "NEEDS_INFORMATION",
   "UNCLASSIFIED",
   "NOT_APPLICABLE"
  ],
  "VERIFIED": [
   "CONFLICT",
   "NEEDS_INFORMATION",
   "UNCLASSIFIED",
   "NOT_APPLICABLE"
  ],
  "CONFLICT": [
   "NEEDS_INFORMATION",
   "UNCLASSIFIED"
  ],
  "NOT_APPLICABLE": [
   "UNCLASSIFIED"
  ]
 },
 "provenance_sources": [
  "USER_DECLARED",
  "AUTHORITATIVE_MAPPING",
  "MANUAL_VERIFIED",
  "AI_SUGGESTED"
 ],
 "never_auto_verified": [
  "AI_SUGGESTED",
  "USER_DECLARED"
 ],
 "subject_types": [
  "PROJECT",
  "SITE",
  "BUILDING",
  "LEVEL",
  "SPACE",
  "ZONE"
 ],
 "pack_states": [
  "DRAFT",
  "UNDER_REVIEW",
  "VERIFIED_PARTIAL",
  "VERIFIED_FOR_DECLARED_SCOPE",
  "SUPERSEDED",
  "REVOKED"
 ],
 "pack_transitions": {
  "DRAFT": [
   "UNDER_REVIEW",
   "REVOKED"
  ],
  "UNDER_REVIEW": [
   "VERIFIED_PARTIAL",
   "VERIFIED_FOR_DECLARED_SCOPE",
   "DRAFT",
   "REVOKED"
  ],
  "VERIFIED_PARTIAL": [
   "VERIFIED_FOR_DECLARED_SCOPE",
   "SUPERSEDED",
   "REVOKED",
   "UNDER_REVIEW"
  ],
  "VERIFIED_FOR_DECLARED_SCOPE": [
   "SUPERSEDED",
   "REVOKED",
   "UNDER_REVIEW"
  ],
  "SUPERSEDED": [
   "REVOKED"
  ],
  "REVOKED": []
 },
 "verification_methods": [
  "explicit_manual_approval",
  "dual_manual_approval",
  "authority_attestation",
  "ai_suggestion"
 ],
 "classification_facts": [
  "sleeping_use",
  "medical_treatment_use",
  "education_use",
  "storage_use",
  "industrial_activity",
  "assembly_use",
  "retail_use",
  "office_use",
  "space_use_description",
  "building_program",
  "represented_activities"
 ],
 "packs": [
  {
   "pack_id": "TEST_ONLY.OCCPACK",
   "version": "1",
   "classification_system": "TEST_OCC",
   "standard": "TEST_STANDARD",
   "edition": "0",
   "jurisdiction": {
    "country": "TESTLAND",
    "region": null,
    "authority": null
   },
   "source_documents": [],
   "regulatory": false,
   "synthetic": true,
   "classifications": [
    {
     "id": "TEST_OCC_A",
     "group": "TEST_OCC_A",
     "subgroup": null,
     "title": "synthetic classification A (engine probe only)",
     "definition_reference": null,
     "conditions": [
      {
       "fact": "sleeping_use",
       "value": true
      }
     ],
     "exceptions": [],
     "fragment_ids": []
    },
    {
     "id": "TEST_OCC_B",
     "group": "TEST_OCC_B",
     "subgroup": null,
     "title": "synthetic classification B (engine probe only)",
     "definition_reference": null,
     "conditions": [
      {
       "fact": "storage_use",
       "value": true
      }
     ],
     "exceptions": [],
     "fragment_ids": []
    },
    {
     "id": "TEST_OCC_C",
     "group": "TEST_OCC_C",
     "subgroup": "C1",
     "title": "synthetic classification C with a synthetic subgroup",
     "definition_reference": null,
     "conditions": [
      {
       "fact": "assembly_use",
       "value": true
      }
     ],
     "exceptions": [
      {
       "condition": "synthetic exception placeholder",
       "resolution": "declared_unsupported"
      }
     ],
     "fragment_ids": []
    }
   ],
   "program_hints": [
    {
     "program": "hotel",
     "candidates": [
      "TEST_OCC_A"
     ],
     "note": "suggestion only — a building program never establishes a regulatory occupancy"
    },
    {
     "program": "warehouse",
     "candidates": [
      "TEST_OCC_B"
     ],
     "note": "suggestion only — a building program never establishes a regulatory occupancy"
    },
    {
     "program": "restaurant",
     "candidates": [
      "TEST_OCC_C"
     ],
     "note": "suggestion only — a building program never establishes a regulatory occupancy"
    }
   ],
   "verification": {
    "status": "DRAFT",
    "method": null,
    "verified_at": null,
    "verified_by": null,
    "notes": null
   },
   "coverage_scope": [
    "synthetic.occupancy_probe"
   ],
   "completeness": "partial",
   "history": []
  },
  {
   "pack_id": "TEST_ONLY.OCCPACK_ED9",
   "version": "1",
   "classification_system": "TEST_OCC",
   "standard": "TEST_STANDARD",
   "edition": "9",
   "jurisdiction": {
    "country": "TESTLAND",
    "region": null,
    "authority": null
   },
   "source_documents": [],
   "regulatory": false,
   "synthetic": true,
   "classifications": [
    {
     "id": "TEST_OCC_A",
     "group": "TEST_OCC_A",
     "subgroup": null,
     "title": "synthetic classification A (engine probe only)",
     "definition_reference": null,
     "conditions": [
      {
       "fact": "sleeping_use",
       "value": true
      }
     ],
     "exceptions": [],
     "fragment_ids": []
    },
    {
     "id": "TEST_OCC_B",
     "group": "TEST_OCC_B",
     "subgroup": null,
     "title": "synthetic classification B (engine probe only)",
     "definition_reference": null,
     "conditions": [
      {
       "fact": "storage_use",
       "value": true
      }
     ],
     "exceptions": [],
     "fragment_ids": []
    },
    {
     "id": "TEST_OCC_C",
     "group": "TEST_OCC_C",
     "subgroup": "C1",
     "title": "synthetic classification C with a synthetic subgroup",
     "definition_reference": null,
     "conditions": [
      {
       "fact": "assembly_use",
       "value": true
      }
     ],
     "exceptions": [
      {
       "condition": "synthetic exception placeholder",
       "resolution": "declared_unsupported"
      }
     ],
     "fragment_ids": []
    }
   ],
   "program_hints": [
    {
     "program": "hotel",
     "candidates": [
      "TEST_OCC_A"
     ],
     "note": "suggestion only — a building program never establishes a regulatory occupancy"
    },
    {
     "program": "warehouse",
     "candidates": [
      "TEST_OCC_B"
     ],
     "note": "suggestion only — a building program never establishes a regulatory occupancy"
    },
    {
     "program": "restaurant",
     "candidates": [
      "TEST_OCC_C"
     ],
     "note": "suggestion only — a building program never establishes a regulatory occupancy"
    }
   ],
   "verification": {
    "status": "DRAFT",
    "method": null,
    "verified_at": null,
    "verified_by": null,
    "notes": null
   },
   "coverage_scope": [
    "synthetic.occupancy_edition_probe"
   ],
   "completeness": "partial",
   "history": []
  }
 ]
};
const OCC_SCHEMA = ACS_OCCUPANCY_REGISTRY.schema;
const OCC_LAYER_VERSION = ACS_OCCUPANCY_REGISTRY.layer_version;
const OCC_STATES = ACS_OCCUPANCY_REGISTRY.classification_states;
const OCC_TRANSITIONS = ACS_OCCUPANCY_REGISTRY.classification_transitions;
const OCC_SOURCES = ACS_OCCUPANCY_REGISTRY.provenance_sources;
const OCC_NEVER_AUTO_VERIFIED = ACS_OCCUPANCY_REGISTRY.never_auto_verified;
const OCC_SUBJECT_TYPES = ACS_OCCUPANCY_REGISTRY.subject_types;
const OCC_PACK_STATES = ACS_OCCUPANCY_REGISTRY.pack_states;
const OCC_PACK_TRANSITIONS = ACS_OCCUPANCY_REGISTRY.pack_transitions;
const OCC_VERIFICATION_METHODS = ACS_OCCUPANCY_REGISTRY.verification_methods;
const OCC_FACTS = ACS_OCCUPANCY_REGISTRY.classification_facts;
const OCC_PACK_ACTIVE_STATES = ['VERIFIED_PARTIAL','VERIFIED_FOR_DECLARED_SCOPE'];
const _OCC_C = o => JSON.parse(JSON.stringify(o));
function occupancyEmptyStore(){ return {classifications:[],packs:[]}; }
function occupancyFixtureStore(){ return {classifications:[],packs:_OCC_C(ACS_OCCUPANCY_REGISTRY.packs)}; }
function occPacks(store){ return store.packs||[]; }
function occPack(store,packId,version){
  for(const p of occPacks(store))
    if(p.pack_id===packId&&(version===undefined||version===null||p.version===version)) return p;
  return null; }
function occClassification(store,cid){
  for(const c of (store.classifications||[])) if(c.id===cid) return c; return null; }
function occClassificationsFor(store,subjectId){
  return (store.classifications||[]).filter(c=>c.subject_id===subjectId); }
function occRealClassificationCount(store){
  return (store.classifications||[]).filter(c=>c.status==='VERIFIED'&&c.regulatory===true).length; }
/* ---------------------------------------------------- حزمة التصنيفات --- */
function validateOccupancyPack(p){
  const issues=[];
  if(!p||typeof p!=='object'||Array.isArray(p)) return ['classification pack is not an object'];
  if(_ingExecutable(p)) issues.push('classification pack contains executable/script-like content');
  ['pack_id','version','classification_system','standard','edition'].forEach(k=>{
    if(!p[k]) issues.push('classification pack missing field: '+k); });
  const st=(p.verification||{}).status;
  if(OCC_PACK_STATES.indexOf(st)<0) issues.push('unknown classification pack status: '+st);
  if(['partial','complete_for_declared_scope','unknown'].indexOf(p.completeness)<0)
    issues.push('unknown completeness: '+p.completeness);
  if(!Array.isArray(p.coverage_scope)||!p.coverage_scope.length)
    issues.push('classification pack must declare a coverage_scope list');
  const seen={};
  if(!Array.isArray(p.classifications)||!p.classifications.length)
    issues.push('classification pack declares no classifications');
  else p.classifications.forEach(c=>{
    if(!c.id) issues.push('classification without an id');
    if(seen[c.id]) issues.push('duplicate classification id: '+c.id);
    seen[c.id]=1;
    if(!c.group) issues.push('classification '+c.id+' has no group');
    (c.exceptions||[]).forEach(ex=>{
      if(['open','resolved','declared_unsupported'].indexOf(ex.resolution)<0)
        issues.push('classification '+c.id+' has an exception with an unknown resolution'); }); });
  (p.source_documents||[]).forEach(did=>{
    if(typeof did!=='string'||!did) issues.push('invalid source document reference in classification pack'); });
  if(p.regulatory===true&&!(p.source_documents||[]).length)
    issues.push('a regulatory classification pack must cite source documents');
  if(OCC_PACK_ACTIVE_STATES.indexOf(st)>=0&&!(p.verification||{}).method)
    issues.push('verified classification pack requires a verification method');
  return issues; }
function canTransitionOccPack(frm,to){ return (OCC_PACK_TRANSITIONS[frm]||[]).indexOf(to)>=0; }
function verifyOccupancyPack(p,to,verifier,at,method,notes){
  to=(to===undefined||to===null)?'VERIFIED_PARTIAL':to;
  method=(method===undefined||method===null)?'explicit_manual_approval':method;
  if(OCC_PACK_STATES.indexOf(to)<0) return [false,'UNKNOWN_TARGET_STATE'];
  if(!p.verification) p.verification={status:'DRAFT'};
  const v=p.verification, frm=v.status;
  if(!canTransitionOccPack(frm,to)) return [false,'INVALID_TRANSITION: '+frm+' -> '+to];
  if(method==='ai_suggestion') return [false,'AI_MAY_NOT_VERIFY'];
  if(OCC_VERIFICATION_METHODS.indexOf(method)<0) return [false,'UNKNOWN_VERIFICATION_METHOD'];
  const issues=validateOccupancyPack(p);
  if(issues.length) return [false,'PACK_INVALID: '+issues[0]];
  if(to==='VERIFIED_FOR_DECLARED_SCOPE'&&p.completeness!=='complete_for_declared_scope')
    return [false,'SCOPE_COMPLETENESS_NOT_DECLARED'];
  v.status=to; v.method=method; v.verified_at=(at===undefined?null:at);
  v.verified_by=(verifier===undefined?null:verifier); v.notes=(notes===undefined?null:notes);
  if(!p.history) p.history=[];
  p.history.push({from:frm,to:to,method:method,at:(at===undefined?null:at)});
  return [true,null]; }
function occPackClassification(p,group,subgroup){
  for(const c of (p.classifications||[]))
    if(c.group===group&&(subgroup===undefined||subgroup===null||c.subgroup===subgroup)) return c;
  return null; }
/* لا تفعيل ضمني: حزمة التصنيف تعمل فقط إن ثبّتها سياق كود المشروع صراحةً */
function activeOccupancyPacks(project,store){
  const out={packs:[],rejected:[]};
  const ctx=((project||{}).code_context)||{};
  (ctx.classification_packs||[]).forEach(ref=>{
    if(ref.enabled!==true){ out.rejected.push({pack_id:(ref.pack_id===undefined?null:ref.pack_id),
      version:(ref.version===undefined?null:ref.version),reason:'NOT_ENABLED'}); return; }
    const p=occPack(store,ref.pack_id,ref.version);
    if(p===null){ out.rejected.push({pack_id:(ref.pack_id===undefined?null:ref.pack_id),
      version:(ref.version===undefined?null:ref.version),reason:'CLASSIFICATION_PACK_NOT_FOUND'}); return; }
    const st=(p.verification||{}).status;
    if(OCC_PACK_ACTIVE_STATES.indexOf(st)<0){ out.rejected.push({pack_id:p.pack_id,version:p.version,
      reason:'CLASSIFICATION_PACK_NOT_VERIFIED ('+st+')'}); return; }
    const issues=validateOccupancyPack(p);
    if(issues.length){ out.rejected.push({pack_id:p.pack_id,version:p.version,
      reason:'CLASSIFICATION_PACK_INVALID',detail:issues[0]}); return; }
    out.packs.push(p); });
  return out; }
/* ------------------------------------------------------- سياق الكود --- */
function newCodeContext(){
  return {jurisdiction:{country:null,region:null,authority:null},
          code_context:{standard:null,edition:null,rulepacks:[],classification_packs:[]},
          occupancy:{status:'UNCLASSIFIED',classifications:[]}}; }
function validateCodeContext(ctx){
  const issues=[];
  if(!ctx||typeof ctx!=='object'||Array.isArray(ctx)) return ['code context is not an object'];
  if(_ingExecutable(ctx)) issues.push('code context contains executable/script-like content');
  if(!ctx.jurisdiction||typeof ctx.jurisdiction!=='object')
    issues.push('code context needs a jurisdiction object (may be all null)');
  const cc=ctx.code_context;
  if(!cc||typeof cc!=='object') issues.push('code context needs a code_context object');
  else {
    ['rulepacks','classification_packs'].forEach(k=>{
      if(!Array.isArray(cc[k])) issues.push('code_context.'+k+' must be a list'); });
    (cc.classification_packs||[]).forEach(ref=>{
      if(!ref.pack_id||!ref.version) issues.push('classification pack reference needs pack_id and version');
      if(ref.enabled!==true&&ref.enabled!==false)
        issues.push('classification pack reference must state enabled explicitly'); }); }
  return issues; }
/* --------------------------------------------------------- التصنيف --- */
function newOccupancyClassification(o){
  o=o||{};
  return {id:o.cid||('occ_'+o.subject_id+'_'+(o.group||'none')),
    subject_id:(o.subject_id===undefined?null:o.subject_id),
    subject_type:(o.subject_type===undefined?null:o.subject_type),
    classification_system:(o.classification_system===undefined?null:o.classification_system),
    standard:(o.standard===undefined?null:o.standard),
    edition:(o.edition===undefined?null:o.edition),
    jurisdiction:o.jurisdiction||{country:null,region:null,authority:null},
    group:(o.group===undefined?null:o.group), subgroup:(o.subgroup===undefined?null:o.subgroup),
    pack_id:(o.pack_id===undefined?null:o.pack_id),
    pack_version:(o.pack_version===undefined?null:o.pack_version),
    source:o.source||'AI_SUGGESTED', status:'UNCLASSIFIED',
    evidence:(o.evidence||[]).slice(),
    declared_value:null, declared_by:null, declaration_time:null,
    verification:null, regulatory:!!o.regulatory, synthetic:o.synthetic!==false,
    history:[]}; }
function validateOccupancyClassification(c,store){
  const issues=[];
  if(!c||typeof c!=='object'||Array.isArray(c)) return ['classification is not an object'];
  if(_ingExecutable(c)) issues.push('classification contains executable/script-like content');
  ['id','subject_id','subject_type','source'].forEach(k=>{
    if(!c[k]) issues.push('classification missing field: '+k); });
  if(OCC_SUBJECT_TYPES.indexOf(c.subject_type)<0)
    issues.push('unknown classification subject_type: '+c.subject_type);
  if(OCC_SOURCES.indexOf(c.source)<0) issues.push('unknown classification source: '+c.source);
  if(OCC_STATES.indexOf(c.status)<0) issues.push('unknown classification status: '+c.status);
  const p=c.pack_id?occPack(store,c.pack_id,c.pack_version):null;
  if(c.group){
    if(p===null) issues.push('classification cites no loaded classification pack for group '+c.group);
    else if(occPackClassification(p,c.group,c.subgroup)===null)
      issues.push('group '+c.group+'/'+c.subgroup+' does not exist in classification pack '+c.pack_id); }
  if(p!==null) ['standard','edition','classification_system'].forEach(f=>{
    if(c[f]&&p[f]&&c[f]!==p[f])
      issues.push('classification '+f+' does not match its pack ('+c[f]+' vs '+p[f]+')'); });
  if(c.status==='VERIFIED'){
    const v=c.verification||null;
    if(!v) issues.push('VERIFIED classification without a verification record');
    else if(!(c.evidence||[]).length) issues.push('VERIFIED classification without recorded evidence');
    if(c.source==='AI_SUGGESTED')
      issues.push('an AI_SUGGESTED classification may never carry VERIFIED status'); }
  if(c.source==='USER_DECLARED'&&(c.declared_value===null||c.declared_value===undefined))
    issues.push('USER_DECLARED classification must record declared_value');
  return issues; }
function canTransitionOccupancy(frm,to){ return (OCC_TRANSITIONS[frm]||[]).indexOf(to)>=0; }
function _occMove(c,to,note){
  const frm=c.status;
  if(!canTransitionOccupancy(frm,to)) return [false,'INVALID_TRANSITION: '+frm+' -> '+to];
  c.status=to;
  if(!c.history) c.history=[];
  c.history.push({from:frm,to:to,note:(note===undefined?null:note)});
  return [true,null]; }
function addOccupancyClassification(store,c){
  if(occClassification(store,c.id)!==null) return [false,'DUPLICATE_CLASSIFICATION_ID'];
  if(!store.classifications) store.classifications=[];
  store.classifications.push(c);
  return [true,null]; }
/* برنامج المبنى يقترح ولا يُثبت — أقصى حالة ممكنة CANDIDATE */
function suggestOccupancyFromProgram(subjectId,subjectType,program,store,project,at){
  const out=[];
  activeOccupancyPacks(project,store).packs.forEach(p=>{
    (p.program_hints||[]).forEach(hint=>{
      if(hint.program!==program) return;
      (hint.candidates||[]).forEach(gid=>{
        const cd=occPackClassification(p,gid);
        if(cd===null) return;
        const c=newOccupancyClassification({subject_id:subjectId,subject_type:subjectType,
          group:cd.group,subgroup:cd.subgroup,source:'AI_SUGGESTED',
          pack_id:p.pack_id,pack_version:p.version,standard:p.standard,edition:p.edition,
          classification_system:p.classification_system,jurisdiction:p.jurisdiction,
          regulatory:p.regulatory===true,synthetic:p.synthetic===true,
          cid:'occ_'+subjectId+'_'+p.pack_id+'_'+cd.group,
          evidence:[{type:'program_hint',ref:program,
                     detail:hint.note||'program suggestion only'},
                    {type:'classification_pack',ref:p.pack_id,
                     detail:'group defined in the loaded classification system'}]});
        _occMove(c,'CANDIDATE','suggested from building program at '+(at===undefined?null:at));
        out.push(c); }); }); });
  return out; }
/* إعلان صريح من مستخدم/مهندس — ليس تحقّقاً بذاته */
function declareOccupancy(subjectId,subjectType,group,store,project,subgroup,declaredBy,at,note){
  const act=activeOccupancyPacks(project,store);
  for(const p of act.packs){
    const cd=occPackClassification(p,group,subgroup);
    if(cd===null) continue;
    const c=newOccupancyClassification({subject_id:subjectId,subject_type:subjectType,
      group:cd.group,subgroup:cd.subgroup,source:'USER_DECLARED',
      pack_id:p.pack_id,pack_version:p.version,standard:p.standard,edition:p.edition,
      classification_system:p.classification_system,jurisdiction:p.jurisdiction,
      regulatory:p.regulatory===true,synthetic:p.synthetic===true,
      cid:'occ_'+subjectId+'_'+p.pack_id+'_'+cd.group+'_declared',
      evidence:[{type:'user_declaration',ref:(declaredBy===undefined?null:declaredBy),
                 detail:note||'declared by the project team'}]});
    c.declared_value=group; c.declared_by=(declaredBy===undefined?null:declaredBy);
    c.declaration_time=(at===undefined?null:at);
    _occMove(c,'CANDIDATE','user declaration recorded at '+(at===undefined?null:at));
    return [c,null]; }
  return [null,'GROUP_NOT_IN_ANY_ACTIVE_CLASSIFICATION_PACK']; }
/* البوّابة الصريحة الوحيدة إلى VERIFIED — الذكاء الاصطناعي لا يجتازها */
function verifyOccupancy(c,store,project,verifier,at,method,evidence,notes){
  method=(method===undefined||method===null)?'explicit_manual_approval':method;
  if(method==='ai_suggestion') return [false,'AI_MAY_NOT_VERIFY',null];
  if(OCC_VERIFICATION_METHODS.indexOf(method)<0) return [false,'UNKNOWN_VERIFICATION_METHOD',null];
  if(!evidence||!evidence.length) return [false,'VERIFICATION_EVIDENCE_REQUIRED',null];
  const p=occPack(store,c.pack_id,c.pack_version);
  if(p===null) return [false,'CLASSIFICATION_PACK_NOT_FOUND',null];
  if(OCC_PACK_ACTIVE_STATES.indexOf((p.verification||{}).status)<0)
    return [false,'CLASSIFICATION_PACK_NOT_VERIFIED',null];
  const act=activeOccupancyPacks(project,store).packs;
  if(!act.some(x=>x.pack_id===c.pack_id&&x.version===c.pack_version))
    return [false,'CLASSIFICATION_PACK_NOT_ACTIVATED',null];
  if(occPackClassification(p,c.group,c.subgroup)===null)
    return [false,'GROUP_NOT_IN_CLASSIFICATION_PACK',null];
  const issues=validateOccupancyClassification(c,store).filter(i=>i.indexOf('VERIFIED')<0);
  if(issues.length) return [false,'CLASSIFICATION_INVALID: '+issues[0],null];
  if(c.status!=='READY_FOR_VERIFICATION'){
    const mv=_occMove(c,'READY_FOR_VERIFICATION','advanced for explicit verification');
    if(!mv[0]) return [false,mv[1],null]; }
  const sourceBefore=c.source;
  const rec={verifier:(verifier===undefined?null:verifier),method:method,
    verified_at:(at===undefined?null:at),pack_id:p.pack_id,pack_version:p.version,
    standard:p.standard,edition:p.edition,source_before:sourceBefore,
    notes:(notes===undefined?null:notes)};
  const mv2=_occMove(c,'VERIFIED','explicitly verified at '+(at===undefined?null:at));
  if(!mv2[0]) return [false,mv2[1],null];
  c.source='MANUAL_VERIFIED'; c.verification=rec;
  c.evidence=(c.evidence||[]).concat(evidence);
  return [true,null,rec]; }
/* حلّ تصنيفات موضوع واحد — تعارض متحقَّقَين ⇒ CONFLICT بلا ترجيح */
function resolveOccupancy(subjectId,store){
  const recs=occClassificationsFor(store,subjectId);
  const out={subject_id:subjectId,status:'UNCLASSIFIED',group:null,subgroup:null,
    standard:null,edition:null,classification_system:null,jurisdiction_country:null,
    source:null,records:recs.length,candidates:[],reason:null};
  if(!recs.length) return out;
  const verified=recs.filter(c=>c.status==='VERIFIED');
  out.candidates=recs.map(c=>({id:c.id,group:c.group,status:c.status,source:c.source}));
  if(verified.length){
    const keys={};
    verified.forEach(c=>{keys[[c.standard,c.edition,c.group,c.subgroup].join('|')]=1;});
    if(Object.keys(keys).length>1){
      out.status='CONFLICT'; out.reason='OCCUPANCY_CLASSIFICATION_CONFLICT'; return out; }
    const v=verified[0];
    out.status='VERIFIED'; out.group=v.group; out.subgroup=v.subgroup;
    out.standard=v.standard; out.edition=v.edition;
    out.classification_system=v.classification_system;
    out.jurisdiction_country=(v.jurisdiction||{}).country;
    out.source=v.source;
    return out; }
  const order=['READY_FOR_VERIFICATION','CANDIDATE','NEEDS_INFORMATION','NOT_APPLICABLE',
               'CONFLICT','UNCLASSIFIED'];
  const present=order.filter(s=>recs.some(c=>c.status===s));
  const st=present.length?present[0]:'UNCLASSIFIED';
  out.status=(st==='READY_FOR_VERIFICATION')?'CANDIDATE':st;
  out.reason='OCCUPANCY_NOT_VERIFIED';
  return out; }
function occupancyIndex(store,subjectIds){
  const idx={}; (subjectIds||[]).forEach(sid=>{idx[sid]=resolveOccupancy(sid,store);}); return idx; }
/* جرد تصنيفي — معلومات فقط، ولا عبارة مطابقة */
function auditOccupancy(store,subjectIds){
  let ids;
  if(subjectIds!==undefined&&subjectIds!==null) ids=subjectIds.slice();
  else { const s={}; (store.classifications||[]).forEach(c=>{s[c.subject_id]=1;}); ids=Object.keys(s).sort(); }
  const counts={UNCLASSIFIED:0,CANDIDATE:0,NEEDS_INFORMATION:0,READY_FOR_VERIFICATION:0,
                VERIFIED:0,CONFLICT:0,NOT_APPLICABLE:0};
  ids.forEach(sid=>{counts[resolveOccupancy(sid,store).status]++;});
  return {subjects_total:ids.length,unclassified:counts.UNCLASSIFIED,candidate:counts.CANDIDATE,
    needs_information:counts.NEEDS_INFORMATION,ready_for_verification:counts.READY_FOR_VERIFICATION,
    verified:counts.VERIFIED,conflict:counts.CONFLICT,not_applicable:counts.NOT_APPLICABLE,
    real_regulatory_verified:occRealClassificationCount(store),layer_version:OCC_LAYER_VERSION,
    note:'classification inventory only — this is not a compliance statement'}; }
function occupancyIssues(store,project){
  const out=[];
  occPacks(store).forEach(p=>validateOccupancyPack(p).forEach(i=>
    out.push('['+p.pack_id+'@'+p.version+'] '+i)));
  const seen={};
  (store.classifications||[]).forEach(c=>{
    if(seen[c.id]) out.push('['+c.id+'] duplicate classification id');
    seen[c.id]=1;
    validateOccupancyClassification(c,store).forEach(i=>out.push('['+c.id+'] '+i)); });
  if(project!==undefined&&project!==null)
    validateCodeContext(project).forEach(i=>out.push('[code_context] '+i));
  return out; }
/* تصدير إضافي — الاقتراحات لا تُصدَّر كحقائق */
function exportOccupancy(store,project){
  const rows=(store.classifications||[]).map(c=>({id:c.id,subject_id:c.subject_id,
    subject_type:c.subject_type,status:c.status,source:c.source,group:c.group,subgroup:c.subgroup,
    standard:c.standard,edition:c.edition,classification_system:c.classification_system,
    regulatory:c.regulatory===true,synthetic:c.synthetic===true,
    authoritative:c.status==='VERIFIED',evidence:(c.evidence||[]).slice(),
    verification:(c.verification===undefined?null:c.verification),
    declared_value:c.declared_value,declared_by:c.declared_by,
    declaration_time:c.declaration_time}));
  const out={layer_version:OCC_LAYER_VERSION,classifications:rows,
    packs:occPacks(store).map(p=>({pack_id:p.pack_id,version:p.version,
      classification_system:p.classification_system,standard:p.standard,edition:p.edition,
      status:(p.verification||{}).status,regulatory:p.regulatory===true,
      synthetic:p.synthetic===true})),
    real_regulatory_verified:occRealClassificationCount(store),
    note:'AI suggestions are exported with their status and are never authoritative'};
  if(project!==undefined&&project!==null)
    out.activated_classification_packs=activeOccupancyPacks(project,store).packs
      .map(p=>({pack_id:p.pack_id,version:p.version}));
  return out; }
__ACS_SHARED.ACS_OCCUPANCY_STORE = occupancyFixtureStore();  // حزم تصنيف اصطناعية، بلا تفعيل ولا تصنيف
/* ==================================================================
   المرحلة 2 — أساس تثبيت النتائج على مراجعة النموذج (نسخة مطابقة لـ acs_revision.py).
   البصمة هي المرساة لا الوقت • تقنين حتمي قبل التجزئة • حالة العرض لا تُبطل
   تقييماً هندسياً • لا إعادة تقييم صامتة • لا تعديل للنموذج لحساب بصمة •
   المشتقّات لا تُجزَّأ بل تُجزَّأ مصادرها.
   ================================================================== */
const ACS_REVISION_SPEC = {
 "schema": "acs.revision/1",
 "canonicalization_version": "acs-model-canonical/1",
 "hash_algorithm": "sha256",
 "revision_id_prefix": "rev_",
 "scopes": [
  "building",
  "project",
  "code_context",
  "occupancy"
 ],
 "integrity_statuses": [
  "CURRENT",
  "CURRENT_UNDER_SAME_HASH",
  "STALE_MODEL_CHANGED",
  "STALE_RULE_CHANGED",
  "STALE_RULEPACK_CHANGED",
  "STALE_OCCUPANCY_CHANGED",
  "STALE_CODE_CONTEXT_CHANGED",
  "STALE_SOURCE_CHANGED",
  "UNVERIFIABLE"
 ],
 "status_precedence": [
  "UNVERIFIABLE",
  "STALE_MODEL_CHANGED",
  "STALE_SOURCE_CHANGED",
  "STALE_RULE_CHANGED",
  "STALE_RULEPACK_CHANGED",
  "STALE_OCCUPANCY_CHANGED",
  "STALE_CODE_CONTEXT_CHANGED",
  "CURRENT_UNDER_SAME_HASH",
  "CURRENT"
 ],
 "inclusion_policy": "denylist — every field of the model participates in the hash except the declared volatile keys below. An unrecognised engineering field therefore still invalidates stale results, which is the safe direction: a false staleness costs one re-evaluation, a false CURRENT costs correctness.",
 "volatile_keys": [
  "camera",
  "view",
  "viewer",
  "ui",
  "selection",
  "selected",
  "debug",
  "fps",
  "stats",
  "session",
  "toast",
  "cache",
  "render",
  "renderer",
  "theme",
  "material_preview",
  "orbit",
  "controls",
  "downloaded_at",
  "exported_at",
  "last_render_ms",
  "_runtime",
  "_ui",
  "_view",
  "preview",
  "thumbnail",
  "layer_visibility",
  "visible_layers"
 ],
 "order_insensitive": [
  {
   "path": "levels",
   "sort_by": [
    "index",
    "template",
    "name",
    "id"
   ],
   "reason": "each level carries an explicit index; array position is not the authority, so a reorder is semantically identical"
  },
  {
   "path": "code_context.rulepacks",
   "sort_by": [
    "rulepack_id",
    "version"
   ],
   "reason": "a set of pins; order carries no meaning"
  },
  {
   "path": "code_context.classification_packs",
   "sort_by": [
    "pack_id",
    "version"
   ],
   "reason": "a set of pins; order carries no meaning"
  },
  {
   "path": "buildings",
   "sort_by": [
    "id",
    "building_id",
    "name"
   ],
   "reason": "buildings are identified by id, and per-building hashes are computed separately"
  }
 ],
 "order_sensitive": [
  {
   "path": "floors.*.rooms",
   "reason": "array position feeds the sp_<i> fallback space id when a room declares no id"
  },
  {
   "path": "floors.*.rooms.*.doors",
   "reason": "door_<i> ids appear in relationships, exit via references and distance anchors"
  },
  {
   "path": "floors.*.rooms.*.objects",
   "reason": "stairs_<i> / elevator_<i> ids appear in vertical transitions"
  },
  {
   "path": "floors.*.rooms.*.points",
   "reason": "exitpoint_<i> ids appear in exit records"
  },
  {
   "path": "*.rect",
   "reason": "a rectangle is [x, z, w, d]; position in the array is the meaning"
  },
  {
   "path": "*.polygon",
   "reason": "vertex order defines the outline"
  },
  {
   "path": "structural.columns",
   "reason": "structural member order is model data; reordering members is a real edit to the structural model"
  },
  {
   "path": "structural.beams",
   "reason": "structural member order is model data; reordering members is a real edit to the structural model"
  },
  {
   "path": "structural.nodes",
   "reason": "node order is model data and members reference nodes by name, so a reorder is a real edit"
  },
  {
   "path": "structural.foundations",
   "reason": "foundation order is model data; reordering is a real edit"
  }
 ],
 "default_array_policy": "any array not listed above keeps its order and is hashed as given — conservative by design, because an unknown array may be positional",
 "derived_excluded": [
  {
   "item": "relationships",
   "reason": "derived from geometry, doors and objects on demand; the geometry that produces them is hashed instead"
  },
  {
   "item": "navigation graph",
   "reason": "derived from relationships"
  },
  {
   "item": "egress results",
   "reason": "derived query output"
  },
  {
   "item": "distance measurements",
   "reason": "derived query output"
  },
  {
   "item": "coverage / report objects",
   "reason": "reporting output, not model input"
  }
 ],
 "numeric_policy": "no rounding before hashing. Integral floats are normalised to integers so that 24.0 and 24 hash alike across languages; every other value keeps full double precision and its shortest round-trip decimal form, which Python and JavaScript produce identically",
 "id_policy": "deterministic ids (space_id, level id, level elevation) are materialised on a deep copy before hashing, so a model hashes the same before and after ensure_element_ids. The input model is never mutated"
};
const REV_SCHEMA = ACS_REVISION_SPEC.schema;
const CANONICALIZATION_VERSION = ACS_REVISION_SPEC.canonicalization_version;
const REV_HASH_ALGORITHM = ACS_REVISION_SPEC.hash_algorithm;
const REV_SCOPES = ACS_REVISION_SPEC.scopes;
const REV_STATUSES = ACS_REVISION_SPEC.integrity_statuses;
const REV_PRECEDENCE = ACS_REVISION_SPEC.status_precedence;
const REV_VOLATILE_KEYS = ACS_REVISION_SPEC.volatile_keys.map(k=>String(k).toLowerCase());
const REV_ORDER_INSENSITIVE = (()=>{ const m={};
  ACS_REVISION_SPEC.order_insensitive.forEach(e=>{m[e.path]=e;}); return m; })();
const _REV_C = o => JSON.parse(JSON.stringify(o));
/* يزيل حالة العرض/الجلسة أينما وردت. كل ما عداها يدخل البصمة عمداً */
function _stripVolatile(v){
  if(Array.isArray(v)) return v.map(_stripVolatile);
  if(v&&typeof v==='object'){ const o={};
    Object.keys(v).forEach(k=>{ if(REV_VOLATILE_KEYS.indexOf(String(k).toLowerCase())<0)
      o[k]=_stripVolatile(v[k]); });
    return o; }
  return v; }
function _revSortKey(item,fields){
  return fields.map(f=>{ const val=(item&&typeof item==='object')?item[f]:undefined;
    const missing=(val===null||val===undefined);
    return [missing?1:0, missing?'':ingestCanonicalJson(val)]; }); }
function _revCmp(a,b){
  for(let i=0;i<Math.min(a.length,b.length);i++){
    if(a[i][0]!==b[i][0]) return a[i][0]-b[i][0];
    if(a[i][1]<b[i][1]) return -1;
    if(a[i][1]>b[i][1]) return 1; }
  return 0; }
function _orderInsensitive(items,path){
  const spec=REV_ORDER_INSENSITIVE[path];
  if(!spec||!Array.isArray(items)) return items;
  const dec=items.map((it,i)=>({it:it,i:i,k:_revSortKey(it,spec.sort_by)}));
  dec.sort((x,y)=>{ const c=_revCmp(x.k,y.k); return c!==0?c:(x.i-y.i); });
  return dec.map(d=>d.it); }
/* إسقاط حتمي لمبنى واحد — لا يمسّ الأصل */
function canonicalBuilding(building,bid){
  bid=bid||'bld_0';
  let b=_REV_C(building);
  ensureElementIds(b,bid);                      // على النسخة فقط
  b=_stripVolatile(b);
  if(Array.isArray(b.levels)) b.levels=_orderInsensitive(b.levels,'levels');
  return b; }
/* المشروع هنا: {schema, project:{... buildings:[{id, building:{...}}]}}؛
   ونقبل أيضاً شكلاً مسطّحاً {buildings:[...]} حتى لا نكسر مستهلكاً مستقبلياً */
function _buildingsContainer(project){
  const inner=project.project;
  return (inner&&typeof inner==='object'&&Array.isArray(inner.buildings))?inner:project; }
function _entryModel(entry){
  return (entry.building&&typeof entry.building==='object')?entry.building:entry; }
function canonicalProject(project){
  let p=_stripVolatile(_REV_C(project));
  const container=_buildingsContainer(p);
  if(Array.isArray(container.buildings)){
    const canon=container.buildings.map(entry=>{
      const bid=entry.id||entry.building_id||'bld_0';
      if(entry.building&&typeof entry.building==='object'){
        const e=Object.assign({},entry); e.building=canonicalBuilding(entry.building,bid); return e; }
      return canonicalBuilding(entry,bid); });
    container.buildings=_orderInsensitive(canon,'buildings'); }
  return p; }
function canonicalCodeContext(projectCtx){
  const c=_stripVolatile(_REV_C(projectCtx||{}));
  const cc=c.code_context;
  if(cc&&typeof cc==='object') ['rulepacks','classification_packs'].forEach(k=>{
    if(Array.isArray(cc[k])) cc[k]=_orderInsensitive(cc[k],'code_context.'+k); });
  delete c.occupancy;
  return c; }
/* التصنيفات المتحقَّق منها فقط — الاقتراحات لا تُثبَّت كحقائق */
function canonicalOccupancy(occStore,subjectIds){
  const rows=[];
  (((occStore||{}).classifications)||[]).forEach(c=>{
    if(c.status!=='VERIFIED') return;
    if(subjectIds&&subjectIds.indexOf(c.subject_id)<0) return;
    rows.push({subject_id:c.subject_id,subject_type:c.subject_type,group:c.group,
      subgroup:c.subgroup,standard:c.standard,edition:c.edition,
      classification_system:c.classification_system,pack_id:c.pack_id,
      pack_version:c.pack_version,jurisdiction:c.jurisdiction}); });
  rows.sort((a,b)=>{ const x=ingestCanonicalJson(a), y=ingestCanonicalJson(b);
    return x<y?-1:(x>y?1:0); });
  return {verified_classifications:rows}; }
function revHashOf(canonical){ return sha256Hex(ingestCanonicalJson(canonical)); }
function modelHash(model,scope,bid){
  scope=scope||'building';
  if(scope==='project') return revHashOf(canonicalProject(model));
  return revHashOf(canonicalBuilding(model,bid||'bld_0')); }
function buildingHashes(project){ const out={};
  const container=_buildingsContainer(project||{});
  (container.buildings||[]).forEach(entry=>{ const bid=entry.id||entry.building_id||'bld_0';
    out[bid]=revHashOf(canonicalBuilding(_entryModel(entry),bid)); });
  return out; }
function codeContextHash(projectCtx){ return revHashOf(canonicalCodeContext(projectCtx)); }
function occupancyHash(occStore,subjectIds){ return revHashOf(canonicalOccupancy(occStore,subjectIds)); }
/* مراجعة مشتقّة عند الطلب — لا تُكتب في النموذج ولا يُعتمد الوقت كهوية */
function modelRevision(model,scope,bid,createdAt){
  scope=scope||'building'; bid=bid||'bld_0';
  const h=modelHash(model,scope,bid);
  const rev={revision_id:ACS_REVISION_SPEC.revision_id_prefix+h.slice(0,16),
    model_hash:h,hash_algorithm:REV_HASH_ALGORITHM,
    canonicalization_version:CANONICALIZATION_VERSION,
    created_at:(createdAt===undefined?null:createdAt),scope:scope};
  if(scope==='project') rev.building_hashes=buildingHashes(model);
  else rev.building_id=bid;
  return rev; }
/* ------------------------------------------------------ لقطة النتيجة --- */
function _revSourceHashes(rule,ingestStore){
  const src=((rule||{}).source)||{}, did=src.document_id;
  if(!did||ingestStore===null||ingestStore===undefined) return {};
  const doc=ingDocument(ingestStore,did);
  const out={};
  out[did]=doc?((doc.integrity||{}).sha256):null;
  return out; }
function snapshotResult(o){
  o=o||{};
  const result=(o.result===undefined?null:o.result);
  const integ={status:'CURRENT',
    model_hash:(o.model!==undefined&&o.model!==null)?modelHash(o.model,o.scope||'building',o.building_id||'bld_0'):null,
    model_scope:o.scope||'building',
    building_id:((o.scope||'building')==='building')?(o.building_id||'bld_0'):null,
    canonicalization_version:CANONICALIZATION_VERSION, hash_algorithm:REV_HASH_ALGORITHM,
    rule_hash:o.rule?ruleDefinitionHash(o.rule):null,
    rule_id:o.rule?o.rule.rule_id:((result||{}).rule_id===undefined?null:(result||{}).rule_id),
    rule_revision:o.rule?(o.rule.revision===undefined?null:o.rule.revision)
                        :((result||{}).rule_revision===undefined?null:(result||{}).rule_revision),
    rulepack_id:o.ruleset?o.ruleset.ruleset_id:((result||{}).ruleset_id===undefined?null:(result||{}).ruleset_id),
    rulepack_version:o.ruleset?o.ruleset.ruleset_version
      :((result||{}).ruleset_version===undefined?null:(result||{}).ruleset_version),
    source_document_hashes:_revSourceHashes(o.rule,o.ingest_store),
    occupancy_refs:(o.occupancy_subjects||[]).slice().sort(),
    occupancy_hash:(o.occupancy_store!==undefined&&o.occupancy_store!==null)
      ?occupancyHash(o.occupancy_store,o.occupancy_subjects||null):null,
    code_context_hash:(o.project_ctx!==undefined&&o.project_ctx!==null)?codeContextHash(o.project_ctx):null,
    engine_version:RULE_ENGINE_VERSION,
    evaluated_at:(o.created_at!==undefined&&o.created_at!==null)?o.created_at
      :((result||{}).evaluated_at===undefined?null:(result||{}).evaluated_at)};
  return {result:(result===null?null:_REV_C(result)),integrity:integ}; }
function _revPick(statuses){
  for(const s of REV_PRECEDENCE) if(statuses.indexOf(s)>=0) return s;
  return 'CURRENT'; }
/* يقارن كل مرساة مسجَّلة بالحالة الحالية ويعيد أسباباً دقيقة */
function checkResultIntegrity(snapshot,o){
  o=o||{};
  const integ=((snapshot||{}).integrity)||{};
  const reasons=[], found=[], unchecked=[];
  if(integ.canonicalization_version!==CANONICALIZATION_VERSION){
    reasons.push({anchor:'canonicalization_version',reason:'CANONICALIZATION_VERSION_MISMATCH',
      stored:(integ.canonicalization_version===undefined?null:integ.canonicalization_version),
      current:CANONICALIZATION_VERSION});
    return {status:'UNVERIFIABLE',reasons:reasons,unchecked:['all'],
            canonicalization_version:CANONICALIZATION_VERSION}; }
  if(integ.hash_algorithm!==REV_HASH_ALGORITHM){
    reasons.push({anchor:'hash_algorithm',reason:'HASH_ALGORITHM_MISMATCH'});
    return {status:'UNVERIFIABLE',reasons:reasons,unchecked:['all'],
            canonicalization_version:CANONICALIZATION_VERSION}; }
  if(o.model!==undefined&&o.model!==null&&integ.model_hash){
    const cur=modelHash(o.model,integ.model_scope||'building',integ.building_id||'bld_0');
    if(cur!==integ.model_hash){ found.push('STALE_MODEL_CHANGED');
      reasons.push({anchor:'model_hash',reason:'MODEL_CHANGED',stored:integ.model_hash,current:cur}); }
  } else unchecked.push('model_hash');
  if(o.rule!==undefined&&o.rule!==null&&integ.rule_hash){
    const cur=ruleDefinitionHash(o.rule);
    if(cur!==integ.rule_hash){ found.push('STALE_RULE_CHANGED');
      reasons.push({anchor:'rule_hash',reason:'RULE_MEANING_CHANGED',stored:integ.rule_hash,current:cur}); }
  } else if(integ.rule_hash) unchecked.push('rule_hash');
  if(o.ruleset!==undefined&&o.ruleset!==null&&integ.rulepack_id){
    if(o.ruleset.ruleset_id!==integ.rulepack_id||o.ruleset.ruleset_version!==integ.rulepack_version){
      found.push('STALE_RULEPACK_CHANGED');
      reasons.push({anchor:'rulepack',reason:'RULEPACK_CHANGED',
        stored:integ.rulepack_id+'@'+integ.rulepack_version,
        current:o.ruleset.ruleset_id+'@'+o.ruleset.ruleset_version}); }
  } else if(integ.rulepack_id) unchecked.push('rulepack');
  if(o.occupancy_store!==undefined&&o.occupancy_store!==null&&
     integ.occupancy_hash!==null&&integ.occupancy_hash!==undefined){
    const cur=occupancyHash(o.occupancy_store,(integ.occupancy_refs&&integ.occupancy_refs.length)
      ?integ.occupancy_refs:null);
    if(cur!==integ.occupancy_hash){ found.push('STALE_OCCUPANCY_CHANGED');
      reasons.push({anchor:'occupancy_hash',reason:'OCCUPANCY_CLASSIFICATION_CHANGED',
        stored:integ.occupancy_hash,current:cur}); }
  } else if(integ.occupancy_hash!==null&&integ.occupancy_hash!==undefined) unchecked.push('occupancy_hash');
  if(o.project_ctx!==undefined&&o.project_ctx!==null&&
     integ.code_context_hash!==null&&integ.code_context_hash!==undefined){
    const cur=codeContextHash(o.project_ctx);
    if(cur!==integ.code_context_hash){ found.push('STALE_CODE_CONTEXT_CHANGED');
      reasons.push({anchor:'code_context_hash',reason:'CODE_CONTEXT_CHANGED',
        stored:integ.code_context_hash,current:cur}); }
  } else if(integ.code_context_hash!==null&&integ.code_context_hash!==undefined)
    unchecked.push('code_context_hash');
  const storedSrc=integ.source_document_hashes||{};
  if(Object.keys(storedSrc).length){
    if(o.ingest_store===undefined||o.ingest_store===null) unchecked.push('source_document_hashes');
    else Object.keys(storedSrc).forEach(did=>{
      const doc=ingDocument(o.ingest_store,did);
      const cur=doc?((doc.integrity||{}).sha256):null;
      if(cur!==storedSrc[did]){ found.push('STALE_SOURCE_CHANGED');
        reasons.push({anchor:'source_document',reason:'SOURCE_BYTES_CHANGED',document_id:did,
          stored:storedSrc[did],current:cur}); } }); }
  let status;
  if(found.length) status=_revPick(found);
  else if(unchecked.length){ status='CURRENT_UNDER_SAME_HASH';
    reasons.push({anchor:'coverage',reason:'ANCHORS_NOT_SUPPLIED_FOR_CHECK',
      unchecked:Array.from(new Set(unchecked)).sort()}); }
  else status='CURRENT';
  return {status:status,reasons:reasons,unchecked:Array.from(new Set(unchecked)).sort(),
          canonicalization_version:CANONICALIZATION_VERSION}; }
/* يوسم اللقطة بحالتها الحالية دون إعادة تقييم أي شيء */
function applyIntegrity(snapshot,o){
  const chk=checkResultIntegrity(snapshot,o);
  const snap=_REV_C(snapshot);
  snap.integrity.status=chk.status;
  snap.integrity.integrity_reasons=chk.reasons;
  snap.integrity.unchecked_anchors=chk.unchecked;
  return snap; }
function staleResults(snapshots,o){
  const out=[];
  (snapshots||[]).forEach(s=>{ const chk=checkResultIntegrity(s,o);
    if(chk.status!=='CURRENT'&&chk.status!=='CURRENT_UNDER_SAME_HASH')
      out.push({rule_id:((s.integrity||{}).rule_id===undefined?null:(s.integrity||{}).rule_id),
        result:(((s.result||{}).status)===undefined?null:((s.result||{}).status)),
        integrity_status:chk.status,reasons:chk.reasons}); });
  return out; }
function exportSnapshot(snapshot){
  const integ=Object.assign({},((snapshot||{}).integrity)||{});
  const res=((snapshot||{}).result)||{};
  return {rule_id:(integ.rule_id===undefined?null:integ.rule_id),
    result:(res.status===undefined?null:res.status),
    reason:(res.reason===undefined?null:res.reason),
    presented_as_current:(integ.status==='CURRENT'||integ.status==='CURRENT_UNDER_SAME_HASH'),
    integrity:{status:(integ.status===undefined?null:integ.status),
      model_hash:(integ.model_hash===undefined?null:integ.model_hash),
      model_scope:(integ.model_scope===undefined?null:integ.model_scope),
      rule_hash:(integ.rule_hash===undefined?null:integ.rule_hash),
      rulepack_id:(integ.rulepack_id===undefined?null:integ.rulepack_id),
      rulepack_version:(integ.rulepack_version===undefined?null:integ.rulepack_version),
      source_document_hashes:(integ.source_document_hashes===undefined?null:integ.source_document_hashes),
      occupancy_hash:(integ.occupancy_hash===undefined?null:integ.occupancy_hash),
      code_context_hash:(integ.code_context_hash===undefined?null:integ.code_context_hash),
      canonicalization_version:(integ.canonicalization_version===undefined?null:integ.canonicalization_version),
      engine_version:(integ.engine_version===undefined?null:integ.engine_version),
      evaluated_at:(integ.evaluated_at===undefined?null:integ.evaluated_at),
      integrity_reasons:(integ.integrity_reasons===undefined?null:integ.integrity_reasons)}}; }
/* ------------------------------------------------- فروق المراجعة --- */
function _revDiff(a,b,path,out,limit){
  if(out.length>=limit) return;
  const isObj=v=>v&&typeof v==='object'&&!Array.isArray(v);
  if(isObj(a)&&isObj(b)){
    const keys=Array.from(new Set(Object.keys(a).concat(Object.keys(b)))).sort();
    keys.forEach(k=>{ const p=path?(path+'.'+k):String(k);
      if(!(k in a)) out.push({path:p,change:'added'});
      else if(!(k in b)) out.push({path:p,change:'removed'});
      else _revDiff(a[k],b[k],p,out,limit); });
    return; }
  if(Array.isArray(a)&&Array.isArray(b)){
    for(let i=0;i<Math.max(a.length,b.length);i++){ const p=path+'['+i+']';
      if(i>=a.length) out.push({path:p,change:'added'});
      else if(i>=b.length) out.push({path:p,change:'removed'});
      else _revDiff(a[i],b[i],p,out,limit); }
    return; }
  if(ingestCanonicalJson(a)!==ingestCanonicalJson(b))
    out.push({path:path,change:'changed',from:(a===undefined?null:a),to:(b===undefined?null:b)}); }
/* فروق واقعية بين مراجعتين — للتدقيق فقط، بلا أي استنتاج هندسي */
function revisionDiff(modelA,modelB,scope,bid,limit){
  scope=scope||'building'; bid=bid||'bld_0'; limit=limit||200;
  const ca=(scope==='project')?canonicalProject(modelA):canonicalBuilding(modelA,bid);
  const cb=(scope==='project')?canonicalProject(modelB):canonicalBuilding(modelB,bid);
  const out=[]; _revDiff(ca,cb,'',out,limit);
  return {scope:scope,hash_a:revHashOf(ca),hash_b:revHashOf(cb),
    identical:revHashOf(ca)===revHashOf(cb),changes:out,truncated:out.length>=limit,
    canonicalization_version:CANONICALIZATION_VERSION,
    note:'factual differences only — no engineering conclusion is drawn'}; }
/* ==================================================================
   المرحلة 2 — أساس الهندسة المعمارية وغلاف المبنى (نسخة مطابقة لـ acs_arch.py).
   عناصر معمارية عامّة فقط • لا إنشاء ولا ميكانيكا ولا حريق ولا مطابقة كود •
   الجدار المشترك يُعرَّف مرّة واحدة • قيمة العرض ليست قيمة هندسية •
   الخارجية لا تُجزَم من صندوق الإحاطة وحده • المصرِّف حتمي.
   ================================================================== */
const ACS_ARCH_SPEC = {
 "schema": "acs.arch/1",
 "compiler_version": "acs-arch-compiler/1.0.0",
 "note": "Architectural geometry only. No structural, MEP, fire, accessibility or code content. Every element here is architectural; nothing is load-bearing, rated or compliant.",
 "element_types": [
  "WALL",
  "DOOR",
  "WINDOW",
  "OPENING",
  "FLOOR_SLAB",
  "FLOOR_OPENING",
  "CEILING",
  "ROOF",
  "STAIR",
  "ELEVATOR_SHAFT",
  "CORE",
  "ENVELOPE"
 ],
 "provenance_values": [
  "user",
  "imported",
  "ai_inference",
  "system_default",
  "unknown"
 ],
 "exposure_values": [
  "interior",
  "exterior",
  "unresolved"
 ],
 "evidence_status": [
  "confirmed",
  "inferred",
  "unresolved"
 ],
 "level_kinds": [
  "occupied",
  "technical",
  "roof"
 ],
 "host_status": [
  "resolved",
  "partial",
  "unresolved"
 ],
 "boundary_basis": [
  "rectangle_edges",
  "polygon_edges",
  "unsupported_shape"
 ],
 "defaults": {
  "wall_thickness_m": 0.15,
  "wall_height_m": 3.0,
  "door_width_m": 0.9,
  "door_height_m": 2.1,
  "window_width_m": 1.2,
  "window_height_m": 1.6,
  "window_sill_m": 0.9,
  "slab_thickness_m": 0.15,
  "stair_footprint_m": [
   1.2,
   4.2
  ],
  "elevator_footprint_m": [
   2.1,
   2.3
  ]
 },
 "defaults_note": "these are RENDER FALLBACKS. When the model does not state a value the semantic field stays null and the fallback is exposed separately as render_fallback_*, so a drawing convenience can never be read as an engineering fact",
 "forbidden_claims": [
  "load_bearing",
  "structural",
  "fire_rated",
  "fire_resistance",
  "compliant",
  "code_required",
  "accessible_route",
  "egress_width_compliant",
  "thermal_performance",
  "acoustic_rating"
 ],
 "geometry_issue_codes": [
  "WALL_ZERO_LENGTH",
  "WALL_NEGATIVE_THICKNESS",
  "WALL_DUPLICATE_OVERLAP",
  "OPENING_HOST_UNRESOLVED",
  "OPENING_OUTSIDE_HOST",
  "OPENING_WIDER_THAN_HOST",
  "WINDOW_ABOVE_WALL_HEIGHT",
  "WINDOW_BELOW_FLOOR",
  "DOOR_TALLER_THAN_WALL",
  "SPACE_OVERLAP",
  "SPACE_CONTAINED",
  "SPACE_OUTSIDE_FOOTPRINT",
  "SPACE_SHAPE_UNSUPPORTED",
  "LEVEL_ELEVATION_INCONSISTENT",
  "LEVEL_STACK_GAP",
  "LEVEL_STACK_OVERLAP",
  "CORE_WITHOUT_SERVED_LEVELS",
  "CORE_POSITION_NOT_STATED",
  "VOID_MISSING_FOR_CORE"
 ],
 "id_patterns": {
  "level": "<bid>.flr_<index>",
  "wall": "<bid>.flr_<index>.wall_<n>",
  "door": "<space_id>.door_<i>",
  "window": "<space_id>.window_<i>",
  "slab": "<bid>.flr_<index>.slab",
  "void": "<bid>.flr_<index>.void_<n>",
  "ceiling": "<bid>.flr_<index>.ceiling_<space>",
  "roof": "<bid>.flr_<index>.roof",
  "core": "<bid>.core_<n>",
  "envelope": "<bid>.envelope"
 },
 "id_note": "wall numbering follows the canonical sort of the wall's own geometry, not the room iteration order, so the same building always produces the same wall ids",
 "source_of_truth": "the semantic model (spaces, doors, windows, levels, objects) is the single source of truth. Physical elements are compiled from it deterministically; renderer, exports, relationships and distance all consume the same compiler output instead of each deriving their own wall geometry",
 "axis_note": "segments carry an explicit local axis and the building transform (position + rotation) is applied as a separate step, so no new algorithm assumes world-axis alignment. Existing Phase 1 probes remain axis-aligned and are reported as such"
};
const ARCH_SCHEMA = ACS_ARCH_SPEC.schema;
const ARCH_COMPILER_VERSION = ACS_ARCH_SPEC.compiler_version;
const ARCH_ELEMENT_TYPES = ACS_ARCH_SPEC.element_types;
const ARCH_PROVENANCE = ACS_ARCH_SPEC.provenance_values;
const ARCH_EXPOSURE = ACS_ARCH_SPEC.exposure_values;
const ARCH_EVIDENCE = ACS_ARCH_SPEC.evidence_status;
const ARCH_LEVEL_KINDS = ACS_ARCH_SPEC.level_kinds;
const ARCH_HOST_STATUS = ACS_ARCH_SPEC.host_status;
const ARCH_DEFAULTS = ACS_ARCH_SPEC.defaults;
const ARCH_ISSUE_CODES = ACS_ARCH_SPEC.geometry_issue_codes;
const _A_EPS = 1e-6;
const _A_PROBE = 0.05;
/* صدق بايثون: القائمة/القاموس الفارغ زائف. لازم لمطابقة `or` حرفياً */
function _pyT(v){
  if(v===null||v===undefined||v===false||v===''||v===0) return false;
  if(Array.isArray(v)) return v.length>0;
  if(typeof v==='object') return Object.keys(v).length>0;
  return true; }
/* مقارنة نصوص بنقاط الترميز — كترتيب بايثون، لا كترتيب UTF-16 */
function _scmp(a,b){ const A=Array.from(String(a)), B=Array.from(String(b));
  const n=Math.min(A.length,B.length);
  for(let i=0;i<n;i++){ const x=A[i].codePointAt(0), y=B[i].codePointAt(0);
    if(x!==y) return x<y?-1:1; }
  return A.length-B.length; }
function _ncmp(a,b){ return a<b?-1:(a>b?1:0); }
function _aInt(v,dflt){ if(v===null||v===undefined) return dflt;
  const n=Number(v); return n<0?Math.ceil(n):Math.floor(n); }
/* تقريب موحّد لمفاتيح الهندسة فقط — لا يُستعمل في أي قيمة منشورة */
function _aq(v){ return _pyRound(Number(v),6)+0; }
function _aRect(room){ const rc=room.rect;
  if(!rc||rc.length<4) return null;
  return [Number(rc[0]),Number(rc[1]),Number(rc[2]),Number(rc[3])]; }
function _aShapeSupported(room){
  return !(_pyT(room.polygon)||_pyT(room.shape)||_pyT(room.vertices)); }
function _aSpaceId(bid,tmpl,room,i){
  return room.space_id || (bid+'.'+tmpl+'.'+(room.id||('sp_'+i))); }
/* حافة مستطيل كمقطع محلي: (محور، ثابت، بداية، نهاية، اتجاه الفراغ) */
function _aEdgeSegment(edge,rc){
  const x=rc[0], z=rc[1], w=rc[2], d=rc[3];
  const e=String(edge===null||edge===undefined?'N':edge).toUpperCase().slice(0,1);
  if(e==='N') return ['x',z,x,x+w,+1];
  if(e==='S') return ['x',z+d,x,x+w,-1];
  if(e==='W') return ['z',x,z,z+d,+1];
  return ['z',x+w,z,z+d,-1]; }
function _aOpenU(edge,rc,off){
  const e=String(edge===null||edge===undefined?'N':edge).toUpperCase().slice(0,1);
  return (e==='N'||e==='S')?(rc[0]+Number(off)):(rc[1]+Number(off)); }
/* قيمة دلالية + احتياط عرض + مصدر. الاحتياط لا يصير حقيقة هندسية أبداً */
function _aVal(stated,dflt,sourceHint){
  if(stated===null||stated===undefined)
    return {value:null,render_fallback:dflt,source:'unknown'};
  return {value:Number(stated),render_fallback:dflt,source:sourceHint||'imported'}; }
function _aLevels(building,bid){
  const out=[]; const fh=building.floor_height;
  (_pyT(building.levels)?building.levels:[]).forEach(l=>{
    const idx=_aInt(l.index,0);
    const tmpl=(l.template===undefined)?null:l.template;
    let kind=l.kind;
    if(!_pyT(kind)){
      const t=String(_pyT(tmpl)?tmpl:'').toLowerCase();
      const nm=String(_pyT(l.name)?l.name:'');
      kind=(t.indexOf('roof')>=0||nm.indexOf('سطح')>=0)?'roof'
          :((t.indexOf('tech')>=0||t.indexOf('mech')>=0)?'technical':'occupied'); }
    let elev=l.elevation;
    const elevSrc=(elev!==null&&elev!==undefined)?'imported'
                 :((fh!==null&&fh!==undefined)?'system_default':'unknown');
    if((elev===null||elev===undefined)&&fh!==null&&fh!==undefined) elev=idx*Number(fh);
    out.push({id:l.id||(bid+'.flr_'+idx), index:idx, template:tmpl,
      name:(l.name===undefined)?null:l.name, kind:kind,
      elevation_m:(elev===null||elev===undefined)?null:Number(elev),
      elevation_source:elevSrc, auto_added:l.auto===true}); });
  out.sort((a,b)=>(a.index-b.index)||_scmp(String(a.id),String(b.id)));
  return out; }
function _aRoomsOf(building,tmpl,bid){
  const rooms=[];
  const fl=(_pyT(building.floors)?building.floors:{});
  const fd=(_pyT(fl[tmpl])?fl[tmpl]:{});
  const rs=(_pyT(fd.rooms)?fd.rooms:[]);
  rs.forEach((r,i)=>rooms.push([_aSpaceId(bid,tmpl,r,i),r,i]));
  return rooms; }
/* ------------------------------------------------------------ الجدران --- */
/* كل حدّ مشترك يُقسَّم عند كل نقطة انكسار، فيُعرَّف الجدار المشترك مرّة واحدة */
function _aWallSegments(rooms){
  const groups=new Map();
  rooms.forEach(tr=>{ const sid=tr[0], room=tr[1];
    const rc=_aRect(room);
    if(rc===null||!_aShapeSupported(room)) return;
    const h=(room.wall_h===undefined)?null:room.wall_h;
    ['N','S','E','W'].forEach(e=>{
      const seg=_aEdgeSegment(e,rc);
      const key=seg[0]+'|'+_aq(seg[1]);
      if(!groups.has(key)) groups.set(key,{axis:seg[0],fixed:_aq(seg[1]),items:[]});
      groups.get(key).items.push({u0:_aq(seg[2]),u1:_aq(seg[3]),space:sid,
        edge:e,side:seg[4],height:h,rect:rc}); }); });
  const walls=[];
  groups.forEach(g=>{
    const cutSet=new Set(); g.items.forEach(it=>{cutSet.add(it.u0);cutSet.add(it.u1);});
    const cuts=Array.from(cutSet).sort((a,b)=>a-b);
    for(let i=0;i+1<cuts.length;i++){
      const a=cuts[i], b=cuts[i+1];
      if(b-a<=_A_EPS) continue;
      const owners=g.items.filter(it=>it.u0<=a+_A_EPS&&it.u1>=b-_A_EPS);
      if(!owners.length) continue;
      const heights=owners.map(o=>o.height).filter(h=>h!==null&&h!==undefined);
      const sides={}, edges={}, spaceSet=new Set();
      owners.forEach(o=>{ sides[o.space]=o.side; edges[o.space]=o.edge; spaceSet.add(o.space); });
      walls.push({axis:g.axis,fixed:g.fixed,u0:a,u1:b,
        spaces:Array.from(spaceSet).sort(_scmp),sides:sides,edges:edges,
        height_stated:heights.length?heights.reduce((m,v)=>Number(v)>Number(m)?v:m):null}); } });
  /* ترتيب حتمي حسب هندسة الجدار نفسه، لا حسب ترتيب الغرف */
  walls.sort((a,b)=>_scmp(a.axis,b.axis)||_ncmp(a.fixed,b.fixed)
    ||_ncmp(a.u0,b.u0)||_ncmp(a.u1,b.u1));
  return walls; }
function _aPointInRects(px,pz,rects){
  for(const rc of rects){
    if(rc[0]-_A_EPS<=px&&px<=rc[0]+rc[2]+_A_EPS&&rc[1]-_A_EPS<=pz&&pz<=rc[1]+rc[3]+_A_EPS)
      return true; }
  return false; }
/* داخلي إن حدّه فراغان. وإلا نفحص الجانب الآخر: داخل فراغ آخر ⇒ داخلي ·
   بجوار فراغ شكله غير مدعوم ⇒ unresolved · خارج المسطح كلّه ⇒ خارجي (استنتاج) ·
   داخل الإحاطة وخارج الفراغات ⇒ unresolved */
function _aClassifyExposure(wall,rects,unsupported,bbox){
  if(wall.spaces.length>1) return ['interior','confirmed','bounded_by_two_spaces'];
  const sid=wall.spaces[0], side=wall.sides[sid];
  const mid=(wall.u0+wall.u1)/2.0;
  let px,pz;
  if(wall.axis==='x'){ px=mid; pz=wall.fixed-side*_A_PROBE; }
  else { px=wall.fixed-side*_A_PROBE; pz=mid; }
  if(_aPointInRects(px,pz,rects))
    return ['interior','inferred','opposite_side_inside_another_space'];
  if(_aPointInRects(px,pz,unsupported))
    /* الجانب الآخر يقع في المستطيل المعلن لفراغ شكله غير مدعوم: لا نجزم */
    return ['unresolved','unresolved','opposite_side_near_a_space_with_unsupported_outline'];
  if(bbox&&bbox[0]-_A_EPS<=px&&px<=bbox[2]+_A_EPS&&bbox[1]-_A_EPS<=pz&&pz<=bbox[3]+_A_EPS)
    /* داخل مسطح الدور لكن خارج كل الفراغات: قد يكون فناءً أو بهواً — لا نجزم */
    return ['unresolved','unresolved','opposite_side_is_void_inside_the_footprint'];
  return ['exterior','inferred','opposite_side_outside_the_level_footprint']; }
function _aBbox(rects){
  if(!rects.length) return null;
  return [Math.min.apply(null,rects.map(r=>r[0])),
          Math.min.apply(null,rects.map(r=>r[1])),
          Math.max.apply(null,rects.map(r=>r[0]+r[2])),
          Math.max.apply(null,rects.map(r=>r[1]+r[3]))]; }
/* ------------------------------------------------------------ الفتحات --- */
function _aOpeningsOf(room,sid,kind){
  const out=[];
  const raw=(kind==='door')?room.doors:room.windows;
  const src=_pyT(raw)?raw:[];
  src.forEach((o,i)=>{
    const rc=_aRect(room);
    if(rc===null) return;
    const seg=_aEdgeSegment(o.edge,rc);
    const uc=_aOpenU(o.edge,rc,_pyT(o.offset)?o.offset:0);
    const w=(o.width===undefined)?null:o.width;
    const defaultW=(kind==='door')?ARCH_DEFAULTS.door_width_m:ARCH_DEFAULTS.window_width_m;
    const defaultH=(kind==='door')?ARCH_DEFAULTS.door_height_m:ARCH_DEFAULTS.window_height_m;
    const el={id:o.id||sid+'.'+kind+'_'+i, type:kind.toUpperCase(), space_id:sid,
      axis:seg[0], fixed:seg[1], u_center:uc,
      edge:String(o.edge===null||o.edge===undefined?'N':o.edge).toUpperCase().slice(0,1),
      offset_stated:(o.offset!==null&&o.offset!==undefined),
      width_m:_aVal(w,defaultW),
      height_m:_aVal((o.height===undefined)?null:o.height,defaultH),
      host_wall_id:null, host_status:'unresolved', host_note:null};
    if(kind==='door'){
      /* العرض الحرّ يبقى منفصلاً عن العرض الاسمي — ولا يُشتق منه */
      const cw=o.clear_width_m;
      el.clear_width_m={value:(cw===null||cw===undefined)?null:Number(cw),
        render_fallback:null, source:(cw===null||cw===undefined)?'unknown':'imported'};
      el.hinge_side=_pyT(o.hinge_side)?o.hinge_side:null;
      el.swing_direction=_pyT(o.swing_direction)?o.swing_direction:null;
      el.swing_angle_deg=(o.swing_angle_deg===undefined)?null:o.swing_angle_deg;
      el.swing_status=(_pyT(o.hinge_side)||_pyT(o.swing_direction))?'specified':'not_specified';
      el.exit_flag=o.exit===true;
      el.destination=(o.destination===undefined)?null:o.destination; }
    else {
      el.sill_m=_aVal((o.sill===undefined)?null:o.sill,ARCH_DEFAULTS.window_sill_m); }
    el.source=_pyT(o.source)?o.source:'unknown';
    out.push(el); });
  return out; }
function _aHost(opening,walls){
  let w=opening.width_m.value;
  if(w===null||w===undefined) w=opening.width_m.render_fallback;
  const a=opening.u_center-w/2.0, b=opening.u_center+w/2.0;
  const cands=walls.filter(x=>x.axis===opening.axis
    &&Math.abs(x.fixed-opening.fixed)<=_A_EPS
    &&x.u1>a+_A_EPS&&x.u0<b-_A_EPS);
  if(!cands.length) return [null,'unresolved','no wall segment hosts this opening'];
  let host=null;
  for(const c of cands){
    if(c.u0-_A_EPS<=opening.u_center&&opening.u_center<=c.u1+_A_EPS){ host=c; break; } }
  host=host||cands[0];
  if(host.u0-_A_EPS<=a&&b<=host.u1+_A_EPS) return [host,'resolved',null];
  if(cands.length>1) return [host,'partial','opening spans '+cands.length+' wall segments'];
  return [host,'partial','opening extends beyond the single wall segment that hosts it']; }
/* ------------------------------------------------------- النوى الرأسية --- */
const _A_STAIR_WORDS=['stair','درج','سلم'];
const _A_LIFT_WORDS=['elevator','lift','مصعد'];
function _aCoreKind(obj){
  const k=String((_pyT(obj.kind)?obj.kind:(_pyT(obj.name)?obj.name:''))).toLowerCase();
  if(_A_STAIR_WORDS.some(w=>k.indexOf(w)>=0)) return 'STAIR';
  if(_A_LIFT_WORDS.some(w=>k.indexOf(w)>=0)) return 'ELEVATOR_SHAFT';
  return null; }
/* نواة رأسية = عنصر درج/مصعد له موضع مستقر ومستويات يخدمها */
function _aCores(building,bid,levels){
  const byPos=new Map();
  levels.forEach(lvl=>{
    _aRoomsOf(building,lvl.template,bid).forEach(tr=>{
      const sid=tr[0], room=tr[1];
      const rc=_aRect(room);
      if(rc===null) return;
      (_pyT(room.objects)?room.objects:[]).forEach((obj,j)=>{
        const kind=_aCoreKind(obj);
        if(kind===null) return;
        const stated=(obj.x!==null&&obj.x!==undefined&&obj.z!==null&&obj.z!==undefined);
        const px=stated?(rc[0]+Number(obj.x)):(rc[0]+rc[2]/2.0);
        const pz=stated?(rc[1]+Number(obj.z)):(rc[1]+rc[3]/2.0);
        const fp=(kind==='STAIR')?ARCH_DEFAULTS.stair_footprint_m:ARCH_DEFAULTS.elevator_footprint_m;
        const w=(obj.w===undefined)?null:obj.w, d=(obj.d===undefined)?null:obj.d;
        const key=kind+'|'+_aq(px)+'|'+_aq(pz);
        if(!byPos.has(key)) byPos.set(key,{_k:[kind,_aq(px),_aq(pz)],
          type:kind, x:px, z:pz,
          position_source:stated?'imported':'system_default',
          footprint_w_m:_aVal(w,fp[0]), footprint_d_m:_aVal(d,fp[1]),
          served_levels:[], spaces:[], via:[]});
        const entry=byPos.get(key);
        entry.served_levels.push(lvl.index);
        entry.spaces.push(sid);
        entry.via.push(sid+'.'+(kind==='STAIR'?'stairs':'elevator')+'_'+j); }); }); });
  const keys=Array.from(byPos.values()).sort((a,b)=>
    _scmp(a._k[0],b._k[0])||_ncmp(a._k[1],b._k[1])||_ncmp(a._k[2],b._k[2]));
  const cores=[];
  keys.forEach((c,n)=>{
    c.served_levels=Array.from(new Set(c.served_levels)).sort((x,y)=>x-y);
    c.spaces=Array.from(new Set(c.spaces)).sort(_scmp);
    c.id=bid+'.core_'+n;
    delete c._k;
    cores.push(c); });
  return cores; }
/* ------------------------------------------------------------ التصريف --- */


/* نشر الارتباطات التي يقرأها مقطع أسبق — تُقرأ داخل دوالّ فقط،
   فالنشر عند نهاية تقييم هذه الوحدة يسبق أي قراءة حتماً. */
Object.assign(__ACS_LATE, { codeRequiredAllowed });


export { ACS_ARCH_SPEC, ACS_INGEST_FIXTURES, ACS_OCCUPANCY_REGISTRY, ACS_REAL_SOURCES, ACS_REVISION_SPEC, ACS_RULES_REGISTRY, ARCH_COMPILER_VERSION, ARCH_DEFAULTS, ARCH_ELEMENT_TYPES, ARCH_EVIDENCE, ARCH_EXPOSURE, ARCH_HOST_STATUS, ARCH_ISSUE_CODES, ARCH_LEVEL_KINDS, ARCH_PROVENANCE, ARCH_SCHEMA, CANONICALIZATION_VERSION, EXCERPT_MAX_CHARS, INGEST_PIPELINE_VERSION, INGEST_SCHEMA, ING_CANDIDATE_STATES, ING_CANDIDATE_TRANSITIONS, ING_DOC_STATES, ING_DOC_TRANSITIONS, ING_EXCEPTION_RESOLUTIONS, ING_EXTRACTION_METHODS, ING_FORBIDDEN, ING_FORBIDDEN_KEYS, ING_FRAGMENT_KINDS, ING_FRAGMENT_STATES, ING_MEANING_FIELDS, ING_OFFICIAL_CHAIN, ING_ORIGIN_AUTHORITIES, ING_ORIGIN_TYPES, ING_PACK_ACTIVE_STATES, ING_PACK_STATES, ING_PACK_TRANSITIONS, ING_PIPELINE_STAGES, ING_RELATION_TYPES, ING_VERIFICATION_METHODS, OCC_FACTS, OCC_LAYER_VERSION, OCC_NEVER_AUTO_VERIFIED, OCC_PACK_ACTIVE_STATES, OCC_PACK_STATES, OCC_PACK_TRANSITIONS, OCC_SCHEMA, OCC_SOURCES, OCC_STATES, OCC_SUBJECT_TYPES, OCC_TRANSITIONS, OCC_VERIFICATION_METHODS, REV_HASH_ALGORITHM, REV_ORDER_INSENSITIVE, REV_PRECEDENCE, REV_SCHEMA, REV_SCOPES, REV_STATUSES, REV_VOLATILE_KEYS, RULE_COMPLETENESS, RULE_CONTRACTS, RULE_ENGINE_VERSION, RULE_FORBIDDEN_KEYS, RULE_OPERATORS, RULE_SEVERITIES, RULE_STATES, RULE_SUBJECT_TYPES, RULE_UNITS, _A_EPS, _A_LIFT_WORDS, _A_PROBE, _A_STAIR_WORDS, _OCC_C, _REV_C, _SHA_K, _aBbox, _aClassifyExposure, _aCoreKind, _aCores, _aEdgeSegment, _aHost, _aInt, _aLevels, _aOpenU, _aOpeningsOf, _aPointInRects, _aRect, _aRoomsOf, _aShapeSupported, _aSpaceId, _aVal, _aWallSegments, _aq, _buildingsContainer, _checkExpected, _cmpNumeric, _contextInput, _entryModel, _evalPrimitive, _ingBy, _ingCanon, _ingExecutable, _ingMissingDefs, _ingNumToken, _ingOpenExceptions, _ingSci, _ingUnresolvedRefs, _isHex64, _isNum, _ncmp, _occMove, _orderInsensitive, _pyList, _pyT, _revCmp, _revDiff, _revPick, _revSortKey, _revSourceHashes, _rotr32, _routeProvenance, _ruleField, _ruleForbidden, _ruleMissing, _ruleRoomOf, _scmp, _stripVolatile, _utf8Bytes, activeOccupancyPacks, addOccupancyClassification, advanceCandidate, aggregateRuleResults, allRules, applyIntegrity, assessCandidate, auditOccupancy, buildingHashes, canTransitionCandidate, canTransitionDocument, canTransitionOccPack, canTransitionOccupancy, canTransitionPack, canonicalBuilding, canonicalCodeContext, canonicalOccupancy, canonicalProject, checkResultIntegrity, codeContextHash, codeRequiredAllowed, declareOccupancy, documentUsable, evaluateProject, evaluateRule, evaluateRuleSet, exportOccupancy, exportSnapshot, fragmentsOf, fromBase, ingCandidate, ingDocument, ingFragment, ingRulePack, ingestAuditExport, ingestCanonicalJson, ingestEmptyStore, ingestFixtureStore, ingestRealStore, ingestRegulatoryRuleCount, ingestStoreIssues, modelHash, modelRevision, newCodeContext, newOccupancyClassification, occClassification, occClassificationsFor, occPack, occPackClassification, occPacks, occRealClassificationCount, occupancyEmptyStore, occupancyFixtureStore, occupancyHash, occupancyIndex, occupancyIssues, packToRuleSet, regulatoryRuleCount, resolveActiveRules, resolveInput, resolveOccupancy, resolveSubject, revHashOf, revisionDiff, ruleById, ruleDefinitionHash, ruleDisplay, ruleIssues, ruleMatches, ruleSetById, ruleSets, ruleSourceById, ruleSources, ruleUid, sha256Hex, snapshotResult, staleResults, suggestOccupancyFromProgram, toBase, transitionDocument, unitDim, validateCandidate, validateCodeContext, validateDocument, validateFragment, validateImport, validateOccupancyClassification, validateOccupancyPack, validatePack, validateRule, validateRuleSet, verificationStillValid, verifyCandidate, verifyDocumentBytes, verifyOccupancy, verifyOccupancyPack, verifyPack };
