const vm = require('vm'), fs = require('fs'), assert = require('assert'), path = require('path');
class Element {
  constructor(tag='div') { this.tagName=tag; this.children=[]; this.innerHTML=''; this.textContent=''; this.classList={add(){}}; }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.children=items; this.innerHTML=''; }
  setAttribute() {}
}
const ids=Object.fromEntries(['raceNotice','raceControls','raceClock','raceNav','raceQuestion','raceActions','raceRanks','raceFull'].map(id=>[id,new Element()]));
let shown=0, phase='running', poll, draft={}, calls=[];
const response=()=>({ok:true,host:false,state:phase,mode:'numeric',now:100,started:90,duration:60,ranking:[],capacity:200,total:2,joined:true,shown,questions:[{kind:'DS',text:'Câu ĐS riêng 1',statements:['a','b','c','d']},{kind:'DS',text:'Câu ĐS riêng 2',statements:['a','b','c','d']}],answers:{...draft},finished:false});
const sandbox={console,document:{getElementById:id=>ids[id],createElement:tag=>new Element(tag),addEventListener(){}},window:{RACE_CONFIG:{code:'CODE',csrf:'csrf',host:false}},location:{origin:'http://example.com'},navigator:{},confirm:()=>true,setInterval(fn,ms){if(ms===3000)poll=fn;},setTimeout(){return 1;},clearTimeout(){},fetch:async(url,opt)=>{const p=opt.body?JSON.parse(opt.body):null;calls.push(p);if(p?.answers)draft=p.answers;return {ok:true,json:async()=>response()};}};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../static/practice-race.js'),'utf8'),sandbox);
const settle=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
  await settle();
  const oldSelect=ids.raceQuestion.children[0].children[1];
  oldSelect.value='1';oldSelect.onchange();await settle();
  await ids.raceActions.children.find(b=>b.textContent==='Câu tiếp →').onclick();
  assert(ids.raceQuestion.innerHTML.includes('Câu ĐS riêng 2'));
  await poll();assert(ids.raceQuestion.innerHTML.includes('Câu ĐS riêng 2'));
  oldSelect.value='0';oldSelect.onchange();await settle();
  assert.equal(draft['0'][0],false);assert.equal(draft['1'],undefined);
  const secondSelect=ids.raceQuestion.children[1].children[1];secondSelect.value='1';secondSelect.onchange();await settle();
  await ids.raceNav.children[0].onclick();
  assert.equal(ids.raceQuestion.children[0].children[1].value,'0');
  shown=1;await poll();assert(ids.raceQuestion.innerHTML.includes('Câu ĐS riêng 2'));
  assert.equal(ids.raceQuestion.children[1].children[1].value,'1');
  console.log('PASS: student can advance DS questions, polling keeps position, teacher changes sync, late selection saves to correct question');
})().catch(e=>{console.error(e);process.exit(1);});
