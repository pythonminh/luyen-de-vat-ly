const assert=require('node:assert/strict');
require('../static/dynamic-practice.js');
const {Q,solve,generate}=global.DynamicPracticeEngine;
const cases={amplitude:[['12'],'6'],projection:[['10','5'],'10;5'],period:[['1','30'],'2'],orbit:[['10','120'],'6'],distance:[['2.5','4','6','3.75'],'75'],rotation:[['15','2'],'1;1'],spring:[['25','12.5','0.08'],'12,8']};
for(const [key,[p,answer]] of Object.entries(cases)){
 assert.equal(solve(key,p).answer,answer);
 for(let i=0;i<1000;i++){
  const next=generate(key,p),r=solve(key,next);
  assert.notDeepEqual(next,p);
  assert.equal(r.choices.length,4);
  assert.equal(r.choices.filter(c=>c.correct).length,1);
  assert.equal(new Set(r.choices.map(c=>c.text)).size,4);
 }
}
assert.equal(String(Q.of('1/3')),'1/3');
assert.equal(String(Q.of('12.8')),'12,8');
assert(Q.of('64/5').eq('12,8'));
assert.throws(()=>Q.of('1/0'));
assert.throws(()=>solve('distance',['3','5','3','4.1']));
// Independent physical check: sum exact displacements between turning points.
for(const denom of [3,4,6])for(const h of [1,3,15,21]){
 const A=3,w=5,phase=Math.PI/denom,end=h*Math.PI;
 const angles=[phase];for(let k=1;k*Math.PI<phase+end;k++)angles.push(k*Math.PI);angles.push(phase+end);
 let S=0;for(let i=1;i<angles.length;i++)S+=Math.abs(A*Math.cos(angles[i])-A*Math.cos(angles[i-1]));
 assert(Math.abs(S-Number(solve('distance',[String(A),String(w),String(denom),`${h}/${w}`]).answer))<1e-10);
}
console.log('Original answers, 7000 variants, exact fractions and phase-dependent distances passed.');
