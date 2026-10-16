const vm = require('vm'), fs = require('fs'), assert = require('assert'), path = require('path');
class Element {
  constructor(tag='div') { this.tagName=tag; this.children=[]; this.innerHTML=''; this.textContent=''; this.classList={add(){}}; }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.children=items; this.innerHTML=''; }
  setAttribute() {}
}
const ids=Object.fromEntries(['raceNotice','raceControls','raceClock','raceNav','raceQuestion','raceActions','raceRanks','raceFull'].map(id=>[id,new Element()]));
let finished=true;let shown=0, phase='running', poll, draft={}, calls=[];
const response=()=>({ok:true,host:false,state:phase,mode:'numeric',now:100,started:90,duration:60,ranking:[],capacity:200,total:2,joined:true,shown,questions:[{kind:'TLN',text:'Riêng em: AB=13',numeric:true},{kind:'TLN',text:'Riêng em: BC=24',numeric:true}],answers:{...draft},finished});
const sandbox={console,document:{getElementById:id=>ids[id],createElement:tag=>new Element(tag),addEventListener(){}},window:{RACE_CONFIG:{code:'CODE',csrf:'csrf',host:false}},location:{origin:'http://example.com'},navigator:{},confirm:()=>true,setInterval(fn,ms){if(ms===3000)poll=fn;},setTimeout(){return 1;},clearTimeout(){},fetch:async(url,opt)=>{const p=opt.body?JSON.parse(opt.body):null;calls.push(p);if(p?.action==='reopen')finished=false;if(p?.answers)draft=p.answers;return {ok:true,json:async()=>response()};}};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../static/practice-race.js'),'utf8'),sandbox);
const settle=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
  await settle();assert(ids.raceQuestion.children[0].disabled);
  const reopen=ids.raceActions.children.find(b=>b.textContent.includes('Chỉnh sửa bài đã nộp'));
  assert(reopen);await reopen.onclick();
  assert(!ids.raceQuestion.children[0].disabled);
  assert(ids.raceActions.children.some(b=>b.textContent==='🏁 Nộp bài'));
  phase='closed';await poll();
  assert(!ids.raceActions.children.some(b=>b.textContent.includes('Chỉnh sửa bài đã nộp')));
  assert(ids.raceQuestion.children[0].disabled);
  console.log('PASS: submitted student can reopen before closure and edit; closed room remains locked');
})().catch(e=>{console.error(e);process.exit(1);});
