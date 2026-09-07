/**
 * MASAR Authoring Core metadata and hosted-opening helpers.
 * This module contains no rendering or compliance assumptions. Wall build-ups are
 * editable concept metadata and must be reviewed by project disciplines before use.
 */
export const AUTHORING_SCHEMA = 'masar-authoring-1';

export const DEFAULT_WALL_TYPES = Object.freeze([
  Object.freeze({
    id:'wall-ext-concept-240', name:'جدار خارجي مفاهيمي 240 مم', classification:'external', totalThickness:0.24,
    layers:Object.freeze([
      Object.freeze({id:'ext-finish',name:'تشطيب خارجي افتراضي',function:'finish',thickness:0.02,provenance:'display-assumption'}),
      Object.freeze({id:'ext-core',name:'طبقة أساسية غير مصممة',function:'core',thickness:0.20,provenance:'concept-assumption'}),
      Object.freeze({id:'int-finish',name:'تشطيب داخلي افتراضي',function:'finish',thickness:0.02,provenance:'display-assumption'})
    ]),
    provenance:'concept-type-not-engineering-spec'
  }),
  Object.freeze({
    id:'wall-int-concept-120', name:'جدار داخلي مفاهيمي 120 مم', classification:'internal', totalThickness:0.12,
    layers:Object.freeze([
      Object.freeze({id:'int-finish-a',name:'تشطيب داخلي افتراضي',function:'finish',thickness:0.015,provenance:'display-assumption'}),
      Object.freeze({id:'int-core',name:'طبقة أساسية غير مصممة',function:'core',thickness:0.09,provenance:'concept-assumption'}),
      Object.freeze({id:'int-finish-b',name:'تشطيب داخلي افتراضي',function:'finish',thickness:0.015,provenance:'display-assumption'})
    ]),
    provenance:'concept-type-not-engineering-spec'
  })
]);

export const DEFAULT_WINDOW_TYPES = Object.freeze([
  Object.freeze({id:'window-concept-1200',name:'نافذة مفاهيمية 1.20 م',width:1.2,height:1.2,sill:0.9,provenance:'concept-type-not-product-spec'}),
  Object.freeze({id:'window-concept-1800',name:'نافذة مفاهيمية 1.80 م',width:1.8,height:1.35,sill:0.75,provenance:'concept-type-not-product-spec'})
]);

const clone = v => structuredClone(v);
export function authoringDefaults() {
  return {
    schema:AUTHORING_SCHEMA,
    wallTypes:clone(DEFAULT_WALL_TYPES),
    windowTypes:clone(DEFAULT_WINDOW_TYPES),
    defaults:{externalWallTypeId:'wall-ext-concept-240',internalWallTypeId:'wall-int-concept-120',windowTypeId:'window-concept-1200'},
    disciplineStatus:{architecture:'concept-authoring',structure:'unchecked',mep:'unchecked',fire:'unchecked',accessibility:'unchecked',regulatory:'unchecked'},
    disclaimer:'Wall layers, windows and hosted openings are authoring metadata for coordination; they are not approved construction specifications.'
  };
}

export function effectiveAuthoring(model) {
  const base=authoringDefaults(), a=model?.authoring;
  if (!a) return base;
  return {
    ...base,...a,
    wallTypes:Array.isArray(a.wallTypes)&&a.wallTypes.length?a.wallTypes:base.wallTypes,
    windowTypes:Array.isArray(a.windowTypes)&&a.windowTypes.length?a.windowTypes:base.windowTypes,
    defaults:{...base.defaults,...(a.defaults||{})},
    disciplineStatus:{...base.disciplineStatus,...(a.disciplineStatus||{})}
  };
}

export function wallTypeFor(model, external) {
  const a=effectiveAuthoring(model), id=external?a.defaults.externalWallTypeId:a.defaults.internalWallTypeId;
  return a.wallTypes.find(t=>t.id===id) || a.wallTypes.find(t=>t.classification===(external?'external':'internal')) || a.wallTypes[0];
}

export function windowTypeFor(model, id) {
  const a=effectiveAuthoring(model), wanted=id||a.defaults.windowTypeId;
  return a.windowTypes.find(t=>t.id===wanted) || a.windowTypes[0];
}

export function openingPoint(room, opening) {
  const q=Number(opening.offset);
  return opening.side==='east'?[room.x+room.w,room.y+room.d*q]
    :opening.side==='west'?[room.x,room.y+room.d*q]
    :opening.side==='north'?[room.x+room.w*q,room.y+room.d]
    :[room.x+room.w*q,room.y];
}

export function sideSpan(room, side) { return ['east','west'].includes(side)?room.d:room.w; }
