# -*- coding: utf-8 -*-
"""بوّابة الرفع — «الخادم يثق بما يقوله العميل عن الملف».

هذا الملف يولّد الحمولات العدائية برمجياً (لا بايتات مُلتزَمة في المستودع)
ويثبت أن acs_upload_security يردّها بالرمز الصحيح. الأعطال المُغطّاة كما هي
في المسار القائم:

  1. /v1/understand/image يقرأ Content-Type من العميل، وإن لم يعجبه أعاد وسمه
     بصمت إلى "image/png" ثم رمّزه base64 وأرسله إلى واجهة الرؤية. أي ملف
     تنفيذي أو صفحة HTML مُسمّاة .png كانت تعبر البوّابة موسومة صورةً سليمة.
  2. لا فحص أبعاد ولا فكّ ترميز: ملف PNG رأسه يعلن 25000×25000 وحجمه بضعة
     كيلوبايت كان يمرّ (قنبلة انضغاط).
  3. /v1/understand/pdf يكتب البايتات إلى tempfile.mkstemp ثم يمرّر **مساراً**،
     بلا توقيع %PDF- ولا سقف صفحات ولا معالجة تشفير، ويطبع اسم الملف الخام
     في السجلّ (حقن سطور).
  4. JSON و DXF بلا أي حارس على الحجم أو العمق أو المفاتيح.

القاعدة المصحَّحة: النوع من البصمة الثنائية وحدها، والتعارض يُعلن ولا يُخفى،
والصورة تُعاد ترميزها من البكسلات فقط، وكل شيء في الذاكرة بلا ملف مؤقت واحد.
"""
import copy
import importlib
import io
import json
import logging
import os
import struct
import sys
import tempfile
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, ROOT)

from PIL import Image                                             # noqa: E402
from PIL.PngImagePlugin import PngInfo                            # noqa: E402
import pypdf                                                      # noqa: E402

import acs_upload_security as S                                   # noqa: E402

# pypdf يشكو بصوت عالٍ من الملفات المبتورة — وهذا بالضبط ما نُغذّيه عمداً.
logging.getLogger('pypdf').setLevel(logging.CRITICAL)
logging.getLogger('pypdf._reader').setLevel(logging.CRITICAL)

# ---------------------------------------------------------------- preflight --
_REQUIRED = ('SPEC', 'UploadRejected', 'sniff', 'safe_filename_label',
             'validate_image', 'validate_images', 'validate_pdf',
             'validate_json_bytes', 'validate_dxf_bytes', 'health_status',
             'ACS_UPLOAD_MAX_IMAGE_BYTES', 'ACS_UPLOAD_MAX_IMAGE_PIXELS',
             'ACS_UPLOAD_MAX_IMAGE_SIDE', 'ACS_UPLOAD_MAX_IMAGES',
             'ACS_UPLOAD_MAX_PDF_BYTES', 'ACS_UPLOAD_MAX_PDF_PAGES',
             'ACS_UPLOAD_MAX_PDF_TEXT_CHARS', 'ACS_UPLOAD_MAX_JSON_BYTES',
             'ACS_UPLOAD_MAX_JSON_DEPTH', 'ACS_UPLOAD_MAX_JSON_KEYS',
             'ACS_UPLOAD_MAX_DXF_BYTES',
             'ACS_UPLOAD_MAX_IMAGE_DECODED_BYTES', '_decoded_bytes',    # F-22
             'ACS_UPLOAD_MAX_PDF_DECOMPRESSED_BYTES', '_flate_expansion')  # F-23
_missing = [s for s in _REQUIRED if not hasattr(S, s)]
if _missing:
    print('UPLOAD SECURITY: CANNOT RUN — PARTIALLY MERGED TREE')
    print('  acs_upload_security.py is missing: %s' % ', '.join(_missing))
    sys.exit(1)

p = [0]
f = [0]


def chk(name, cond, detail=''):
    if cond:
        p[0] += 1
        print('  ✓ %s' % name)
    else:
        f[0] += 1
        print('  ✗ %s %s' % (name, detail))


# ------------------------------------------------ مراقبة الملفات المؤقتة --
TMPROOT = tempfile.gettempdir()
FIXTURES = tempfile.mkdtemp(prefix='acs_upload_fixtures_')   # قبل أي لقطة


def _tmp_snapshot():
    try:
        return set(os.listdir(TMPROOT))
    except OSError:
        return set()


def expect_reject(name, code, fn, *args, **kw):
    """يشغّل الحمولة العدائية ويثبت: الرمز الصحيح، لا استثناء آخر، ولا ملف مؤقت."""
    before = _tmp_snapshot()
    try:
        result = fn(*args, **kw)
    except S.UploadRejected as exc:
        leaked = _tmp_snapshot() - before
        chk(name, exc.code == code and not leaked,
            'code=%s expected=%s leaked=%s' % (exc.code, code, sorted(leaked)))
        chk('%s — الرسالة عربية قابلة للتنفيذ والتفصيل تقني آمن' % name,
            bool(exc.message_ar.strip()) and bool(exc.detail.strip())
            and any('؀' <= ch <= 'ۿ' for ch in exc.message_ar),
            'message_ar=%r' % exc.message_ar[:40])
        return exc
    except Exception as exc:                       # noqa: BLE001 — هذا هو العطل
        f[0] += 1
        print('  ✗ %s — تسرّب استثناء غير UploadRejected: %s: %s'
              % (name, type(exc).__name__, exc))
        f[0] += 1
        print('  ✗ %s — الرسالة عربية قابلة للتنفيذ (لم تُصدر أصلاً)' % name)
        return None
    leaked = _tmp_snapshot() - before
    f[0] += 1
    print('  ✗ %s — قُبلت الحمولة العدائية بدل رفضها (%s) leaked=%s'
          % (name, code, sorted(leaked)))
    f[0] += 1
    print('  ✗ %s — الرسالة عربية قابلة للتنفيذ (لم تُصدر أصلاً)' % name)
    return result


def expect_ok(name, fn, *args, **kw):
    """يشغّل حمولة سليمة ويثبت أنها تمرّ بلا استثناء وبلا ملف مؤقت."""
    before = _tmp_snapshot()
    try:
        result = fn(*args, **kw)
    except Exception as exc:                       # noqa: BLE001
        f[0] += 1
        print('  ✗ %s — رُفضت حمولة سليمة: %s: %s'
              % (name, type(exc).__name__, exc))
        return None
    leaked = _tmp_snapshot() - before
    chk(name, not leaked, 'leaked=%s' % sorted(leaked))
    return result


