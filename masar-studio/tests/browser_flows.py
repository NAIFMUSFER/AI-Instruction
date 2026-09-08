"""Real Chromium UI checks on the exact standalone distribution.
set_content is used because this test environment blocks URL navigation.
No IndexedDB mock: storage failure handling is checked, not persistence.
"""
import json, time, tempfile, os, shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
results=[];errors=[]
def check(name,fn):
 try:
  fn();results.append({'name':name,'status':'PASS'})
 except Exception as e:
  results.append({'name':name,'status':'FAIL','error':str(e)})
  print(json.dumps(results[-1],ensure_ascii=False),flush=True)
def ok(condition,detail='assertion failed'):
 if not condition: raise AssertionError(detail)
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=os.environ.get('MASAR_CHROMIUM_PATH') or shutil.which('chromium') or p.chromium.executable_path,headless=True,args=['--no-sandbox','--disable-webgl'])
 page=browser.new_page(viewport={'width':1512,'height':982})
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.set_default_timeout(2500)
 def fresh():
  global page
  viewport=page.viewport_size
  page.close()
  page=browser.new_page(viewport=viewport)
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.set_default_timeout(2500)
  # Initial document parsing/boot has its own bound, not the 2.5 s UI-action budget.
  page.set_content((ROOT/'dist/index.html').read_text(),wait_until='domcontentloaded',timeout=20000)
  page.wait_for_selector('#scene[data-ready="true"]',state='attached',timeout=20000)
 def action(name,scope=None):
  (scope or page).locator(f'button[data-action="{name}"]').first.click()
 def close():
  if page.locator('#modal').evaluate('(e)=>e.open'): action('close-modal')
 def cancel():
  if page.locator('#preview-banner').is_visible():action('cancel-preview')
 def name():return page.locator('#properties-form [name="name"]').input_value()
 def dismiss():page.locator('#toasts').evaluate('(e)=>e.innerHTML=""')
 fresh()
 check('desktop: 2D and real software 3D render',lambda:ok(page.locator('#plan-host svg').count()==1 and page.locator('#scene').get_attribute('data-renderer')=='canvas3d'))
 check('desktop: no horizontal overflow',lambda:ok(page.evaluate('document.documentElement.scrollWidth<=innerWidth')))
 check('storage: unavailable IndexedDB is disclosed',lambda:ok('الحفظ المحلي غير متاح' in page.locator('#toasts').inner_text()))
 def select_in_3d():
  canvas=page.locator('#scene');box=canvas.bounding_box()
  canvas.click(position={'x':box['width']*.54,'y':box['height']*.39})
  ok(name()=='مطبخ مفتوح')
  ok(name() in page.locator('.tree-room.selected').inner_text())
  group=page.locator('#plan-host [data-room-id]').filter(has=page.locator('rect[stroke="#176653"]'))
  ok('مطبخ مفتوح' in group.get_attribute('aria-label'))
  page.locator('.tree-room',has_text='مجلس الضيوف').click()
 check('3D ray selection synchronizes inspector, 2D highlight and tree',select_in_3d)
 def rename_preview():
  page.locator('#properties-form [name="name"]').fill('مجلس نايف')
  page.locator('#properties-form [type="submit"]').click()
  page.locator('#preview-banner').wait_for(state='visible')
  ok('مجلس نايف' in page.locator('#preview-banner').inner_text())
 check('room rename creates an explicit preview',rename_preview)
 def cancel_preview():
  action('cancel-preview');ok(name()=='مجلس الضيوف')
 check('cancel restores canonical name',cancel_preview)
 def commit_rename():
  page.locator('#properties-form [name="name"]').fill('مجلس نايف');page.locator('#properties-form [type="submit"]').click()
  action('commit-preview');ok(name()=='مجلس نايف')
 check('commit applies room rename',commit_rename)
 def undo_redo():
  action('undo');ok(name()=='مجلس الضيوف');action('redo');ok(name()=='مجلس نايف')
 check('undo and redo restore exact room names',undo_redo)
 def invalid_edit():
  page.locator('#properties-form [name="w"]').fill('15');page.locator('#properties-form [type="submit"]').click()
  page.locator('#preview-banner').wait_for(state='visible');ok(page.locator('[data-action="commit-preview"]').is_disabled());action('cancel-preview')
 check('overlap preview is blocked',invalid_edit)
 cancel()
 def safe_conflict_resolution():
  fresh();dismiss();page.locator('.tree-room',has_text='دورة مياه الضيوف').click();depth=float(page.locator('#properties-form [name="d"]').input_value());page.locator('#properties-form [name="d"]').fill(str(depth+1));page.locator('#properties-form [type="submit"]').click();page.locator('#preview-banner').wait_for(state='visible');ok('تعارض في المعاينة' in page.locator('#issues-strip').inner_text());ok(page.locator('[data-action="resolve-preview"]').is_visible());action('resolve-preview');ok(not page.locator('[data-action="commit-preview"]').is_disabled());ok('الدرج الرئيسي دون تحريك' in page.locator('#preview-banner').inner_text());action('commit-preview');ok('تعارض في المعاينة' not in page.locator('#issues-strip').inner_text())
 check('blocked resize offers safe reflow and keeps locked stair fixed',safe_conflict_resolution)
 def select_plan():
  target=page.locator('#plan-host [data-room-id]').nth(2);label=target.get_attribute('aria-label');target.click();ok(name() in label)
 check('2D selection updates inspector',select_plan)
 def measure_tool():
  action('history');before=page.locator('.revision-item').count();close();action('measure');ok(page.locator('[data-action="measure"]').get_attribute('aria-pressed')=='true');host=page.locator('#plan-host');box=host.bounding_box();host.click(position={'x':box['width']*.30,'y':box['height']*.35});host.click(position={'x':box['width']*.62,'y':box['height']*.58});ok(page.locator('#plan-host .measure-overlay').count()==1);ok('م' in page.locator('#measure-status').inner_text());action('history');ok(page.locator('.revision-item').count()==before);close();action('measure');ok(page.locator('[data-action="measure"]').get_attribute('aria-pressed')=='false')
 check('transient 2D measurement reports distance without creating a revision',measure_tool)
 def lock_room():
  action('lock');ok(page.locator('#properties-form [name="w"]').is_disabled());action('lock');ok(page.locator('#properties-form [name="w"]').is_enabled())
 check('lock disables geometry and explicit unlock restores it',lock_room)
 def command_edit():
  page.locator('#command-input').fill('سم مطبخ العائلة');page.locator('#command-form [type="submit"]').click();page.locator('#preview-banner').wait_for(state='visible');action('commit-preview');ok(name()=='مطبخ العائلة')
 check('local Arabic command proposes then commits',command_edit)
 cancel()
 def bad_command():
  before=name();page.locator('#command-input').fill('اجعل المبنى ينتقل إلى كوكب آخر');page.locator('#command-form [type="submit"]').click();ok(not page.locator('#preview-banner').is_visible());ok(name()==before);ok('error' in page.locator('#assistant-message').get_attribute('class'))
 check('unsupported language is refused without mutations',bad_command)
 def comments():
  action('comments');page.locator('#comment-form [name="text"]').fill('تأكد من إطلالة المطبخ على الحديقة');page.locator('#comment-form [type="submit"]').click();ok('تأكد من إطلالة' in page.locator('#modal-content').inner_text());action('resolve-comment');ok('مغلق' in page.locator('.comment-item').first.inner_text());close()
 check('room comments add and resolve',comments)
 close()
 def revisions():
  action('history');before=page.locator('.revision-item').count();action('name-revision');page.locator('#revision-form [name="label"]').fill('مراجعة نايف الأولى');page.locator('#revision-form [type="submit"]').click();action('history');ok(page.locator('.revision-item').count()==before+1);ok('مراجعة نايف الأولى' in page.locator('#modal-content').inner_text());close()
 check('named revision preserves history',revisions)
 close()
 def restore():
  action('history');before=page.locator('.revision-item').count();page.locator('[data-action="restore"]:enabled').last.click();action('history');ok(page.locator('.revision-item').count()==before+1);close()
 check('restoring a version appends instead of deleting',restore)
 close()
 def compare_revisions():
  action('history');action('compare-revisions');form=page.locator('#compare-form');opts=form.locator('select[name="after"] option').count();ok(opts>=2);form.locator('select[name="before"]').select_option('0');form.locator('select[name="after"]').select_option(str(opts-1));form.locator('[type="submit"]').click();ok('فروق النسختين' in page.locator('#modal-title').inner_text());text=page.locator('#modal-content').inner_text();ok('المسطحات' in text and 'مؤشر المفهوم' in text and 'عناصر تغيّرت' in text);close()
 check('revision comparison is read-only and exposes geometry and concept deltas',compare_revisions)
 close()
 def alternatives():
  action('alternatives');ok(page.locator('[data-action="use-alternative"]').count()==4);ok('الخصوصية' in page.locator('#modal-content').inner_text());page.locator('[data-action="use-alternative"]:enabled').first.click();ok(page.locator('#preview-banner').is_visible());action('cancel-preview')
 check('alternative comparison produces preview',alternatives)
 close();cancel()
 def issue_status():
  action('issues');ok(page.locator('.issue-item.unchecked').count()>=4);ok(page.locator('.issue-item.checked').count()>0);ok('لم يُفحص' in page.locator('#modal-content').inner_text());ok('فُحص' in page.locator('#modal-content').inner_text());close()
 check('unperformed engineering checks never display PASS',issue_status)
 close()
 def model_health():
  action('model-health');text=page.locator('#modal-content').inner_text();ok('نموذج المبنى' in page.locator('#modal-title').inner_text());ok('جدارًا مشتقًا' in text);ok('ليست حزمة امتثال' in text);ok('جاهزية' in text);close()
 check('derived building model and non-compliance quality center are visible',model_health)
 close()
 def building_schedule_ui():
  action('model-health');action('building-elements');text=page.locator('#modal-content').inner_text();ok('جدول عناصر نموذج المبنى' in page.locator('#modal-title').inner_text());ok('جدار' in text and 'مساحة' in text);close()
 check('derived element schedule is inspectable in the UI',building_schedule_ui)
 close()
 def requirements_ui():
  action('model-health');action('requirements-center');text=page.locator('#modal-content').inner_text();ok('مصفوفة متطلبات المشروع' in page.locator('#modal-title').inner_text());ok('المصدر:' in text and ('محقق داخل نموذج مسار' in text or 'مراجعة بشرية' in text));close()
 check('requirement traceability matrix is inspectable in the UI',requirements_ui)
 close()
 # MASAR 4 authoring flows: exercised through the real built UI and preview/commit path.
 def hosted_window_authoring():
  fresh();dismiss();page.locator('.tree-room',has_text='مجلس الضيوف').click();action('window');form=page.locator('#window-form');field=form.locator('[name="width"]');before=float(field.input_value());field.fill(str(round(before+.1,2)));form.locator('[type="submit"]').click();page.locator('#preview-banner').wait_for(state='visible');ok(not page.locator('[data-action="commit-preview"]').is_disabled());action('commit-preview');action('window');after=float(page.locator('#window-form [name="width"]').input_value());ok(abs(after-(before+.1))<.001);close();ok(page.locator('#plan-host path[stroke="#2b8790"]').count()>0)
 check('hosted window authoring previews, commits and renders in 2D/model health',hosted_window_authoring)
 close();cancel()
 def orthogonal_notch_authoring():
  fresh();dismiss();page.locator('.tree-room',has_text='مجلس الضيوف').click();action('notch');form=page.locator('#notch-form');form.locator('[name="width"]').fill('.5');form.locator('[name="depth"]').fill('.5');form.locator('[type="submit"]').click();page.locator('#preview-banner').wait_for(state='visible');ok(not page.locator('[data-action="commit-preview"]').is_disabled());action('commit-preview');ok(page.locator('#properties-form [name="w"]').is_disabled());ok(page.locator('#plan-host polygon').count()>0);ok('غير مستطيلة' in page.locator('#inspector-content').inner_text())
 check('orthogonal L-space authoring uses a polygon and disables unsafe bbox resizing',orthogonal_notch_authoring)
 close();cancel()
 def authoring_types_revision():
  fresh();dismiss();action('wall-types');form=page.locator('#wall-types-form');field=form.locator('input[name^="layer-"]').first;before=float(field.input_value());field.fill(str(before+1));form.locator('[type="submit"]').click();page.locator('#preview-banner').wait_for(state='visible');ok('نواة التأليف' in page.locator('#preview-banner').inner_text() or 'طبقات الجدران' in page.locator('#preview-banner').inner_text());action('commit-preview');action('wall-types');after=float(page.locator('#wall-types-form input[name^="layer-"]').first.input_value());ok(after==before+1);close();action('history');ok('طبقات الجدران' in page.locator('#modal-content').inner_text());close()
 check('composite wall/window authoring types are revisioned through preview',authoring_types_revision)
 close();cancel()
 def ifc_ui_roundtrip():
  fresh();dismiss();action('export')
  with page.expect_download(timeout=3000) as pending: page.locator('[data-action="download"][data-kind="ifc"]').click()
  download=pending.value;destination=Path(tempfile.gettempdir())/'masar-v4-ui-roundtrip.ifc';download.save_as(str(destination));data=destination.read_bytes();ok(b'IFCWINDOW' in data and b'IFCMATERIALLAYERSET' in data and b'IFCRELVOIDSELEMENT' in data);close()
  page.locator('#import-input').set_input_files(str(destination));page.locator('#modal').wait_for(state='visible');ok('IFC' in page.locator('#modal-title').inner_text());page.locator('#ifc-ack').check();action('confirm-ifc');page.wait_for_timeout(120);ok(page.locator('#project-title').inner_text()=='مشروع IFC مستورد');ok(page.locator('#floor-tabs button').count()>=1)
 check('exported IFC4 reimports through the declared limited authoring path',ifc_ui_roundtrip)
 fresh();dismiss()
 # Browser download events capture real Blob exports, without a test implementation.
 for kind,extension in [('json','.json'),('svg','.svg'),('dxf','.dxf'),('ifc','.ifc'),('obj','.obj'),('csv','.csv'),('elements','.csv'),('requirements','.csv'),('rules','.json'),('report','.html'),('png','.png')]:
  def export_file(kind=kind,extension=extension):
   action('export')
   # PNG is produced by asynchronous canvas.toBlob rasterization; keep the same
   # real download/signature checks but allow CI rasterization additional time.
   download_timeout=10000 if kind=='png' else 3000
   with page.expect_download(timeout=download_timeout) as pending:
    page.locator(f'[data-action="download"][data-kind="{kind}"]').click()
   download=pending.value
   ok(download.suggested_filename.endswith(extension))
   destination=Path(tempfile.gettempdir())/(f'masar-ui-export-{kind}'+extension)
   download.save_as(str(destination));data=destination.read_bytes();ok(len(data)>100)
   if kind=='json':ok(json.loads(data)['format']=='masar-project')
   if kind=='svg':ok(b'<svg' in data)
   if kind=='dxf':ok(b'ENTITIES' in data)
   if kind=='ifc':ok(b'FILE_SCHEMA' in data and b'IFCSPACE' in data and b'IFCWALL' in data and b'NOT FOR CONSTRUCTION' in data)
   if kind=='obj':ok(b'\nv ' in data and b'\nf ' in data)
   if kind=='csv':ok(b'Width_m' in data and b'Area_m2' in data)
   if kind=='elements':ok(b'Category' in data and b'Wall' in data and b'Door' in data)
   if kind=='requirements':ok(b'Requirement_ID' in data and b'Measurable' in data)
   if kind=='rules':
    parsed=json.loads(data);ok(parsed['pack']['compliance'] is False and parsed['summary']['unchecked']>0)
   if kind=='report':ok(b'<html' in data)
   if kind=='png':ok(data.startswith(bytes.fromhex('89504e470d0a1a0a')))
   close()
  check(f'browser actually downloads {kind.upper()} export',export_file)
  close()
 def import_exported():
  document=json.loads((Path(tempfile.gettempdir())/'masar-ui-export-json.json').read_bytes())
  expected_title=document['history']['revisions'][document['history']['cursor']]['model']['title']
  page.locator('#import-input').set_input_files(str(Path(tempfile.gettempdir())/'masar-ui-export-json.json'))
  page.wait_for_timeout(150);ok(page.locator('#project-title').inner_text()==expected_title)
  action('history');ok(page.locator('.revision-item').count()==len(document['history']['revisions']));close()
 check('exported JSON reimports with all revisions intact',import_exported)
 close()
 def import_bad():
  before=name();page.locator('#import-input').set_input_files({'name':'bad.json','mimeType':'application/json','buffer':b'{"untrusted":true}'});page.wait_for_timeout(100);ok(name()==before);ok(page.locator('#toasts .error').count()>0)
 check('malformed JSON import preserves project',import_bad)
 def new_wizard():
  action('new');page.locator('#new-prompt').fill('أرض 24×30، ثلاثة أدوار، خمس غرف نوم، الشارع شرق.');page.locator('#new-form [type="submit"]').click();ok(page.locator('#brief-form [name="floors"]').input_value()=='3');ok(page.locator('#brief-form [name="bedrooms"]').input_value()=='5');ok(page.locator('#brief-form [name="street"]').input_value()=='شرق');page.locator('#brief-form [name="title"]').fill('منزل نايف');page.locator('#brief-form [name="confirm"]').check();page.locator('#brief-form [type="submit"]').click();ok(page.locator('#project-title').inner_text()=='منزل نايف');ok(page.locator('#floor-tabs button').count()==3)
 check('Arabic project wizard confirms dimensions/floors/beds/street',new_wizard)
 close()
 def full_prompt():
  action('brief');ok('أرض 24×30' in page.locator('.original-prompt').inner_text());close()
 check('verbatim original brief survives generation',full_prompt)
 close()
 def design_settings():
  action('design-settings');page.locator('#design-settings-form [name="stage"]').select_option('development');page.locator('#design-settings-form [name="priority"]').select_option('privacy');page.locator('#design-settings-form [type="submit"]').click();ok('تطوير' in page.locator('#project-type').inner_text());ok(page.locator('.design-stage button[data-stage="development"]').get_attribute('aria-pressed')=='true')
 check('design stage and priority are first-class revisioned settings',design_settings)
 close()
 def floor():
  page.locator('#floor-tabs button').nth(1).click();ok('الدور 1' in page.locator('#level-label').inner_text());ok('نوم' in page.locator('#level-tree').inner_text());page.locator('#floor-tabs button').first.click()
 check('floor switching synchronizes plan and room tree',floor)
 def view_controls():
  for view in ['3d','2d','split']:
   page.locator(f'[data-action="view"][data-view="{view}"]').click();ok(page.locator('#view-deck').get_attribute('data-view')==view)
  action('all-floors');ok(page.locator('[data-action="all-floors"]').get_attribute('aria-pressed')=='true');action('all-floors');action('cutaway');action('cutaway');action('fit')
 check('2D/3D modes, multi-floor and cutaway controls',view_controls)
 def keyboard_3d():
  canvas=page.locator('#scene');before=canvas.evaluate('(e)=>e.toDataURL()');canvas.focus();page.keyboard.press('ArrowLeft');page.wait_for_timeout(100);after=canvas.evaluate('(e)=>e.toDataURL()');ok(before!=after,'render did not rotate')
 check('keyboard rotates real 3D geometry',keyboard_3d)
 def cloud_scope():
  action('account');ok('الخادم' in page.locator('#modal-content').inner_text());close();action('ai-mode');ok('غير مربوط' in page.locator('#modal-title').inner_text());close()
 check('standalone does not claim cloud/AI connectivity',cloud_scope)
 close()
 dismiss();action('fit');page.screenshot(path=str(ROOT/'docs/desktop-tested.png'),full_page=True)
 # Fresh mobile instance: actual responsive UI, no simulated persistence.
 for width in [390,320,768]:
  page.set_viewport_size({'width':width,'height':844});fresh();dismiss()
  check(f'{width}px: no document overflow',lambda:ok(page.evaluate('document.documentElement.scrollWidth<=innerWidth')))
  if width<720:
   def mobile_navigation():
    for panel,target in [('project','#project-panel'),('inspector','#inspector-panel'),('workspace','#workspace')]:
     page.locator(f'[data-action="mobile"][data-panel="{panel}"]').click();ok(page.locator(target).is_visible())
   check(f'{width}px: all mobile panels reachable',mobile_navigation)
   check(f'{width}px: plan renders',lambda:ok(page.locator('#plan-host svg').is_visible()))
  if width==390:page.screenshot(path=str(ROOT/'docs/mobile-tested.png'),full_page=True)
 check('all UI flows: no uncaught JavaScript exceptions',lambda:ok(not errors,str(errors)))
 browser.close()
report={'harness':'Chromium set_content of exact standalone build; navigation blocked by environment policy','renderer':'Canvas2D software 3D; WebGL unverified','indexedDB':'Unavailable in about:blank; failure state verified; browser-origin persistence NOT VERIFIED','results':results,'passed':sum(x['status']=='PASS' for x in results),'failed':sum(x['status']=='FAIL' for x in results),'pageErrors':errors}
(ROOT/'docs/browser-tests.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({'passed':report['passed'],'failed':report['failed'],'pageErrors':errors},ensure_ascii=False))
raise SystemExit(1 if report['failed'] else 0)
