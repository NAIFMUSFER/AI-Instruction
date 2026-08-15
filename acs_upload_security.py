# -*- coding: utf-8 -*-
# =============================================================================
# acs_upload_security.py — بوّابة الرفع الآمنة (طبقة نقيّة بلا إطار عمل).
#
# العقد بإيجاز:
#   تأخذ هذه الوحدة **بايتات** فقط، وتعيد نتيجة موصوفة أو ترفع UploadRejected.
#   لا تستورد fastapi، ولا تفتح شبكة، ولا تكتب ملفاً مؤقتاً، ولا تنفّذ شيئاً،
#   ولا تستعمل اسم الملف مساراً على القرص إطلاقاً.
#
# ما تُصلحه (مقابل السلوك القائم في acs_understand_api.py):
#   1) /v1/understand/image كان يثق بـ Content-Type القادم من العميل، وحين لا
#      يعجبه كان يعيد وسمه بصمت إلى "image/png" ثم يرسله إلى واجهة الرؤية.
#      هنا: النوع يُستنتج من البصمة الثنائية (magic bytes)، وأي تعارض مع النوع
#      المُعلَن يُرفض صراحةً — لا إعادة وسم صامتة أبداً.
#   2) لم يكن هناك فكّ ترميز ولا سقف أبعاد: صورة 25000×25000 مضغوطة في بضعة
#      كيلوبايت كانت تمرّ. هنا: يُقرأ الرأس وحده أولاً (فتح كسول)، ويُرفض
#      الحجم المنطقي قبل فكّ الترميز، ثم يُحمَّل فعلياً لإثبات أنه غير مبتور.
#   3) الصورة المُمرَّرة إلى الأعلى صارت **صورة مُعاد ترميزها** من البكسلات
#      وحدها: بلا EXIF ولا ملفات تعريف لون ولا مقاطع نصّية ولا حمولة مخبّأة،
#      ومع تصحيح الدوران من EXIF قبل إسقاطه.
#   4) /v1/understand/pdf كان يكتب الملف إلى tempfile.mkstemp ثم يمرّر مساراً،
#      بلا توقيع %PDF- ولا سقف صفحات ولا معالجة تشفير. هنا: كل شيء في الذاكرة
#      عبر io.BytesIO، وتوقيع إلزامي، وسقف صفحات يُطبَّق **قبل** استخراج أي نص،
#      وأي استثناء من المحلّل يُترجم إلى PDF_UNREADABLE ولا يتسرّب كخطأ 500.
#   5) اسم الملف كان يُطبع خاماً في السجلّ (حقن سطور). هنا safe_filename_label
#      يجرّد المسار ومحارف التحكّم ويقصّ الطول.
#   6) JSON و DXF كانا يُحلَّلان في المتصفّح بلا أي حارس. هنا حارس مستقلّ عن
#      الإطار جاهز لأي مسار رفع مستقبلي: سقف حجم وعمق ومفاتيح، ورفض مفاتيح
#      تلويث النموذج الأولي (__proto__ / constructor / prototype).
#
# الرسائل الموجَّهة للمستخدم بالعربية وقابلة للتنفيذ (تقول له ماذا يفعل)،
# والتفصيل التقني بالإنجليزية وآمن للسجلّ: لا بايتات خام ولا اسم ملف خام.
#
# قراءة الإعدادات من البيئة تتحمّل القيمة الفارغة "" وتعود إلى الافتراضي —
# المستودع فيه عطل إقلاع كامن من نوع int("") قادم من .env.example، ولا يُكرَّر هنا.
# =============================================================================
import io
import json
import os
import warnings
import zlib

from PIL import Image, ImageOps
import pypdf


# ---------------------------------------------------------------- الإعدادات --
def _env_int(name, default):
    """قراءة عدد صحيح من البيئة تتحمّل الغياب والفراغ والقيمة الفاسدة."""
    raw = os.environ.get(name)
    if raw is None:
        return int(default)
    raw = raw.strip()
    if not raw:                                   # "" لا يُسقط الخدمة
        return int(default)
    try:
        val = int(raw, 10)
    except (TypeError, ValueError):
        return int(default)
    return val if val > 0 else int(default)


ACS_UPLOAD_MAX_IMAGE_BYTES = _env_int("ACS_UPLOAD_MAX_IMAGE_BYTES", 5 * 1024 * 1024)
ACS_UPLOAD_MAX_IMAGE_PIXELS = _env_int("ACS_UPLOAD_MAX_IMAGE_PIXELS", 40_000_000)
ACS_UPLOAD_MAX_IMAGE_SIDE = _env_int("ACS_UPLOAD_MAX_IMAGE_SIDE", 12000)
# F-22: ميزانية الذاكرة بعد فكّ الترميز — بالبايتات لا بالبكسلات.
#
# الحدود الثلاثة أعلاه كلّها تقيس ما يصل عبر السلك أو عدد البكسلات، ولا يقيس
# أيٌّ منها ما يشغله الرستر بعد فكّ الترميز. صورة PNG صلبة اللون بحجم ١٢٠ ك.ب
# على السلك تعلن ‎11000×3600‎ = ٣٩٫٦ مليون بكسل: دون سقف البكسلات (٤٠ مليون)،
# ودون سقف البايتات (٥ م.ب)، ودون سقف الضلع (١٢٠٠٠). قياساً في هذا المستودع:
# `validate_image` عليها بلغت ذروة الذاكرة ٦٠١ م.ب وقُبِلت. نسخة Render من فئة
# starter تملك ٥١٢ م.ب، فطلب واحد غير موثّق يقتل العملية بكاملها.
#
# الرقم أدناه هو حجم الرستر الخام (عرض × ارتفاع × بايتات القناة). التضخيم
# المقيس على مسار PNG ≈ ٥ أضعاف الرستر (تحميل + exif_transpose + tobytes +
# frombytes + مخزن الترميز)، فـ ٣٢ م.ب رستر ≈ ١٧٠ م.ب ذروة — ضمن حدود نسخة
# ٥١٢ م.ب مع هامش. ‎32 MiB‎ من RGB ≈ ١١٫٢ مليون بكسل ≈ ‎4000×2800‎، وهو أعلى
# بكثير من أي مخطّط معماري يُرفع للقراءة بالرؤية.
ACS_UPLOAD_MAX_IMAGE_DECODED_BYTES = _env_int(
    "ACS_UPLOAD_MAX_IMAGE_DECODED_BYTES", 32 * 1024 * 1024)
