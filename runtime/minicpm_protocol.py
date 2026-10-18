"""Streaming input and conversation boundaries, independent of GPU libraries."""
from dataclasses import dataclass
import uuid

def chunk_windows(length,rate=16000):
    if length<=0 or rate<=0:raise ValueError('Audio must contain samples')
    for start in range(0,length,rate):
        end=min(start+rate,length)
        yield start,end,rate-(end-start),end==length

@dataclass
class Conversation:
    key:tuple|None=None
    session_id:str|None=None
    last_active:float=0
    turns:int=0
    ttl_seconds:int=300
    max_turns:int=12

    def begin(self,client_id,language,now):
        key=(client_id or str(uuid.uuid4()),language)
        reset=key!=self.key or now-self.last_active>self.ttl_seconds or self.turns>=self.max_turns
        if reset:self.key=key;self.session_id=str(uuid.uuid4());self.turns=0
        self.last_active=now
        return reset

    def finish(self,now):self.turns+=1;self.last_active=now
    def invalidate(self):self.key=None;self.session_id=None;self.turns=0
