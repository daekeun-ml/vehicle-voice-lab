// Publish only synthetic benchmark replies, never microphone recordings.
import{mkdir,readdir,copyFile}from'node:fs/promises';
await mkdir('public/benchmark-audio',{recursive:true});
const files=await readdir('output/vehicle-benchmark').catch(()=>[]);
let count=0;for(const name of files.filter(n=>/^[a-z0-9-]+-(passenger-25|defrost-on)-reply\.wav$/.test(n))){await copyFile('output/vehicle-benchmark/'+name,'public/benchmark-audio/'+name);count++;}
console.log(`Copied ${count} synthetic benchmark replies.`);
