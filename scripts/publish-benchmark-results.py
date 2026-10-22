"""Render existing recorded results only; never invoke models."""
from pathlib import Path
import json,statistics
ROOT=Path(__file__).resolve().parents[1]
read=lambda p:json.loads((ROOT/p).read_text())
control=read('research/deployment-benchmarks/summary.json')
asr=read('research/asr-comparison/summary.json')
lines=['# 벤치마크 결과', '', '웹에 게시한 실제 평가 기록을 표로 정리했습니다. 이 문서 생성 과정에서는 모델을 다시 호출하지 않습니다.', '',
       f"- 제어 평가 기록 시각: {control['updatedAt']}",f"- STT 평가 완료 시각: {asr['updatedAt']}",
       '- 환경: AWS 서울, g6e.2xlarge × 2, 서버당 NVIDIA L40S 48GB. Sonic은 도쿄 Bedrock API.',
       '- 입력: 합성 음성. 실제 차량 녹음·사람 청취/MOS 평가 결과가 아닙니다.',
       '- Qwen3-Omni의 남은 고난도 평가는 사용자 요청에 따라 보류했습니다. 부분 결과를 전체 점수로 환산하지 않습니다.', '',
       '## 제어 모델 14개 설정', '',
       '기존 31개는 동작·상태·답변 규칙·음성 출력을 함께 검사합니다. 고난도 48개는 동작·상태 자동 판정과 답변 의미를 포함한 AI 검토를 분리했습니다. 모델 원안은 앱의 검증·보정 전 동작 제안입니다.', '',
       '| 모델 / 설정 | STT / 입력 | 기존 31개 통과 | 고난도 동작·상태 | 고난도 답변 포함 | 고난도 모델 원안 | 기존 첫 음성 중앙값 | 상태 |',
       '|---|---|---:|---:|---:|---:|---:|---|']
for m in control['models']:
 a,b=m['suites']['original31'],m['suites']['hard48']
 partial=b['status']!='complete'
 auto=f"{b['actionStateCorrect']}/{b['completed']}"+(' (부분)' if partial else '')
 strict=f"{b['strictPassed']}/48" if b.get('strictPassed') is not None else '미검토'
 timing=f"{a['medianFirstAudioMs']/1000:.2f}s" if a.get('medianFirstAudioMs') is not None else '—'
 state=f"보류 · {b['completed']}/48 실행" if partial else '완료'
 lines.append(f"| {m['name']} | {a.get('asrId') or '직접 음성'} | {a['passed']}/31 | {auto} | {strict} | {b['modelActionCorrect']}/{b['completed']} | {timing} | {state} |")
