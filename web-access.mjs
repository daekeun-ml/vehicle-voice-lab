import{timingSafeEqual}from'node:crypto';
const publicOrigin=process.env.PUBLIC_ORIGIN||'',originKey=process.env.ORIGIN_VERIFY_SECRET||'';
if(publicOrigin&&(!publicOrigin.startsWith('https://')||originKey.length<32))throw Error('Cloud deployment needs HTTPS PUBLIC_ORIGIN and an origin verification secret');
export const cloudMode=!!publicOrigin;
export function allowedRequest(req,port,{websocket=false}={}){
 const host=req.headers.host,allowed=new Set([`localhost:${port}`,`127.0.0.1:${port}`,...(publicOrigin?[new URL(publicOrigin).host,process.env.ORIGIN_HOST].filter(Boolean):[])]);
 if(!allowed.has(host))return false;
 if(publicOrigin){const actual=Buffer.from(String(req.headers['x-vehicle-origin-key']||'')),expected=Buffer.from(originKey);if(actual.length!==expected.length||!timingSafeEqual(actual,expected))return false;}
 const expected=publicOrigin||`http://${host}`;
 return websocket?req.headers.origin===expected:!req.headers.origin||req.headers.origin===expected;
}
export function startSse(res){
 res.writeHead(200,{'Content-Type':'text/event-stream','Cache-Control':'no-store, no-transform','Connection':'keep-alive','X-Accel-Buffering':'no'});res.flushHeaders();
 const heartbeat=setInterval(()=>{if(!res.destroyed&&!res.writableEnded)res.write(': keepalive\n\n');},10000);heartbeat.unref();
 const clear=()=>clearInterval(heartbeat);res.once('close',clear);res.once('finish',clear);
}
