const vm = require('vm'), fs = require('fs'), assert = require('assert'), path = require('path');
class Element {
  constructor(tag='div') { this.tagName=tag; this.children=[]; this.innerHTML=''; this.textContent=''; this.classList={add(){}}; }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.children=items; this.innerHTML=''; }
  setAttribute() {}
}
const ids=Object.fromEntries(['raceNotice','raceControls','raceClock','raceNav','raceQuestion','raceActions','raceRanks','raceFull'].map(id=>[id,new Element()]));
let shown=0, phase='running', poll, draft={}, calls=[];
const response=()=>({ok:true,host:false,state:phase,mode:'numeric',now:100,started:90,duration:60,ranking:[],capacity:200,total:2,joined:true,shown,review:phase==='closed'?[{correct:false,parts:[{label:'A (độ)',answer:'60',expected:'55,42'},{label:'S',answer:'8,19',expected:'12,34'}],solution:'Lời giải riêng'}]:undefined,questions:[{kind:'TLN',text:'Riêng em: AB=13',numeric:true,components:2,decimal_places:2,component_labels:['A (độ)','S']},{kind:'TLN',text:'Riêng em: BC=24',numeric:true}],answers:{...draft},finished:false});
const sandbox={console,document:{getElementById:id=>ids[id],createElement:tag=>new Element(tag),addEventListener(){}},window:{RACE_CONFIG:{code:'CODE',csrf:'csrf',host:false}},location:{origin:'http://example.com'},navigator:{},confirm:()=>true,setInterval(fn,ms){if(ms===3000)poll=fn;},setTimeout(){return 1;},clearTimeout(){},fetch:async(url,opt)=>{const p=opt.body?JSON.parse(opt.body):null;calls.push(p);if(p?.answers)draft=p.answers;return {ok:true,json:async()=>response()};}};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../static/practice-race.js'),'utf8'),sandbox);
const settle=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
  await settle();
  let fields=ids.raceQuestion.children[0];
  assert.equal(fields.children.length,2);
  assert.equal(fields.children[0].children[0].textContent,'A (độ)');
  const first=fields.children[0].children[1], second=fields.children[1].children[1];
  second.value='8,19'; second.oninput(); second.onchange(); await settle();
  assert.equal(draft['0'],';8,19'); // An empty first part must retain its position.
  first.value='60'; first.oninput(); first.onchange(); await settle();
  assert.equal(draft['0'],'60;8,19');
  shown=1; await poll();
  first.onchange(); await settle(); // Late blur still belongs to the old question.
  assert.equal(draft['1'],undefined);
  shown=0; await poll();
  fields=ids.raceQuestion.children[0];
  assert.equal(fields.children[0].children[1].value,'60');
  assert.equal(fields.children[1].children[1].value,'8,19');
  phase='closed'; await poll();
  assert(ids.raceQuestion.children[0].children.every(label=>label.children[1].disabled));
  const review=ids.raceQuestion.children[1].innerHTML;
  assert(review.includes('Em đã nhập')); assert(review.includes('Đáp án đúng'));
  assert(review.includes('8,19')); assert(review.includes('12,34'));
  assert(review.includes('Lời giải riêng'));
  console.log('PASS: separate labeled fields preserve commas, blank positions, drafts, late blur and read-only review');
})().catch(e=>{console.error(e);process.exit(1);});
