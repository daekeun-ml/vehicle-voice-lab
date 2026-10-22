// Provider names are explicit: unknown values must never silently select Polly.
export const ttsProviders = {
  polly: {id:'polly',name:'Amazon Polly · Seoyeon',model:'Amazon Polly',voice:'Seoyeon',managed:true},
  qwen: {id:'qwen',name:'Qwen3-TTS 0.6B · Sohee',model:'Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice',voice:'Sohee',url:process.env.TTS_URL||'http://127.0.0.1:19102'},
  qwen17: {id:'qwen17',name:'Qwen3-TTS 1.7B · Sohee',model:'Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice',revision:'0c0e3051f131929182e2c023b9537f8b1c68adfe',voice:'Sohee',url:process.env.QWEN17_TTS_URL||'http://127.0.0.1:19106'},
  supertonic: {id:'supertonic',name:'Supertonic 3 · F1 · CPU',model:'Supertone/supertonic-3',revision:'3cadd1ee6394adea1bd021217a0e650ede09a323',voice:'F1',url:process.env.SUPERTONIC_TTS_URL||'http://127.0.0.1:19107'},
  ppaso: {id:'ppaso',name:'Ppaso-TTS · 한국어 · ONNX CPU',model:'akamotaco/ppaso-tts-v1',revision:'53d09664c4f636a5fb6f2ebe3ec22cd83ee249b9',voice:'single-female',notice:'한국어 전용 단일 여성 음성. 자연스러움보다 속도를 우선한 경량 모델입니다.',url:process.env.PPASO_TTS_URL||'http://127.0.0.1:19108'},
};
export function selectTtsProvider(value){
  const id=value??'polly';
  if(typeof id!=='string'||!Object.hasOwn(ttsProviders,id))throw new Error('지원하지 않는 응답 음성입니다.');
  return id;
}
export function publicTtsProviders(){
  return Object.values(ttsProviders).map(({url,...provider})=>provider);
}