# بايتات الرستر لكل بكسل حسب الوضع المُعلن في الرأس. الوضع غير المعروف يُحسب
# بأربعة بايتات — التقدير يعلو ولا يقلّ، فلا يمرّ حِمل غير محسوب.
_MODE_BYTES_PER_PIXEL = {
    "1": 1, "L": 1, "P": 1, "LA": 2, "La": 2, "I;16": 2, "I;16B": 2,
    "I;16L": 2, "RGB": 3, "YCbCr": 3, "LAB": 3, "HSV": 3, "BGR;24": 3,
    "RGBA": 4, "RGBa": 4, "RGBX": 4, "CMYK": 4, "I": 4, "F": 4, "PA": 4,
}


def _decoded_bytes(mode, width, height):
    """حجم الرستر الخام بعد فكّ الترميز — تقدير أعلى لا أدنى."""
    return int(width) * int(height) * _MODE_BYTES_PER_PIXEL.get(str(mode), 4)
ACS_UPLOAD_MAX_IMAGES = _env_int("ACS_UPLOAD_MAX_IMAGES", 6)
ACS_UPLOAD_MAX_PDF_BYTES = _env_int("ACS_UPLOAD_MAX_PDF_BYTES", 12 * 1024 * 1024)
ACS_UPLOAD_MAX_PDF_PAGES = _env_int("ACS_UPLOAD_MAX_PDF_PAGES", 200)
ACS_UPLOAD_MAX_PDF_TEXT_CHARS = _env_int("ACS_UPLOAD_MAX_PDF_TEXT_CHARS", 400000)
# F-23: سقف مجموع ما تتمدّد إليه مجاري المحتوى المضغوطة داخل الملفّ.
#
# سقف الحجم (١٢ م.ب) وسقف الصفحات (٢٠٠) وسقف الأحرف (٤٠٠ ألف) لا يقيس أيٌّ
# منها ما يتمدّد إليه المحتوى بعد فكّ الضغط. pypdf يفكّ مجرى الصفحة كاملاً
# ويحلّله إلى قائمة عمليات **قبل** أن يبدأ الاستخراج، فسقف الأحرف لا يوقف تلك
# المرحلة. قياساً في هذا المستودع: ملفّ بصفحة واحدة حجمه ٧٢ ك.ب يتمدّد مجراه
# إلى ١٨٫٤ م.ب وشغّل المعالج ٦٢ ثانية قبل هذا الإصلاح.
ACS_UPLOAD_MAX_PDF_DECOMPRESSED_BYTES = _env_int(
    "ACS_UPLOAD_MAX_PDF_DECOMPRESSED_BYTES", 24 * 1024 * 1024)
ACS_UPLOAD_MAX_JSON_BYTES = _env_int("ACS_UPLOAD_MAX_JSON_BYTES", 900000)
ACS_UPLOAD_MAX_JSON_DEPTH = _env_int("ACS_UPLOAD_MAX_JSON_DEPTH", 40)
ACS_UPLOAD_MAX_JSON_KEYS = _env_int("ACS_UPLOAD_MAX_JSON_KEYS", 100000)
ACS_UPLOAD_MAX_DXF_BYTES = _env_int("ACS_UPLOAD_MAX_DXF_BYTES", 16 * 1024 * 1024)

CONTRACT_VERSION = "1.0"

# أنواع الصور المسموح بتمريرها إلى واجهة الرؤية. GIF مستبعد عمداً: إطارات
# متحرّكة، وسطح هجوم أوسع، ولا فائدة منه لمخطّط معماري ساكن.
IMAGE_ALLOWED = ("png", "jpeg", "webp")
IMAGE_MEDIA_TYPE = {"png": "image/png", "jpeg": "image/jpeg", "webp": "image/webp"}
# المقابل المعياري لما قد يُعلنه العميل (بما فيه الصيغ الشائعة الخاطئة).
_DECLARED_ALIAS = {
    "image/png": "png", "image/x-png": "png", "image/apng": "png",
    "image/jpeg": "jpeg", "image/jpg": "jpeg", "image/pjpeg": "jpeg",
    "image/webp": "webp", "image/gif": "gif",
}

# مفاتيح يُرفض ورودها في أي مستند JSON مهما كان عمقها.
JSON_FORBIDDEN_KEYS = ("__proto__", "constructor", "prototype")

ISSUE_CODES = (
    "EMPTY_UPLOAD",
    "TOO_MANY_FILES",
    "IMAGE_TOO_LARGE",
    "IMAGE_TYPE_NOT_ALLOWED",
    "IMAGE_TYPE_MISMATCH",
    "IMAGE_TOO_MANY_PIXELS",
    "IMAGE_SIDE_TOO_LARGE",
    "IMAGE_PIXEL_BUDGET_EXCEEDED",
    "IMAGE_DECODED_TOO_LARGE",
    "IMAGE_DECODED_BUDGET_EXCEEDED",
    "IMAGE_CORRUPT",
    "IMAGE_REENCODE_FAILED",
    "PDF_TOO_LARGE",
    "PDF_BAD_SIGNATURE",
    "PDF_ENCRYPTED",
    "PDF_TOO_MANY_PAGES",
    "PDF_DECOMPRESSION_BOMB",
    "PDF_UNREADABLE",
    "JSON_TOO_LARGE",
    "JSON_MALFORMED",
    "JSON_TOO_DEEP",
    "JSON_TOO_MANY_KEYS",
    "JSON_FORBIDDEN_KEY",
    "DXF_TOO_LARGE",
    "DXF_MALFORMED",
)

