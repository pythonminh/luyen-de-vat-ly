# -*- coding: utf-8 -*-
"""Build bank_index.json from all LaTeX files under ngan-hang/."""
from __future__ import annotations
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
BANK_DIR=ROOT/'ngan-hang'
OUTPUT=ROOT/'bank_index.json'
QUESTION_RE=re.compile(r"\\begin\s*\{\s*(?:ex|bt)\s*\}",re.I)
DANG_RE=re.compile(r"\\dangbt\s*\{([^{}]*)\}",re.I)
HEADER_RE=re.compile(r"^\s*%\s*(Môn|Lớp|Chương|Bài)\s*:\s*(.+?)\s*$",re.I|re.M)
def clean(v): return re.sub(r'\s+',' ',v or '').strip()
def get_header(text):
 m={'môn':'Mon','lớp':'Lop','chương':'Chuong','bài':'BaiHoc'}; out={}
 for x in HEADER_RE.finditer(text):
  k=clean(x.group(1)).lower(); v=clean(x.group(2))
  if k in m and v: out[m[k]]=v
 if 'BaiHoc' in out: out['De']=out['BaiHoc']
 return out
def count_questions(text):
 positions=[m.start() for m in QUESTION_RE.finditer(text)]
 markers=[(m.start(),clean(m.group(1))) for m in DANG_RE.finditer(text)]
 counts={}; i=0; current=''
 for pos in positions:
  while i<len(markers) and markers[i][0]<pos: current=markers[i][1]; i+=1
  name=current or 'Chưa phân dạng'; counts[name]=counts.get(name,0)+1
 return len(positions),counts
def path_meta(rel):
 parts=[p for p in rel.replace('\\','/').split('/') if p]
 if parts and parts[0].lower()=='ngan-hang': parts=parts[1:]
 r={'Mon':parts[0] if len(parts)>0 else '','Lop':parts[1] if len(parts)>1 else '','Chuong':parts[2] if len(parts)>2 else '','BaiHoc':parts[3] if len(parts)>3 else ''}
 if r['Lop'].lower().startswith('lớp '): r['Lop']=r['Lop'][4:].strip()
 if r['Lop'].lower().startswith('lop '): r['Lop']=r['Lop'][4:].strip()
 r['De']=r['BaiHoc']; return r
def build():
 if not BANK_DIR.exists(): raise SystemExit(f'Không tìm thấy {BANK_DIR}')
 lessons=[]
 for fp in sorted(BANK_DIR.rglob('*.tex'),key=lambda p:str(p).lower()):
  try: text=fp.read_text(encoding='utf-8',errors='replace')
  except Exception as e: print('[WARN]',fp,e); continue
  rel=fp.relative_to(ROOT).as_posix(); meta={**path_meta(rel),**get_header(text)}; n,d=count_questions(text)
  lessons.append({'id':rel,'file':rel,'path':rel,'Mon':meta.get('Mon',''),'Lop':meta.get('Lop',''),'Chuong':meta.get('Chuong',''),'BaiHoc':meta.get('BaiHoc',''),'De':meta.get('De',''),'questions':n,'count':n,'dang':d})
 index={'schema':1,'source':'GitHub','generated_by':'scripts/build_bank_index.py','total_files':len(lessons),'total_questions':sum(x['questions'] for x in lessons),'lessons':lessons}
 OUTPUT.write_text(json.dumps(index,ensure_ascii=False,indent=2),encoding='utf-8')
 print(f'[OK] {OUTPUT.name}: {len(lessons)} file, {index["total_questions"]} câu')
if __name__=='__main__': build()
