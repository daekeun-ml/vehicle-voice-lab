"""Validate completed paired STT runs and render final guide tables."""
from pathlib import Path
import json, math, statistics
ROOT=Path(__file__).resolve().parents[1]
folder=ROOT/'research/asr-comparison'
summary=json.loads((folder/'summary.json').read_text())
manifest=json.loads((ROOT/'output/asr-comparison/manifest.json').read_text())
inputs={x['id']:x for x in manifest['items']}
names={'whisper':'Whisper turbo','nemotron':'Nemotron 3.5','qwen3-asr-06b':'Qwen3-ASR 0.6B','qwen3-asr-17b':'Qwen3-ASR 1.7B'}
assert summary['status']=='complete', 'Do not publish unfinished evaluations as final'
lines=['## 실측 결과', '', f"집계 시각: {summary['updatedAt']}. 네 모델 모두 동일한 {len(inputs)}개 입력을 처리했습니다.", '',
       '아래 제어 점수는 답변 의미를 제외한 동작·최종 상태 일치입니다. CER은 숫자의 문자 표기 차이도 오류로 셉니다.', '']
conditions={'original':'기존 79개 원음','original-denoised':'기존 79개 노이즈 제거',
            'colored-10dB':'유색 잡음 10dB','colored-10dB-denoised':'유색 잡음 10dB + 노이즈 제거',
            'white-0dB':'백색 잡음 0dB','white-0dB-denoised':'백색 잡음 0dB + 노이즈 제거'}
runs={}
for m in summary['models']:
    run=json.loads((folder/(m['id']+'.json')).read_text())
    assert run['status']=='complete' and len(run['rows'])==len(inputs)
    assert len({r['id'] for r in run['rows']})==len(inputs)
    assert run['corpusHash']==summary['corpusHash']
    for r in run['rows']:
        assert r['sha256']==inputs[r['id']]['sha256']
    runs[m['id']]=run
for condition,title in conditions.items():
    lines += ['### '+title, '',
              '| STT | CER ↓ | 숫자 | 좌석 | 목적지 | 인식 중앙값 / P95 | 제어 동작·상태 | 실행 오류 |',
              '|---|---:|---:|---:|---:|---:|---:|---:|']
    for model in summary['models']:
        g=next(x for x in model['groups'] if x['condition']==condition)
        timings=sorted(r['asrMs'] for r in runs[model['id']]['rows'] if r['condition']==condition and not r.get('error') and not r.get('loadMs'))
        p95=timings[math.ceil(len(timings)*.95)-1] if timings else None
        entity=lambda k:f"{g['entities'][k]['correct']}/{g['entities'][k]['total']}" if g['entities'][k]['total'] else '—'
        cer=f"{g['cer']*100:.1f}%" if g['cer'] is not None else '—'
        lines.append(f"| {names[model['id']]} | {cer} | {entity('numbers')} | {entity('seats')} | {entity('destinations')} | {g['medianAsrMs']} / {p95} ms | {g['actionStateCorrect']}/{g['completed']} | {g['errors']} |")
    lines.append('')
lines+=['### 원음 세트별 제어 결과','',
        '| STT | 기존 31개 동작·상태 | 고난도 48개 동작·상태 |','|---|---:|---:|']
for mid,run in runs.items():
    counts=[]
    for suite in ['original31','hard48']:
        rows=[r for r in run['rows'] if r['condition']=='original' and r['suite']==suite]
        counts.append(f"{sum(bool(r.get('control',{}).get('actionStateCorrect')) for r in rows)}/{len(rows)}")
    lines.append(f"| {names[mid]} | {counts[0]} | {counts[1]} |")
lines+=['','### 전처리의 짝지은 영향','',
        '같은 모델·같은 원본 음성에서 전처리로 제어 결과가 개선되거나 악화된 수입니다. 두 조건 모두 성공하거나 모두 실패한 입력은 개선·악화에 포함하지 않습니다.','',
        '| STT | 입력 조건 | 실패 → 성공 | 성공 → 실패 |','|---|---|---:|---:|']
for mid,run in runs.items():
    rows={r['id']:r for r in run['rows']}
    for condition in ['original','colored-10dB','white-0dB']:
        improved=worsened=0
        for r in run['rows']:
            if r['condition']!=condition:continue
            after=rows[r['id']+'-denoised']
            if r.get('error') or after.get('error'):continue
            a=bool(r.get('control',{}).get('actionStateCorrect'));b=bool(after.get('control',{}).get('actionStateCorrect'))
            improved+=not a and b;worsened+=a and not b
        lines.append(f'| {names[mid]} | {conditions[condition]} | {improved} | {worsened} |')
lines+=['',f"입력 manifest SHA-256: `{summary['corpusHash']}`.",'',
        '원본 79개와 별도 12개 잡음 부분집합의 크기가 다릅니다. 표의 비율을 서로 다른 전체 모집단의 일반 성능으로 해석하지 마세요.']
p=ROOT/'asset-guide/STT_COMPARISON.md'
text=p.read_text().split('<!-- ASR_RESULTS -->')[0].rstrip()
p.write_text(text+'\n\n<!-- ASR_RESULTS -->\n\n'+'\n'.join(lines)+'\n')
print('Validated four completed STT runs and rendered result tables.')