SPEC = {
    "module": "acs_upload_security",
    "contract_version": CONTRACT_VERSION,
    "limits": {
        "max_image_bytes": ACS_UPLOAD_MAX_IMAGE_BYTES,
        "max_image_pixels": ACS_UPLOAD_MAX_IMAGE_PIXELS,
        "max_image_side": ACS_UPLOAD_MAX_IMAGE_SIDE,
        "max_image_decoded_bytes": ACS_UPLOAD_MAX_IMAGE_DECODED_BYTES,
        "max_images": ACS_UPLOAD_MAX_IMAGES,
        "max_pdf_bytes": ACS_UPLOAD_MAX_PDF_BYTES,
        "max_pdf_pages": ACS_UPLOAD_MAX_PDF_PAGES,
        "max_pdf_text_chars": ACS_UPLOAD_MAX_PDF_TEXT_CHARS,
        "max_pdf_decompressed_bytes": ACS_UPLOAD_MAX_PDF_DECOMPRESSED_BYTES,
        "max_json_bytes": ACS_UPLOAD_MAX_JSON_BYTES,
        "max_json_depth": ACS_UPLOAD_MAX_JSON_DEPTH,
        "max_json_keys": ACS_UPLOAD_MAX_JSON_KEYS,
        "max_dxf_bytes": ACS_UPLOAD_MAX_DXF_BYTES,
    },
    "image_allowed": list(IMAGE_ALLOWED),
    "image_batch_pixel_budget": "shared, equal to max_image_pixels",
    "issue_codes": list(ISSUE_CODES),
    "guarantees": [
        "no temporary file is ever created by this module",
        "the uploaded filename is never used as a filesystem path",
        "no uploaded byte is ever executed, evaluated or interpreted",
        "every rejection is an UploadRejected with a stable code",
        "images are forwarded re-encoded from pixels only (metadata stripped)",
    ],
    "filename_label_max_chars": 64,
}


# ----------------------------------------------------------------- الاستثناء --
class UploadRejected(Exception):
    """رفض مقصود لحمولة مرفوعة — يحمل رمزاً ثابتاً ورسالة عربية وتفصيلاً آمناً."""

    def __init__(self, code, message_ar, detail=""):
        self.code = str(code)
        self.message_ar = str(message_ar)
        self.detail = str(detail or "")
        Exception.__init__(self, "%s: %s" % (self.code, self.detail or self.code))

    def as_dict(self):
        return {"code": self.code, "message_ar": self.message_ar,
                "detail": self.detail}


def _reject(code, message_ar, detail=""):
    raise UploadRejected(code, message_ar, detail)


def _mb(n):
    return float(n) / 1048576.0


# ------------------------------------------------------ البصمة الثنائية --
_PNG_SIG = b"\x89PNG\r\n\x1a\n"
_HTML_MARKERS = ("<!doctype html", "<html", "<head", "<body", "<script",
                 "<?xml", "<svg")


def _head_text(data, limit=2048):
    """نصّ الرأس للفحص البنيوي فقط — errors=replace فلا يرفع استثناءً أبداً."""
    return data[:limit].decode("utf-8", errors="replace")


