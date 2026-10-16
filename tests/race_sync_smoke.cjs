const vm = require('vm'), fs = require('fs'), assert = require('assert'), path = require('path');
class Element {
  constructor(tag='div') { this.tagName=tag; this.children=[]; this.innerHTML=''; this.textContent=''; this.classList={add(){}}; }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.children=items; this.innerHTML=''; }
  setAttribute() {}
}
const ids=Object.fromEntries(['raceNotice','raceControls','raceClock','raceNav','raceQuestion','raceActions','raceRanks','raceFull'].map(id=>[id,new Element()]));
let shown=0, phase='running', poll, draft={}, calls=[];
const response=()=>({ok:true,host:false,state:phase,mode:'numeric',now:100,started:90,duration:60,ranking:[],capacity:200,total:2,joined:true,shown,questions:[{kind:'TLN',text:'Riêng em: AB=13',numeric:true},{kind:'TLN',text:'Riêng em: BC=24',numeric:true}],answers:{...draft},finished:false});
const sandbox={console,document:{getElementById:id=>ids[id],createElement:tag=>new Element(tag),addEventListener(){}},window:{RACE_CONFIG:{code:'CODE',csrf:'csrf',host:false}},location:{origin:'http://example.com'},navigator:{},confirm:()=>true,setInterval(fn,ms){if(ms===3000)poll=fn;},setTimeout(){return 1;},clearTimeout(){},fetch:async(url,opt)=>{const p=opt.body?JSON.parse(opt.body):null;calls.push(p);if(p?.answers)draft=p.answers;return {ok:true,json:async()=>response()};}};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../static/practice-race.js'),'utf8'),sandbox);
const settle=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
  await settle();
  assert(ids.raceQuestion.innerHTML.includes('AB=13'));
  assert(ids.raceNav.children.every(b=>!b.disabled));
  await ids.raceNav.children[1].onclick(); await poll();
  assert(ids.raceQuestion.innerHTML.includes('BC=24')); // Polling must not undo free navigation.
  await ids.raceNav.children[0].onclick();
  const first=ids.raceQuestion.children[0]; first.value='sqrt(67)'; first.oninput();
  shown=1; await poll();
  assert(ids.raceQuestion.innerHTML.includes('BC=24'));
  assert(ids.raceActions.children.some(b=>b.textContent==='← Câu trước'));
  // A delayed blur from the old input must still save the first question.
  first.onchange(); await settle();
  assert.equal(draft['0'],'sqrt(67)'); assert.equal(draft['1'],undefined);
  const second=ids.raceQuestion.children[0]; second.value='24'; second.oninput(); second.onchange(); await settle();
  shown=0; await poll();
  assert.equal(ids.raceQuestion.children[0].value,'sqrt(67)');
  assert.equal(draft['1'],'24');
  phase='closed'; await poll();
  assert(ids.raceNav.children.every(b=>!b.disabled));
  console.log('PASS: follows ADMIN, preserves separate questions and drafts, handles late blur, enables review after closing');
})().catch(e=>{console.error(e);process.exit(1);});
