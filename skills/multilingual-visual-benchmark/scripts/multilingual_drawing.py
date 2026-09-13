"""HarfBuzz + FreeType text shaping for Latin/CJK/Arabic/Devanagari in raster figures."""
from functools import lru_cache

import freetype
import numpy as np
import uharfbuzz as hb
from PIL import Image
import unicodedata
from bidi import algorithm as bidi_algorithm

import os
FONT=os.environ.get('MVISQA_FONT','/System/Library/Fonts/Supplemental/Arial Unicode.ttf')
FONT_BYTES=open(FONT,'rb').read()
HB_FACE=hb.Face(FONT_BYTES)
MISSING_GLYPHS=[]
USED_FONTS=set()
FALLBACK_FONTS=[p for p in os.environ.get('MVISQA_FALLBACK_FONTS',
    '/System/Library/Fonts/KohinoorBangla.ttc:/System/Library/Fonts/GeezaPro.ttc:/System/Library/Fonts/KohinoorTelugu.ttc').split(os.pathsep) if os.path.isfile(p)]


@lru_cache(maxsize=32)
def font_face(path):
    return hb.Face(open(path,'rb').read())


@lru_cache(maxsize=16384)
def supports(path,text):
    face=freetype.Face(path)
    return all(face.get_char_index(ord(c)) or unicodedata.category(c)=='Cf' for c in text)


def font_runs(text,direction):
    # Keep the original font and shaping byte-for-byte when it covers a whole run.
    if supports(FONT,text):return [(text,FONT)]
    groups=[]
    for char in text:
        name=unicodedata.name(char,'')
        script=next((s for s in ('ARABIC','BENGALI','TELUGU','TAMIL','DEVANAGARI','THAI') if name.startswith(s)),'common')
        if unicodedata.category(char)=='Cf' and groups:script=groups[-1][0]
        if groups and groups[-1][0]==script:groups[-1][1]+=char
        else:groups.append([script,char])
    result=[]
    for _,part in groups:
        path=next((p for p in [FONT]+FALLBACK_FONTS if supports(p,part)),FONT)
        result.append((part,path))
    return result[::-1] if direction=='rtl' else result


def bidi_runs(text):
    """Return logical text per directional run, in visual left-to-right order."""
    if not any(unicodedata.bidirectional(c) in ('R','AL') for c in text):
        return [(text,'ltr')]
    storage=bidi_algorithm.get_empty_storage()
    storage['base_level']=bidi_algorithm.get_base_level(text)
    storage['base_dir']=('L','R')[storage['base_level']]
    bidi_algorithm.get_embedding_levels(text,storage)
    bidi_algorithm.explicit_embed_and_overrides(storage,False)
    bidi_algorithm.resolve_weak_types(storage,False)
    bidi_algorithm.resolve_neutral_types(storage,False)
    bidi_algorithm.resolve_implicit_levels(storage,False)
    bidi_algorithm.reorder_resolved_levels(storage,False)
    groups=[]
    for char in storage['chars']:
        level=char['level']
        if groups and groups[-1][0]==level:groups[-1][1].append(char['ch'])
        else:groups.append((level,[char['ch']]))
    # HarfBuzz performs glyph shaping and RTL mirroring inside each logical run.
    # It does not implement the paragraph-level Unicode bidi algorithm itself.
    return [(''.join(chars[::-1] if level%2 else chars),'rtl' if level%2 else 'ltr')
            for level,chars in groups]


