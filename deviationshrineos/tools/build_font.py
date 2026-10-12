"""Build a scalable pixel font from TempleOS's public-domain 8x8 font table."""
import re, json
from pathlib import Path
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
root=Path(__file__).resolve().parents[1]/'dist/assets'
values=json.loads((root/'font-bitmap.json').read_text())
assert len(values)==256
fb=FontBuilder(800,isTTF=True)
order=['.notdef']+['u%04X'%i for i in range(32,127)]
fb.setupGlyphOrder(order)
glyphs={}; metrics={}
for name in order:
 pen=TTGlyphPen(None)
 n=int(values[int(name[1:],16)],16) if name!='.notdef' else 0
 for y in range(8):
  row=(n>>(8*y))&255
  for x in range(8):
   if row&(1<<x):
    x0=x*100; y0=(7-y)*100
    pen.moveTo((x0,y0));pen.lineTo((x0,y0+100));pen.lineTo((x0+100,y0+100));pen.lineTo((x0+100,y0));pen.closePath()
 glyphs[name]=pen.glyph();metrics[name]=(800,0)
fb.setupGlyf(glyphs);fb.setupHorizontalMetrics(metrics)
fb.setupHorizontalHeader(ascent=800,descent=0,lineGap=0)
fb.setupCharacterMap({i:'u%04X'%i for i in range(32,127)})
fb.setupNameTable({'familyName':'Shrine VGA','styleName':'Regular','uniqueFontIdentifier':'ShrineVGA-1','fullName':'Shrine VGA Regular','psName':'ShrineVGA','version':'Version 1.0','licenseDescription':'TempleOS public-domain bitmap; vector conversion for DeviationShrineOS.'})
fb.setupOS2(sTypoAscender=800,sTypoDescender=0,sTypoLineGap=0,usWinAscent=800,usWinDescent=0)
fb.setupPost();fb.setupMaxp();fb.font.flavor='woff';fb.save(root/'shrine-vga.woff')
print('95 bitmap glyphs converted to WOFF')