def sniff(data):
    """يستنتج النوع من محتوى البايتات وحدها — لا من الامتداد ولا من العميل.

    يعيد أحد: png jpeg webp gif pdf zip elf pe html json dxf unknown
    """
    if not isinstance(data, (bytes, bytearray, memoryview)):
        return "unknown"
    data = bytes(data)
    if not data:
        return "unknown"

    if data.startswith(_PNG_SIG):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if b"%PDF-" in data[:1024]:
        return "pdf"
    if data[:4] in (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"):
        return "zip"
    if data.startswith(b"\x7fELF"):
        return "elf"
    if data.startswith(b"MZ"):
        return "pe"

    head = _head_text(data)
    stripped = head.lstrip("﻿ \t\r\n")
    low = stripped.lower()
    for marker in _HTML_MARKERS:
        if low.startswith(marker):
            return "html"
    if "<html" in low[:512] or "<!doctype html" in low[:512]:
        return "html"

    # DXF نصّي: أزواج (رمز مجموعة / قيمة)، ويبدأ عملياً بمجموعة 0 = SECTION.
    if stripped.startswith("AutoCAD Binary DXF"):
        return "dxf"
    if "SECTION" in head and ("HEADER" in head or "ENTITIES" in head
                              or "TABLES" in head or "BLOCKS" in head):
        return "dxf"

    if stripped[:1] in ("{", "["):
        tail = data[-256:].decode("utf-8", errors="replace").rstrip()
        if tail[-1:] in ("}", "]"):
            return "json"
    return "unknown"


# ------------------------------------------------------- اسم آمن للسجلّ --
_LABEL_SAFE = set("abcdefghijklmnopqrstuvwxyz"
                  "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                  "0123456789._- ")
_LABEL_MAX = 64


def safe_filename_label(name):
    """وسم آمن للسجلّ من اسم ملف قادم من المهاجم — للعرض فقط، ليس مساراً.

    يجرّد الأدلّة (فلا يبقى اجتياز مسار)، ويحذف CR/LF ومحارف التحكّم (فلا يبقى
    حقن سطور في السجلّ)، ويقصر المحارف على مجموعة متحفّظة، ويقصّ إلى 64 محرفاً.
    """
    if name is None:
        return "unnamed"
    if isinstance(name, (bytes, bytearray)):
        name = bytes(name).decode("utf-8", errors="replace")
    try:
        text = str(name)
    except Exception:
        return "unnamed"

    text = text.replace("\\", "/").replace("\x00", "")
    text = text.rsplit("/", 1)[-1]                 # تجريد كل الأدلّة
    out = []
    for ch in text:
        if ch in _LABEL_SAFE and ord(ch) >= 32:
            out.append(ch)
        else:
            out.append("_")                        # ولا حتى سطر جديد واحد
    label = "".join(out).strip(" ._-")
    label = label[:_LABEL_MAX].strip(" ._-")
    return label or "unnamed"


# ------------------------------------------------------------ الصور --
def _normalize_declared(declared_content_type):
    if not declared_content_type:
        return None
    try:
        raw = str(declared_content_type)
    except Exception:
        return None
    raw = raw.split(";", 1)[0].strip().lower()
    if not raw:
        return None
    return _DECLARED_ALIAS.get(raw, raw)


def _open_header(data):
    """فتح كسول للرأس وحده مع حارس قنبلة الانضغاط — قبل أي فكّ ترميز."""
    budget = int(ACS_UPLOAD_MAX_IMAGE_PIXELS)
    previous = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = budget
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            im = Image.open(io.BytesIO(data))
            im.load  # noqa: B018 — لا تحميل هنا: الرأس فقط
            return im
    except Image.DecompressionBombError:
        _reject("IMAGE_TOO_MANY_PIXELS",
                "أبعاد الصورة أكبر من الحدّ المسموح — صدّرها بدقّة أقل "
                "(الحدّ %d مليون بكسل) ثم أعد الرفع." % (budget // 1000000),
                "decompression bomb guard tripped at %d pixels" % budget)
    except Image.DecompressionBombWarning:
        _reject("IMAGE_TOO_MANY_PIXELS",
                "أبعاد الصورة أكبر من الحدّ المسموح — صدّرها بدقّة أقل "
                "(الحدّ %d مليون بكسل) ثم أعد الرفع." % (budget // 1000000),
                "decompression bomb guard warned at %d pixels" % budget)
    except UploadRejected:
        raise
    except Exception as exc:
        _reject("IMAGE_CORRUPT",
                "تعذّرت قراءة الصورة — يبدو الملف تالفاً أو ناقصاً. "
                "أعد تصديره من البرنامج الأصلي ثم ارفعه مرّة أخرى.",
                "header parse failed: %s" % type(exc).__name__)
    finally:
        Image.MAX_IMAGE_PIXELS = previous


def _reencode(im, kind):
    """يبني صورة جديدة من البكسلات وحدها ثم يرمّزها — بلا أي بيانات وصفية."""
    if kind == "jpeg":
        mode = "L" if im.mode in ("L", "1") else "RGB"
    elif im.mode in ("RGBA", "LA", "PA"):
        mode = "RGBA"
    elif im.mode in ("L", "1"):
        mode = "L"
    else:
        mode = "RGB"
    if im.mode != mode:
        im = im.convert(mode)
    # صورة جديدة تماماً: البكسلات فقط، بلا info ولا exif ولا icc ولا مقاطع نصّية.
    fresh = Image.frombytes(mode, im.size, im.tobytes())
    buf = io.BytesIO()
    if kind == "png":
        fresh.save(buf, format="PNG", optimize=False, compress_level=6)
    elif kind == "jpeg":
        fresh.save(buf, format="JPEG", quality=88, optimize=False,
                   progressive=False, subsampling=2)
    else:
        fresh.save(buf, format="WEBP", quality=90, method=4)
    return buf.getvalue(), fresh.size


def validate_image(data, declared_content_type=None):
    """يتحقّق من صورة واحدة ويعيد نسخة مُعاد ترميزها آمنة للتمرير.

    يعيد: {"media_type","width","height","bytes","sniffed","normalized"}
    """
    if not isinstance(data, (bytes, bytearray, memoryview)):
        _reject("EMPTY_UPLOAD",
                "لم تصل بيانات الصورة — أعد اختيار الملف ثم ارفعه مرّة أخرى.",
                "payload is not bytes: %s" % type(data).__name__)
    data = bytes(data)
    size = len(data)
    if size == 0:
        _reject("EMPTY_UPLOAD",
                "الملف فارغ — اختر صورة صالحة ثم أعد الرفع.",
                "zero-length image payload")
    limit = int(ACS_UPLOAD_MAX_IMAGE_BYTES)
    if size > limit:
        _reject("IMAGE_TOO_LARGE",
                "حجم الصورة %.1f م.ب — الحدّ %.1f م.ب. صغّرها أو صدّرها بجودة "
                "أقل ثم أعد الرفع." % (_mb(size), _mb(limit)),
                "image bytes %d exceed limit %d" % (size, limit))

    kind = sniff(data)
    if kind == "gif":
        _reject("IMAGE_TYPE_NOT_ALLOWED",
                "صيغة GIF غير مدعومة لأنها صيغة متحرّكة — احفظ المخطّط بصيغة "
                "PNG أو JPEG أو WEBP ثم أعد الرفع.",
                "sniffed type gif is not in the still-image allowlist")
    if kind not in IMAGE_ALLOWED:
        _reject("IMAGE_TYPE_NOT_ALLOWED",
                "محتوى الملف ليس صورة PNG أو JPEG أو WEBP — تأكّد أنك اخترت "
                "ملف الصورة الصحيح ثم أعد الرفع.",
                "sniffed type %s is not an allowed image type" % kind)

    declared = _normalize_declared(declared_content_type)
    if declared is not None and declared != kind:
        # لا إعادة وسم صامتة: التعارض يُعلن، لأن إخفاءه هو بالضبط ما كان يمرّر
        # حمولة غير صورة إلى واجهة الرؤية موسومة image/png.
        _reject("IMAGE_TYPE_MISMATCH",
                "نوع الملف المُعلَن لا يطابق محتواه الفعلي — أعد حفظ الصورة "
                "بصيغة واحدة واضحة (PNG أو JPEG أو WEBP) ثم ارفعها.",
                "declared %s but content is %s" % (declared, kind))

    im = _open_header(data)
    try:
        width, height = int(im.size[0] or 0), int(im.size[1] or 0)
        if width <= 0 or height <= 0:
            _reject("IMAGE_CORRUPT",
                    "أبعاد الصورة غير صالحة — أعد تصديرها من البرنامج الأصلي "
                    "ثم ارفعها مرّة أخرى.",
                    "non-positive dimensions in header")
        pixel_budget = int(ACS_UPLOAD_MAX_IMAGE_PIXELS)
        if width * height > pixel_budget:
            _reject("IMAGE_TOO_MANY_PIXELS",
                    "عدد بكسلات الصورة أكبر من الحدّ (%d مليون بكسل) — صدّرها "
                    "بدقّة أقل ثم أعد الرفع." % (pixel_budget // 1000000),
                    "declared %dx%d exceeds pixel budget %d"
                    % (width, height, pixel_budget))
        side_budget = int(ACS_UPLOAD_MAX_IMAGE_SIDE)
        if width > side_budget or height > side_budget:
            _reject("IMAGE_SIDE_TOO_LARGE",
                    "أحد أبعاد الصورة أكبر من %d بكسل — صغّر الصورة ثم أعد "
                    "الرفع." % side_budget,
                    "declared %dx%d exceeds side budget %d"
                    % (width, height, side_budget))
        frames = int(getattr(im, "n_frames", 1) or 1)
        if frames > 1:
            _reject("IMAGE_TYPE_NOT_ALLOWED",
                    "الصورة متحرّكة (أكثر من إطار) وهي غير مدعومة — احفظ إطاراً "
                    "واحداً ثابتاً بصيغة PNG أو JPEG ثم أعد الرفع.",
                    "multi-frame image rejected (%d frames)" % frames)

        # F-22: ميزانية الذاكرة تُفحص من الرأس **قبل** أي فكّ ترميز. الحدود
        # الثلاثة السابقة تقيس السلك والبكسلات، ولا يقيس أيّها الرستر الناتج.
        decoded_budget = int(ACS_UPLOAD_MAX_IMAGE_DECODED_BYTES)
        decoded = _decoded_bytes(im.mode, width, height)
        if decoded > decoded_budget:
            _reject("IMAGE_DECODED_TOO_LARGE",
                    "الصورة تحتاج %.0f م.ب من الذاكرة بعد فكّ ضغطها والحدّ "
                    "%.0f م.ب — صدّرها بدقّة أقل (مثلاً ‎4000×2800‎) ثم أعد "
                    "الرفع." % (_mb(decoded), _mb(decoded_budget)),
                    "decoded raster %d bytes (%s %dx%d) exceeds budget %d"
                    % (decoded, im.mode, width, height, decoded_budget))

        # الآن فقط يُحمَّل فعلياً: هذا ما يثبت أن الملف غير مبتور.
        try:
            im.load()
        except UploadRejected:
            raise
        except Exception as exc:
            _reject("IMAGE_CORRUPT",
                    "الصورة ناقصة أو تالفة ولم تكتمل قراءتها — أعد تصديرها "
                    "ثم ارفعها مرّة أخرى.",
                    "decode failed: %s" % type(exc).__name__)

        try:
            fixed = ImageOps.exif_transpose(im) or im
        except Exception:
            fixed = im                              # دوران غير قابل للتفسير: تُترك كما هي

        try:
            normalized, out_size = _reencode(fixed, kind)
        except UploadRejected:
            raise
        except Exception as exc:
            _reject("IMAGE_REENCODE_FAILED",
                    "تعذّرت إعادة ترميز الصورة بأمان — احفظها بصيغة PNG "
                    "بسيطة ثم أعد الرفع.",
                    "re-encode failed: %s" % type(exc).__name__)

        return {
            "media_type": IMAGE_MEDIA_TYPE[kind],
            "width": int(out_size[0]),
            "height": int(out_size[1]),
            "bytes": size,
            "sniffed": kind,
            "normalized": normalized,
        }
    finally:
        try:
            im.close()
        except Exception:
            pass


def _item_parts(item):
    """يقبل bytes أو (bytes, content_type) أو {"data","content_type"}."""
    if isinstance(item, (bytes, bytearray, memoryview)):
        return bytes(item), None
    if isinstance(item, dict):
        return item.get("data"), (item.get("content_type")
                                  or item.get("declared_content_type"))
    if isinstance(item, (tuple, list)):
        if len(item) == 1:
            return item[0], None
        if len(item) >= 2:
            return item[0], item[1]
    return item, None


def validate_images(items):
    """يتحقّق من دفعة صور: سقف العدد صراحةً، وميزانية بكسلات مشتركة.

    لا تُقصّ القائمة بصمت (كان `files[:6]` يبتلع الملفات الزائدة دون أن يعلم
    المستخدم أن نصف مخطّطه لم يُقرأ).
    """
    if items is None:
        _reject("EMPTY_UPLOAD",
                "لم تُرفع صور — اختر صورة واحدة على الأقل ثم أعد المحاولة.",
                "no image list supplied")
    try:
        seq = list(items)
    except TypeError:
        _reject("EMPTY_UPLOAD",
                "لم تُرفع صور — اختر صورة واحدة على الأقل ثم أعد المحاولة.",
                "image list is not iterable")
    if not seq:
        _reject("EMPTY_UPLOAD",
                "لم تُرفع صور — اختر صورة واحدة على الأقل ثم أعد المحاولة.",
                "empty image list")
    max_images = int(ACS_UPLOAD_MAX_IMAGES)
    if len(seq) > max_images:
        _reject("TOO_MANY_FILES",
                "عدد الصور %d والحدّ %d — ارفعها على دفعات حتى لا يسقط جزء من "
                "المخطّط بصمت." % (len(seq), max_images),
                "image count %d exceeds limit %d" % (len(seq), max_images))

    budget = int(ACS_UPLOAD_MAX_IMAGE_PIXELS)
    decoded_budget = int(ACS_UPLOAD_MAX_IMAGE_DECODED_BYTES)
    used = 0
    used_decoded = 0
    out = []
    for index, item in enumerate(seq):
        data, declared = _item_parts(item)
        try:
            result = validate_image(data, declared)
        except UploadRejected as exc:
            # يُعاد رفعه كما هو مع إشارة إلى ترتيب الصورة (لا اسمها ولا بايتاتها).
            raise UploadRejected(exc.code, exc.message_ar,
                                 "image #%d: %s" % (index + 1, exc.detail))
        used += result["width"] * result["height"]
        if used > budget:
            _reject("IMAGE_PIXEL_BUDGET_EXCEEDED",
                    "مجموع أبعاد الصور المرفوعة أكبر من ميزانية المعالجة "
                    "(%d مليون بكسل) — ارفعها على دفعات أصغر أو بدقّة أقل."
                    % (budget // 1000000),
                    "batch pixels %d exceed shared budget %d at image #%d"
                    % (used, budget, index + 1))
        # F-22: ميزانية ذاكرة مشتركة للدفعة أيضاً، وإلا مرّت ستّ صور كلٌّ منها
        # تحت السقف الفردي ومجموعها فوق ما تحتمله النسخة.
        used_decoded += _decoded_bytes("RGBA", result["width"], result["height"])
        if used_decoded > decoded_budget * max_images:
            _reject("IMAGE_DECODED_BUDGET_EXCEEDED",
                    "مجموع ما تحتاجه الصور من الذاكرة بعد فكّ ضغطها أكبر من "
                    "ميزانية المعالجة — ارفعها على دفعات أصغر أو بدقّة أقل.",
                    "batch decoded %d bytes exceed shared budget %d at image #%d"
                    % (used_decoded, decoded_budget * max_images, index + 1))
        result["index"] = index
        out.append(result)
    return out


# -------------------------------------------------------------- PDF --
def _flate_expansion(data, budget):
    """يقيس تمدّد مجاري zlib داخل الملفّ بلا تجاوز الميزانية أصلاً.

    F-23: المسح على البايتات الخام وحدها — لا يلمس بنية pypdf الداخلية ولا
    يعتمد عليها. كل مجرى يُفكّ بـ`decompressobj` بحدّ `max_length`، فلا يُبنى
    في الذاكرة أكثر ممّا تبقّى من الميزانية مهما بلغت نسبة الانضغاط. المجاري
    غير المضغوطة بـFlate (صور JPEG مثلاً) تفشل في zlib فتُتجاوَز بلا كلفة.

    يعيد (المجموع، هل تجاوز الميزانية).
    """
    budget = int(budget)
    total = 0
    position = 0
    length = len(data)
    while position < length:
        start = data.find(b"stream", position)
        if start < 0:
            break
        cursor = start + 6
        if data[cursor:cursor + 2] == b"\r\n":
            cursor += 2
        elif data[cursor:cursor + 1] in (b"\n", b"\r"):
            cursor += 1
        end = data.find(b"endstream", cursor)
        if end < 0:
            break
        position = end + 9
        blob = data[cursor:end]
        if not blob:
            continue
        try:
            engine = zlib.decompressobj()
            room = budget - total + 1          # +1 حتى يظهر التجاوز صراحةً
            produced = len(engine.decompress(blob, room))
            while engine.unconsumed_tail and produced < room:
                produced += len(engine.decompress(engine.unconsumed_tail,
                                                  room - produced))
        except zlib.error:
            continue                            # ليس مجرى Flate — لا شأن لنا به
        total += produced
        if total > budget:
            return total, True
    return total, False


class _PageBudgetReached(Exception):
    """إشارة داخلية: بلغت هذه الصفحة وحدها سقف الأحرف المتبقّي — أوقِف الاستخراج."""


def _extract_page_text(page, room):
    """F-23: استخراج نصّ صفحة واحدة **محدوداً** بالمساحة المتبقّية.

    الحلقة في validate_pdf كانت تفحص الميزانية قبل الصفحة وتقصّ بعدها، لكن
    `page.extract_text()` نفسه كان بلا حدّ: صفحة واحدة قد يتمدّد مجرى محتواها
    إلى ما لا نهاية. قياساً في هذا المستودع، ملفّ PDF بصفحة واحدة حجمه ٧٢ ك.ب
    (مجرى منضغط يتمدّد إلى ١٨٫٤ م.ب) شغّل المعالج ٦٢ ثانية وقُبِل — وسقف الحجم
    المسموح ١٢ م.ب، أي ١٦٦ ضعفاً منه.

    هنا يُمرَّر مراقب نصّي إلى pypdf: يجمع القطع ويتوقّف فور بلوغ المساحة
    المتبقّية، فينتهي تفكيك المجرى عند الحدّ بدل أن يمضي إلى آخره. يعيد
    (النصّ، هل قُطع).
    """
    room = max(0, int(room))
    if room <= 0:
        return "", True
    parts = []
    seen = [0]

    def _visit(text, cm=None, tm=None, font=None, size=None):
        if not text:
            return
        parts.append(text)
        seen[0] += len(text)
        if seen[0] >= room:
            raise _PageBudgetReached()

    try:
        whole = page.extract_text(visitor_text=_visit)
    except _PageBudgetReached:
        return "".join(parts)[:room], True
    except TypeError:
        # نسخة pypdf لا تعرف visitor_text: نعود إلى الاستخراج الكامل مع القصّ.
        whole = page.extract_text() or ""
        return (whole[:room], True) if len(whole) > room else (whole, False)
    whole = whole or ""
    if len(whole) > room:
        return whole[:room], True
    return whole, False


def validate_pdf(data):
    """يتحقّق من PDF في الذاكرة ويستخرج نصّه بحدود صريحة.

    يعيد: {"bytes","pages","text","truncated"}
    لا يستقبل مساراً ولا يكتب ملفاً مؤقتاً: io.BytesIO حصراً.
    """
    if not isinstance(data, (bytes, bytearray, memoryview)):
        _reject("EMPTY_UPLOAD",
                "لم تصل بيانات الملف — أعد اختيار ملف PDF ثم ارفعه.",
                "payload is not bytes: %s" % type(data).__name__)
    data = bytes(data)
    size = len(data)
    if size == 0:
        _reject("EMPTY_UPLOAD",
                "الملف فارغ — اختر ملف PDF صالحاً ثم أعد الرفع.",
                "zero-length pdf payload")
    limit = int(ACS_UPLOAD_MAX_PDF_BYTES)
    if size > limit:
        _reject("PDF_TOO_LARGE",
                "حجم الملف %.1f م.ب — الحدّ %.1f م.ب. قسّم المستند أو صدّره "
                "بجودة أقل ثم أعد الرفع." % (_mb(size), _mb(limit)),
                "pdf bytes %d exceed limit %d" % (size, limit))
    if b"%PDF-" not in data[:1024]:
        _reject("PDF_BAD_SIGNATURE",
                "الملف ليس PDF فعلياً (توقيع الملف غير صحيح) — تأكّد أنك اخترت "
                "ملف PDF ثم أعد الرفع.",
                "missing %PDF- signature within the first 1024 bytes")

    try:
        reader = pypdf.PdfReader(io.BytesIO(data), strict=False)
    except UploadRejected:
        raise
    except Exception as exc:
        _reject("PDF_UNREADABLE",
                "تعذّرت قراءة ملف PDF — يبدو تالفاً أو غير مكتمل. أعد تصديره "
                "من البرنامج الأصلي ثم ارفعه مرّة أخرى.",
                "pdf open failed: %s" % type(exc).__name__)

    try:
        encrypted = bool(getattr(reader, "is_encrypted", False))
    except Exception:
        encrypted = False
    if encrypted:
        opened = False
        try:
            opened = bool(reader.decrypt(""))
        except Exception:
            opened = False
        if not opened:
            _reject("PDF_ENCRYPTED",
                    "ملف PDF محمي بكلمة مرور — أزل الحماية واحفظ نسخة مفتوحة "
                    "ثم ارفعها.",
                    "encrypted pdf: empty-password decrypt refused")

    try:
        pages = reader.pages
        page_count = len(pages)
    except UploadRejected:
        raise
    except Exception as exc:
        _reject("PDF_UNREADABLE",
                "تعذّرت قراءة صفحات ملف PDF — يبدو تالفاً. أعد تصديره ثم "
                "ارفعه مرّة أخرى.",
                "page enumeration failed: %s" % type(exc).__name__)

    max_pages = int(ACS_UPLOAD_MAX_PDF_PAGES)
    if page_count > max_pages:
        # يُرفض **قبل** استخراج أي نص: العدّ وحده هو المعيار، فلا يُستهلك وقت
        # المعالج على مستند ضخم ثم يُرفض.
        _reject("PDF_TOO_MANY_PAGES",
                "عدد صفحات الملف %d والحدّ %d — أرسل الصفحات المطلوبة فقط "
                "(أو قسّم الملف) ثم أعد الرفع." % (page_count, max_pages),
                "page count %d exceeds limit %d" % (page_count, max_pages))

    # F-23: قنبلة الانضغاط تُرفض **قبل** أي استخراج. pypdf يفكّ مجرى الصفحة
    # كاملاً ويحلّله إلى قائمة عمليات قبل أن يبدأ الاستخراج، فلا يوقفه سقف
    # الأحرف. القياس نفسه محدود بالميزانية فلا يصير الفحص هجوماً بذاته.
    expanded_budget = int(ACS_UPLOAD_MAX_PDF_DECOMPRESSED_BYTES)
    expanded, overflowed = _flate_expansion(data, expanded_budget)
    if overflowed:
        _reject("PDF_DECOMPRESSION_BOMB",
                "محتوى الملفّ يتمدّد بعد فكّ ضغطه إلى أكثر من %.0f م.ب وهو فوق "
                "حدّ المعالجة — أعد تصديره من البرنامج الأصلي (أو اطبعه إلى PDF "
                "جديد) ثم ارفعه." % _mb(expanded_budget),
                "flate streams expand beyond %d bytes (file %d bytes)"
                % (expanded_budget, size))

    char_budget = int(ACS_UPLOAD_MAX_PDF_TEXT_CHARS)
    chunks = []
    total = 0
    truncated = False
    for index in range(page_count):
        if total >= char_budget:
            truncated = True
            break
        try:
            piece, cut = _extract_page_text(pages[index], char_budget - total)
        except Exception:
            piece, cut = "", False                  # صفحة عاجزة لا تُسقط المستند
        if cut:
            truncated = True
        if not piece:
            if truncated:
                break
            continue
        room = char_budget - total
        if len(piece) > room:
            piece = piece[:room]
            truncated = True
        chunks.append(piece)
        total += len(piece)
        if truncated:
            break

    return {"bytes": size, "pages": page_count,
            "text": "\n".join(chunks), "truncated": truncated}


# ------------------------------------------------------------- JSON --
def _walk_json(node, depth, state):
    max_depth = int(ACS_UPLOAD_MAX_JSON_DEPTH)
    max_keys = int(ACS_UPLOAD_MAX_JSON_KEYS)
    if depth > max_depth:
        _reject("JSON_TOO_DEEP",
                "بنية الملف متداخلة أعمق من الحدّ (%d مستوى) — بسّط البنية "
                "ثم أعد الرفع." % max_depth,
                "json depth exceeds %d" % max_depth)
    if isinstance(node, dict):
        for key, value in node.items():
            state["keys"] += 1
            if state["keys"] > max_keys:
                _reject("JSON_TOO_MANY_KEYS",
                        "عدد الحقول في الملف أكبر من الحدّ (%d حقل) — قسّم "
                        "الملف ثم أعد الرفع." % max_keys,
                        "json key count exceeds %d" % max_keys)
            if isinstance(key, str) and key in JSON_FORBIDDEN_KEYS:
                _reject("JSON_FORBIDDEN_KEY",
                        "الملف يحتوي حقلاً محجوزاً غير مسموح به — احذف الحقول "
                        "ذات الأسماء المحجوزة ثم أعد الرفع.",
                        "forbidden key present at depth %d" % depth)
            _walk_json(value, depth + 1, state)
    elif isinstance(node, list):
        for value in node:
            _walk_json(value, depth + 1, state)


def validate_json_bytes(data):
    """يتحقّق من مستند JSON مرفوع ويعيد الكائن المحلَّل بعد كل الحدود."""
    if not isinstance(data, (bytes, bytearray, memoryview)):
        _reject("JSON_MALFORMED",
                "لم تصل بيانات الملف — أعد اختياره ثم ارفعه مرّة أخرى.",
                "payload is not bytes: %s" % type(data).__name__)
    data = bytes(data)
    size = len(data)
    if size == 0:
        _reject("JSON_MALFORMED",
                "الملف فارغ — اختر ملف JSON صالحاً ثم أعد الرفع.",
                "zero-length json payload")
    limit = int(ACS_UPLOAD_MAX_JSON_BYTES)
    if size > limit:
        _reject("JSON_TOO_LARGE",
                "حجم الملف %.1f م.ب — الحدّ %.1f م.ب. قسّم الملف ثم أعد الرفع."
                % (_mb(size), _mb(limit)),
                "json bytes %d exceed limit %d" % (size, limit))
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        _reject("JSON_MALFORMED",
                "ترميز الملف ليس UTF-8 — احفظه بترميز UTF-8 ثم أعد الرفع.",
                "json payload is not valid utf-8")
    try:
        parsed = json.loads(text)
    except UploadRejected:
        raise
    except Exception as exc:
        _reject("JSON_MALFORMED",
                "صيغة JSON غير صحيحة — تحقّق من الملف في محرّر JSON ثم أعد "
                "الرفع.",
                "json parse failed: %s" % type(exc).__name__)
    _walk_json(parsed, 1, {"keys": 0})
    return parsed


# -------------------------------------------------------------- DXF --
def validate_dxf_bytes(data):
    """فحص بنيوي رخيص لملف DXF مرفوع — يعيد {"bytes","sections"}."""
    if not isinstance(data, (bytes, bytearray, memoryview)):
        _reject("DXF_MALFORMED",
                "لم تصل بيانات الملف — أعد اختياره ثم ارفعه مرّة أخرى.",
                "payload is not bytes: %s" % type(data).__name__)
    data = bytes(data)
    size = len(data)
    if size == 0:
        _reject("DXF_MALFORMED",
                "الملف فارغ — اختر ملف DXF صالحاً ثم أعد الرفع.",
                "zero-length dxf payload")
    limit = int(ACS_UPLOAD_MAX_DXF_BYTES)
    if size > limit:
        _reject("DXF_TOO_LARGE",
                "حجم الملف %.1f م.ب — الحدّ %.1f م.ب. صدّر الطبقات المطلوبة "
                "فقط ثم أعد الرفع." % (_mb(size), _mb(limit)),
                "dxf bytes %d exceed limit %d" % (size, limit))
    text = data.decode("utf-8", errors="replace")   # لا يرفع استثناءً أبداً
    sections = text.count("SECTION")
    if sections <= 0 and not text.startswith("AutoCAD Binary DXF"):
        _reject("DXF_MALFORMED",
                "الملف لا يبدو ملف DXF صالحاً (لا يحتوي أقساماً) — صدّره من "
                "البرنامج بصيغة DXF ثم أعد الرفع.",
                "no SECTION group found in dxf payload")
    if "ENDSEC" not in text and sections > 0:
        _reject("DXF_MALFORMED",
                "ملف DXF ناقص (قسم غير مغلق) — أعد تصديره كاملاً ثم ارفعه.",
                "SECTION without ENDSEC — truncated dxf")
    return {"bytes": size, "sections": sections}


# ------------------------------------------------------------ الصحّة --
def health_status():
    """الحدود المُعلَنة — صالحة للعرض في /health. لا تحتوي أي سرّ."""
    return {
        "module": "acs_upload_security",
        "contract_version": CONTRACT_VERSION,
        "limits": {
            "max_image_bytes": int(ACS_UPLOAD_MAX_IMAGE_BYTES),
            "max_image_pixels": int(ACS_UPLOAD_MAX_IMAGE_PIXELS),
            "max_image_side": int(ACS_UPLOAD_MAX_IMAGE_SIDE),
            "max_image_decoded_bytes": int(ACS_UPLOAD_MAX_IMAGE_DECODED_BYTES),
            "max_images": int(ACS_UPLOAD_MAX_IMAGES),
            "max_pdf_bytes": int(ACS_UPLOAD_MAX_PDF_BYTES),
            "max_pdf_pages": int(ACS_UPLOAD_MAX_PDF_PAGES),
            "max_pdf_text_chars": int(ACS_UPLOAD_MAX_PDF_TEXT_CHARS),
            "max_pdf_decompressed_bytes":
                int(ACS_UPLOAD_MAX_PDF_DECOMPRESSED_BYTES),
            "max_json_bytes": int(ACS_UPLOAD_MAX_JSON_BYTES),
            "max_json_depth": int(ACS_UPLOAD_MAX_JSON_DEPTH),
            "max_json_keys": int(ACS_UPLOAD_MAX_JSON_KEYS),
            "max_dxf_bytes": int(ACS_UPLOAD_MAX_DXF_BYTES),
        },
        "image_allowed": list(IMAGE_ALLOWED),
        "image_rejected": ["gif"],
        "issue_codes": list(ISSUE_CODES),
        "writes_temp_files": False,
        "uses_filename_as_path": False,
    }
