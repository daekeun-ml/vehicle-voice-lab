class PCMRecorder extends AudioWorkletProcessor {
  constructor(){super();this.chunk=new Float32Array(2048);this.position=0;}
  process(inputs){
    const input=inputs[0]?.[0];if(!input)return true;
    for(let i=0;i<input.length;i++){this.chunk[this.position++]=input[i];if(this.position===this.chunk.length){this.port.postMessage(this.chunk,[this.chunk.buffer]);this.chunk=new Float32Array(2048);this.position=0;}}
    return true;
  }
}
registerProcessor('pcm-recorder',PCMRecorder);
