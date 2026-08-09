/* يستخرج شيفرة المتصفّح من public/index.html إلى حزمة قابلة للتشغيل في Node.
   يعمل من أي مجلّد: كل المسارات تُحلّ نسبةً إلى جذر المستودع. */
const fs=require('fs'), path=require('path');
const ROOT=path.resolve(__dirname,'..','..','..');
const OUT=process.env.ACS_BUNDLE||path.join(require('os').tmpdir(),'acs_browser_bundle.js');
const src=fs.readFileSync(path.join(ROOT,'public','index.html'),'utf8').split('\n');
function grab(a,b){ return src.slice(a-1,b).join('\n'); }
function L(re){ for(let i=0;i<src.length;i++) if(re.test(src[i])) return i+1; throw new Error('not found '+re); }
const P=[];
P.push('var FLOOR_NAMES={};');
P.push(grab(L(/^const LAYER_NAMES=\{/), L(/^const FLOOR_NAMES=/)-1));   // طبقات العرض + ألوان الإنشائي و MEP
P.push(grab(L(/^const ROLE_COLOR=\{/), L(/^const LAYER_NAMES=\{/)-1));   // ترميز الأدوار + أنواع النقاط
P.push(grab(L(/^const OBJ_LIB = \{/), L(/^const OBJ_MAT = \{/)-1));
P.push(grab(L(/^const _AL='/), L(/^const _AR_KEYS=/)-1));
P.push(grab(L(/^const AR_NUM=\{/), L(/^const ROOM_KW=/)-1));         // AR_NUM+normDigits
P.push(grab(L(/^const ROOM_KW=/), L(/^\/\* توليد قياسي سريع/)-1));   // ROOM_KW..countNear..parseDescription
P.push(grab(L(/^const NEG_RE=/), L(/^function negatedAt/)+3));
P.push(grab(L(/^function normHex\(h\)\{/), L(/^const OBJ_LIB = \{/)-1));   // normHex..addBox..openU
P.push(grab(L(/^const OBJ_MAT = \{/), L(/^const _AL='/)-1));                        // OBJ_MAT
P.push(grab(L(/^const _AR_KEYS=/), L(/^\/\* ========================= محلّل الوصف العربي/)-1));  // بقية العارض + compile
P.push(grab(L(/^const OBJ_KIND_AR = \{/), L(/المرحلة 2 — أساس: طبقة المشروع/)-2)); // objectsFromText/stampMeta/objCoverage/attachObjects
function closeOf(st){for(let i=st;i<src.length;i++)if(src[i-1]==='}')return i;throw new Error('no close');}
P.push(grab(L(/^const ACS_PROJECT_SCHEMA=/), closeOf(L(/^function detectTypeJS/))));
P.push(grab(L(/^function showReport\(/), L(/^function esc\(s\)\{return String/)));
fs.writeFileSync(OUT, P.join('\n\n'));
console.log('browser bundle extracted ->', OUT);
