# -*- coding: utf-8 -*-
"""تجهيزات المرحلة 8: نماذج المستودع، وملفّات IFC مصطنعة للفحص الخصومي."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


def models():
    with open(os.path.join(ROOT, 'tests', 'phase3', 'fixtures',
                           'base_fixtures.json'), encoding='utf-8') as f:
        base = json.load(f)
    with open(os.path.join(ROOT, 'tests', 'phase7', 'fixtures',
                           'render_fixtures.json'), encoding='utf-8') as f:
        base.update(json.load(f))
    return base


HEAD = ("ISO-10303-21;\nHEADER;\n"
        "FILE_DESCRIPTION((''),'2;1');\n"
        "FILE_NAME('t.ifc','1970-01-01T00:00:00',(''),(''),'','','');\n"
        "FILE_SCHEMA(('%s'));\nENDSEC;\nDATA;\n")
TAIL = "ENDSEC;\nEND-ISO-10303-21;\n"


def wrap(body, schema='IFC4'):
    return (HEAD % schema) + body + TAIL


def units(n=1, prefix=None, name='METRE', kind='LENGTHUNIT'):
    p = '.%s.' % prefix if prefix else '$'
    return "#%d=IFCSIUNIT(*,.%s.,%s,.%s.);\n" % (n, kind, p, name)


def minimal(length_prefix=None, extra='', schema='IFC4', unit_name='METRE'):
    """ملفّ صالح صغير: وحدات ومشروع وموقع ومبنى ودور وفراغ."""
    b = units(1, length_prefix, unit_name)
    b += "#2=IFCSIUNIT(*,.PLANEANGLEUNIT.,$,.RADIAN.);\n"
    b += "#3=IFCUNITASSIGNMENT((#1,#2));\n"
    b += "#4=IFCCARTESIANPOINT((0.,0.,0.));\n"
    b += "#5=IFCDIRECTION((0.,0.,1.));\n"
    b += "#6=IFCDIRECTION((1.,0.,0.));\n"
    b += "#7=IFCAXIS2PLACEMENT3D(#4,#5,#6);\n"
    b += "#8=IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.E-05,#7,$);\n"
    b += "#9=IFCPROJECT('0aaaaaaaaaaaaaaaaaaaa1',$,'P',$,$,$,$,(#8),#3);\n"
    b += "#10=IFCLOCALPLACEMENT($,#7);\n"
    b += "#11=IFCSITE('0aaaaaaaaaaaaaaaaaaaa2',$,'S',$,$,#10,$,$,.ELEMENT.,$,$,$,$,$);\n"
    b += "#12=IFCLOCALPLACEMENT(#10,#7);\n"
    b += "#13=IFCBUILDING('0aaaaaaaaaaaaaaaaaaaa3',$,'B',$,$,#12,$,$,.ELEMENT.,$,$,$);\n"
    b += "#14=IFCLOCALPLACEMENT(#12,#7);\n"
    b += ("#15=IFCBUILDINGSTOREY('0aaaaaaaaaaaaaaaaaaaa4',$,'L0',$,$,#14,$,$,"
          ".ELEMENT.,0.);\n")
    b += "#16=IFCRELAGGREGATES('0aaaaaaaaaaaaaaaaaaaa5',$,$,$,#9,(#11));\n"
    b += "#17=IFCRELAGGREGATES('0aaaaaaaaaaaaaaaaaaaa6',$,$,$,#11,(#13));\n"
    b += "#18=IFCRELAGGREGATES('0aaaaaaaaaaaaaaaaaaaa7',$,$,$,#13,(#15));\n"
    return wrap(b + extra, schema)
