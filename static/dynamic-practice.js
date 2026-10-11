/* Exact rational arithmetic: no rounding, no AI call, no bank mutation. */
(function(root){
'use strict';
const gcd=(a,b)=>b?gcd(b,a%b):(a<0n?-a:a);
class Q{
 constructor(n,d=1n){n=BigInt(n);d=BigInt(d);if(!d)throw Error('Mẫu bằng 0');if(d<0n){n=-n;d=-d}const g=gcd(n,d);this.n=n/g;this.d=d/g}
 static of(s){if(s instanceof Q)return s;const t=String(s).trim().replace(/,/g,'.');if(t.includes('/')){const p=t.split('/');if(p.length!==2)throw Error('Phân số không hợp lệ');return Q.of(p[0]).div(Q.of(p[1]))}if(!/^[+-]?\d+(\.\d+)?$/.test(t))throw Error('Nhập số hoặc phân số');const places=(t.split('.')[1]||'').length;return new Q(BigInt(t.replace('.','')),10n**BigInt(places))}
 add(x){x=Q.of(x);return new Q(this.n*x.d+x.n*this.d,this.d*x.d)}
 mul(x){x=Q.of(x);return new Q(this.n*x.n,this.d*x.d)}
 div(x){x=Q.of(x);return new Q(this.n*x.d,this.d*x.n)}
 eq(x){x=Q.of(x);return this.n===x.n&&this.d===x.d}
 toString(){let d=this.d;while(d%2n===0n)d/=2n;while(d%5n===0n)d/=5n;if(d!==1n)return `${this.n}/${this.d}`;const neg=this.n<0n;let n=neg?-this.n:this.n;let out=String(n/this.d),r=n%this.d;if(r){out+=',';while(r){r*=10n;out+=String(r/this.d);r%=this.d}}return (neg?'-':'')+out}
 value(){return Number(this.n)/Number(this.d)}
}
const pick=a=>a[Math.floor(Math.random()*a.length)],int=(a,b)=>a+Math.floor(Math.random()*(b-a+1));
function generate(key,previous){let p;do{
 switch(key){
 case 'amplitude':p=[String(2*int(2,15))];break;
 case 'projection':p=[String(int(2,15)),String(int(2,10))];break;
 case 'period':p=[String(int(1,4)),String(pick([15,20,24,25,30,40,45,60]))];break;
 case 'orbit':{const n=int(2,20),a=int(2,12);p=[String(n),String(4*n*a)];break}
 case 'rotation':p=[String(int(3,20)),String(int(1,10))];break;
 case 'spring':{const n=int(10,40),t=Q.of(n).mul(pick(['0.4','0.5','0.8','1','1.2']));p=[String(n),t.toString().replace(',','.'),pick(['0.04','0.08','0.1','0.12','0.2'])];break}
 case 'distance':{const w=int(2,12),h=int(3,25);p=[String(int(1,12)),String(w),String(pick([3,4,6])),String(h)+'/'+String(w)];break}
 default:throw Error('Chưa có mẫu');
 }
 }while(JSON.stringify(p)===JSON.stringify(previous));return p}
function solve(key,params){const p=params.map(Q.of);let answer,unit='cm',stem,formula,steps,options,A=p[0],w=Q.of(2);const f=x=>String(x);
 switch(key){
 case 'amplitude':answer=p[0].div(2);A=null;stem=`Một vật dao động điều hòa trên đoạn thẳng quỹ đạo dài ${p[0]} cm. Biên độ của vật bằng bao nhiêu?`;formula='Chiều dài quỹ đạo L = 2A; A = L/2.';steps=`A = ${p[0]}/2 = ${answer} cm.`;options=[p[0],answer,p[0].mul(2),p[0].div(4)];break;
 case 'projection':answer=`${p[0]};${p[1]}`;w=p[1];stem=`Chất điểm chuyển động tròn đều có R = ${p[0]} cm và tốc độ góc ${p[1]} rad/s. Biên độ và tần số góc của hình chiếu lên đường kính lần lượt là?`;formula='x = R cos(ωt + φ); A = R; ω của hình chiếu bằng tốc độ góc quay.';steps=`A = ${p[0]} cm; ω = ${p[1]} rad/s.`;options=[`${p[1]} cm; ${p[0]} rad/s`,`${p[0]} cm; ${p[1]} rad/s`,`${p[0].mul(2)} cm; ${p[1]} rad/s`,`${p[0]} cm; ${p[1].mul(2)} rad/s`];unit='';break;
 case 'period':answer=p[0].mul(60).div(p[1]);unit='s';stem=`Trong ${p[0]} phút, một vật thực hiện ${p[1]} dao động toàn phần. Chu kì của vật là bao nhiêu?`;formula='T = Δt/N; f = N/Δt. Đổi phút sang giây trước khi tính.';steps=`Δt = ${p[0].mul(60)} s. T = Δt/N = ${answer} s.`;A=null;break;
 case 'orbit':answer=p[1].div(p[0].mul(2));A=null;stem=`Vật thực hiện ${p[0]} dao động toàn phần và đi được ${p[1]} cm. Chiều dài quỹ đạo là bao nhiêu?`;formula='S = 4AN; L = 2A = S/(2N).';steps=`L = ${p[1]}/(2 × ${p[0]}) = ${answer} cm.`;break;
 case 'rotation':answer=`${Q.of(2).div(p[1])};${p[1].div(2)}`;unit='';w=p[1];stem=`Thanh nhỏ cách tâm bàn xoay ${p[0]} cm. Bàn quay đều với tốc độ góc ${p[1]}π rad/s. Chu kì và tần số của bóng trên màn lần lượt là?`;formula='T = 2π/ω; f = 1/T; A = R.';steps=`T = 2/${p[1]} = ${Q.of(2).div(p[1])} s; f = ${p[1]}/2 = ${p[1].div(2)} Hz.`;options=[`${Q.of(2).div(p[1])} s; ${p[1].div(2)} Hz`,`${Q.of(4).div(p[1])} s; ${p[1].div(4)} Hz`,`${Q.of(2).div(p[1])} s; ${p[1]} Hz`,`${Q.of(1).div(p[1])} s; ${p[1]} Hz`];break;
 case 'spring':{const T=p[1].div(p[0]);answer=p[2].mul(40).div(T.mul(T));unit='N/m';A=null;stem=`Con lắc lò xo thực hiện ${p[0]} dao động trong ${p[1]} s. Khối lượng m = ${p[2]} kg. Tính độ cứng k (N/m), lấy π² = 10.`;formula='T = Δt/N; k = 4π²m/T².';steps=`T = ${T} s. k = 40 × ${p[2]}/(${T})² = ${answer} N/m.`;break}
 case 'distance':{const h=p[1].mul(p[3]);if(h.d!==1n)throw Error('Mẫu này yêu cầu số nguyên nửa chu kì');w=p[1];answer=p[0].mul(2).mul(h);stem=`Vật dao động x = ${p[0]} cos(${p[1]}πt + π/${p[2]}) cm. Tính tổng quãng đường trong ${p[3]} s kể từ t = 0.`;formula='T = 2π/ω. Trong mỗi T/2, vật luôn đi 2A, với mọi pha ban đầu.';steps=`T = ${Q.of(2).div(p[1])} s; Δt/(T/2) = ${h}. S = ${h} × 2 × ${p[0]} = ${answer} cm.`;break}
 default:throw Error('Chưa có mẫu');
 }
 if(!options){options=[answer,answer.mul(2),answer.div(2),answer.mul(3)].map(f)}
 else options=options.map(f);
 // Deduplicate alternatives, e.g. equal R and omega.
 const correct=(key==='projection'?`${p[0]} cm; ${p[1]} rad/s`:key==='rotation'?`${Q.of(2).div(p[1])} s; ${p[1].div(2)} Hz`:String(answer));
 const unique=[correct,...options.filter(o=>o!==correct)];let i=2;while(new Set(unique).size<4)unique.push(key==='projection'?`${p[0].mul(++i)} cm; ${p[1]} rad/s`:String(Q.of(answer).mul(++i)));
 const choices=[...new Set(unique)].slice(0,4).map(text=>({text:text+(unit?' '+unit:''),correct:text===correct}));
 return {answer:String(answer),stem,formula,steps,choices,A:A?String(A):null,w:String(w)};
}
root.DynamicPracticeEngine={Q,generate,solve};
if(typeof document==='undefined')return;
const $=id=>document.getElementById(id),escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const data=JSON.parse(new TextDecoder().decode(Uint8Array.from(atob($('dpData').textContent.trim()),c=>c.charCodeAt(0))));let group=0,source=0,current=null,params=null,original=true,running=false,frame=null,angle=0;
const formulas={amplitude:'L = 2A; A = L/2.',projection:'A = R; ω của hình chiếu bằng tốc độ góc quay.',period:'T = Δt/N; f = N/Δt.',orbit:'S = 4AN; L = 2A.',distance:'T = 2π/ω; S = 2Ah khi Δt = hT/2.',rotation:'T = 2π/ω; f = 1/T.',spring:'T = Δt/N; k = 4π²m/T².'};
$('dpGroup').innerHTML=data.map((g,i)=>`<option value="${i}">${escape(g.label)} · ${g.items.length} câu gốc</option>`).join('');
function item(){return data[group].items[source]}
function sources(){ $('dpSource').innerHTML=data[group].items.map((s,i)=>`<option value="${i}">${escape(s.original.id||'Chưa có ID')} · STT file ${s.original.file_idx}</option>`).join('');source=0;restore()}
function stop(){running=false;if(frame!==null)cancelAnimationFrame(frame);frame=null;angle=0}
function restore(){original=true;params=item().params;current=solve(item().template,params);render()}
function render(){stop();const q=item().original;const opts=original?(q.options||[]):current.choices;$('dpStem').innerHTML=original?q.text:escape(current.stem);$('dpFormula').textContent=original?formulas[item().template]:current.formula;
 $('dpOptions').innerHTML=opts.map((o,i)=>`<label><input type="radio" name="dpAnswer" value="${i}"><span>${'ABCD'[i]}. ${original?o.text.replace(/^\s*[ABCD]\s*[.)]\s*/,''):escape(o.text)}</span></label>`).join('');$('dpInputLabel').hidden=opts.length>0;$('dpInput').value='';$('dpFeedback').textContent='';$('dpSolution').hidden=true;$('dpSolution').innerHTML=original?q.solution:escape(current.steps);$('dpMeta').textContent=`${original?'Đề gốc':'Đề đã đổi số'} · ${data[group].label} · ID: ${q.id||'Chưa có ID'} · STT file: ${q.file_idx} · ${data[group].items.length} câu cùng mẫu`;figure();if(root.ldvlTypeset)root.ldvlTypeset($('dynamicPractice'))}
function figure(){const x=90*Math.cos(angle),y=-90*Math.sin(angle);const label=current.A?`A = ${current.A} cm`:'Biên độ A';$('dpFigure').innerHTML=`<svg viewBox="0 0 420 250" role="img" aria-label="Hình chiếu chuyển động tròn đều"><circle cx="125" cy="115" r="90" fill="none" stroke="#91b3d5"/><path d="M25 115H235 M260 115H405" stroke="#536e87"/><path d="M125 115L${125+x} ${115+y}L${305+x} 190" fill="none" stroke="#b0bfd1" stroke-dasharray="4 4"/><circle cx="${125+x}" cy="${115+y}" r="7" fill="#1760bc"/><circle cx="${305+x}" cy="190" r="7" fill="#df8535"/><path d="M215 190H400" stroke="#536e87"/><text x="105" y="137">O</text><text x="15" y="235">${escape(label)} · Hình chiếu lên đường kính</text><text x="235" y="215">−A</text><text x="300" y="215">0</text><text x="380" y="215">+A</text></svg><small>Mô phỏng hình chiếu; tốc độ được điều chỉnh để quan sát. Số liệu đề: ${params.map(escape).join(' · ')}.</small>`}
$('dpGroup').onchange=e=>{group=Number(e.target.value);sources()};$('dpSource').onchange=e=>{source=Number(e.target.value);restore()};$('dpOriginal').onclick=restore;
$('dpNew').onclick=()=>{params=generate(item().template,params);original=false;current=solve(item().template,params);current.choices.sort(()=>Math.random()-.5);render()};
$('dpCheck').onclick=()=>{const opts=original?(item().original.options||[]):current.choices;let ok=false;if(opts.length){const checked=document.querySelector('input[name="dpAnswer"]:checked');if(!checked){$('dpFeedback').textContent='Hãy chọn một phương án.';return}ok=opts[Number(checked.value)].correct}else{try{ok=Q.of($('dpInput').value).eq(original?item().original.answer:current.answer)}catch(e){$('dpFeedback').textContent='Nhập số chính xác hoặc phân số, ví dụ 64/5.';return}}$('dpFeedback').textContent=ok?'✓ Đúng!':'Chưa đúng. Thầy/cô gợi ý: xem lại công thức và đơn vị.';$('dpFeedback').style.color=ok?'#087438':'#b23a2c'};
$('dpReveal').onclick=()=>{$('dpSolution').hidden=!$('dpSolution').hidden};$('dpFull').onclick=async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await $('dynamicPractice').requestFullscreen()}catch(e){$('dpFeedback').textContent='Trình duyệt chưa hỗ trợ toàn màn hình.'}};
$('dpAnimate').onclick=()=>{if(running){stop();return}running=true;let last=null;function tick(t){if(!running)return;if(last!==null)angle+=(t-last)*0.0015;last=t;figure();frame=requestAnimationFrame(tick)}frame=requestAnimationFrame(tick)};
sources();
})(typeof window==='undefined'?globalThis:window);