def patched(**limits):
    """يبدّل الحدود المُعلَنة مؤقتاً لإثبات الحارس بسرعة وبلا حمولات ضخمة."""
    saved = {k: getattr(S, k) for k in limits}
    for k, v in limits.items():
        setattr(S, k, v)
    return saved


def restore(saved):
    for k, v in saved.items():
        setattr(S, k, v)


# ------------------------------------------------------ توليد الحمولات --
def png_bytes(w, h, color=(30, 60, 90), mode='RGB'):
    buf = io.BytesIO()
    Image.new(mode, (w, h), color if mode == 'RGB' else 200).save(
        buf, format='PNG')
    return buf.getvalue()


def noisy_png(w, h):
    """PNG بضجيج حقيقي — لا ينضغط، فيثبت سقف البايتات بلا حمولة عملاقة."""
    img = Image.frombytes('RGB', (w, h), os.urandom(w * h * 3))
    buf = io.BytesIO()
    img.save(buf, format='PNG', compress_level=0)
    return buf.getvalue()


def jpeg_bytes(w, h, exif=None):
    buf = io.BytesIO()
    img = Image.new('RGB', (w, h), (200, 40, 40))
    for x in range(0, w, 4):                       # محتوى غير مسطّح: ملف حقيقي
        for y in range(0, h, 4):
            img.putpixel((x, y), (10, 220, 10))
    if exif is not None:
        img.save(buf, format='JPEG', quality=92, exif=exif)
    else:
        img.save(buf, format='JPEG', quality=92)
    return buf.getvalue()


def webp_bytes(w, h):
    buf = io.BytesIO()
    Image.new('RGB', (w, h), (12, 200, 120)).save(buf, format='WEBP')
    return buf.getvalue()


def gif_bytes(w, h):
    buf = io.BytesIO()
    Image.new('P', (w, h)).save(buf, format='GIF')
    return buf.getvalue()


def png_declaring_size(w, h):
    """PNG رأسه صحيح تماماً ويعلن أبعاداً هائلة — شكل قنبلة الانضغاط بالضبط."""
    def chunk(tag, body):
        return (struct.pack('>I', len(body)) + tag + body
                + struct.pack('>I', zlib.crc32(tag + body) & 0xffffffff))
    ihdr = struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr)
            + chunk(b'IDAT', zlib.compress(b'\x00' * 4096))
            + chunk(b'IEND', b''))


def pe_stub():
    """جذع تنفيذي ويندوز (MZ ... PE\\0\\0) مُسمّى plan.png."""
    dos = bytearray(b'MZ' + b'\x90\x00' * 29)
    dos += struct.pack('<I', 0x80)
    body = bytes(dos).ljust(0x80, b'\x00')
    return body + b'PE\x00\x00' + b'\x4c\x01' + b'\x00' * 240


def html_doc():
    return (b'<!DOCTYPE html>\n<html><head><title>plan</title></head>'
            b'<body><script>fetch("https://evil.example/x")</script>'
            b'</body></html>\n')


def make_pdf(page_texts):
    """مولّد PDF نصّي أدنى مع جدول xref صحيح — بلا اعتماد على مكتبة توليد."""
    objects = []                                   # 1-based

    def add(body):
        objects.append(body)
        return len(objects)

    catalog_num = add(b'')                          # 1 — يُملأ لاحقاً
    pages_num = add(b'')                            # 2 — يُملأ لاحقاً
    font_num = add(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')
    kids = []
    for text in page_texts:
        safe = text.replace('\\', '').replace('(', '').replace(')', '')
        stream = ('BT /F1 18 Tf 60 700 Td (%s) Tj ET' % safe).encode('ascii')
        content_num = add(b'<< /Length ' + str(len(stream)).encode('ascii')
                          + b' >>\nstream\n' + stream + b'\nendstream')
        page_num = add(
            b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] '
            b'/Resources << /Font << /F1 ' + str(font_num).encode('ascii')
            + b' 0 R >> >> /Contents ' + str(content_num).encode('ascii')
            + b' 0 R >>')
        kids.append(page_num)
    objects[catalog_num - 1] = b'<< /Type /Catalog /Pages 2 0 R >>'
    objects[pages_num - 1] = (
        b'<< /Type /Pages /Kids ['
        + b' '.join(b'%d 0 R' % k for k in kids)
        + b'] /Count ' + str(len(kids)).encode('ascii') + b' >>')

    out = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
    offsets = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b'%d 0 obj\n' % i + body + b'\nendobj\n'
    xref_at = len(out)
    out += b'xref\n0 %d\n' % (len(objects) + 1)
    out += b'0000000000 65535 f \n'
    for off in offsets:
        out += b'%010d 00000 n \n' % off
    out += (b'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n'
            % (len(objects) + 1, xref_at))
    return bytes(out)


def encrypted_pdf():
    """PDF مشفّر فعلياً عبر pypdf، مع بديل يدوي إن عجزت النسخة عن التشفير."""
    try:
        reader = pypdf.PdfReader(io.BytesIO(make_pdf(['SECRET PLAN'])))
        writer = pypdf.PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        writer.encrypt(user_password='correct-horse',
                       owner_password='owner-horse')
        buf = io.BytesIO()
        writer.write(buf)
        return buf.getvalue(), 'pypdf'
    except Exception:
        raw = make_pdf(['SECRET PLAN'])
        return raw.replace(b'/Root 1 0 R',
                           b'/Root 1 0 R /Encrypt << /Filter /Standard /V 1 '
                           b'/R 2 /O <00> /U <00> /P -1 >>'), 'handmade'


def dxf_text(sections=('HEADER', 'ENTITIES')):
    lines = ['999', 'ACS test fixture']
    for name in sections:
        lines += ['  0', 'SECTION', '  2', name, '  0', 'ENDSEC']
    lines += ['  0', 'EOF']
    return ('\r\n'.join(lines) + '\r\n').encode('utf-8')


def keep(name, data):
    """يكتب الحمولة داخل مجلّد مؤقت خاص — لإثبات أن الوحدة لا تلمس القرص."""
    path = os.path.join(FIXTURES, name)
    with open(path, 'wb') as fh:
        fh.write(data)
    return path


