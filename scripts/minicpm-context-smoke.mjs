import assert from 'node:assert/strict';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
const base='http://localhost:8787';
async function session(){return(await fetch(base+'/api/session',{method:'POST'})).json();}
const headers=s=>({'Content-Type':'application/json','X-Session-Id':s.id});
async function turn(s,file){
  const audio=await readFile('output/minicpm-audit/'+file+'.wav');
  const response=await fetch(base+'/api/s2s',{method:'POST',headers:headers(s),body:JSON.stringify({comparisonOnly:true,audio:audio.toString('base64'),language:'en'}),signal:AbortSignal.timeout(120000)});
  if(!response.ok)throw new Error(await response.text());
  const events=(await response.text()).split('\n\n').filter(Boolean).map(block=>({event:block.split('\n')[0].slice(7),data:JSON.parse(block.split('\n')[1].slice(6))}));
  const error=events.find(e=>e.event==='error');if(error)throw new Error(error.data.error);
  assert.ok(events.some(e=>e.event==='audio'));
  const row=events.find(e=>e.event==='done')?.data.metrics;assert.equal(row?.completed,true);assert.equal(row.integrationVersion,2);
  const exported=await(await fetch(base+'/api/export',{headers:headers(s)})).json();assert.deepEqual(exported.state,s.state);
  const result={reply:row.reply,conversationContinued:row.conversationContinued,inputSamples:row.inputSamples,paddedSamples:row.paddedSamples};console.log(JSON.stringify(result));return result;
}
const s=await session(),results=[];
results.push(await turn(s,'remember'));assert.equal(results[0].conversationContinued,false);
results.push(await turn(s,'recall'));assert.equal(results[1].conversationContinued,true);assert.match(results[1].reply,/Alex/i);
const other=await session();results.push(await turn(other,'recall'));assert.equal(results[2].conversationContinued,false);assert.doesNotMatch(results[2].reply,/Alex/i);
await fetch(base+'/api/reset',{method:'POST',headers:headers(s),body:'{}'});
results.push(await turn(s,'recall'));assert.equal(results[3].conversationContinued,false);assert.doesNotMatch(results[3].reply,/Alex/i);
await mkdir('output',{recursive:true});await writeFile('output/minicpm-context-smoke.json',JSON.stringify({at:new Date().toISOString(),syntheticAudioOnly:true,passed:true,results},null,2));
