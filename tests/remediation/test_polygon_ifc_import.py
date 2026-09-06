"""C09f: preserve actual IFC profile boundaries and convert file units once."""
import re
import unittest
from test_polygon_ifc import exported
from test_polygon_gltf import model,L
import acs_bim as B
import acs_polygon as G


def staged(building):
    result,_=exported(building);parsed=B.stage_import(result['file'])
    assert parsed['valid'],parsed['issues']
    return parsed['staging']


def mm_rotated_space():
    """A valid external millimetre file with product yaw and a solid offset."""
    b=model([[1000*x-100000,1000*z+230000] for x,z in L])
    b['site']={'w':20000,'d':25000};b['wall_h']=3000;b['wall_t']=150
    b['floor_height']=3200;b['levels'][0]['elevation']=7000
    result,step=exported(b);text=result['file'].replace('.LENGTHUNIT.,$,.METRE.','.LENGTHUNIT.,.MILLI.,.METRE.')
    space=next(e for e in step['entities'].values() if e['type']=='IFCSPACE')
    placement=B._deref(step,B._arg(space,5))
    rep=B._deref(step,B._arg(space,6));shape=B._deref(step,B._arg(rep,2)[0]);solid=B._deref(step,B._arg(shape,3)[0])
    n=max(step['entities'])+1
    extra=[f'#{n}=IFCCARTESIANPOINT((-100000.,230000.,0.));',
           f'#{n+1}=IFCDIRECTION((0.,0.,1.));',f'#{n+2}=IFCDIRECTION((0.,1.,0.));',
           f'#{n+3}=IFCAXIS2PLACEMENT3D(#{n},#{n+1},#{n+2});',
           f'#{n+4}=IFCLOCALPLACEMENT(#{B._arg(placement,0).n},#{n+3});',
           f'#{n+5}=IFCCARTESIANPOINT((1000.,2000.,0.));',
           f'#{n+6}=IFCAXIS2PLACEMENT3D(#{n+5},$,$);']
    line=re.search(r'#'+str(space['id'])+r'=.*?;',text).group(0)
    text=text.replace(line,line.replace(',#%d,'%placement['id'],',#%d,'%(n+4),1))
    line=re.search(r'#'+str(solid['id'])+r'=.*?;',text).group(0)
    text=text.replace(line,line.replace(',#%d,'%B._arg(solid,1).n,',#%d,'%(n+6),1))
    text=text.replace('ENDSEC;\nEND-ISO-10303-21;','\n'.join(extra)+'\nENDSEC;\nEND-ISO-10303-21;')
    return text


class PolygonIfcImport(unittest.TestCase):
    def test_l_boundary_and_height_are_mapped_without_spurious_products(self):
        st=staged(model());spaces=[e for e in st['entities'] if e['canonical_kind']=='space']
        self.assertEqual(len(spaces),1);space=spaces[0]
        self.assertEqual(space['mapping_class'],'PARAMETRIC_MAPPED')
        self.assertEqual(space['geometry']['polygon'],L)
        self.assertEqual(space['geometry']['height'],3)
        self.assertEqual(space['geometry']['elevation'],7)
        self.assertIsNotNone(space['level_source_id'])
        self.assertFalse(any(e['entity_type']=='IFCARBITRARYCLOSEDPROFILEDEF' for e in st['entities']))

    def test_all_upper_slab_cells_and_the_core_hole_are_retained(self):
        b=model(objects=[{'kind':'stairs','core_id':'A','x':1,'z':3,'w':1,'d':1}])
        b['levels'].append({'index':1,'template':'plan','elevation':10.2})
        st=staged(b);slabs=[e for e in st['entities'] if e['canonical_kind']=='slab']
        self.assertEqual(len(slabs),2)
        geometries=sorted([e['geometry'] for e in slabs],key=lambda g:g.get('elevation',0))
        self.assertTrue(all(e['mapping_class']=='PARAMETRIC_MAPPED' for e in slabs))
        self.assertEqual([g['elevation'] for g in geometries],[7,10.2])
        self.assertEqual([sum(abs(G.signed_area(c)) for c in g['cells']) for g in geometries],[20,19])
        self.assertFalse(any(G.contains_point(c,[1,3]) for c in geometries[1]['cells']))

    def test_millimetres_product_yaw_and_solid_offset_are_composed_once(self):
        text=mm_rotated_space();result=B.stage_import(text);self.assertTrue(result['valid'],result['issues'])
        self.assertEqual(result['staging']['units']['length']['to_metre'],.001)
        space=next(e for e in result['staging']['entities'] if e['canonical_kind']=='space')
        self.assertEqual(space['mapping_class'],'PARAMETRIC_MAPPED')
        g=space['geometry'];expected=[[-102-z,231+x] for x,z in L]
        self.assertEqual(g['polygon'],expected)
        self.assertEqual([g[k] for k in ('x','z','w','d','height','elevation')],[-108,231,6,6,3,7])

    def test_tilted_polygon_stays_explicitly_outside_the_horizontal_mapping(self):
        text=mm_rotated_space().replace('IFCDIRECTION((0.,0.,1.))','IFCDIRECTION((0.,1.,0.))')
        result=B.stage_import(text);self.assertTrue(result['valid'],result['issues'])
        spaces=[e for e in result['staging']['entities'] if e['canonical_kind']=='space']
        self.assertEqual(len(spaces),1)
        self.assertEqual(spaces[0]['mapping_class'],'BOUNDING_GEOMETRY_ONLY')
        self.assertTrue(any(i['code']=='BIM_GEOMETRY_LOSS' for i in result['issues']))

    def test_non_reference_body_item_does_not_crash_the_reader(self):
        result,step=exported(model());text=result['file']
        space=next(e for e in step['entities'].values() if e['type']=='IFCSPACE')
        rep=B._deref(step,B._arg(space,6));shape=B._deref(step,B._arg(rep,2)[0])
        line=re.search(r'#'+str(shape['id'])+r'=.*?;',text).group(0)
        broken=re.sub(r',\(#[0-9]+\)\);$',',(5.));',line)
        self.assertNotEqual(broken,line)
        parsed=B.stage_import(text.replace(line,broken));self.assertTrue(parsed['valid'])
        staged_space=next(e for e in parsed['staging']['entities'] if e['canonical_kind']=='space')
        self.assertEqual(staged_space['mapping_class'],'BOUNDING_GEOMETRY_ONLY')


if __name__=='__main__':unittest.main(verbosity=2)