# =============================================================================
print('\n== A · البصمة الثنائية تحلّ محلّ ثقة العميل ==')
CASES = (
    ('png', png_bytes(8, 8)),
    ('jpeg', jpeg_bytes(16, 16)),
    ('webp', webp_bytes(8, 8)),
    ('gif', gif_bytes(8, 8)),
    ('pdf', make_pdf(['A'])),
    ('zip', b'PK\x03\x04' + b'\x00' * 64),
    ('elf', b'\x7fELF' + b'\x02\x01\x01' + b'\x00' * 64),
    ('pe', pe_stub()),
    ('html', html_doc()),
    ('json', json.dumps({'a': [1, 2, 3]}).encode('utf-8')),
    ('dxf', dxf_text()),
    ('unknown', b'\x00\x01\x02\x03 not a known container at all'),
)
for expected, blob in CASES:
    got = S.sniff(blob)
    chk('sniff يتعرّف على %s من محتواه لا من امتداده' % expected,
        got == expected, 'got=%s' % got)
chk('sniff لا ينهار على بايتات فارغة أو نوع غريب',
    S.sniff(b'') == 'unknown' and S.sniff(None) == 'unknown'
    and S.sniff(bytearray(b'\x89PNG\r\n\x1a\n')) == 'png')
chk('امتداد .png وحده لا يجعل الملف صورة (نفس بايتات PE)',
    S.sniff(pe_stub()) == 'pe')

print('\n== B · اسم الملف وسمٌ للسجلّ لا مسارٌ على القرص ==')
LABELS = (
    ('../../etc/passwd', 'passwd'),
    ('..\\..\\windows\\system32\\cmd.exe', 'cmd.exe'),
    ('/etc/shadow', 'shadow'),
    ('..', 'unnamed'),
    ('', 'unnamed'),
    (None, 'unnamed'),
    ('   ', 'unnamed'),
)
for raw, expected in LABELS:
    got = S.safe_filename_label(raw)
    chk('اجتياز المسار %r يصير %r' % (raw, expected), got == expected,
        'got=%r' % got)
inj = S.safe_filename_label('plan.png\nACS] FAKE LOG LINE: admin logged in\r\n')
chk('حقن السجلّ يفقد كل CR/LF ومحارف التحكّم',
    '\n' not in inj and '\r' not in inj and all(ord(c) >= 32 for c in inj),
    'got=%r' % inj)
long_label = S.safe_filename_label('x' * 500 + '.png')
chk('الوسم يُقصّ إلى 64 محرفاً', len(long_label) <= 64,
    'len=%d' % len(long_label))
weird = S.safe_filename_label('مخطط;rm -rf /;$(whoami)`id`.png')
chk('المحارف الصدفية والوحدوية تُستبدل بمجموعة متحفّظة',
    all(c in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        '0123456789._- ' for c in weird) and '/' not in weird,
    'got=%r' % weird)
chk('الوسم لا يُعيد أبداً فاصل مسار مهما كان الدخل',
    all('/' not in S.safe_filename_label(x) and '\\' not in
        S.safe_filename_label(x)
        for x in ('a/b/c', 'a\\b\\c', '....//....//etc/passwd', '\x00/x')))

print('\n== C · الحمولات العدائية المُقنَّعة كصور ==')
keep('plan.png', pe_stub())
expect_reject('ملف تنفيذي ويندوز مُسمّى plan.png يُرفض',
              'IMAGE_TYPE_NOT_ALLOWED', S.validate_image, pe_stub(),
              'image/png')
keep('plan2.png', html_doc())
expect_reject('صفحة HTML مُسمّاة plan.png تُرفض (كانت تُعاد وسمها image/png)',
              'IMAGE_TYPE_NOT_ALLOWED', S.validate_image, html_doc(),
              'image/png')
expect_reject('أرشيف ZIP مُسمّى صورة يُرفض', 'IMAGE_TYPE_NOT_ALLOWED',
              S.validate_image, b'PK\x03\x04' + b'\x00' * 128, 'image/png')
expect_reject('ملف ELF تنفيذي يُرفض', 'IMAGE_TYPE_NOT_ALLOWED',
              S.validate_image, b'\x7fELF' + b'\x02\x01\x01' + b'\x00' * 128,
              'image/jpeg')
expect_reject('GIF يُرفض صراحةً لأنه صيغة متحرّكة', 'IMAGE_TYPE_NOT_ALLOWED',
              S.validate_image, gif_bytes(8, 8), 'image/gif')
gif_rej = None
try:
    S.validate_image(gif_bytes(8, 8), 'image/gif')
except S.UploadRejected as exc:
    gif_rej = exc
chk('رسالة GIF تشرح أن الصيغة المتحرّكة غير مدعومة وتقترح البديل',
    gif_rej is not None and 'متحرّكة' in gif_rej.message_ar
    and ('PNG' in gif_rej.message_ar or 'JPEG' in gif_rej.message_ar),
    'msg=%r' % (gif_rej.message_ar if gif_rej else None))
expect_reject('PNG سليم مُعلَن image/jpeg يُرفض ولا يُعاد وسمه بصمت',
              'IMAGE_TYPE_MISMATCH', S.validate_image, png_bytes(8, 8),
              'image/jpeg')
expect_reject('JPEG سليم مُعلَن image/webp يُرفض', 'IMAGE_TYPE_MISMATCH',
              S.validate_image, jpeg_bytes(16, 16), 'image/webp')
expect_reject('نوع مُعلَن ليس صورة أصلاً يُرفض', 'IMAGE_TYPE_MISMATCH',
              S.validate_image, png_bytes(8, 8), 'application/pdf')
chk('النوع المُعلَن image/jpg (خطأ شائع) يُقبل لصورة JPEG حقيقية',
    S.validate_image(jpeg_bytes(16, 16),
                     'image/jpg; charset=binary')['sniffed'] == 'jpeg')
expect_reject('ملف فارغ يُرفض بلا انهيار', 'EMPTY_UPLOAD',
              S.validate_image, b'', 'image/png')
expect_reject('حمولة ليست bytes تُرفض بلا انهيار', 'EMPTY_UPLOAD',
              S.validate_image, '/etc/passwd', 'image/png')

print('\n== D · الحجم والأبعاد وقنبلة الانضغاط ==')
saved = patched(ACS_UPLOAD_MAX_IMAGE_BYTES=1024)
expect_reject('صورة أكبر من سقف البايتات تُرفض', 'IMAGE_TOO_LARGE',
              S.validate_image, noisy_png(200, 200), 'image/png')
restore(saved)
saved = patched(ACS_UPLOAD_MAX_IMAGE_PIXELS=64)
expect_reject('الحارس يعمل بحدود مُخفَّضة على صورة صغيرة حقيقية',
              'IMAGE_TOO_MANY_PIXELS', S.validate_image, png_bytes(64, 64),
              'image/png')
