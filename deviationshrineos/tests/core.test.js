import test from 'node:test';
import assert from 'node:assert/strict';
import {parseProgram,parseShell,EXAMPLES,getFragment,escapeHTML} from '../dist/core.js';

test('all included drawings compile with visible drawing operations',()=>{
 for(const source of Object.values(EXAMPLES)){
  const ops=parseProgram(source);
  assert.ok(ops.some(o=>['Star','Anchor','Orbit','Line'].includes(o.name)));
  assert.equal(ops[0].name,'Clear');
 }
});
test('quoted semicolons and parentheses are preserved as text',()=>{
 assert.deepEqual(parseProgram('Print("A; B (unresolved)");'),[{name:'Print',args:['A; B (unresolved)']}]);
});
test('program validation rejects execution, extreme work, and invalid palette entries',()=>{
 for(const source of ['eval("alert(1)");','Print(document.cookie);','Color(-1);','Color(1.5);','Clear(16);','Orbit(0,0,-5);','Star(0,0,999999);','Line(0,0,3);','Anchor(0,0,2); evil();'])assert.throws(()=>parseProgram(source));
 assert.throws(()=>parseProgram('Clear(0);\n'.repeat(257)),/256 commands/);
 assert.throws(()=>parseProgram('x'.repeat(16001)),/16,000/);
});
test('invalid commands report source lines and leave source comments harmless',()=>{
 assert.throws(()=>parseProgram('// hello\n\nBreak();'),/Line 3: Unknown command Break/);
 assert.equal(parseProgram('Color(5); // choose magenta').length,1);
});
test('shell supports OS-style calls and preserves original argument case',()=>{
 assert.deepEqual(parseShell('  Help(); '),{command:'help',args:''});
 assert.deepEqual(parseShell('log The Unmatched Fraction'),{command:'log',args:'The Unmatched Fraction'});
 assert.deepEqual(parseShell(''),{command:'',args:''});
});
test('oracle boundary draws remain complete and carry a residue',()=>{
 for(const r of [0,.5,.999999]){const x=getFragment(()=>r);assert.ok(x.text.length>10);assert.match(x.residue,/^Residue:/)}
});
test('user text is escaped before any template interpolation',()=>{
 assert.equal(escapeHTML('<img onerror="x">&'), '&lt;img onerror=&quot;x&quot;&gt;&amp;');
});
