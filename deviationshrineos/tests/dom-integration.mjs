// Interaction QA with a simulated DOM. This does not verify browser layout.
// Usage: node tests/dom-integration.mjs /absolute/path/to/linkedom/esm/index.js
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
const {parseHTML}=await import(pathToFileURL(process.argv[2]).href);
const html=await readFile(new URL('../dist/index.html',import.meta.url),'utf8');
const data=new Map();let timers=[],drawCalls=0,downloads=[];
const storage={getItem:k=>data.get(k)||null,setItem:(k,v)=>data.set(k,v)};
function setup(blocked=false){
 const {document,window}=parseHTML(html);
 Object.assign(globalThis,{document,window,localStorage:blocked?{getItem(){throw Error('blocked')},setItem(){throw Error('blocked')}}:storage,matchMedia:()=>({matches:false}),requestAnimationFrame:()=>0});
 Object.defineProperties(window,{innerWidth:{value:1200,configurable:true},innerHeight:{value:1000,configurable:true}});
 Object.defineProperty(document.querySelector('#viewport'),'clientWidth',{value:1100});
 document.fonts={ready:Promise.resolve()};
 window.HTMLElement.prototype.focus=function(){};
 window.HTMLElement.prototype.setPointerCapture=function(){};
 Object.defineProperty(window.HTMLElement.prototype,'offsetWidth',{get(){return parseFloat(this.style.width)||0},configurable:true});
 window.HTMLCanvasElement.prototype.getContext=function(){return {fillRect(){drawCalls++},clearRect(){},fillText(){},strokeRect(){}}};
 window.HTMLTextAreaElement.prototype.setRangeText=function(s,start,end){this.value=this.value.slice(0,start)+s+this.value.slice(end);this.selectionStart=this.selectionEnd=start+s.length};
 window.HTMLAnchorElement.prototype.click=function(){downloads.push({filename:this.download,href:this.href})};
 globalThis.setInterval=()=>0;
 globalThis.setTimeout=(fn,ms)=>{timers.push({fn,ms});return timers.length};
 globalThis.clearTimeout=()=>{};
 return {document,window};
}
setup();
await import(new URL('../dist/app.js?normal',import.meta.url));
const q=s=>document.querySelector(s),qa=s=>[...document.querySelectorAll(s)];
function fire(el,type,props={}){assert.ok(el,`target exists for ${type}`);const e=new window.Event(type,{bubbles:true,cancelable:true});Object.assign(e,props);el.dispatchEvent(e)}
function click(s){fire(q(s),'click')}
function type(s,value){q(s).value=value;fire(q(s),'input')}
assert.equal(qa('.window').length,4,'four initial desktop windows');
assert.ok(drawCalls>100,'procedural artwork was drawn');
click('#temple-menu-button');assert.equal(q('#start-menu').hidden,false);assert.equal(q('#temple-menu-button').getAttribute('aria-expanded'),'true');
click('[data-open="oracle"]');assert.ok(q('.window[data-id="oracle"]'));assert.equal(q('#start-menu').hidden,true);
type('#oracle-question','What is behind <this> door?');click('[data-action="cast"]');
assert.equal(q('#cast-number').textContent,'#001');
assert.ok(!q('[data-action="keep-fragment"]').disabled);
const fragment=q('#oracle-reading').textContent;click('[data-action="keep-fragment"]');
click('[data-open="logbook"]');assert.match(q('#log-editor').value,/Carrying: What is behind <this> door\?/);assert.ok(q('#log-editor').value.includes(fragment));
type('#log-editor','My log. <img src=x onerror=alert(1)>');
assert.ok(data.get('deviationshrineos.0137').includes('My log.'));
click('.window[data-id="logbook"] [data-action="close"]');click('[data-open="logbook"]');
assert.equal(q('#log-editor').value,'My log. <img src=x onerror=alert(1)>');assert.equal(q('.window[data-id="logbook"] img'),null);
click('[data-action="export-log"]');assert.equal(downloads.at(-1).filename,'DeviationShrineOS-ShipsLog.txt');
click('[data-open="crew"]');click('[data-crew="2"]');assert.match(q('#crew-details').textContent,/adorable/);assert.match(q('#crew-details a').href,/jupiterfox.html$/);
click('[data-open="atlas"]');click('[data-room="6"]');assert.match(q('#atlas-details').textContent,/HERE BE DRAGONS/);assert.equal(q('[data-action="enter-room"]'),null);
click('[data-room="5"]');click('[data-action="enter-room"]');assert.match(q('#crew-details').textContent,/The Mycelium/);assert.equal(q('[data-crew="6"]').classList.contains('selected'),true);
click('.window[data-id="crew"] [data-action="minimize"]');assert.equal(q('.window[data-id="crew"]').hidden,true);
click('[data-task="crew"]');assert.equal(q('.window[data-id="crew"]').hidden,false);
const initialWidth=q('.window[data-id="crew"]').style.width;
click('.window[data-id="crew"] [data-action="maximize"]');assert.equal(q('.window[data-id="crew"]').style.width,'636px');
click('.window[data-id="crew"] [data-action="maximize"]');assert.equal(q('.window[data-id="crew"]').style.width,initialWidth);
click('[data-open="workshop"]');assert.match(q('#program-output').textContent,/One open hatch/);
type('#code-editor','Clear(15);\nPrint("A new offering");');click('[data-action="run-code"]');assert.equal(q('#program-output').textContent,'A new offering');
type('#code-editor','Clear(15);\neval("bad");');click('[data-action="run-code"]');assert.match(q('#program-output').textContent,/Line 2: Unknown command eval/);
type('#code-editor','Color(13);\nStar(100,70,20);\nPrint("Preserved offering");');
fire(document,'keydown',{key:'F5'});assert.match(q('#program-output').textContent,/Preserved offering/);
click('[data-open="shell"]');type('#shell-input','log A message from the shell');fire(q('.shell-form'),'submit');assert.match(q('.shell-output').textContent,/Kept in the logbook/);
type('#shell-input','open atlas');fire(q('.shell-form'),'submit');assert.equal(q('.window.active').dataset.id,'atlas');
click('[data-open="shell"]');type('#shell-input','unknown-command');fire(q('.shell-form'),'submit');assert.match(q('.shell-output').textContent,/Unknown command/);
type('#shell-input','echo <script>alert(1)</script>');fire(q('.shell-form'),'submit');assert.equal(q('.shell-output script'),null);
fire(q('#shell-input'),'keydown',{key:'ArrowUp'});assert.equal(q('#shell-input').value,'echo <script>alert(1)</script>');
click('[data-action="detune"]');assert.equal(q('#detune-label').textContent,'FREE DRIFT');
click('[data-action="scale"]');assert.equal(q('#screen').style.transform,'scale(1)');
click('[data-action="motion"]');assert.equal(q('#motion-button').textContent,'MOTION OFF');
click('[data-action="reboot"]');timers.findLast(t=>t.ms===100).fn();assert.equal(qa('.window').length,4);
click('[data-open="logbook"]');assert.ok(q('#log-editor').value.includes('A message from the shell'));
// Simulate a reload with the same browser-local storage.
setup();await import(new URL('../dist/app.js?reload',import.meta.url));
click('[data-open="logbook"]');assert.ok(q('#log-editor').value.includes('A message from the shell'));
click('[data-open="workshop"]');assert.match(q('#code-editor').value,/Preserved offering/);
// The unavailable-storage branch still permits writing and export.
setup(true);await import(new URL('../dist/app.js?storage-blocked',import.meta.url));
click('[data-open="logbook"]');type('#log-editor','Keep this in session.');assert.match(q('#log-status').textContent,/Storage unavailable/);
click('.window[data-id="logbook"] [data-action="close"]');click('[data-open="logbook"]');assert.equal(q('#log-editor').value,'Keep this in session.');
click('[data-action="export-log"]');assert.equal(downloads.at(-1).filename,'DeviationShrineOS-ShipsLog.txt');
console.log('PASS: desktop, oracle, crew, map, window controls, drawing, shell, export, reboot, reload, and storage fallback.');
