"""Build the Korean TTS result page and summary from saved, complete reports."""
from pathlib import Path
import json,statistics,html
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'research/tts-comparison'
NAMES={'supertonic3':'Supertonic 3 · F1 · CPU','qwen17':'Qwen3-TTS 1.7B · Sohee · GPU','cosyvoice3':'CosyVoice 3 · 합성 참조 음성 · GPU'}
suite=json.loads((OUT/'cases.json').read_text());asr=json.loads((OUT/'asr-diagnostic.json').read_text())
reports={n:json.loads((OUT/(n+'.json')).read_text()) for n in NAMES}
assert len(asr['rows'])==24 and all(len(r['rows'])==8 for r in reports.values())
escape=html.escape
summary={'suiteId':suite['suiteId'],'caseCount':8,'outputCount':24,'humanListeningCompleted':False,
         'scope':'one generation per model/case; normalized ASR re-transcription, not MOS or a general model ranking',
         'timingBasis':'warm whole-utterance synthesis, valid audio only; not first streamed audio',
         'models':[]}
for name,report in reports.items():
    rs=[r for r in asr['rows'] if r['model']==name]
    valid=[r for r in report['rows'] if r.get('audioValid',r['durationSeconds']>=.1)]
    numeric=[r for r in rs if r['numberSequenceExpected']]
    summary['models'].append({'id':name,'repo':report['repo'],'revision':report['revision'],
        'device':report['configuration']['device'],'validAudio':len(valid),'total':8,
        'normalizedExact':sum(r['normalizedExact'] for r in rs),
        'normalizedCer':sum(r['characterErrors'] for r in rs)/sum(r['referenceCharacters'] for r in rs),
        'numericSequenceMatches':sum(r['numberSequenceMatches'] for r in numeric),'numericCases':len(numeric),
        'medianSynthesisMs':statistics.median(r['synthesisMs'] for r in valid),
        'medianRealTimeFactor':statistics.median(r['realTimeFactor'] for r in valid),
        'processLifetimePeakRssMiB':max(r['processLifetimePeakRssMiB'] for r in report['rows']),
        'torchCudaPeakAllocatedMiB':max((r.get('cudaPeakAllocatedMiB',0) for r in report['rows']),default=0) or None,
        'invalidAudioIds':[r['id'] for r in report['rows'] if not r.get('audioValid',r['durationSeconds']>=.1)],
        'mismatchIds':[r['id'] for r in rs if not r['normalizedExact']]})
(OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
parts=['<h1>한국어 차량 안내 TTS: 세 모델 직접 비교</h1>',
 '<p>동일한 8문장, 모델별 1회 생성입니다. 원본 입력과 Whisper 재인식 결과를 나란히 표시합니다. 아래 수치는 사람의 청취 품질 점수가 아닙니다.</p>',
 '<table><thead><tr><th>모델</th><th>재인식 완전 일치</th><th>숫자 순서 일치</th><th>문장 전체 생성 중앙값</th></tr></thead><tbody>']
for m in summary['models']:
 parts.append(f'<tr><td>{escape(NAMES[m["id"]])}</td><td>{m["normalizedExact"]}/8</td><td>{m["numericSequenceMatches"]}/{m["numericCases"]}</td><td>{m["medianSynthesisMs"]/1000:.2f}초</td></tr>')
parts.append('</tbody></table><p>CPU/GPU·목소리·출력 길이가 다릅니다. 속도는 첫 음성이 아닌 전체 생성 완료 시간이며, CosyVoice의 0.08초 실패는 속도 중앙값에서 제외했습니다. 음량 정규화 없이 모델 출력을 저장했습니다.</p>')
for case in suite['cases']:
 parts.append(f'<section><h2>{escape(case["id"])}: {escape(case["text"])}</h2><div class="players">')
 for name,report in reports.items():
  row=next(r for r in report['rows'] if r['id']==case['id']);ar=next(r for r in asr['rows'] if r['model']==name and r['id']==case['id'])
  caption=ar['transcript'] or '재인식 생략: 0.1초 미만의 짧은 산출물'
  parts.append(f'<article><h3>{escape(NAMES[name])}</h3><audio controls preload="none" src="../{escape(row["file"])}" aria-label="{escape(name+" "+case["id"])}"></audio><p><a href="../{escape(row["file"])}">WAV 다운로드</a> · 길이 {row["durationSeconds"]:.2f}초 · 생성 {row["synthesisMs"]/1000:.2f}초</p><p><strong>재인식:</strong> {escape(caption)}</p></article>')
 parts.append('</div></section>')
ref=reports['qwen17']['referenceGenerated']
parts.append('<section><h2>CosyVoice에 사용한 합성 참조 음성</h2><p>Qwen3-TTS 1.7B의 Sohee로 별도 생성했습니다. 실제 사람의 녹음이 아니며 시험 문장 8개와도 별개입니다. CosyVoice 결과는 이 참조·설정 조합의 결과입니다.</p>')
parts.append(f'<p>{escape(ref["text"])}</p><audio controls preload="none" src="../{escape(ref["file"])}" aria-label="CosyVoice 합성 참조 음성"></audio></section>')
parts.append('<p><a href="TTS_COMPARISON.md">설정·결과 해석·재현 방법</a> · <a href="MODEL_CANDIDATES.md">후보 목록</a> · <a href="README.md">에셋 가이드</a></p>')
css='body{font:16px/1.7 system-ui,sans-serif;color:#232f3e;background:white;max-width:1320px;margin:auto;padding:32px}a{color:#0972d3}section{margin:36px 0;border-top:1px solid #d5dbdb;padding-top:20px}h2{font-size:20px}h3{font-size:16px}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:12px;border-bottom:1px solid #d5dbdb}.players{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:24px}audio{width:100%;max-width:440px}p{overflow-wrap:anywhere}'
(ROOT/'asset-guide/tts-comparison.html').write_text('<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>한국어 TTS 비교</title><style>'+css+'</style></head><body>'+''.join(parts)+'</body></html>')
print(json.dumps(summary,ensure_ascii=False,indent=2))