restore(saved)
bomb = png_declaring_size(25000, 25000)
keep('bomb.png', bomb)
chk('قنبلة الانضغاط صغيرة على القرص (%d بايت) وضخمة عند فكّ الترميز'
    % len(bomb), len(bomb) < 64 * 1024)
expect_reject('PNG يعلن 25000×25000 يُرفض قبل فكّ الترميز',
              'IMAGE_TOO_MANY_PIXELS', S.validate_image, bomb, 'image/png')
wide = png_bytes(13000, 40, mode='L')
keep('wide.png', wide)
chk('PNG عريض حقيقي 13000×40 مضغوط في %d بايت' % len(wide),
    len(wide) < 200 * 1024)
expect_reject('ضلع أطول من الحدّ يُرفض بالحدود الحقيقية غير المُعدَّلة',
              'IMAGE_SIDE_TOO_LARGE', S.validate_image, wide, 'image/png')

print('\n== E · الصور التالفة والمبتورة ==')
whole = jpeg_bytes(64, 64)
truncated = whole[:len(whole) // 2]
keep('truncated.jpg', truncated)
chk('البايتات المبتورة ما زالت تُشمّ jpeg (التوقيع سليم — العطل أعمق)',
    S.sniff(truncated) == 'jpeg')
expect_reject('JPEG مبتور يُرفض عند التحميل الفعلي لا عند قراءة الرأس',
              'IMAGE_CORRUPT', S.validate_image, truncated, 'image/jpeg')
expect_reject('PNG برأس صحيح وبيانات مهشّمة يُرفض', 'IMAGE_CORRUPT',
              S.validate_image,
              png_bytes(32, 32)[:40] + b'\xde\xad\xbe\xef' * 16, 'image/png')
expect_reject('توقيع PNG وحده بلا محتوى يُرفض', 'IMAGE_CORRUPT',
              S.validate_image, b'\x89PNG\r\n\x1a\n' + b'\x00' * 8,
              'image/png')

print('\n== F · إعادة الترميز تُسقط كل البيانات الوصفية ==')
meta = PngInfo()
meta.add_text('Software', 'ACS test rig')
meta.add_text('Comment', 'CONFIDENTIAL: internal site coordinates')
meta.add_text('acs_secret', 'do-not-forward-to-the-vision-api')
exif = Image.Exif()
exif[274] = 6                                       # Orientation = تدوير 90°
exif[271] = 'ACSCam'
buf = io.BytesIO()
Image.new('RGB', (24, 12), (9, 9, 200)).save(
    buf, format='PNG', pnginfo=meta, exif=exif.tobytes())
png_meta = buf.getvalue()
keep('meta.png', png_meta)
chk('حمولة الاختبار تحمل فعلاً مقاطع وصفية قبل التنقية',
    b'acs_secret' in png_meta and b'do-not-forward' in png_meta)
res = expect_ok('PNG بمقاطع وصفية يمرّ ويُعاد ترميزه',
                S.validate_image, png_meta, 'image/png')
if res:
    norm = res['normalized']
    reopened = Image.open(io.BytesIO(norm))
    reopened.load()
    chk('البايتات المُنقّاة تُفتح نظيفة وتُحمَّل بلا خطأ',
        reopened.size == (res['width'], res['height']))
    chk('النصّ السرّي لم يعد موجوداً في البايتات المُمرَّرة',
        b'acs_secret' not in norm and b'do-not-forward' not in norm
        and b'CONFIDENTIAL' not in norm and b'ACSCam' not in norm)
    chk('لا EXIF ولا مقاطع نصّية في الصورة المُنقّاة',
        len(dict(reopened.getexif())) == 0
        and not any(k in reopened.info for k in
                    ('Software', 'Comment', 'acs_secret', 'exif',
                     'icc_profile')),
        'info=%s' % sorted(reopened.info))
    chk('تدوير EXIF طُبّق ثم أُسقط: 24×12 صارت 12×24',
        (res['width'], res['height']) == (12, 24),
        'got=%dx%d' % (res['width'], res['height']))
    chk('نوع الوسيط المُعاد مستنتج لا مُعلَن',
        res['media_type'] == 'image/png' and res['sniffed'] == 'png'
        and res['bytes'] == len(png_meta))

jpg_meta = jpeg_bytes(32, 16, exif=exif.tobytes())
res = expect_ok('JPEG بـ EXIF يمرّ ويُعاد ترميزه',
                S.validate_image, jpg_meta, 'image/jpeg')
if res:
    reopened = Image.open(io.BytesIO(res['normalized']))
    reopened.load()
    chk('JPEG المُنقّى بلا EXIF وبأبعاد مصحّحة الدوران',
        len(dict(reopened.getexif())) == 0
        and (res['width'], res['height']) == (16, 32)
        and reopened.format == 'JPEG',
        'got=%dx%d exif=%d' % (res['width'], res['height'],
                               len(dict(reopened.getexif()))))
res = expect_ok('WEBP سليم يمرّ ويُعاد ترميزه WEBP',
                S.validate_image, webp_bytes(20, 10), 'image/webp')
if res:
    reopened = Image.open(io.BytesIO(res['normalized']))
    reopened.load()
    chk('WEBP المُنقّى يُفتح WEBP بالأبعاد نفسها',
        reopened.format == 'WEBP' and reopened.size == (20, 10))
res = expect_ok('PNG بلا نوع مُعلَن إطلاقاً يمرّ بالاستنتاج وحده',
                S.validate_image, png_bytes(10, 10))
chk('غياب Content-Type لا يمنع القبول ولا يُخترع نوع خاطئ',
    res is not None and res['media_type'] == 'image/png')

print('\n== G · الدفعة: سقف العدد وميزانية البكسلات ==')
one = png_bytes(10, 10)
batch = expect_ok('دفعة من ٣ صور سليمة تمرّ', S.validate_images,
                  [(one, 'image/png'), one, {'data': one,
                                             'content_type': 'image/png'}])
chk('الدفعة تعيد نتيجة لكل صورة بترتيبها',
    batch is not None and len(batch) == 3
    and [b['index'] for b in batch] == [0, 1, 2])
expect_reject('عدد صور أكبر من الحدّ يُرفض ولا يُقصّ بصمت (كان files[:6])',
              'TOO_MANY_FILES', S.validate_images, [one] * 7)
big_batch = [one] * 7
before_len = len(big_batch)
try:
    S.validate_images(big_batch)
except S.UploadRejected:
    pass
chk('قائمة الدخل نفسها لم تُعدَّل ولم تُقصّ', len(big_batch) == before_len)
saved = patched(ACS_UPLOAD_MAX_IMAGE_PIXELS=250)
expect_reject('ميزانية البكسلات المشتركة عبر الدفعة تُطبَّق',
              'IMAGE_PIXEL_BUDGET_EXCEEDED', S.validate_images,
              [one, one, one])
restore(saved)
expect_reject('دفعة فارغة تُرفض بلا انهيار', 'EMPTY_UPLOAD',
              S.validate_images, [])
expect_reject('صورة عدائية داخل دفعة سليمة تُسقط الدفعة كلها',
              'IMAGE_TYPE_NOT_ALLOWED', S.validate_images,
              [one, (pe_stub(), 'image/png'), one])
rej = None
try:
    S.validate_images([one, (pe_stub(), 'image/png')])
except S.UploadRejected as exc:
    rej = exc
chk('التفصيل يذكر ترتيب الصورة لا اسمها ولا بايتاتها',
    rej is not None and 'image #2' in rej.detail
    and 'MZ' not in rej.detail, 'detail=%r' % (rej.detail if rej else None))

print('\n== H · PDF: توقيع، تشفير، سقف صفحات، ولا ملف مؤقت ==')
good_pdf = make_pdf(['GROUND FLOOR PLAN AREA 240',
                     'FIRST FLOOR PLAN AREA 210',
                     'ROOF PLAN'])
keep('good.pdf', good_pdf)
res = expect_ok('PDF من ثلاث صفحات يُقرأ ويُستخرج نصّه',
                S.validate_pdf, good_pdf)
chk('عدد الصفحات والنصّ صحيحان وعلَم البتر مطفأ',
    res is not None and res['pages'] == 3
    and 'GROUND FLOOR PLAN' in res['text']
    and 'ROOF PLAN' in res['text'] and res['truncated'] is False,
    'res=%s' % (None if res is None else
                {'pages': res['pages'], 'chars': len(res['text'])}))
chk('حجم البايتات المُبلَّغ يطابق المرفوع',
    res is not None and res['bytes'] == len(good_pdf))

bad_sig = b'GIF89a' + good_pdf[6:]
keep('badsig.pdf', bad_sig)
expect_reject('ملف بلا توقيع %PDF- يُرفض', 'PDF_BAD_SIGNATURE',
              S.validate_pdf, bad_sig)
expect_reject('صفحة HTML مُسمّاة .pdf تُرفض', 'PDF_BAD_SIGNATURE',
              S.validate_pdf, html_doc())
expect_reject('ملف تنفيذي مُسمّى .pdf يُرفض', 'PDF_BAD_SIGNATURE',
              S.validate_pdf, pe_stub())
expect_reject('توقيع PDF متأخّر بعد 1024 بايت لا يُقبل', 'PDF_BAD_SIGNATURE',
              S.validate_pdf, b'A' * 2048 + good_pdf)
expect_reject('ملف PDF فارغ يُرفض', 'EMPTY_UPLOAD', S.validate_pdf, b'')
expect_reject('مسار نصّي بدل بايتات يُرفض (الوحدة لا تقبل مساراً أبداً)',
              'EMPTY_UPLOAD', S.validate_pdf, os.path.join(FIXTURES,
                                                           'good.pdf'))

trunc_pdf = good_pdf[:120]
keep('truncated.pdf', trunc_pdf)
expect_reject('PDF مبتور يُترجم إلى PDF_UNREADABLE لا إلى خطأ 500',
              'PDF_UNREADABLE', S.validate_pdf, trunc_pdf)
expect_reject('توقيع PDF على قمامة يُترجم إلى PDF_UNREADABLE',
              'PDF_UNREADABLE', S.validate_pdf,
              b'%PDF-1.7\n' + os.urandom(0) + b'\xff' * 900)

enc_pdf, enc_how = encrypted_pdf()
keep('encrypted.pdf', enc_pdf)
before = _tmp_snapshot()
enc_code = None
enc_other = None
try:
    S.validate_pdf(enc_pdf)
except S.UploadRejected as exc:
    enc_code = exc.code
except Exception as exc:                            # noqa: BLE001
    enc_other = '%s: %s' % (type(exc).__name__, exc)
chk('PDF مشفّر (%s) يُرفض بـ PDF_ENCRYPTED أو PDF_UNREADABLE ولا يتسرّب خطأ'
    % enc_how,
    enc_code in ('PDF_ENCRYPTED', 'PDF_UNREADABLE') and enc_other is None
    and not (_tmp_snapshot() - before),
    'code=%s other=%s' % (enc_code, enc_other))

many_pdf = make_pdf(['PAGE %d TEXT' % i for i in range(5)])
_page_cls = getattr(pypdf, 'PageObject', None) or pypdf._page.PageObject
_original_extract = _page_cls.extract_text
_calls = [0]


def _spy_extract(self, *a, **kw):
    _calls[0] += 1
    return _original_extract(self, *a, **kw)


saved = patched(ACS_UPLOAD_MAX_PDF_PAGES=2)
_page_cls.extract_text = _spy_extract
_calls[0] = 0
expect_reject('عدد صفحات أكبر من الحدّ يُرفض', 'PDF_TOO_MANY_PAGES',
              S.validate_pdf, many_pdf)
chk('الرفض وقع **قبل** استخراج أي نص (لا استدعاء واحد لـ extract_text)',
    _calls[0] == 0, 'extract_text calls=%d' % _calls[0])
_page_cls.extract_text = _original_extract
restore(saved)

saved = patched(ACS_UPLOAD_MAX_PDF_TEXT_CHARS=12)
res = expect_ok('سقف الحروف يقطع الاستخراج ويرفع علَم البتر',
                S.validate_pdf, many_pdf)
chk('النصّ مقصوص عند الحدّ و truncated=True',
    res is not None and res['truncated'] is True
    and len(res['text']) <= 12 + 4, 'res=%s' % (res or {}).get('truncated'))
restore(saved)

saved = patched(ACS_UPLOAD_MAX_PDF_BYTES=200)
expect_reject('PDF أكبر من سقف البايتات يُرفض قبل أي تحليل', 'PDF_TOO_LARGE',
              S.validate_pdf, good_pdf)
restore(saved)

print('\n== I · JSON: حجم وعمق ومفاتيح وتلويث النموذج الأولي ==')
res = expect_ok('JSON سليم يمرّ ويُعاد كائناً محلَّلاً', S.validate_json_bytes,
                json.dumps({'building': {'floors': [1, 2, 3]}}).encode('utf-8'))
chk('الكائن المُعاد هو المحتوى نفسه',
    res == {'building': {'floors': [1, 2, 3]}})
expect_reject('JSON مشوّه يُرفض', 'JSON_MALFORMED', S.validate_json_bytes,
              b'{"floors": [1, 2, ,}')
expect_reject('JSON مبتور يُرفض', 'JSON_MALFORMED', S.validate_json_bytes,
              b'{"a": {"b": [1,2,3')
expect_reject('بايتات ليست UTF-8 تُرفض', 'JSON_MALFORMED',
              S.validate_json_bytes, b'{"a": "\xff\xfe\xfa"}')
expect_reject('JSON فارغ يُرفض', 'JSON_MALFORMED', S.validate_json_bytes, b'')
for payload, where in (
        (b'{"__proto__": {"isAdmin": true}}', 'الجذر'),
        (b'{"a": {"b": {"__proto__": {"x": 1}}}}', 'العمق'),
        (b'{"rooms": [{"constructor": {"prototype": {"y": 1}}}]}', 'مصفوفة'),
        (b'{"prototype": 1}', 'مفتاح prototype')):
    expect_reject('تلويث النموذج الأولي في %s يُرفض' % where,
                  'JSON_FORBIDDEN_KEY', S.validate_json_bytes, payload)
deep = json.dumps(json.loads('[' * 60 + ']' * 60)).encode('utf-8')
expect_reject('تداخل أعمق من الحدّ يُرفض', 'JSON_TOO_DEEP',
              S.validate_json_bytes, deep)
saved = patched(ACS_UPLOAD_MAX_JSON_KEYS=10)
expect_reject('عدد مفاتيح أكبر من الحدّ يُرفض', 'JSON_TOO_MANY_KEYS',
              S.validate_json_bytes,
              json.dumps({'k%d' % i: i for i in range(40)}).encode('utf-8'))
restore(saved)
saved = patched(ACS_UPLOAD_MAX_JSON_BYTES=64)
expect_reject('JSON أكبر من سقف البايتات يُرفض قبل التحليل', 'JSON_TOO_LARGE',
              S.validate_json_bytes,
              json.dumps({'k%d' % i: i for i in range(200)}).encode('utf-8'))
restore(saved)

print('\n== J · DXF: حجم وسلامة بنيوية ==')
res = expect_ok('DXF سليم يمرّ', S.validate_dxf_bytes, dxf_text())
chk('عدد الأقسام مُبلَّغ', res is not None and res['sections'] == 2
    and res['bytes'] == len(dxf_text()))
expect_reject('ملف بلا أي قسم SECTION يُرفض', 'DXF_MALFORMED',
              S.validate_dxf_bytes, b'this is definitely not a dxf drawing')
expect_reject('DXF مبتور (قسم غير مغلق) يُرفض', 'DXF_MALFORMED',
              S.validate_dxf_bytes, b'  0\r\nSECTION\r\n  2\r\nHEADER\r\n')
expect_reject('DXF فارغ يُرفض', 'DXF_MALFORMED', S.validate_dxf_bytes, b'')
expect_reject('بايتات ثنائية عشوائية لا تنهار على فكّ الترميز',
              'DXF_MALFORMED', S.validate_dxf_bytes, bytes(range(256)) * 4)
saved = patched(ACS_UPLOAD_MAX_DXF_BYTES=32)
expect_reject('DXF أكبر من سقف البايتات يُرفض', 'DXF_TOO_LARGE',
              S.validate_dxf_bytes, dxf_text())
restore(saved)

print('\n== K · لا ملف مؤقت، لا مسار، لا تنفيذ ==')
# الكود نفسه يُفحص شجرةً نحوية، لا نصّاً: رأس الوحدة يذكر mkstemp و fastapi
# وهو يشرح ما تُصلحه، فالبحث النصّي يكذب في الاتجاهين (إيجاباً وسلباً).
SOURCE = io.open(os.path.join(ROOT, 'acs_upload_security.py'),
                 encoding='utf-8').read()
TREE = __import__('ast').parse(SOURCE)
ast = __import__('ast')

IMPORTED = set()
for node in ast.walk(TREE):
    if isinstance(node, ast.Import):
        for alias in node.names:
            IMPORTED.add(alias.name.split('.')[0])
    elif isinstance(node, ast.ImportFrom):
        IMPORTED.add((node.module or '').split('.')[0])


def _call_name(node):
    parts = []
    cur = node.func
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
    return '.'.join(reversed(parts))


CALLED = {_call_name(n) for n in ast.walk(TREE) if isinstance(n, ast.Call)}

# zlib أُضيف مع F-23: حارس قنبلة انضغاط PDF يفكّ كل مجرى بحدّ max_length صريح
# فلا يبني في الذاكرة أكثر من الميزانية. وحدة قياسية بلا شبكة ولا نظام ملفّات.
ALLOWED_IMPORTS = {'io', 'json', 'os', 'warnings', 'zlib', 'PIL', 'pypdf'}
chk('الوحدة لا تستورد سوى %s' % ', '.join(sorted(ALLOWED_IMPORTS)),
    IMPORTED <= ALLOWED_IMPORTS, 'extra=%s' % sorted(IMPORTED
                                                     - ALLOWED_IMPORTS))
chk('الوحدة لا تستورد fastapi ولا starlette (استقلال تام عن الإطار)',
    not (IMPORTED & {'fastapi', 'starlette'})
    and 'fastapi' not in sys.modules)
chk('الوحدة لا تستورد tempfile ولا subprocess ولا pickle/marshal',
    not (IMPORTED & {'tempfile', 'subprocess', 'pickle', 'marshal',
                     'shutil', 'shelve'}))
for banned in ('open', 'eval', 'exec', 'compile', '__import__', 'input',
               'os.remove', 'os.system', 'os.popen', 'os.unlink', 'os.open',
               'os.makedirs', 'io.open', 'tempfile.mkstemp',
               'tempfile.mkdtemp', 'tempfile.NamedTemporaryFile',
               'tempfile.TemporaryFile'):
    chk('الوحدة لا تستدعي %s إطلاقاً' % banned, banned not in CALLED)
chk('الاستدعاء الوحيد المسمّى open هو PIL.Image.open (قراءة رأس في الذاكرة)',
    'Image.open' in CALLED and 'io.BytesIO' in CALLED)
chk('القراءة الوحيدة من البيئة تمرّ بالحارس المتسامح مع الفراغ',
    CALLED >= {'os.environ.get'} and 'os.environ.__getitem__' not in CALLED)
sig = [n for n in ast.walk(TREE) if isinstance(n, ast.FunctionDef)
       and n.name in ('validate_pdf', 'validate_image', 'validate_json_bytes',
                      'validate_dxf_bytes')]
bad_args = [n.name for n in sig
            if any(a.arg in ('path', 'filename', 'file', 'fp', 'name')
                   for a in n.args.args)]
chk('لا دالّة تحقّق تأخذ مساراً أو اسم ملف كوسيط', not bad_args,
    ','.join(bad_args))
before = _tmp_snapshot()
for blob, fn in ((pe_stub(), S.validate_image), (html_doc(), S.validate_image),
                 (bomb, S.validate_image), (good_pdf, S.validate_pdf),
                 (trunc_pdf, S.validate_pdf), (enc_pdf, S.validate_pdf),
                 (b'{"__proto__":1}', S.validate_json_bytes),
                 (dxf_text(), S.validate_dxf_bytes)):
    try:
        fn(blob)
    except S.UploadRejected:
        pass
chk('لم يُنشأ ملف مؤقت واحد عبر كل الحمولات مجتمعة',
    not (_tmp_snapshot() - before), 'leaked=%s'
    % sorted(_tmp_snapshot() - before))

FUZZ = [b'', b'\x00', b'\xff' * 10, b'%PDF-', b'%PDF-1.4', b'{', b'[',
        b'GIF89a', b'\x89PNG\r\n\x1a\n', b'RIFF0000WEBP', b'MZ',
        b'\x7fELF', b'<html>', b'SECTION', os.urandom(64), b'0' * 1000,
        b'\x89PNG\r\n\x1a\n' + os.urandom(200), b'%PDF-1.4' + os.urandom(300)]
escaped = []
for blob in FUZZ:
    for fn in (S.validate_image, S.validate_pdf, S.validate_json_bytes,
               S.validate_dxf_bytes, S.sniff, S.safe_filename_label):
        try:
            fn(blob)
        except S.UploadRejected:
            pass
        except Exception as exc:                    # noqa: BLE001
            escaped.append('%s(%r) -> %s' % (fn.__name__, blob[:8],
                                             type(exc).__name__))
chk('لا استثناء غير UploadRejected يتسرّب من %d حمولة × ٦ مداخل'
    % len(FUZZ), not escaped, '; '.join(escaped[:3]))

print('\n== L · قراءة البيئة لا تُسقط الإقلاع (عطل int("") الكامن) ==')
ENV_NAMES = ('ACS_UPLOAD_MAX_IMAGE_BYTES', 'ACS_UPLOAD_MAX_IMAGE_PIXELS',
             'ACS_UPLOAD_MAX_IMAGE_SIDE',
             'ACS_UPLOAD_MAX_IMAGE_DECODED_BYTES',      # F-22
             'ACS_UPLOAD_MAX_IMAGES',
             'ACS_UPLOAD_MAX_PDF_BYTES', 'ACS_UPLOAD_MAX_PDF_PAGES',
             'ACS_UPLOAD_MAX_PDF_TEXT_CHARS',
             'ACS_UPLOAD_MAX_PDF_DECOMPRESSED_BYTES',   # F-23
             'ACS_UPLOAD_MAX_JSON_BYTES',
             'ACS_UPLOAD_MAX_JSON_DEPTH', 'ACS_UPLOAD_MAX_JSON_KEYS',
             'ACS_UPLOAD_MAX_DXF_BYTES')
DEFAULTS = copy.deepcopy(S.SPEC['limits'])
_env_backup = {k: os.environ.get(k) for k in ENV_NAMES}


def _reload_with(value):
    for k in ENV_NAMES:
        if value is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = value
    return importlib.reload(S)


for label, value in (('فارغة ""', ''), ('مسافات "  "', '   '),
                     ('غير رقمية "abc"', 'abc'), ('سالبة "-5"', '-5'),
                     ('صفر "0"', '0')):
    ok = True
    try:
        mod = _reload_with(value)
        ok = all(mod.SPEC['limits'][k] == v for k, v in DEFAULTS.items())
    except Exception as exc:                        # noqa: BLE001
        ok = False
        print('    (%s -> %s: %s)' % (label, type(exc).__name__, exc))
    chk('قيمة بيئة %s تعود إلى الافتراضي ولا تُسقط الاستيراد' % label, ok)
mod = _reload_with('7')
chk('قيمة بيئة صحيحة تُحترم فعلاً',
    mod.ACS_UPLOAD_MAX_IMAGES == 7 and mod.SPEC['limits']['max_images'] == 7)
for k, v in _env_backup.items():
    if v is None:
        os.environ.pop(k, None)
    else:
        os.environ[k] = v
S = importlib.reload(S)
chk('الحدود عادت إلى الافتراضي بعد استعادة البيئة',
    S.SPEC['limits'] == DEFAULTS)

print('\n== N · ميزانية الذاكرة بعد فكّ الترميز (F-22) ==')
# صورة PNG صلبة اللون تمرّ من الحدود الثلاثة القديمة كلّها: ١٢٠ ك.ب على السلك
# (الحدّ ٥ م.ب)، و٣٩٫٦ مليون بكسل (الحدّ ٤٠ مليون)، وضلع ١١٠٠٠ (الحدّ ١٢٠٠٠).
# قياساً قبل الإصلاح: ذروة ٦٠١ م.ب وقُبِلت — على نسخة بـ٥١٢ م.ب هذا قتل للعملية.
_bomb = io.BytesIO()
Image.new('RGB', (11000, 3600), (3, 7, 11)).save(_bomb, 'PNG', optimize=True)
_bomb = _bomb.getvalue()
chk('الصورة الاصطناعية تمرّ فعلاً من الحدود الثلاثة القديمة (الفحص غير عبثي)',
    len(_bomb) <= S.ACS_UPLOAD_MAX_IMAGE_BYTES
    and 11000 * 3600 <= S.ACS_UPLOAD_MAX_IMAGE_PIXELS
    and 11000 <= S.ACS_UPLOAD_MAX_IMAGE_SIDE,
    'wire=%d px=%d' % (len(_bomb), 11000 * 3600))
try:
    S.validate_image(_bomb, 'image/png')
    _code = None
except S.UploadRejected as exc:
    _code = exc.code
chk('صورة ٣٩٫٦ مليون بكسل تُرفض بـIMAGE_DECODED_TOO_LARGE قبل أي فكّ ترميز',
    _code == 'IMAGE_DECODED_TOO_LARGE', _code)
_ok = io.BytesIO()
Image.new('RGB', (2400, 1700), (200, 30, 60)).save(_ok, 'PNG')
_ok = _ok.getvalue()
try:
    _res = S.validate_image(_ok, 'image/png')
    _pass = _res['width'] == 2400 and _res['height'] == 1700
except S.UploadRejected as exc:
    _pass = False
    _res = exc.code
chk('مخطّط معماري واقعي ‎2400×1700‎ ما زال يُقبل (لا رفض زائد)', _pass, _res)
chk('الميزانية تُحسب بالبايتات لا بالبكسلات (RGBA أثقل من L لنفس الأبعاد)',
    S._decoded_bytes('RGBA', 100, 100) == 4 * 10000
    and S._decoded_bytes('L', 100, 100) == 10000
    and S._decoded_bytes('MODE-NOT-KNOWN', 100, 100) == 4 * 10000)

print('\n== O · قنبلة انضغاط PDF (F-23) ==')


def _flate_pdf(repeats):
    """PDF بصفحة واحدة، مجرى محتواه ينضغط بنسبة عالية جداً."""
    body = (b'BT /F1 8 Tf 10 10 Td (' + b'A' * 200 + b') Tj ET\n') * repeats
    comp = zlib.compress(body, 9)
    objs = [b'<< /Type /Catalog /Pages 2 0 R >>',
            b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
            b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] '
            b'/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>',
            b'<< /Length %d /Filter /FlateDecode >>\nstream\n' % len(comp)
            + comp + b'\nendstream',
            b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    out = io.BytesIO()
    out.write(b'%PDF-1.4\n')
    offsets = []
    for i, obj in enumerate(objs, 1):
        offsets.append(out.tell())
        out.write(b'%d 0 obj\n' % i + obj + b'\nendobj\n')
    start = out.tell()
    out.write(b'xref\n0 %d\n0000000000 65535 f \n' % (len(objs) + 1))
    for off in offsets:
        out.write(b'%010d 00000 n \n' % off)
    out.write(b'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n'
              % (len(objs) + 1, start))
    return out.getvalue(), len(body)


_pdf, _expanded = _flate_pdf(300000)
chk('القنبلة أصغر بكثير من سقف الحجم وصفحتها واحدة (الفحص غير عبثي)',
    len(_pdf) < S.ACS_UPLOAD_MAX_PDF_BYTES
    and _expanded > S.ACS_UPLOAD_MAX_PDF_DECOMPRESSED_BYTES,
    'file=%d expands=%d' % (len(_pdf), _expanded))
try:
    S.validate_pdf(_pdf)
    _code = None
except S.UploadRejected as exc:
    _code = exc.code
chk('PDF يتمدّد فوق الميزانية يُرفض بـPDF_DECOMPRESSION_BOMB',
    _code == 'PDF_DECOMPRESSION_BOMB', _code)
_small, _ = _flate_pdf(200)
try:
    _res = S.validate_pdf(_small)
    _pass = len(_res['text']) > 0 and _res['pages'] == 1
except S.UploadRejected as exc:
    _pass = False
    _res = exc.code
chk('PDF نصّي عادي ما زال يُقبل ويُستخرج نصّه (لا رفض زائد)', _pass, _res)
_mid, _ = _flate_pdf(80000)
try:
    _res = S.validate_pdf(_mid)
    _pass = _res['truncated'] is True and \
        len(_res['text']) <= S.ACS_UPLOAD_MAX_PDF_TEXT_CHARS
except S.UploadRejected as exc:
    _pass = False
    _res = exc.code
chk('صفحة واحدة طويلة تُقصّ عند سقف الأحرف وتُعلَن truncated', _pass, _res)
_measured, _over = S._flate_expansion(_pdf, 1024)
chk('قياس التمدّد نفسه محدود بالميزانية فلا يصير الفحص هجوماً',
    _over is True and _measured <= 4096, '%d' % _measured)

print('\n== M · العقد المُعلَن صالح للعرض في /health ==')
h = S.health_status()
_blob = json.dumps(h, ensure_ascii=False).lower()
chk('health يعلن كل الحدود بلا سرّ واحد',
    h['limits'] == DEFAULTS
    and not any(w in _blob for w in ('anthropic', 'api_key', 'apikey',
                                     'secret', 'token', 'password', 'sk-ant')),
    'limits=%s' % (h['limits'] == DEFAULTS))
chk('كل قيمة في health عدد أو نصّ أو قائمة (لا كائن حيّ يتسرّب)',
    all(isinstance(v, (int, float, str, bool, list, dict))
        for v in h.values())
    and all(isinstance(v, int) for v in h['limits'].values()))
chk('health يعلن صراحةً أنه لا يكتب ملفات مؤقتة ولا يستعمل الاسم مساراً',
    h['writes_temp_files'] is False and h['uses_filename_as_path'] is False)
chk('health قابل للتسلسل JSON كما هو',
    json.loads(json.dumps(h))['contract_version'] == S.SPEC['contract_version'])
chk('GIF معلن مرفوضاً و PNG/JPEG/WEBP معلنة مقبولة',
    h['image_rejected'] == ['gif']
    and set(h['image_allowed']) == {'png', 'jpeg', 'webp'})
USED = ('EMPTY_UPLOAD', 'TOO_MANY_FILES', 'IMAGE_TOO_LARGE',
        'IMAGE_TYPE_NOT_ALLOWED', 'IMAGE_TYPE_MISMATCH',
        'IMAGE_TOO_MANY_PIXELS', 'IMAGE_SIDE_TOO_LARGE',
        'IMAGE_PIXEL_BUDGET_EXCEEDED', 'IMAGE_CORRUPT',
        'IMAGE_DECODED_TOO_LARGE', 'PDF_TOO_LARGE',
        'PDF_BAD_SIGNATURE', 'PDF_ENCRYPTED', 'PDF_TOO_MANY_PAGES',
        'PDF_DECOMPRESSION_BOMB',
        'PDF_UNREADABLE', 'JSON_TOO_LARGE', 'JSON_MALFORMED', 'JSON_TOO_DEEP',
        'JSON_TOO_MANY_KEYS', 'JSON_FORBIDDEN_KEY', 'DXF_TOO_LARGE',
        'DXF_MALFORMED')
chk('كل رمز استعمله هذا الاختبار مُعلَن في SPEC',
    all(c in S.SPEC['issue_codes'] for c in USED),
    ','.join(c for c in USED if c not in S.SPEC['issue_codes']))
chk('كل رمز مُعلَن هو UPPER_SNAKE ثابت',
    all(c.replace('_', '').isalnum() and c.upper() == c
        for c in S.SPEC['issue_codes']))

print('\n──────────────────────────────────────────────')
print('الحمولات العدائية وُلّدت برمجياً في: %s' % FIXTURES)
print('TEST SUMMARY: %d passed, %d failed' % (p[0], f[0]))
if f[0]:
    sys.exit(1)