lines+=['', '- 14개 설정은 14개 서로 다른 가중치를 뜻하지 않습니다. Qwen3.5 4B의 BF16/NF4 설정을 별도 평가했습니다.',
        '- Qwen3-Omni는 thinker NF4 + 오디오 부분 BF16입니다. Sonic 한국어는 실험 경로입니다.',
        '- 워커는 웹과 공유합니다. 초기 로딩은 지연 집계에서 제외했고, ASR 분리 작업 중 클라이언트가 멈췄던 Omni `scope-04`는 품질 결과를 유지하되 지연 집계에서 제외했습니다.',
        '- 인프라 오류 재시도 기록은 원시 파일에 보존했습니다. 미실행 문제는 오답으로 세지 않았습니다.',
        '- [원시 제어 결과](research/deployment-benchmarks/summary.json) · [답변 의미 검토 근거](research/deployment-benchmarks/semantic-reviews.json)', '',
        '## STT 비교 — 824건 완료', '',
        '네 STT에 동일한 206개 입력을 사용했습니다. 아래 원음은 기존 31개와 고난도 48개를 합친 79개입니다. 제어 모델은 Qwen3.5 4B BF16 / compact-v2로 고정했습니다.', '',
        '| STT | 원음 CER ↓ | 숫자 언급 일치 | 좌석 언급 일치 | 목적지 언급 일치 | 인식 중앙값 | 최종 제어 동작·상태 | 전체 실행 오류 |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
names={'whisper':'Whisper large-v3-turbo','nemotron':'Nemotron 3.5 ASR','qwen3-asr-06b':'Qwen3-ASR 0.6B','qwen3-asr-17b':'Qwen3-ASR 1.7B'}
for m in asr['models']:
 g=next(g for g in m['groups'] if g['condition']=='original')
 ratio=lambda k:f"{g['entities'][k]['correct']}/{g['entities'][k]['total']}"
 lines.append(f"| {names[m['id']]} | {g['cer']*100:.2f}% | {ratio('numbers')} | {ratio('seats')} | {ratio('destinations')} | {g['medianAsrMs']}ms | {g['actionStateCorrect']}/79 | {sum(g['errors'] for g in m['groups'])}/{m['completed']} |")
lines+=['', 'CER은 공백·문장부호를 제거하지만 `24`와 `이십사`의 표기 차이는 유지합니다. 숫자·좌석·목적지 점수는 제한된 명시적 언급 검사이며 일반 개체명 인식 점수가 아닙니다. 제어 실패에는 STT뿐 아니라 고정 판단 모델의 오류도 포함됩니다.', '',
        '### 잡음 전처리 전후', '',
        '| STT | 원음 79개 | 원음 + 필터 | 유색 잡음 10dB 12개 | 유색 잡음 + 필터 | 백색 잡음 0dB 12개 | 백색 잡음 필터 경로 |',
        '|---|---:|---:|---:|---:|---:|---:|']
conditions=['original','original-denoised','colored-10dB','colored-10dB-denoised','white-0dB','white-0dB-denoised']
for m in asr['models']:
 groups={g['condition']:g for g in m['groups']}
 cells=[f"{groups[c]['actionStateCorrect']}/{groups[c]['completed']}" for c in conditions]
 lines.append('| '+names[m['id']]+' | '+' | '.join(cells)+' |')
lines+=['', '표는 최종 제어 동작·상태 일치 수입니다. 필터는 `conservative-dd-wiener-v1`입니다. 백색 잡음 0dB는 12개 모두 신뢰할 조용한 구간을 찾지 못해 감쇠를 적용하지 않았습니다. 저장 정밀도 차이(최대 1 LSB)가 있어 그 경로의 작은 점수 차이를 노이즈 제거 효과로 해석하지 않습니다.',
        '', '824건은 GPU2 모델을 순차 교체하던 구성에서 측정했습니다. 이후 웹 STT의 429 충돌을 고쳐 Qwen3-ASR 두 워커를 독립 상주·별도 대기열로 분리했습니다. 동시 동작 검증은 아래 별도 기록입니다.',
        '', '- [STT 상세 표·방법](asset-guide/STT_COMPARISON.md) · [원시 STT 결과](research/asr-comparison/summary.json) · [독립 워커 동시 호출 검증](research/asr-comparison/live-concurrency-validation.json)', '',
        '## TTS — 실제 배포의 같은 문장 합성', '',
        '문장: “조수석 온도를 스물네 도로 맞췄어요.” 각 모델 단건이며 측정 시각이 다릅니다. 서버는 전체 WAV 생성 후 반환합니다.', '',
        '| 모델 | 실행 | 합성 처리 시간 | 출력 음성 길이 |', '|---|---|---:|---:|']
snapshot=read('research/tts-comparison/live-latency-snapshot.json')
for r in snapshot['rows']:
 name={'qwen':'Qwen CustomVoice 0.6B','qwen17':'Qwen CustomVoice 1.7B','supertonic':'Supertonic 3','polly':'Amazon Polly'}[r['provider']]
 device='AWS API 왕복' if r['provider']=='polly' else 'CPU' if r['provider']=='supertonic' else 'L40S GPU'
 lines.append(f"| {name} | {device} | {r['inferenceMs']}ms | {r['audioSeconds']:.2f}s |")
ppaso=read('research/tts-comparison/ppaso.json');r=next(r for r in ppaso['rows'] if r['id']=='temperature')
lines.append(f"| Ppaso-TTS | ONNX CPU | {r['synthesisMs']}ms | {r['durationSeconds']:.2f}s |")
lines+=['', '출력 음성 길이·구현·하드웨어가 달라 위 수치만으로 모델 자체의 속도를 일반화할 수 없습니다. Polly의 수치는 순수 합성 연산이 아니라 API 왕복입니다.', '',
        '### 8문장 발음 진단', '', '| 모델 | 정규화 재인식 일치 | 측정 구분 |', '|---|---:|---|']
diag=read('research/tts-comparison/asr-diagnostic.json')
for name,label in [('qwen17','Qwen CustomVoice 1.7B'),('supertonic3','Supertonic 3'),('cosyvoice3','CosyVoice 3')]:
 rows=[r for r in diag['rows'] if r['model']==name]
 lines.append(f"| {label} | {sum(r['normalizedExact'] for r in rows)}/{len(rows)} | 기존 격리 실험; GPU 모델은 RTX PRO 4500 Blackwell |")
lines.append(f"| Ppaso-TTS | {sum(r['normalizedExact'] for r in ppaso['rows'])}/8 | 서울 EC2 CPU; 소수·음수 전처리 보완 후 개발 세트 |")
lines+=['', f"Ppaso의 8문장 합성 중앙값은 **{statistics.median(r['synthesisMs'] for r in ppaso['rows']):g}ms**입니다. 재인식 일치는 사람 청취/MOS가 아닙니다. Ppaso 수정 전 결과는 별도 보존했고, Kokoro는 사용자의 요청에 따라 UI·API·서비스에서 제거했습니다.",
        '', '- [Ppaso 상세·음성 파일](asset-guide/PPASO_TTS.md) · [Ppaso 원시 결과](research/tts-comparison/ppaso.json) · [기존 TTS 3종 실험](asset-guide/TTS_COMPARISON.md)', '',
        '## 재현과 검증', '',
        '- [핸즈온 가이드](asset-guide/HANDS_ON.md): 배포·모델 선택·실행 절차',
        '- `scripts/run-deployment-benchmarks.mjs`: 고정 31/48개 평가, 체크포인트 재개',
        '- `scripts/run-asr-comparison.mjs`: 4종 STT와 고정 판단 모델 비교',
        '- `scripts/probe-ppaso-live.py`: 합성·재인식·차량 상태 무변경·Kokoro 제거 검증',
        '- `python3 scripts/publish-benchmark-results.py`: 저장된 결과에서 이 Markdown 재생성',
        '- Git에는 합성 음성·비식별 결과·코드만 포함합니다. 개인 키, 세션 키, 배포 비밀 설정은 포함하지 않습니다.', '']
(ROOT/'BENCHMARK_RESULTS.md').write_text('\n'.join(lines))
print('Wrote BENCHMARK_RESULTS.md from recorded results.')
