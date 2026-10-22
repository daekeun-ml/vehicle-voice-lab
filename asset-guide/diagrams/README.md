# 아키텍처 다이어그램

[전체 그림 한 번에 보기](../architecture.html)

| 그림 | PNG | 형식 | 설명 |
| --- | --- | --- | --- |
| [GPU 모델 상주](gpu-residency-ko.html) | [다운로드](gpu-residency-ko.png) | Architecture | GPU 1의 독립 워커와 GPU 2의 단일 모델 교체 |
| [AWS 배포 구성](deployment-ko.html) | [다운로드](deployment-ko.png) | Architecture | 9개 구성 요소, GPU 워커·CPU Supertonic·AWS API 연결 |
| [명령 처리 순서](command-sequence-ko.html) | [다운로드](command-sequence-ko.png) | Sequence | 5개 참여자, 기본 Whisper → Qwen3.5-4B NF4 → Polly 경로 |
| [모델 경로 비교](model-paths-ko.html) | [다운로드](model-paths-ko.png) | Architecture | 6개 구성 요소, 3가지 이해 경로와 공통 실행기 |

`aws-diagram-design` 스킬의 Python 생성기로 작성했습니다. 모두 1280×720 가로형이며 AWS 공식 아이콘, Amazon Ember 글꼴, 직각 연결선을 사용합니다. HTML에 아이콘과 영문 글꼴을 포함하므로 스킬 설치 경로에 의존하지 않고 열 수 있습니다. 한글은 시스템 CJK 글꼴을 사용합니다.

가이드에는 2배 해상도인 **2560×1440 PNG**를 삽입했습니다. PNG에는 렌더링된 한글이 포함되어 보는 환경의 글꼴에 영향을 받지 않습니다.

## 다시 생성하기

스킬이 설치된 환경에서:

```bash
python3 asset-guide/diagrams/build.py
```

다른 경로에 설치했다면:

```bash
python3 asset-guide/diagrams/build.py --skill /path/to/aws-diagram-design
```

[spec_vehicle.py](spec_vehicle.py)가 내용과 배치 원본이고, [build.py](build.py)가 스킬 생성기를 실행한 뒤 글꼴을 내장하고 통합 HTML을 만듭니다. 생성기의 레이아웃·텍스트 경고가 있으면 빌드를 실패시킵니다.

HTML을 수정·재생성한 뒤 PNG도 갱신하세요. Playwright·Chromium과 한글 글꼴이 설치된 환경에서:

```bash
python3 asset-guide/diagrams/export_png.py
```

[export_png.py](export_png.py)는 HTML의 SVG 영역만 투명 배경으로 내보냅니다. 페이지 제목과 설명은 포함하지 않습니다.

## 상세 수준

- 배포 구성: GPU 1의 독립 워커를 VRAM 공유 그룹으로 묶었습니다. Gateway 뒤의 Lambda·Web Search와 로컬 도구는 설명에 남겼습니다.
- GPU 상주: Core의 Nemotron+판단 모델, 별도 Whisper·Qwen TTS 2개·MiniCPM 워커와 GPU 2의 모델 교체 단위를 표시합니다. 메모리 공유는 GPU 경계로 표현하며 호출 순서를 나타내는 화살표는 사용하지 않습니다.
- 명령 순서: 기본 모델 이름·정밀도를 명시한 정상 차량 변경 한 건을 보여줍니다. 실패·확인 질문 분기는 설명에 남겼습니다.
- 모델 비교: README의 기존 Mermaid 6개 노드·5개 연결을 유지하여 다시 배치했습니다. 네이티브 음성 비교 모드는 실행기 밖의 별도 모드로 명시했습니다.

배포 가동 상태를 조회한 그림이 아닙니다. 구현 근거는 [상세 아키텍처](../ARCHITECTURE.md)에 있습니다.
