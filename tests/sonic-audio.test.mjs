import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';

test('Sonic microphone input resamples to 16kHz signed PCM with clipped amplitudes',()=>{
  const scope=vm.createContext({window:{},Float32Array,Uint8Array,DataView});
  vm.runInContext(readFileSync(new URL('../public/sonic-client.js',import.meta.url),'utf8'),scope);
  const pcm=scope.window.voiceLabPCM16(new Float32Array(4800).fill(.25),48000);
  assert.equal(pcm.length,3200);assert.equal(new DataView(pcm.buffer).getInt16(0,true),8191);
  const clipped=scope.window.voiceLabPCM16(new Float32Array([2,-2]),16000),view=new DataView(clipped.buffer);
  assert.equal(view.getInt16(0,true),32767);assert.equal(view.getInt16(2,true),-32768);
});
