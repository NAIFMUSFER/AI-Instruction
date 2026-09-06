"""C17: actual STEP spatial decomposition and imported storey membership."""
import copy
import re
import unittest
from test_ifc_profile_positions import project
import acs_authoring as A
import acs_bim as B


def two_levels():
    model=project()['model']
    model['levels'].append({'index':1,'template':'g','elevation':10.2})
    p=A.create_project(model); before=copy.deepcopy(p)
    result=B.export_ifc(p,generated_at='2026-09-06T00:00:00Z')
    assert result['valid'],result['issues']
    assert p==before
    return result['file'],B.parse_step(result['file'])['step']


def correctly_aggregated_fixture(text,step):
    """Build a standards-shaped external fixture, independent of writer relations."""
    spaces=[e for e in step['entities'].values() if e['type']=='IFCSPACE']
    storeys=[e for e in step['entities'].values() if e['type']=='IFCBUILDINGSTOREY']
    ids={e['id'] for e in spaces}
    for e in step['entities'].values():
        if e['type']=='IFCRELAGGREGATES' and any(r.n in ids for r in B._arg(e,5)):
            text=re.sub(r'#'+str(e['id'])+r'=.*?;\n','',text)
        if e['type']=='IFCRELCONTAINEDINSPATIALSTRUCTURE':
            remaining=[r.n for r in B._arg(e,4) if r.n not in ids]
            args="'%s',#%d,$,$,(%s),#%d" % (B._arg(e,0),B._arg(e,1).n,
                  ','.join('#%d'%n for n in remaining),B._arg(e,5).n)
            text=re.sub(r'#'+str(e['id'])+r'=.*?;', '#%d=IFCRELCONTAINEDINSPATIALSTRUCTURE(%s);'%(e['id'],args),text)
    n=max(step['entities'])+1; rows=[]
    expected={}
    for i,(space,storey) in enumerate(zip(spaces,storeys)):
        rows.append("#%d=IFCRELAGGREGATES('%s',#%d,$,$,#%d,(#%d));" %
                    (n+i,B.ifc_guid('audit:spatial:%d'%i),B._arg(space,1).n,storey['id'],space['id']))
        expected['#%d'%space['id']]=storey['id']
    text=text.replace('ENDSEC;\nEND-ISO-10303-21;','\n'.join(rows)+'\nENDSEC;\nEND-ISO-10303-21;')
    assert all(row in text for row in rows)
    return text,expected


class IfcSpatialAggregation(unittest.TestCase):
    def test_spaces_are_aggregated_to_each_storey_and_products_stay_contained(self):
        _,step=two_levels();ents=step['entities']
        spaces=[e for e in ents.values() if e['type']=='IFCSPACE'];self.assertEqual(len(spaces),2)
        spatial_parents={};contained={}
        for e in ents.values():
            if e['type']=='IFCRELAGGREGATES':
                for child in B._arg(e,5):spatial_parents.setdefault(child.n,[]).append(B._arg(e,4).n)
            if e['type']=='IFCRELCONTAINEDINSPATIALSTRUCTURE':
                for child in B._arg(e,4):contained[child.n]=B._arg(e,5).n
        for space in spaces:
            with self.subTest(space=space['id']):
                self.assertNotIn(space['id'],contained)
                parents=spatial_parents.get(space['id'],[]);self.assertEqual(len(parents),1)
                parent=ents[parents[0]];self.assertEqual(parent['type'],'IFCBUILDINGSTOREY')
                pl=B._deref(step,B._arg(space,5))
                self.assertEqual(B._arg(pl,0).n,B._arg(parent,5).n)
        walls=[e for e in ents.values() if e['type'] in ('IFCWALL','IFCWALLSTANDARDCASE')]
        self.assertEqual(len(walls),8)
        self.assertEqual(len([e for e in walls if e['id'] in contained]),8)

    def test_reader_resolves_correct_aggregation_to_both_explicit_elevations(self):
        text,step=two_levels();text,expected=correctly_aggregated_fixture(text,step)
        imported=B.stage_import(text);self.assertTrue(imported['valid'],imported['issues'])
        ents=imported['staging']['entities']
        levels={e['source_entity_id']:e for e in ents if e['canonical_kind']=='level'}
        spaces=[e for e in ents if e['canonical_kind']=='space'];self.assertEqual(len(spaces),2)
        for space in spaces:
            with self.subTest(space=space['source_entity_id']):
                ref='#%d'%expected[space['source_entity_id']]
                self.assertEqual(space['level_source_id'],ref)
                self.assertEqual(space['containment_basis'],'IFC_RELATIONSHIP')
                self.assertEqual(space['world']['xyz'][2],levels[ref]['geometry']['elevation'])
        self.assertEqual(sorted(e['geometry']['elevation'] for e in levels.values()),[7,10.2])


if __name__=='__main__':unittest.main(verbosity=2)
