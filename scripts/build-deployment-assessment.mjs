import {readFile,writeFile} from 'node:fs/promises';
const catalog=JSON.parse(await readFile('model-catalog.json','utf8'));
let quantizationComparison;try{quantizationComparison=JSON.parse(await readFile('research/qwen35-quantization-comparison.json','utf8'));}catch{}
const sources=[
 {title:'NVIDIA DRIVE AGX Orin / Thor 공식 사양',url:'https://developer.nvidia.com/drive/agx/'},
 {title:'Qualcomm Snapdragon Cockpit / Ride Elite',url:'https://www.qualcomm.com/automotive/products/elite'},
 {title:'SA8295P에서 NPU 포팅을 검증한 AutoNeural 논문',url:'https://arxiv.org/html/2512.02924v1'},
 {title:'NVIDIA 차량 AI Box와 클라우드·차량 배포 구성',url:'https://developer.nvidia.com/blog/how-to-build-in-vehicle-ai-agents-with-nvidia-from-cloud-to-car/'},
 {title:'AWS Nova 2.5 Sonic 출시·Bedrock 제공',url:'https://aws.amazon.com/ko/about-aws/whats-new/2026/10/amazon-nova-2.5-Sonic/'},
 {title:'AWS Sonic 공식 음성·언어 목록',url:'https://docs.aws.amazon.com/nova/latest/nova2-userguide/sonic-language-support.html'},
];
const report={checkedAt:new Date().toISOString(),method:'가중치 하한 = 전체 파라미터 × 정밀도 바이트 / 2^30 (GiB). INT4는 0.5 byte, BF16은 2 bytes. 양자화 메타데이터·KV/상태 캐시·활성화·음성 코덱·OS는 이 하한에 포함되지 않음. 실행 메모리 범위는 짧은 문맥·단일 세션의 설계 추정이며 실제 차량 측정이 아님. 각 모델의 전체 가중치 기준으로 보수적으로 계산.',hardware:[
 {name:'일반 콕핏 · Snapdragon Cockpit / 8295 계열을 상정',spec:'설계 예산: 공유 RAM 8~16GB, AI에 2~6GB 가용 가정',assessment:'RAM 용량·AI 가용량은 OEM별 차이. 여기의 숫자는 보편 사양이나 시장 점유율 주장이 아닌 비교용 가정. 0.5~2B INT4 우선, 3~4B는 여유 메모리·연산자 지원 확인.',source:sources[2].url},
 {name:'차세대 Snapdragon Cockpit Elite',spec:'Oryon CPU · Hexagon NPU · RAM은 OEM 구성별 확인',assessment:'공식 제품 페이지에 고정 RAM 용량이 없어 16/32GB 탑재로 단정하지 않음. QNN 변환·연산자 지원과 차량 동시 부하 검증 필요.',source:sources[1].url},
 {name:'NVIDIA DRIVE AGX Orin 개발 장비',spec:'32GB LPDDR5 · 최대 200GB/s · 254 INT8 TOPS',assessment:'소형 LLM과 로컬 ASR/TTS의 통합 후보. 8~9B BF16 음성 모델은 다른 차량 작업과 동시 실행 시 여유 부족 가능. 개발 키트 사양이며 모든 양산 ECU의 사양이 아님.',source:sources[0].url},
 {name:'NVIDIA DRIVE AGX Thor 개발 장비',spec:'64GB LPDDR5X · 최대 273GB/s · 1000 INT8 TOPS',assessment:'대형 음성 모델의 메모리 검토 후보. CPU/GPU 포팅·전력·열·동시 ADAS/IVI 부하와 실제 지연 검증 필요. 개발 장비를 보급형 콕핏으로 취급하지 않음.',source:sources[0].url},
],limits:['TOPS만으로 이 모델들의 토큰 속도나 첫 음성 지연을 환산할 수 없음. 표의 속도는 현재 AWS L40S 측정이며 차량 속도는 모두 미측정.','메모리에 들어간다는 판단과 실제 지원되는 런타임은 별개. CUDA Transformers 코드를 Qualcomm NPU에 그대로 올릴 수 없음.','일반 콕핏의 AI 가용 RAM 가정과 Orin/Thor의 전체 RAM을 혼동하지 않음. ASR·TTS·OS·화면·내비·ADAS 예산을 별도 확보.','오픈 가중치와 상업 이용 허용은 별개. 게이트 접근·라이선스 조건은 모델별 확인. SageMaker에 배포해도 폐쇄형 모델의 가중치를 받을 수 있는 것은 아님.'],routes:[
 {name:'현재 sLLM 데모',path:'차량/브라우저 → 우리 AWS GPU의 Whisper 또는 Nemotron ASR → 선택 sLLM → 앱 차량 실행기 → Amazon Polly → 음성',external:'추가 외부 추론 서비스 1종: Polly TTS. ASR·sLLM은 자체 GPU. WAN 연결 필요.'},
 {name:'현재 직접 음성 제어 데모',path:'차량/브라우저 → 우리 AWS GPU의 선택 음성 모델 → 앱 차량 실행기 → Amazon Polly → 음성',external:'추가 외부 추론 서비스 1종: Polly TTS. 모델 내장 한국어 음성 품질 점수가 아님.'},
 {name:'자체 GPU로만 구성할 때',path:'차량/브라우저 → 우리 AWS GPU의 ASR·판단·Qwen3-TTS → 차량 실행기',external:'Qwen TTS 선택 시 제3자 모델 API 호출 0종. 우리 서버까지 네트워크 홉은 남음. 음성 전체 경로 품질은 별도 재평가 필요.'},
 {name:'완전 차량 내 실행 목표',path:'차량 내 ASR → INT4 sLLM → 로컬 차량 실행기 → 차량 내 TTS',external:'외부 추론 호출 0종·오프라인 가능. 현재 구현은 AWS 실행이며 차량용 런타임 포팅은 미완료.'},
 {name:'Nova 2.5 Sonic',path:'차량/브라우저 → 우리 백엔드 → AWS Bedrock 양방향 S2S ↔ 앱 차량 도구 → 내장 음성',external:'필수 외부 추론 서비스: Bedrock. 가중치 다운로드·자체 GPU 서빙·완전 오프라인 불가. 도구 결과 왕복은 같은 스트리밍 세션에서 발생.'},
],components:[
 {name:'Whisper large-v3-turbo · 0.809B',hosting:'오픈 가중치 · MIT · 자체 GPU 가능',memory:'FP16 가중치 약 1.51GiB + 실행 버퍼. 경량화·차량 포팅 후 edge 검토',external:'현재 우리 GPU, 외부 ASR API 없음',source:'https://huggingface.co/openai/whisper-large-v3-turbo'},
 {name:'Nemotron ASR · 0.6B',hosting:'오픈 가중치 · 자체 GPU 가능 · 원본 라이선스 적용',memory:'현재 FP32 실행. edge 정밀도·스트리밍 런타임 별도 검증',external:'현재 우리 GPU, 외부 ASR API 없음',source:'https://huggingface.co/nvidia/nemotron-3.5-asr-streaming-0.6b'},
 {name:'Qwen3-TTS · 0.6B · Sohee',hosting:'오픈 가중치 · Apache-2.0 · 자체 GPU 가능',memory:'FP16 가중치 하한 약 1.12GiB + 음성 코덱·실행 버퍼. 차량 지연 미측정',external:'선택 시 외부 TTS API 없음',source:'https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice'},
 {name:'Amazon Polly · Seoyeon',hosting:'AWS 관리형 · 가중치 비공개 · 자체 GPU 불가',memory:'차량에는 API 클라이언트만 필요. 완전 오프라인 불가',external:'현재 기본 TTS이므로 open-weight 판단 모델에도 외부 API 호출이 남음',source:'https://docs.aws.amazon.com/polly/latest/dg/what-is.html'},
],sources,models:[]};
for(const m of catalog.models){
 const closed=m.id==='sonic',p=m.evidence?.parameters;const entry={id:m.id,name:m.name,parameters:p??null,openWeights:!closed,weightsStatus:closed?'비공개 · 자체 GPU 서빙 불가':m.status==='access-needed'?'오픈 가중치 · 접근 승인 필요':'오픈 가중치',selfHosting:closed?'불가 · Bedrock 전용':m.status==='access-needed'?'승인·라이선스 충족 후 가능':m.status==='license-review'?'라이선스 조건 충족 후 가능':'가능 · 원본 라이선스 적용',license:m.license,source:m.source,weightLowerBoundGiB:p?{int4:+(p*.5/2**30).toFixed(2),bf16:+(p*2/2**30).toFixed(2)}:null,edgeMeasured:false,currentHosting:closed?'AWS Bedrock · 도쿄':m.status==='ready'?'우리 EC2 L40S 48GB · 서울':'미배포',currentExtraApi:closed?'Bedrock S2S 필수 · 자체 GPU 대체 불가':'기본 제어 경로: Polly TTS 1종 추가 · Qwen TTS 선택 시 0종',server:closed?'자체 GPU 불가. 관리형 API만 이용':m.status==='ready'?'현재 자체 GPU 서빙 검증':'자체 GPU 배포 후보 · 미검증'};
 if(closed)Object.assign(entry,{runtimeMemory:'모델 크기·메모리 비공개',cockpit:'불가 · API 클라이언트만 탑재',orin:'불가 · 자체 추론 가중치 없음',thor:'불가 · 자체 추론 가중치 없음',deployment:'관리형 API 필수'});
 else if(m.role==='sllm'){
  const b=p/1e9,range=b<1.5?'1~3GiB':b<3?'2~4GiB':'3~6GiB';
  Object.assign(entry,{runtimeMemory:`INT4 판단 모델 ${range} 추정 + 로컬 ASR/TTS 약 3~6GiB 별도 예산`,cockpit:b<1.5?'메모리상 우선 후보 · 품질·NPU 포팅 검증':b<3?'조건부 후보 · 가용 RAM·NPU 포팅 검증':'16GB급 중 AI 여유 6GiB 이상이면 검토 · 전체 음성 경로는 더 필요',orin:'메모리상 후보 · INT4 런타임 포팅 필요',thor:'메모리상 후보 · 런타임 포팅 필요',deployment:'edge 포팅 후보 · 현재는 자체 서버'});
  if(m.id.startsWith('qwen35'))entry.porting='Hybrid GatedDeltaNet/conv 등 연산자·양자화 지원 확인. 미지원 시 CPU fallback 지연 측정.';
  else if(m.id==='gemma4-e2b')entry.porting='유효 2.3B와 저장 5.12B 구분. Per-layer embedding·멀티모달 분기 등 backend 지원 확인. 전체 가중치 기준 추정.';
  else entry.porting='해당 모델의 attention·토크나이저·JSON 제약 생성 지원 확인. INT4 전환 후 차량 명령 품질 재평가.';
 }else{
  const omni=m.id==='qwen3-omni';Object.assign(entry,{runtimeMemory:omni?'현재 NF4 Thinker + BF16 음성 분기 약 24GiB GPU 적재 관찰; 요청 peak·차량 공유 RAM은 별도':'BF16 음성 모델 실행 예산 약 20~28GiB 추정 · 모델/코덱/문맥에 따라 증가',cockpit:'현재 구성 부적합 · 8~16GB 공유 RAM 초과',orin:omni?'32GB 전체 중 여유 부족 · 서버 권장':'전용 메모리 확보 시 검토 · 다른 차량 작업과 공유 시 부족 가능',thor:'64GB급 메모리 후보 · 포팅·전력·지연 미검증',deployment:'현재는 서버 GPU 권장',porting:'CUDA·custom code·오디오 코덱·스트리밍 상태를 차량 runtime으로 포팅 필요. INT4 가중치 하한은 전체 음성 파이프라인 양자화 성공을 의미하지 않음.'});
  if(m.id==='moshi'){entry.currentExtraApi='음성 비교 전용: 외부 TTS API 없음 · 차량 판단 미지원';entry.deployment+=' · 한국어 제어 제외';}
  if(['minicpm-o45','step-audio2-mini','mimo-audio','personaplex','glm4-voice'].includes(m.id))entry.porting+=' 한국어 이해·내장 발음 제약을 메모리 포팅과 별도로 해결해야 함.';
 }
 entry.serverGpu=closed?'GPU 선택 불가 · Bedrock 관리형':m.role==='sllm'?'현재 L40S 48GB 검증. 전용 판단+ASR/TTS는 16~24GB급부터 메모리 검토(동시 세션·모델 분리 시 재산정)':m.id==='qwen3-omni'?'현재 L40S 48GB + 혼합 NF4 검증. 24GB GPU는 적재 관찰치만으로 여유를 보장할 수 없음':'현재 연결 모델은 L40S 48GB 검증. 24GB는 peak 확인 필요, 48GB급에서 시작 권장';
 if(m.status!=='ready'){entry.deployment=m.role==='sllm'?'미배포 · edge 포팅 후보':'미배포 · 서버 GPU 후보';entry.serverGpu='예상 24~48GB급부터 검토 · 자체 배포·메모리 미측정';}
 if(m.status!=='ready')entry.currentExtraApi='미배포 · 가중치 접근/라이선스 조건부터 충족 필요';
 const measured=quantizationComparison?.models.find(x=>x.id===m.id);if(measured){entry.measuredMemory=measured;entry.runtimeMemory=`현재 ${measured.quantization.toUpperCase()} 판단 모델 CUDA 적재 ${(measured.plannerCudaAllocatedMiB/1024).toFixed(2)}GiB + 요청 추가 peak ${(measured.maxRequestAdditionalMiB/1024).toFixed(2)}GiB 실측. ASR/TTS·OS 별도. 차량 공유 RAM 미측정.`;if(m.quantization==='nf4')entry.porting+=' 현재 CUDA NF4 양자화는 검증. Qualcomm NPU 형식 변환·정확도·발열·지연 재검증 필요.';}
 report.models.push(entry);
}
await writeFile('research/deployment-assessment.json',JSON.stringify(report,null,2));
console.log(`Deployment assessment: ${report.models.length} models, ${report.components.length} speech components`);
