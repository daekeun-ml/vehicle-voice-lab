"""Publish only non-sensitive verification facts; never copy private deployment state."""
from pathlib import Path
import json,re,datetime
ROOT=Path(__file__).resolve().parents[1]
read=lambda p:json.loads((ROOT/p).read_text())
cloud=read('research/cloud-deployment-validation.json')
tts=read('.runtime/cloud-tts-validation.json')
audio=read('.runtime/cloud-audio-paths-validation.json')
sonic=read('output/sonic-cloud-smoke.json')
browser=read('.runtime/browser-microphone-validation.json')
timers=read('.runtime/auto-stop-times.json')
assert cloud['passed'] and tts['passed'] and len(tts['checks'])==12
assert len(audio['checks'])==2 and all(r['passed'] for r in audio['checks'])
assert sonic['results'][0]['commandCorrect'] and sonic['results'][0]['audioGenerated']
assert browser['passed'] and browser['cancellationVerified']
log=(ROOT/('.runtime/ppaso-tests.log' if (ROOT/'.runtime/ppaso-tests.log').exists() else '.runtime/unit-tests.log')).read_text()
passed=int(re.search(r'# pass (\d+)',log)[1]);failed=int(re.search(r'# fail (\d+)',log)[1]);assert failed==0
summary={'validatedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'url':cloud['base'],'computeRegion':'ap-northeast-2','instanceType':'g6e.2xlarge','gpuHosts':2,
 'defaultTts':'polly','enabledTts':['polly','qwen','qwen17','supertonic','ppaso'],
 'verification':{'unitPassed':passed,'unitFailed':failed,'coreAudioControl':True,'sessionIsolation':cloud['sessionIsolation'],
 'ttsChecks':len(tts['checks']),'ttsModelIdentityAndWav':True,
 'directAudioModels':[r['model'] for r in audio['checks']],
 'sonicEnglish':True,'sonicKoreanExperimental':bool(sonic['results'][1].get('commandCorrect') and sonic['results'][1].get('audioGenerated')),
 'syntheticBrowserMicrophone':True,'browserPlayback':True,'browserCancel':True,'realHumanMicrophoneTested':False},
 'scopeNotes':['Qwen3-ASR 0.6B/1.7B and Ppaso are active. Kokoro was removed; CosyVoice remains an offline experiment.',
 'Noise suppression prototypes are not applied to the live audio path.',
 'AgentCore Gateway was not provisioned; local information providers remain available.',
 'The 14 control configurations and four ASR providers have separate checkpointed benchmark reports. Moshi is not a vehicle-control benchmark configuration.',
 'The 48-case hard suite is separate and not reported as passed deployment coverage.'],
 'configuredAutoStopHours':read('.runtime/aws.json').get('autoStopHours',4),'autoStopAt':{k:v['autoStopAt'] for k,v in timers.items()}}
if (ROOT/'research/asr-comparison/summary.json').exists():
 asr=read('research/asr-comparison/summary.json')
 summary['asrComparison']={'status':asr['status'],'completed':sum(m['completed'] for m in asr['models']),
  'total':sum(m['total'] for m in asr['models']),'corpusHash':asr['corpusHash']}
if (ROOT/'research/tts-comparison/ppaso.json').exists():
 ppaso=read('research/tts-comparison/ppaso.json')
 summary['ppasoVerification']={'model':ppaso['repo'],'revision':ppaso['revision'],'synthesized':len(ppaso['rows']),
  'normalizedRetranscriptionExact':sum(r['normalizedExact'] for r in ppaso['rows']),
  'vehicleStateUnchanged':ppaso.get('vehicleStateUnchanged'),'kokoroRejected':ppaso.get('kokoroRejected'),
  'humanListeningCompleted':False}
(ROOT/'asset-guide/deployment-status.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
start='<!-- VERIFIED_DEPLOYMENT_START -->';end='<!-- VERIFIED_DEPLOYMENT_END -->'
block=f'''{start}
## 이번 서울 배포에서 확인한 결과

- 공유 URL: [{cloud['base']}]({cloud['base']}/?lang=ko)
- 검증 시점: `{summary['validatedAt']}`.
- 자동 테스트 {passed}개, 기본 음성 제어·세션 분리, 기존 네 TTS의 12개 요청 검증 통과.
- [STT 4종 비교](STT_COMPARISON.md)와 [Ppaso ONNX CPU 합성·재인식](PPASO_TTS.md)은 별도 결과로 확인합니다. Kokoro는 제거했습니다.
- MiniCPM·Step-Audio 직접 음성 제어, Sonic 영어 및 한국어 실험 샘플 동작 확인.
- 브라우저 합성 마이크 입력·실제 오디오 재생 이벤트·취소·새 세션 상태 확인.
- 실제 사람의 마이크·소음 환경·청취 품질은 참가자 실습에서 별도로 확인.
- 이번 부팅 기준 자동 중지 예정: GPU 1 `{timers['core']['autoStopAt']}`, GPU 2 `{timers['speech']['autoStopAt']}`. 재부팅하면 일정이 바뀝니다.

[기계 판독용 검증 요약](deployment-status.json). 이 검증은 모든 후보 모델·고난도 48문제·실차 성능을 통과했다는 뜻이 아닙니다. 이번 배포는 로컬 정보 제공자를 사용하며 AgentCore Gateway는 선택 확장으로 남겼습니다.
{end}
'''
p=ROOT/'asset-guide/HANDS_ON.md';text=p.read_text()
if start in text:text=re.sub(re.escape(start)+r'.*?'+re.escape(end),block.strip(),text,flags=re.S)
else:text=text.replace('## 실습 완료 기준',block+'\n## 실습 완료 기준',1)
p.write_text(text)
print(json.dumps(summary,ensure_ascii=False,indent=2))
