import test from 'node:test';
import assert from 'node:assert/strict';
import {TimerMonitor} from '../public/timer-monitor.js';

test('timer expiry alerts once even after a delayed background tick and a repeated snapshot',()=>{
 let now=1000;const alerts=[];const monitor=new TimerMonitor(due=>alerts.push(due.map(t=>t.id)),()=>now);
 const timers=[{id:'a',deadline:2000},{id:'b',deadline:8000}];
 assert.equal(monitor.set(timers)[0].seconds,1);
 now=6500;assert.equal(monitor.tick()[1].seconds,2);monitor.tick();monitor.set(timers);
 assert.deepEqual(alerts,[['a']]);now=9000;monitor.tick();assert.deepEqual(alerts,[['a'],['b']]);
});

test('canceling timers prevents their future alerts; already-expired arrivals alert immediately',()=>{
 let now=1000;const alerts=[];const monitor=new TimerMonitor(due=>alerts.push(...due),()=>now);
 monitor.set([{id:'cancel',deadline:2000}]);monitor.set([]);now=3000;monitor.tick();assert.equal(alerts.length,0);
 monitor.set([{id:'late',deadline:2000}]);assert.equal(alerts.length,1);assert.equal(alerts[0].id,'late');
});
