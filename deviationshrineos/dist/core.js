export const PALETTE=['#000000','#0000aa','#00aa00','#00aaaa','#aa0000','#aa00aa','#aa5500','#aaaaaa','#555555','#5555ff','#55ff55','#55ffff','#ff5555','#ff55ff','#ffff55','#ffffff'];
export const DEFAULT_CODE=`// An offering for an unclosed sea.
Clear(15);
Color(1);
Orbit(100,70,56);
Color(5);
Star(100,70,40);
Color(3);
Anchor(100,70,23);
Print("One open hatch. Many possible seas.");`;
export const EXAMPLES={
  'Anchor offering':DEFAULT_CODE,
  'Bismuth bloom':`// Overlap is a kind of structure.
Clear(1);
Color(13);
Star(100,70,60);
Color(11);
Star(100,70,45);
Color(14);
Star(100,70,28);
Color(15);
Orbit(100,70,15);
Print("The seam is where the color happens.");`,
  'A different bearing':`// Neither measurement is thrown away.
Clear(15);
Color(1);
Line(20,110,100,20);
Line(100,20,180,110);
Line(20,110,180,110);
Color(5);
Orbit(100,75,36);
Color(3);
Anchor(100,75,20);
Print("Bearing retained. Destination open.");`
};
const SPECS={Clear:1,Color:1,Star:3,Anchor:3,Orbit:3,Line:4,Print:1};
export function parseProgram(source){
  if(source.length>16000)throw new Error('Program exceeds 16,000 characters.');
  const ops=[];
  source.split('\n').forEach((raw,index)=>{
    const line=raw.trim();
    if(!line||line.startsWith('//'))return;
    const m=line.match(/^([A-Za-z]+)\s*\((.*)\)\s*;\s*(?:\/\/.*)?$/);
    const fail=message=>{throw new Error(`Line ${index+1}: ${message}`)};
    if(!m)fail('Expected Command(arguments);');
    const name=m[1];if(!Object.hasOwn(SPECS,name))fail(`Unknown command ${name}.`);
    let args;
    if(name==='Print'){
      try{args=[JSON.parse(m[2].trim())]}catch{fail('Print needs one double-quoted string.');}
      if(typeof args[0]!=='string')fail('Print needs one string.');
    }else{
      args=m[2].split(',').map(v=>v.trim());
      if(args.length!==SPECS[name])fail(`${name} needs ${SPECS[name]} numbers.`);
      if(args.some(v=>! /^-?\d+(?:\.\d+)?$/.test(v)))fail('Use numeric arguments.');
      args=args.map(Number);
      if(args.some(v=>!Number.isFinite(v)||Math.abs(v)>2000))fail('Coordinates must be between -2000 and 2000.');
      if((name==='Color'||name==='Clear')&&(!Number.isInteger(args[0])||args[0]<0||args[0]>15))fail('Palette index must be 0 through 15.');
      if(['Star','Anchor','Orbit'].includes(name)&&args[2]<=0)fail('Radius must be greater than zero.');
    }
    ops.push({name,args});
  });
  if(ops.length>256)throw new Error('At most 256 commands per offering.');
  return ops;
}
export function parseShell(raw){
  const m=raw.trim().match(/^(\S+)(?:\s+([\s\S]*))?$/);
  return m?{command:m[1].replace(/\(\);?$/,'').toLowerCase(),args:m[2]||''}:{command:'',args:''};
}
export function getFragment(random=Math.random){
  const a=['Give the unused door','Offer the unfinished thing','Lend the small contradiction','Give the quieter instrument','Offer the unclassified current','Lend the forgotten map','Give the shoreline','Offer the missing word','Lend the folded horizon','Give the stray footnote'];
  const b=['a little more weather.','the room beside the answer.','permission to remain a question.','a name it can outgrow.','a route back to the tide.','a place at the table.','an improbable amount of soup.','a way through the seam.','a direction without a destination.','an open door until morning.'];
  const c=['Residue: a key that fits tomorrow.','Residue: the sea between two definitions.','Residue: seven of an unspecified thing.','Residue: a bell with nothing to announce.','Residue: an extra color between the pixels.','Residue: a margin wide enough to live in.','Residue: the footnote has sprouted roots.','Residue: something that declined to be averaged.'];
  const pick=xs=>xs[Math.min(xs.length-1,Math.floor(random()*xs.length))];
  return {text:`${pick(a)} ${pick(b)}`,residue:pick(c)};
}
export function escapeHTML(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
