// Deadline-based, so a delayed background-tab tick still detects expiry once.
export class TimerMonitor {
  constructor(onExpire,now=Date.now){this.onExpire=onExpire;this.now=now;this.timers=[];this.notified=new Set();}
  set(timers){this.timers=timers;const ids=new Set(timers.map(t=>t.id));for(const id of this.notified)if(!ids.has(id))this.notified.delete(id);return this.tick();}
  tick(){
    const remaining=this.timers.map(t=>({...t,seconds:Math.max(0,Math.ceil((t.deadline-this.now())/1000))}));
    const due=remaining.filter(t=>t.seconds===0&&!this.notified.has(t.id));
    for(const t of due)this.notified.add(t.id);
    if(due.length)this.onExpire(due);
    return remaining;
  }
}
