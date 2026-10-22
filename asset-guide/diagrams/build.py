#!/usr/bin/env python3
"""Rebuild with the installed aws-diagram-design skill, then embed fonts for portability."""
from pathlib import Path
import argparse, base64, re, subprocess, sys

here=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--skill', type=Path, default=Path.home()/'.codex/skills/aws-diagram-design')
args=parser.parse_args()
subprocess.run([sys.executable,str(args.skill/'scripts/pygen/build.py'),str(here),'--out',str(here),'--langs','ko','--strict'],check=True)
notes={
 'deployment':'서울 공유 배포 구성입니다. 실시간 상태는 앱의 health API에서 확인합니다. GPU 1은 Core·Whisper·Qwen TTS 0.6B/1.7B·MiniCPM 워커가 같은 GPU의 VRAM을 공유합니다. Core는 판단 모델 1개와 필요할 때 로드하는 Nemotron ASR을 사용합니다. GPU 2는 Qwen3-ASR 두 모델을 독립 실행하며, 추가 음성 모델만 하나씩 교체합니다. 각 워커의 상주 여부와 한 요청의 모델 호출 경로는 별개입니다. Supertonic 3와 Ppaso는 GPU 1 호스트의 CPU에서 실행합니다. Ppaso는 한국어 전용 ONNX 경로입니다. AgentCore Gateway는 선택 확장이며 이번 배포에는 구성하지 않았습니다. 로컬 정보 도구는 별도 어댑터를 사용합니다.',
 'command-sequence':'기본 Whisper large-v3-turbo → Qwen3.5-4B NF4 → Polly Seoyeon 경로의 성공 사례입니다. Node 서버가 모든 네트워크 호출을 중계하고 차량 상태를 보관합니다. 실패·확인 질문 분기는 이 그림에서 생략했습니다. 검증 실패 시 상태를 유지하며, 상태 변경 후 TTS만 실패한 경우 차량 변경은 자동 취소되지 않습니다. 텍스트 입력은 STT를 건너뜁니다.',
 'gpu-residency':'상주는 모델이 GPU 메모리에 올라가 있다는 뜻이며 동시에 추론 중이라는 뜻은 아닙니다. GPU 1의 Core 워커에서는 판단 모델을 교체하고, Nemotron은 필요할 때 로드하거나 메모리가 부족하면 해제합니다. Whisper·Qwen TTS 0.6B·Qwen TTS 1.7B·MiniCPM은 별도 GPU 워커로, 요청에서 선택하지 않아도 활성 워커는 메모리를 점유할 수 있습니다. 실제 상주는 서비스 활성화·로딩 성공·메모리 여유에 따라 달라집니다. Supertonic 3와 Ppaso는 같은 호스트의 CPU/RAM을 사용하며 GPU VRAM 그룹 밖의 구성 요소입니다. GPU 2는 Qwen3-ASR 두 모델을 독립 실행하며 추가 음성 모델만 한 프로세스씩 교체합니다.',
 'model-paths':'세 경로는 선택 가능한 대안입니다. 단계형 박스에는 기본 모델 조합을 표시했습니다. 단계형·직접 음성 판단은 실행기가 만든 안내 문구를 별도 TTS로 읽고, Sonic은 도구 결과를 받아 자체 음성으로 답합니다. 제어 없는 네이티브 비교 모드는 별도입니다. Sonic의 한국어 지원 표시는 저장소에서 false입니다.'
}
order=['deployment','gpu-residency','command-sequence','model-paths']
styles=None
sections=[]
for slug in order:
 p=here/f'{slug}-ko.html';s=p.read_text()
 s=re.sub(r'<link href="https://fonts.googleapis.com/[^>]+>\s*','',s)
 def embed(m):
  data=base64.b64encode(Path(m[1]).read_bytes()).decode()
  return f'url(data:font/woff2;base64,{data})'
 s=re.sub(r"url\('file://([^']+)'\)",embed,s)
 s=s.replace("'Noto Sans KR',", "'Noto Sans KR','Noto Sans CJK KR',")
 s=s.replace('<meta charset="UTF-8">','<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">')
 s=s.replace('.frame{max-width:1200px}', '.frame{max-width:1280px;margin:auto}')
 s=s.replace('</style>','p.caption{font-size:16px;line-height:1.8;margin:16px 0}a{color:#0972D3}footer{font-size:12px;line-height:1.8;margin-top:24px;color:#545B64}nav{margin:20px 0}section{margin:48px 0}h2{font-size:28px}svg{margin:20px 0}html{scroll-behavior:smooth}</style>')
 caption=f'<p class="caption">{notes[slug]}</p>'
 footer='<footer>AWS Architecture Icons © Amazon Web Services, Inc. · aws.amazon.com/architecture/icons/<br>Amazon Ember 字体 내장 · 한글은 시스템 CJK 글꼴 사용 · aws-diagram-design / 1280 × 720</footer>'.replace('字体','글꼴')
 s=s.replace('</div></body>',caption+'<p><a href="../architecture.html">전체 다이어그램</a> · <a href="../ARCHITECTURE.md">상세 설명</a> · <a href="../MODELS.md">정확한 모델 목록</a></p>'+footer+'</div></body>')
 p.write_text(s)
 if styles is None:styles=re.search(r'<style>(.*?)</style>',s,re.S)[1]
 svg=re.search(r'(<svg\b.*?</svg>)',s,re.S)[1]
 # Isolate marker and icon IDs when several generated SVGs share a page.
 ids=re.findall(r'\bid="([^"]+)"',svg)
 for ident in sorted(set(ids),key=len,reverse=True):
  new=slug+'-page-'+ident
  svg=svg.replace(f'id="{ident}"',f'id="{new}"').replace(f'url(#{ident})',f'url(#{new})')
  svg=re.sub(r'(aria-labelledby=")([^"]+)(")',lambda m:m[1]+' '.join(new if v==ident else v for v in m[2].split())+m[3],svg)
 title=re.search(r'<h1>(.*?)</h1>',s,re.S)[1]
 sections.append(f'<section id="{slug}"><h2>{title}</h2>{svg}{caption}</section>')
index='<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>차량 음성 랩 — 아키텍처 다이어그램</title><style>'+styles+'</style></head><body><main class="frame"><p class="eyebrow">AWS DIAGRAM DESIGN · VEHICLE VOICE LAB</p><h1>차량 음성 랩: 구조와 실행 흐름</h1><p class="caption">모델은 명령을 제안하고, Node 서버가 검증한 뒤 가상 차량 상태를 변경합니다.</p><nav><a href="#deployment">① AWS 배포</a> · <a href="#gpu-residency">② GPU 상주</a> · <a href="#command-sequence">③ 명령 처리 순서</a> · <a href="#model-paths">④ 모델 경로 비교</a></nav>'+''.join(sections)+'<p><a href="README.md">에셋 안내</a> · <a href="ARCHITECTURE.md">구현 상세</a> · <a href="MODELS.md">정확한 모델 목록</a></p>'+footer+'</main></body></html>'
(here.parent/'architecture.html').write_text(index)
print('Portable HTML diagrams and architecture.html rebuilt.')
