// Numeric notation only; never infer a device, seat, action, or requested value.
const digits={영:0,공:0,일:1,이:2,삼:3,사:4,오:5,육:6,칠:7,팔:8,구:9};
function sino(s){let total=0,n=0;for(const c of s){if(c==='십'||c==='백'){total+=(n||1)*(c==='십'?10:100);n=0;}else n=digits[c];}return total+n;}
export function normalizeTranscript(text){return text.replace(/([영공일이삼사오육칠팔구십백]+)(?=\s*(?:도|단|으로|까지))/g,(_,s)=>String(sino(s)));}
