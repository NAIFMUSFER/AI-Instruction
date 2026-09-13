'use strict';
// Static regression for the shipped Plan Review scorecard vocabulary.
// Full browser interaction remains covered by test_plan_review_ui.cjs / CI.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const file = path.resolve(__dirname, '../../public/plan-review/review.mjs');
const source = fs.readFileSync(file, 'utf8');

const requiredMetricKeys = [
  'space_area_by_role_m2',
  'unclassified_space_area_m2',
  'space_count_by_role',
  'unclassified_space_count',
  'zone_area_by_role_m2',
  'unclassified_zone_area_m2',
  'dock_count_by_zone_role',
  'rack_declared_level_sum',
  'rack_declared_footprint_area_m2',
  'lane_centerline_length_by_kind_m',
  'lane_overlap_area_by_kind_pair_m2',
  'storage_capacity_positions',
  'throughput_per_hour',
  'travel_distance_m',
  'pedestrian_vehicle_separation_compliance',
  'fire_life_safety_compliance',
];

for (const key of requiredMetricKeys) {
  assert.match(source, new RegExp(`(?:^|[,\\n])\\s*${key}:`), `missing Arabic scorecard label for ${key}`);
}

assert.match(
  source,
  /active\.scorecard\.unavailable/,
  'null scorecard metrics must surface the deterministic unavailable reason when one exists',
);
assert.doesNotMatch(source, /\bstorage_capacity\s*:/, 'obsolete storage_capacity UI key must not remain');
assert.doesNotMatch(source, /\bthroughput\s*:/, 'obsolete throughput UI key must not remain');

console.log(`PLAN REVIEW SCORECARD DISCLOSURES: ${requiredMetricKeys.length + 3} assertions passed.`);