@lru_cache(maxsize=4096)
def mask(text,size):
    size=int(size)
    if not str(text):return Image.new('L',(1,max(1,size)),0)
    text=str(text).replace('\t','    ')
    if '\n' in text:
        lines=[mask(line,size) for line in text.split('\n')]
        spacing=max(size+4,max(m.height for m in lines)+4)
        result=Image.new('L',(max(m.width for m in lines),spacing*len(lines)),0)
        for i,line in enumerate(lines):
            result.paste(line,((result.width-line.width)//2,i*spacing))
        return result
    parts=[];penx=0;peny=0
    shaped_runs=[(part,direction,path) for run,direction in bidi_runs(text) for part,path in font_runs(run,direction)]
    for run,direction,path in shaped_runs:
        USED_FONTS.add(path)
        font=hb.Font(font_face(path));font.scale=(size*64,size*64)
        hb.ot_font_set_funcs(font)
        ft=freetype.Face(path);ft.set_char_size(size*64)
        buf=hb.Buffer();buf.add_str(run);buf.guess_segment_properties();buf.direction=direction;hb.shape(font,buf)
        for info,pos in zip(buf.glyph_infos,buf.glyph_positions):
            if info.codepoint==0:MISSING_GLYPHS.append(str(text))
            ft.load_glyph(info.codepoint,freetype.FT_LOAD_RENDER)
            bitmap=ft.glyph.bitmap
            if bitmap.width and bitmap.rows:
                a=np.asarray(bitmap.buffer,dtype=np.uint8).reshape(bitmap.rows,abs(bitmap.pitch))[:,:bitmap.width]
                x=round(penx+pos.x_offset/64+ft.glyph.bitmap_left)
                y=round(-peny-pos.y_offset/64-ft.glyph.bitmap_top)
                parts.append((x,y,Image.fromarray(a,'L')))
            penx+=pos.x_advance/64;peny+=pos.y_advance/64
    if not parts:return Image.new('L',(max(1,round(abs(penx))),max(1,size)),0)
    left=min(p[0] for p in parts);top=min(p[1] for p in parts)
    right=max(p[0]+p[2].width for p in parts);bottom=max(p[1]+p[2].height for p in parts)
    result=Image.new('L',(max(1,right-left),max(1,bottom-top)),0)
    for x,y,im in parts:
        # lighter() merges overlapping shaped glyphs without erasing earlier strokes.
        from PIL import ImageChops
        patch=result.crop((x-left,y-top,x-left+im.width,y-top+im.height))
        result.paste(ImageChops.lighter(patch,im),(x-left,y-top))
    return result


def put(canvas,text,x,y,size=30,color='#202626',anchor='center',max_width=None,rotate=0):
    text=str(text)
    m=mask(text,size)
    while max_width and m.width>max_width and size>13:
        size-=1;m=mask(text,size)
    if rotate:m=m.rotate(rotate,expand=True)
    rgba=Image.new('RGBA',m.size,color);rgba.putalpha(m)
    left=round(x-(m.width/2 if anchor=='center' else m.width if anchor=='right' else 0))
    top=round(y-m.height/2)
    canvas.paste(rgba,(left,top),rgba)
    return {'text':text,'font_size':size,'box':[left,top,left+m.width,top+m.height],
            'inside_canvas':left>=0 and top>=0 and left+m.width<=canvas.width and top+m.height<=canvas.height}


def text_clusters(text):
    """Conservative wrapping units: keep marks, joiners and Indic conjuncts intact."""
    clusters=[]
    join_next=False
    for char in str(text):
        mark=unicodedata.category(char).startswith('M')
        joiner=char in ('\u200c','\u200d')
        if clusters and (mark or joiner or join_next):clusters[-1]+=char
        else:clusters.append(char)
        name=unicodedata.name(char,'')
        join_next=joiner or 'VIRAMA' in name or char in '\u0e40\u0e41\u0e42\u0e43\u0e44'
    return clusters


def wrap(text,max_width,size):
    text=str(text).strip()
    if not text:return ['']
    if '\n' in text:
        return [line for paragraph in text.split('\n') for line in wrap(paragraph,max_width,size)]
    # Word wrapping for scripts using spaces; character wrapping for CJK phrases.
    words=text.split(' ') if ' ' in text else text_clusters(text)
    join=' ' if ' ' in text else ''
    lines=[];current=''
    for word in words:
        if mask(word,size).width>max_width:
            if current:lines.append(current);current=''
            chunk=''
            for char in text_clusters(word):
                candidate=chunk+char
                if chunk and mask(candidate,size).width>max_width:
                    lines.append(chunk);chunk=char
                else:chunk=candidate
            if chunk:current=chunk
            continue
        candidate=current+join+word if current else word
        if current and mask(candidate,size).width>max_width:
            lines.append(current);current=word
        else:current=candidate
    if current:lines.append(current)
    return lines
