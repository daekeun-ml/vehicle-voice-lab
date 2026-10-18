import test from'node:test';import assert from'node:assert/strict';
test('cloud HTTP and WebSocket access needs our origin secret and expected browser origin',async()=>{
 const names=['PUBLIC_ORIGIN','ORIGIN_HOST','ORIGIN_VERIFY_SECRET'],old=Object.fromEntries(names.map(n=>[n,process.env[n]]));
 try{Object.assign(process.env,{PUBLIC_ORIGIN:'https://demo.cloudfront.net',ORIGIN_HOST:'ip-10-0-0-1.internal',ORIGIN_VERIFY_SECRET:'a'.repeat(48)});const{allowedRequest}=await import('../web-access.mjs?cloud-test');const request={headers:{host:'demo.cloudfront.net',origin:'https://demo.cloudfront.net','x-vehicle-origin-key':'a'.repeat(48)}};
 assert.equal(allowedRequest(request,8787),true);assert.equal(allowedRequest(request,8787,{websocket:true}),true);
 assert.equal(allowedRequest({headers:{...request.headers,'x-vehicle-origin-key':''}},8787),false);
 assert.equal(allowedRequest({headers:{...request.headers,origin:'https://other.example'}},8787),false);
 assert.equal(allowedRequest({headers:{...request.headers,host:'other.example'}},8787),false);
 assert.equal(allowedRequest({headers:{host:'ip-10-0-0-1.internal','x-vehicle-origin-key':'a'.repeat(48)}},8787),true);
 assert.equal(allowedRequest({headers:{...request.headers,origin:undefined}},8787,{websocket:true}),false);
 }finally{for(const n of names)if(old[n]===undefined)delete process.env[n];else process.env[n]=old[n];}
});
