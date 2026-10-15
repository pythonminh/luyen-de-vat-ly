const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
class Element{constructor(){this.children=[];this.classList={add(){}};}append(...items){this.children.push(...items)}replaceChildren(...items){this.children=items}setAttribute(){}}
const ids=Object.fromEntries(['raceNotice','raceControls','raceClock','raceNav','raceQuestion','raceActions','raceRanks','raceFull'].map(id=>[id,new Element()]));
const events={};
let available=350;
const long={style:{},parentElement:{get clientWidth(){return available}},querySelector(){return {getBoundingClientRect:()=>({width:900*parseFloat(long.style.fontSize)/100})}}};
const short={style:{},parentElement:{get clientWidth(){return available}},querySelector(){return {getBoundingClientRect:()=>({width:100*parseFloat(short.style.fontSize)/100})}}};
const root={clientWidth:390,querySelectorAll:()=>[long,short],addEventListener(type,fn){events[type]=fn}};
const sandbox={console,document:{body:{classList:{add(){}}},querySelector:()=>root,getElementById:id=>ids[id],createElement:()=>new Element(),addEventListener(){},fonts:{addEventListener(type,fn){events[type]=fn}}},window:{RACE_CONFIG:{code:'TEST',host:false},requestAnimationFrame(fn){assert.equal(this,sandbox.window);fn();},addEventListener(type,fn){events[type]=fn}},location:{origin:'http://example.com'},setInterval(){},setTimeout(){},clearTimeout(){},fetch:async()=>({ok:true,json:async()=>({ok:true,state:'waiting',now:1,duration:60,ranking:[],capacity:200,total:5,joined:true})})};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../static/practice-race.js'),'utf8'),sandbox);
assert(long.querySelector().getBoundingClientRect().width<=available);
assert.equal(short.style.fontSize,'100%');
available=280;root.clientWidth=320;events.resize();
assert(long.querySelector().getBoundingClientRect().width<=available);
available=1100;root.clientWidth=1280;events.resize();assert.equal(long.style.fontSize,'100%');
available=280;root.clientWidth=320;events.loadingdone();assert(long.querySelector().getBoundingClientRect().width<=available);
console.log('PASS: long equations fit narrow screens; short equations keep normal size; resize and font loading refit');
