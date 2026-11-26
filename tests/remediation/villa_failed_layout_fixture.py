"""Room layout saved before the failed production repair of the «فيلا عائلية»
starter (signed-in path, outline + two plan chunks + one repair, then
PLAN_LAYOUT_INCOMPLETE). Kept as Python, not a .json file under tests/, so the
real-model corpus scans do not count this deliberately defective layout.
"""
import json

LAYOUT_JSON = '''{
 "meta": {
  "acs_plan_contract": "acs.plan-chunks/1.0.0"
 },
 "site": {
  "d": 28,
  "w": 18
 },
 "floors": {
  "villa_upper": {
   "rooms": [
    {
     "id": "bedroom_master",
     "name": "غرفة النوم الرئيسية",
     "rect": [
      0,
      0,
      4.6,
      5
     ],
     "role": "غرفة نوم رئيسية",
     "walls": [
      "north",
      "east",
      "south",
      "west"
     ],
     "wall_h": 3,
     "unit_id": "villa_upper_unit"
    },
    {
     "id": "bedroom_2",
     "name": "غرفة نوم ٢",
     "rect": [
      7.2,
      0,
      4.6,
      5
     ],
     "role": "bedroom",
     "walls": [
      "north",
      "east",
      "south",
      "west"
     ],
     "wall_h": 3,
     "unit_id": "villa_upper_unit"
    },
    {
     "id": "bedroom_3",
     "name": "غرفة نوم ٣",
     "rect": [
      11.8,
      0,
      6.2,
      5
     ],
     "role": "bedroom",
     "walls": [
      "north",
      "east",
      "south",
      "west"
     ],
     "wall_h": 3,
     "unit_id": "villa_upper_unit"
    },
    {
     "id": "upper_living",
     "name": "الصالة العلوية",
     "rect": [
      7.2,
      7.2,
      10.8,
      6
     ],
     "role": "صالة علوية",
     "walls": [
      "north",
      "east",
      "south",
      "west"
     ],
     "wall_h": 3,
     "unit_id": "villa_upper_unit"
    },
    {
     "id": "master_bath",
     "name": "حمام رئيسي",
     "rect": [
      4.6,
      0,
      2.6,
      3
     ],
     "role": "حمام رئيسي",
     "walls": [
      "north",
      "east",
      "south",
      "west"
     ],
     "wall_h": 3,
     "unit_id": "villa_upper_unit"
    },
    {
     "id": "shared_bath",
     "name": "حمام مشترك",
     "rect": [
      4.6,
      3,
      2.6,
      2
     ],
     "role": "حمام مشترك",
     "walls": [
      "north",
      "east",
      "south",
      "west"
     ],
     "wall_h": 3,
     "unit_id": "villa_upper_unit"
    },
    {
     "id": "uf_corridor",
     "name": "ممر الدور الأول",
     "rect": [
      4.2,
      5,
      13.8,
      2.2
     ],
     "role": "corridor",
     "walls": [
      "north",
      "east",
      "south",
      "west"
     ],
     "wall_h": 3,
     "unit_id": "villa_upper_unit"
    },
    {
     "id": "stairs_upper",
     "name": "درج الدور الأول",
     "rect": [
      0,
      5,
      4.2,
      6
     ],
     "role": "stairs",
     "walls": [
      "north",
      "east",
      "south",
      "west"
     ],
     "wall_h": 3,
     "core_id": "core_stairs",
     "unit_id": "villa_upper_unit"
    }
   ]
  },
  "villa_ground": {
   "rooms": [
    {
     "id": "entrance_lobby",
     "name": "المدخل",
     "rect": [
      0,
      0,
      4.2,
      5
     ],
     "role": "entrance",
     "walls": [
      "north",
      "east",
      "south",
      "west"
     ],
     "wall_h": 3
    },
    {
     "id": "guest_majlis",
     "name": "مجلس الضيوف",
     "rect": [
      4.2,
      0,
      6.6,
      6
     ],
     "role": "مجلس ضيوف",
     "walls": [
      "north",
      "east",
      "south",
      "west"
     ],
     "wall_h": 3
    },
    {
     "id": "family_living",
     "name": "صالة الأسرة",
     "rect": [
      4.2,
      6,
      10.8,
      10
     ],
     "role": "صالة أسرة",
     "walls": [
      "north",
      "east",
      "south",
      "west"
     ],
     "wall_h": 3
    },
    {
     "id": "dining",
     "name": "غرفة الطعام",
     "rect": [
      4.2,
      16,
      6.8,
      6
     ],
     "role": "غرفة طعام",
     "walls": [
      "north",
      "east",
      "south",
      "west"
     ],
     "wall_h": 3
    },
    {
     "id": "kitchen",
     "name": "المطبخ",
     "rect": [
      11,
      16,
      7,
      6
     ],
     "role": "kitchen",
     "walls": [
      "north",
      "east",
      "south",
      "west"
     ],
     "wall_h": 3
    },
    {
     "id": "gf_bathroom",
     "name": "حمام أرضي",
     "rect": [
      0,
      16,
      4.2,
      4
     ],
     "role": "bathroom",
     "walls": [
      "north",
      "east",
      "south",
      "west"
     ],
     "wall_h": 3
    },
    {
     "id": "gf_corridor",
     "name": "الممر الأرضي",
     "rect": [
      0,
      5,
      4.2,
      11
     ],
     "role": "corridor",
     "walls": [
      "north",
      "east",
      "south",
      "west"
     ],
     "wall_h": 3
    },
    {
     "id": "stairs",
     "name": "الدرج",
     "rect": [
      0,
      20,
      4.2,
      6
     ],
     "role": "stairs",
     "walls": [
      "north",
      "east",
      "south",
      "west"
     ],
     "wall_h": 3,
     "core_id": "core_stairs"
    }
   ]
  }
 },
 "levels": [
  {
   "id": "L0",
   "name": "الدور الأرضي",
   "index": 0,
   "template": "villa_ground"
  },
  {
   "id": "L1",
   "name": "الدور الأول",
   "index": 1,
   "template": "villa_upper"
  }
 ],
 "wall_h": 3,
 "wall_t": 0.2,
 "floor_height": 3.2,
 "_opening_identity": {
  "next": 0,
  "schema": "acs.opening-identity/1"
 }
}'''


def layout():
    return json.loads(LAYOUT_JSON)
