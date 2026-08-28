from pathlib import Path

path = Path('app.py')
text = path.read_text(encoding='utf-8')

start_marker = '/* ===== V248 FIXLOAD: 2 trang riêng Toán / Vật lí, giữ lõi V246 ổn định ===== */'
end_marker = '/* ===== V233 PWA: cài app lên màn hình chính ===== */'

start = text.find(start_marker)
end = text.find(end_marker)

if start < 0:
    raise SystemExit('Không tìm thấy block V248 trong app.py')
if end < 0 or end <= start:
    raise SystemExit('Không tìm thấy mốc kết thúc V233')

replacement = r'''/* ===== V308 SUBJECT SWITCH: một logic duy nhất cho Toán / Vật lí ===== */
function subjectNorm(s){
  try{
    return String(s || '').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d').replace(/\s+/g,' ').trim();
  }catch(e){ return String(s || '').toLowerCase().trim(); }
}
function subjectKind(s){
  let n=subjectNorm(s);
  if(n.includes('toan')||n.includes('math')) return 'math';
  if(n.includes('vat li')||n.includes('vat ly')||n.includes('vatli')||n.includes('vatly')||n.includes('physics')||n==='ly') return 'physics';
  return '';
}
function findSubject(kind){
  let subjects=[];
  try{
    for(let x of (CATALOG||[])){
      let m=String(x.Mon||'').trim();
      if(m&&!subjects.some(s=>subjectNorm(s)===subjectNorm(m))) subjects.push(m);
    }
  }catch(e){}
  for(let m of subjects) if(subjectKind(m)===kind) return m;
  return kind==='math'?'Toán':(kind==='physics'?'Vật lí':'');
}
function clearSubjectFilters(){
  window.CATALOG_SELECTED_KHOI='';
  ['fLop','fChuong','fBaiHoc','fDangBaiTap','fBoDe','fMucDo','fDang','fSearch'].forEach(id=>{let el=document.getElementById(id);if(el)el.value='';});
}
function setSubjectSelect(id,mon){
  let el=document.getElementById(id);if(!el)return false;
  let target=subjectNorm(mon),found='';
  for(let o of el.options){
    if(subjectNorm(o.value)===target||subjectNorm(o.textContent)===target||(subjectKind(o.value)&&subjectKind(o.value)===subjectKind(mon))){found=o.value;break;}
  }
  el.value=found||mon||'';
  return !!found;
}
function syncSubjectButtons(){
  let mon='';try{let el=document.getElementById('fMon');mon=el?el.value:'';}catch(e){}
  let kind=subjectKind(mon);
  let mathBtn=document.getElementById('topSubjectMathV253');
  let physicsBtn=document.getElementById('topSubjectPhysicsV253');
  if(mathBtn)mathBtn.classList.toggle('active',kind==='math');
  if(physicsBtn)physicsBtn.classList.toggle('active',kind==='physics');
}
function selectSubject(mon){
  mon=String(mon||'').trim();if(!mon)return;
  clearSubjectFilters();
  setSubjectSelect('fMon',mon);
  try{refreshFilterOptions();}catch(e){console.error('refreshFilterOptions:',e);}
  setSubjectSelect('fMon',mon);
  try{setSubjectSelect('rpMon',mon);if(typeof onRpScopeChange==='function')onRpScopeChange('mon');}catch(e){}
  try{renderCatalog();}catch(e){console.error('renderCatalog:',e);}
  setTimeout(syncSubjectButtons,0);
}
function v253SelectSubject(kind){
  let mon=findSubject(kind);
  if(!mon){alert(kind==='math'?'Không tìm thấy dữ liệu môn Toán.':'Không tìm thấy dữ liệu môn Vật lí.');return false;}
  selectSubject(mon);return false;
}
function v253ToggleSubjectTabs(){
  let box=document.getElementById('topSubjectTabsV253');if(!box)return;
  let show=box.classList.contains('subjectTabsHiddenV253');
  if(typeof v253SetSubjectTabsVisible==='function')v253SetSubjectTabsVisible(show);
  else box.classList.toggle('subjectTabsHiddenV253',!show);
}
document.addEventListener('change',function(ev){
  if(!ev.target||ev.target.id!=='fMon')return;
  setTimeout(syncSubjectButtons,0);
});
document.addEventListener('click',function(ev){
  let btn=ev.target&&ev.target.closest?ev.target.closest('#topSubjectMathV253,#topSubjectPhysicsV253'):null;
  if(!btn)return;
  ev.preventDefault();ev.stopPropagation();
  v253SelectSubject(btn.id==='topSubjectMathV253'?'math':'physics');
},true);
document.addEventListener('DOMContentLoaded',function(){setTimeout(syncSubjectButtons,300);});
'''

new_text = text[:start] + replacement + text[end:]
compile(new_text, 'app.py', 'exec')
path.write_text(new_text, encoding='utf-8')
print('PATCH_OK')
