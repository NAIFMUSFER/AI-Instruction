"""Deterministic embedded Unicode text for ACS PDF serializers.

Shaping changes glyph presentation only. /ActualText preserves the original
logical label and /ToUnicode preserves searchable glyph text. No source model
or approval is modified. Imports stay lazy for the server's no-provider boot.
"""
from pathlib import Path
import io
import math
import unicodedata

FONT = Path(__file__).resolve().parent / 'assets/fonts/DejaVuSans.ttf'


class PdfTextError(ValueError):
    pass


def _number(value):
    if not math.isfinite(float(value)):
        raise PdfTextError('PDF_TEXT_POSITION_INVALID')
    return ('%.4f' % value).rstrip('0').rstrip('.') or '0'


class PdfUnicodeFont:
    def __init__(self):
        from fontTools.ttLib import TTFont
        self.font = TTFont(FONT, recalcTimestamp=False)
        self.cmap = self.font.getBestCmap()
        self.codes = {}
        self.units = self.font['head'].unitsPerEm

    def shape(self, value):
        import arabic_reshaper
        from bidi.algorithm import get_display
        text = str(value)
        if len(text) > 4096 or any(unicodedata.category(c) == 'Cc' for c in text):
            raise PdfTextError('PDF_TEXT_TOO_LONG_OR_CONTROL_CHARACTER')
        # Retain vowel marks and correct their position before visual reordering.
        reshaper = arabic_reshaper.ArabicReshaper(configuration={
            'delete_harakat': False, 'shift_harakat_position': True})
        try:
            visual = get_display(reshaper.reshape(text))
        except (AssertionError, ValueError) as exc:
            raise PdfTextError('PDF_TEXT_DIRECTION_UNSUPPORTED') from exc
        if any(ord(ch) not in self.cmap for ch in visual):
            raise PdfTextError('PDF_FONT_CHARACTER_UNSUPPORTED')
        for ch in visual:
            if ch not in self.codes:
                self.codes[ch] = len(self.codes) + 1
        width = sum(self.font['hmtx'][self.cmap[ord(ch)]][0] for ch in visual) / self.units
        return text, visual, width

    def command(self, value, x, y, size, *, center=False, max_width=None):
        logical, visual, width = self.shape(value)
        if max_width is not None and width * size > max_width and width:
            size = max_width / width
        if center:
            x -= width * size / 2
        glyphs = ''.join('%04X' % self.codes[ch] for ch in visual)
        actual = ('\ufeff' + logical).encode('utf-16-be').hex().upper()
        return ('/Span << /ActualText <%s> >> BDC\n'
                'BT /F2 %s Tf %s %s Td <%s> Tj ET\nEMC' % (
                    actual, _number(size), _number(x), _number(y), glyphs))

    def append_objects(self, objects):
        """Append a self-contained Type0 font; return its one-based PDF ID."""
        from fontTools import subset
        from fontTools.ttLib import TTFont
        font = TTFont(FONT, recalcTimestamp=False)
        options = subset.Options()
        options.recalc_timestamp = False
        options.drop_tables += ['FFTM']
        sub = subset.Subsetter(options=options)
        sub.populate(unicodes=[ord(c) for c in self.codes])
        sub.subset(font)
        out = io.BytesIO()
        font.save(out)
        font_data = out.getvalue()
        cmap = font.getBestCmap()
        scale = 1000 / self.units
        widths = [round(self.font['hmtx'][self.cmap[ord(ch)]][0] * scale) for ch in self.codes]
        gids = b'\0\0' + b''.join(font.getGlyphID(cmap[ord(ch)]).to_bytes(2, 'big') for ch in self.codes)
        pairs = ['<%04X> <%s>' % (cid, unicodedata.normalize('NFKC', ch).encode('utf-16-be').hex().upper())
                 for ch, cid in self.codes.items()]
        cm = ['/CIDInit /ProcSet findresource begin', '12 dict begin', 'begincmap',
              '/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def',
              '/CMapName /ACSUnicode def', '/CMapType 2 def',
              '1 begincodespacerange', '<0000> <FFFF>', 'endcodespacerange']
        for start in range(0, len(pairs), 100):
            group = pairs[start:start + 100]
            cm += [str(len(group)) + ' beginbfchar', *group, 'endbfchar']
        cm += ['endcmap', 'CMapName currentdict /CMap defineresource pop', 'end', 'end']
        cmap_data = '\n'.join(cm).encode('ascii')
        first = len(objects) + 1
        font_id, cid_id, descriptor_id, data_id, unicode_id, gid_id = range(first, first + 6)
        head, hhea = self.font['head'], self.font['hhea']
        bbox = ' '.join(str(round(v * scale)) for v in (head.xMin, head.yMin, head.xMax, head.yMax))
        def stream(data, extra=''):
            return ('<< /Length %d %s >>\nstream\n' % (len(data), extra)).encode('ascii') + data + b'\nendstream'
        objects.extend([
            ('<< /Type /Font /Subtype /Type0 /BaseFont /ACSDejaVuSans /Encoding /Identity-H '
             '/DescendantFonts [%d 0 R] /ToUnicode %d 0 R >>' % (cid_id, unicode_id)).encode(),
            ('<< /Type /Font /Subtype /CIDFontType2 /BaseFont /ACSDejaVuSans '
             '/CIDSystemInfo << /Registry (Adobe) /Ordering (Identity) /Supplement 0 >> '
             '/FontDescriptor %d 0 R /CIDToGIDMap %d 0 R /DW 1000 /W [1 [%s]] >>' % (
                 descriptor_id, gid_id, ' '.join(map(str, widths)))).encode(),
            ('<< /Type /FontDescriptor /FontName /ACSDejaVuSans /Flags 32 /FontBBox [%s] '
             '/ItalicAngle 0 /Ascent %d /Descent %d /CapHeight %d /StemV 80 /FontFile2 %d 0 R >>' % (
                 bbox, round(hhea.ascent * scale), round(hhea.descent * scale),
                 round(hhea.ascent * scale), data_id)).encode(),
            stream(font_data, '/Length1 %d' % len(font_data)), stream(cmap_data), stream(gids),
        ])
        return font_id
