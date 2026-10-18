import test from'node:test';import assert from'node:assert/strict';
import{translate,initialLocale}from'../public/i18n.js';
test('UI locale selection validates explicit links and saved preferences',()=>{
 assert.equal(initialLocale('?lang=en','ko'),'en');assert.equal(initialLocale('?lang=ko','en'),'ko');assert.equal(initialLocale('', 'en'),'en');assert.equal(initialLocale('?lang=fr','en'),'en');assert.equal(initialLocale('?lang=fr','invalid'),'ko');
});
test('UI copy localizes units and dynamic model labels without changing source Korean',()=>{
 const source='✓ Qwen3.5 · 4B · 4bit NF4 · 97점';assert.equal(translate(source,'en'),'✓ Qwen3.5 · 4B · 4bit NF4 · 97 pts');assert.equal(translate(source,'ko'),source);assert.equal(translate('2단','en'),'Level 2');assert.equal(translate('교체 로딩 5.27초','en'),'Model loading 5.27 s');assert.equal(translate('AWS 서울 · L40S 48GB','en'),'AWS Seoul · L40S 48GB');
});
