"""Render local audio A/B galleries from recorded probe results; does not rerun models."""
import json,html,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
read=lambda name:json.loads((ROOT/name).read_text())
k=read('research/kokoro-korean/asr-diagnostic.json')
n=read('research/audio-front-end/asr-diagnostic.json')
s=read('research/audio-front-end/signal-metrics.json')
r=read('research/audio-front-end/rnnoise-metrics.json')
ra=read('research/audio-front-end/rnnoise-asr.json')
escape=html.escape

def player(path,label):
    return f'<audio controls preload="none" aria-label="{escape(label)}" src="../{escape(path)}"></audio><a href="../{escape(path)}">WAV 다운로드</a>'

parts=['<h1>음성 실험: 원본과 결과 직접 비교</h1>',
 '<p>앱 기본 경로에 적용하지 않은 실험입니다. Kokoro는 한국어 음소 우회 입력, 잡음 시험은 기존 합성 음원 2개에 인공 잡음을 섞었습니다. ASR 결과는 청취 품질이나 차량 명령 정확도 점수가 아닙니다.</p>',
 '<nav><a href="#noise">잡음 제거 A/B</a> · <a href="#kokoro">Kokoro 한국어</a></nav>',
 '<section id="noise"><h2>잡음 제거: 원본 / 보수적 DSP / RNNoise</h2>',
 '<p>RNNoise는 이 환경에서 확인한 고정 20ms 지연을 오프라인으로 보정했습니다. 숫자·좌석·부정이 달라지는지 듣고 확인하세요. 일부 사례는 잡음이 줄어도 ASR이 나빠집니다.</p>']
for i,row in enumerate(s['rows']):
    asr=next(x for x in n['rows'] if x['id']==row['id'])
    rnn=next(x for x in r['rows'] if x['id']==row['id'])
    rnasr=next(x for x in ra['rows'] if x['id']==row['id'])
    parts.append(f'<details {"open" if row["id"]=="command-stationary-colored-0dB" else ""}><summary>{escape(row["id"])}</summary>')
    parts.append('<p>정답 대용: '+escape(asr['referenceProxy'])+' (깨끗한 원본의 ASR 결과이며, 사람이 작성한 정답 전사가 아님)</p><div class="players">')
    for title,path,transcript in [('원본',row['input'],asr['before']['text']),('보수적 DSP',row['output'],asr['after']['text']),('RNNoise',rnn['output'],rnasr['asr']['text'])]:
        parts.append(f'<article><h3>{title}</h3>{player(path,title)}<p>재인식: {escape(transcript)}</p></article>')
    parts.append('</div></details>')
parts.append('</section><section id="kokoro"><h2>Kokoro-82M: 한국어 음소 입력 실험</h2><p>공식 ko/k 모드는 거부됩니다. 아래는 eSpeak 한국어 음소를 직접 넣은 우회 실험이며, 영어 af_heart와 일본어 jf_alpha 음성을 사용했습니다. 한국어 학습·음성 추가를 한 것은 아닙니다.</p>')
for sid in ['greeting','temperature','negation','seat-scope']:
    subset=[row for row in k['rows'] if row['id']==sid]
    parts.append(f'<details {"open" if sid=="temperature" else ""}><summary>{escape(subset[0]["text"])}</summary><div class="players">')
    for row in subset:
        title=row['adapter']+' / '+row['voice']
        parts.append(f'<article><h3>{escape(title)}</h3>{player(row["file"],title)}<p>재인식: {escape(row["asr"]["text"])}</p></article>')
    parts.append('</div></details>')
p=read('research/kokoro-korean/probe.json')
parts.append('<h3>영어 합성 확인용</h3>'+player(p['englishControl']['file'],'영어 합성 확인')+'<p>'+escape(k['englishControl']['text'])+'</p></section>')
parts.append('<p><a href="AUDIO_FRONTEND.md">잡음 제거 설계·측정 설명</a> · <a href="KOKORO_KOREAN_TEST.md">Kokoro 진단 설명</a> · <a href="README.md">가이드</a></p>')
css='body{font:16px/1.7 system-ui,sans-serif;color:#232f3e;background:#fff;max-width:1280px;margin:auto;padding:32px}a{color:#0972d3}section{margin:48px 0}details{border:1px solid #d5dbdb;border-radius:8px;padding:16px;margin:16px 0}summary{font-weight:700;cursor:pointer}.players{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:24px}article{min-width:0}audio{width:100%}h3{font-size:16px}p{overflow-wrap:anywhere}'
(ROOT/'asset-guide/audio-lab.html').write_text('<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>음성 처리 실험</title><style>'+css+'</style></head><body>'+''.join(parts)+'</body></html>')

summary={'scope':'2 synthetic source clips × 2 artificial noise types × 3 levels; clean ASR proxy reference',
         'noiseCaseCount':12,'cleanControlCount':2,'methods':{}}
for name in ['conservative-dd-wiener-v1','RNNoise']:
    counts={'improved':0,'same':0,'worse':0}
    for row in n['rows']:
        if row['condition']=='clean':continue
        score=row['afterAgreementErrorRate'] if name!='RNNoise' else next(x for x in ra['rows'] if x['id']==row['id'])['agreementErrorRate']
        before=row['beforeAgreementErrorRate']
        counts['improved' if score<before else 'worse' if score>before else 'same']+=1
    summary['methods'][name]=counts
summary['decision']='Do not enable either algorithm globally. Validate real recorded speech, critical token errors, and downstream vehicle plans first.'
(ROOT/'research/audio-front-end/summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(summary,ensure_ascii=False))
