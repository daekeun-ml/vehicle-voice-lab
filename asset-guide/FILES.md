# 어떤 파일이 무엇인가요?

[처음 설명으로 돌아가기](README.md)

## 화면·음성 에셋

| 위치 | 무엇인가요? | 어떻게 보면 되나요? |
| --- | --- | --- |
| [한국어 화면](../docs/screenshots/korean-ui.png) / [영어 화면](../docs/screenshots/english-ui.png) | 데모 화면을 찍은 이미지 | 앱의 전체 모습을 먼저 확인 |
| [sample-command.wav](../public/sample-command.wav) | 한국어 차량 명령 입력 샘플 | “조수석 온도 25도” 테스트에 사용 |
| [sample-english.wav](../public/sample-english.wav) | 영어 입력 샘플 | 영어 음성 테스트에 사용 |
| [sample-greeting.wav](../public/sample-greeting.wav) | MiniCPM 경로에서 쓰는 별도 입력 샘플 | 해당 모델의 샘플 음성 테스트에 사용 |
| [reference-neutral.wav](../public/reference-neutral.wav) | MiniCPM 음성 생성에 사용하는 참조 음성 | 음성 생성 설정용 자료 |
| [benchmark-audio 폴더](../public/benchmark-audio/) | 모델 비교 실험에서 저장한 응답 음성 | 모델별 시험 응답을 직접 들어보기 |
| [favicon.svg](../public/favicon.svg) | 브라우저 탭의 작은 아이콘 | 앱 표시용 이미지 |

비교 음성 파일명은 **`모델명-시험내용-reply.wav`** 형태입니다.

- `passenger-25`: 조수석 온도 25도 요청.
- `defrost-on`: 앞유리 김서림 제거 켜기 요청.
- `reply`: 사용자의 입력이 아니라 시스템의 응답 음성.

예를 들어 `qwen35-4b-nf4-passenger-25-reply.wav`는 Qwen3.5-4B NF4 설정으로 조수석 온도 요청을 시험했을 때의 응답입니다. **파일의 모델명이 곧 목소리를 만든 모델이라는 뜻은 아닙니다.** 명령 판단은 해당 모델이 하고, 음성은 Polly 같은 별도 서비스가 만들 수 있습니다.

## 프로젝트 구성

| 위치 | 쉬운 설명 |
| --- | --- |
| [public/](../public/) | 사용자가 보는 화면, 버튼 동작, 디자인, 샘플 음성 |
| [server.mjs](../server.mjs) | 화면의 요청을 받아 모델·차량 상태·응답을 연결하는 중앙 서버 |
| [vehicle.mjs](../vehicle.mjs) | 가상 차량의 상태와 명령 실행 규칙. 온도 범위 등도 검사 |
| [planner-prompt-v2.mjs](../planner-prompt-v2.mjs) | AI에게 차량 명령을 어떻게 판단할지 알려주는 지시문 |
| [runtime/](../runtime/) | 서버에서 음성 인식·명령 판단·음성 생성 모델을 실행하는 코드 |
| [model-catalog.json](../model-catalog.json) | 비교 대상 모델과 관련 정보 목록 |
| [research/](../research/) | 비교 점수, 속도, 실패 사례 등 실험 기록 |
| [scripts/](../scripts/) | 반복 시험, 결과 정리, 실행·배포 작업을 돕는 스크립트 |
| [tests/](../tests/) | 프로그램이 예상대로 동작하는지 확인하는 자동 테스트 |
| [infra/](../infra/) | AWS 서버와 관련 서비스를 구성하는 코드 |
| [docs/](../docs/) | 구조·배포·도우미 기능에 대한 상세 설명 |

## 목적에 따라 이 파일부터 보세요

- **“무슨 앱인지 알고 싶다”** → [쉬운 설명](README.md), [한국어 원본 안내](../README.ko.md).
- **“비교 결과가 궁금하다”** → [비교 CSV](../research/vehicle-model-comparison.csv), [평가 요약 JSON](../research/vehicle-benchmark-summary.json). CSV는 표 형태, JSON은 프로그램이 읽기 좋은 데이터 형태입니다.
- **“어떤 문장으로 시험했나?”** → [평가 문장과 정답 정의](../scripts/vehicle-benchmark-cases.mjs).
- **“더 어려운 문제는?”** → [별도 고난도 48문제와 해설](HARD_BENCHMARK.md), [평가 입력·정답 JSON](../research/vehicle-hard-v1/cases.json). 신규 세트이며 모델 평가·음성 생성은 아직 미실행.
- **“정확히 어떤 모델을 쓰나?”** → [서버별 모델 ID·크기·정밀도](MODELS.md).
- **“새 STT·TTS와 최신 모델 후보는?”** → [Qwen3-ASR·Kokoro·MiniCPM 최신 계열 검토](MODEL_CANDIDATES.md), [후보 메타데이터](../research/model-candidate-review.json).
- **“잡음 제거와 Kokoro를 직접 시험한 결과는?”** → [잡음 제거 설계·실험](AUDIO_FRONTEND.md), [Kokoro 한국어 진단](KOKORO_KOREAN_TEST.md), [오디오 A/B 청취 페이지](audio-lab.html).
- **“다른 한국어 TTS 3종 비교는?”** → [Supertonic·Qwen 1.7B·CosyVoice 실행 결과](TTS_COMPARISON.md), [24개 생성 음성 듣기](tts-comparison.html).
- **“코드가 어떻게 연결되나?”** → [한국어 아키텍처 설명](ARCHITECTURE.md), [AWS 아키텍처 그림](architecture.html), [기존 영문 상세 구조](../docs/ARCHITECTURE.md).
- **“직접 실행하고 싶다”** → [배포 안내](../docs/DEPLOYMENT.md).
- **“가져다 써도 되나?”** → [앱 라이선스](../LICENSE), [모델별 주의사항](../NOTICE).
