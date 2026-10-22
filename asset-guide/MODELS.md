# 실제 연결된 AI 모델과 GPU 사양

[시작 안내](README.md) · [아키텍처](ARCHITECTURE.md) · [배포 그림](diagrams/deployment-ko.png)

새 후보는 [Qwen3-ASR 0.6B·1.7B, Kokoro-82M 및 최신 MiniCPM 계열 검토](MODEL_CANDIDATES.md)에 정리했습니다. Qwen 1.7B·Supertonic 3는 공유 데모에 연동했고, Qwen3-ASR 0.6B·1.7B도 GPU2에 연동했습니다. Kokoro를 제거하고 Ppaso-TTS 한국어 ONNX CPU 경로로 교체했습니다. CosyVoice 3는 현재 앱 선택지에 추가하지 않았습니다. Kokoro는 별도 [한국어 실행 진단](KOKORO_KOREAN_TEST.md)을 수행했으며, Qwen3-ASR의 동일 입력 비교는 [STT 비교](STT_COMPARISON.md)에 정리합니다.

Supertonic 3·Qwen3-TTS 1.7B·CosyVoice 3는 [별도 8문장 실행 비교](TTS_COMPARISON.md)를 완료했습니다. 이후 Qwen 1.7B·Supertonic을 앱 선택지로 추가했습니다. Polly 기본값은 유지합니다.

**기본 단계형 요청: Whisper large-v3-turbo → Qwen3.5-4B NF4 → 서버 검증·실행 → Polly Seoyeon.**

이 문서의 “기본”은 카탈로그·UI·서버의 기본 선택 설정입니다. 현재 GPU에 무엇이 올라와 있는지 실시간 조회한 목록이 아닙니다. 아래 모델 크기는 저장소 카탈로그의 기록이며 제품명에 붙은 숫자와 전체 파라미터 수를 구분합니다.

## 하드웨어와 AI 모델을 구분하기

| 항목 | GPU 1 | GPU 2 |
| --- | --- | --- |
| EC2 인스턴스 유형 | `g6e.2xlarge` | `g6e.2xlarge` |
| GPU 제품명 | NVIDIA L40S × 1 | NVIDIA L40S × 1 |
| GPU 메모리 | 48GB | 48GB |
| CPU / 시스템 RAM | 8 vCPU / 64GiB | 8 vCPU / 64GiB |
| 프로비저닝 EBS | gp3 150GiB | gp3 250GiB |
| 역할 | Node·STT·판단 모델·TTS·MiniCPM | 추가 음성 모델 중 하나 선택 |

서로 다른 서버의 GPU 메모리를 하나의 96GB 공간으로 묶는 구성은 아닙니다. 사양 근거: [AWS G6e](https://aws.amazon.com/ec2/instance-types/g6e/), [기본 서버 프로비저닝](../infra/provision.py), [음성 서버 프로비저닝](../infra/provision_speech.py).

## 어떤 모델이 함께 상주하나요?

GPU 1의 Core 워커는 **판단 모델 1개를 적재하고 Nemotron ASR은 필요할 때 적재**합니다. Whisper·Qwen TTS 0.6B·Qwen TTS 1.7B·MiniCPM은 별도 GPU 워커이며, 활성화되어 로딩에 성공하면 같은 L40S의 VRAM을 함께 점유합니다. 판단 모델을 Qwen에서 Gemma로 바꿔도 큰 판단 모델의 공간이 부족하면 사용하지 않는 Nemotron을 해제합니다. 다른 TTS·MiniCPM 워커는 유지합니다.

GPU 2는 추가 음성 모델 중 **하나만** 실행합니다. 모델을 바꾸면 이전 프로세스를 종료하고 새 프로세스를 실행합니다.

기본 요청에서 사용하는 것은 Whisper와 선택한 판단 모델이며, 음성 응답은 기본적으로 외부 Polly입니다. 이때 사용하지 않는 활성 워커도 GPU 메모리에 남아 있을 수 있습니다. **동시 상주와 한 요청의 호출 경로는 별개**입니다. [워커별 표와 그림](README.md#gpu에-올라간-모델과-요청에서-쓰는-모델은-다릅니다)을 참고하세요.

Supertonic 3는 GPU 1 호스트의 CPU에서 별도 실행하며 GPU VRAM을 쓰지 않습니다. 모델 ID는 `Supertone/supertonic-3`, 목소리는 `F1`, 샘플레이트는 44.1kHz입니다.

## GPU 1: 음성 인식·합성·직접 음성 판단

| 역할 | 정확한 모델 ID | 크기 | 실행 정밀도 | 기본/선택 |
| --- | --- | --- | --- | --- |
| STT | `openai/whisper-large-v3-turbo` | 카탈로그에 수치 없음 | FP16 | 기본 |
| STT | `nvidia/nemotron-3.5-asr-streaming-0.6b` | 제품명 0.6B | FP32 | 대체 |
| TTS | `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice` | 제품명 0.6B | BF16 | Polly 대신 선택; `TTS_MODEL`로 변경 가능 |
| 추가 TTS | `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` | 제품명 1.7B / Hub 전체 약 1.92B | BF16 | 신규 앱 선택지 |
| 직접 음성 판단 | `openbmb/MiniCPM-o-4_5` | 전체 약 9.37B | BF16 | MiniCPM 제어/음성 비교 경로 |

Whisper는 Transformers의 `AutoModelForSpeechSeq2Seq`로 직접 로드합니다. OpenAI 관리형 음성 API나 faster-whisper를 호출하는 구성이 아닙니다. Nemotron의 제품명에 streaming이 들어가지만 이 앱의 해당 경로는 발화 단위 업로드로 처리합니다.

## GPU 1: 선택 가능한 텍스트 판단 모델

| 앱 선택 ID | 정확한 모델 ID | 카탈로그 크기 | 정밀도 |
| --- | --- | --- | --- |
| `qwen35-4b` | `Qwen/Qwen3.5-4B` | 4.66B total | BF16 |
| `qwen35-4b-nf4` | `Qwen/Qwen3.5-4B` | 4.66B total | **4bit NF4 · BF16 연산 (앱 기본)** |
| `qwen35-2b` | `Qwen/Qwen3.5-2B` | 2.27B total | BF16 |
| `qwen35-08b` | `Qwen/Qwen3.5-0.8B` | 0.87B total | BF16 |
| `gemma4-e2b` | `google/gemma-4-E2B-it` | 2.3B effective / 5.12B total | BF16 |
| `phi4-mini` | `microsoft/Phi-4-mini-instruct` | 3.84B total | BF16 |
| `hyperclova-05b` | `naver-hyperclovax/HyperCLOVAX-SEED-Text-Instruct-0.5B` | 0.57B total | BF16 |
| `exaone4-12b` | `LGAI-EXAONE/EXAONE-4.0-1.2B` | 1.28B total | BF16 |
| `smollm3` | `HuggingFaceTB/SmolLM3-3B` | 3.08B total | BF16 |

`Qwen/Qwen3.5-4B`의 BF16와 NF4는 동일 체크포인트의 두 로딩 설정입니다. NF4는 선택한 선형 계층에 적용하며 double quantization과 BF16 연산을 사용합니다. STT·TTS까지 모두 4bit로 바뀌는 것은 아닙니다.

**워커 시작 상태와 앱 기본 선택은 다릅니다.** `runtime/model_server.py`는 시작할 때 Qwen3.5-4B BF16을 먼저 로드합니다. 카탈로그 기본값 `qwen35-4b-nf4`로 요청하면 NF4로 교체합니다. 따라서 재시작 직후 GPU 상태를 앱 기본 구성과 동일하다고 단정하면 안 됩니다.

## GPU 2: 추가 음성 모델

| 앱 선택 ID | 정확한 모델 ID | 카탈로그 크기 | 실행 설정 | 차량 제어 |
| --- | --- | --- | --- | --- |
| `qwen3-omni` | `Qwen/Qwen3-Omni-30B-A3B-Instruct` | 35.26B total / A3B 표기 | Thinker 선형 계층 NF4 + 오디오 등 BF16 | 직접 음성 → 명령 JSON → 공통 실행기 |
| `step-audio2-mini` | `stepfun-ai/Step-Audio-2-mini` | 8.32B total | BF16¹ | 직접 음성 → 명령 JSON → 공통 실행기 |
| `mimo-audio` | `XiaomiMiMo/MiMo-Audio-7B-Instruct` | 7B 표기 + 별도 오디오 토크나이저 | BF16¹ | 직접 음성 → 명령 JSON → 공통 실행기 |
| `moshi` | `kyutai/moshiko-pytorch-bf16` | 7.69B total | BF16 | 없음 · 네이티브 음성 비교만 |

¹ Step-Audio·MiMo는 워커 상태에 BF16로 표시하며 외부 어댑터가 실제 모델을 로드합니다. 구성 요소 전체의 dtype를 이번에 실측한 것은 아닙니다. Qwen3-Omni는 `talker`, `code2wav`, `audio_tower`, `visual`을 NF4 대상에서 제외합니다.

MiMo는 별도 `XiaomiMiMo/MiMo-Audio-Tokenizer`도 사용합니다. Moshi는 저장소에 함께 있는 Mimi 코덱 체크포인트를 로드합니다. `runtime/speech_manager.py`는 모델을 바꿀 때 기존 프로세스를 종료하고 새 프로세스를 실행하므로 이 네 모델이 동시에 상주하지 않습니다.

## 자체 GPU 밖에서 호출하는 서비스

| 역할 | 정확한 식별자·설정 | 기본 리전 |
| --- | --- | --- |
| 기본 한국어 TTS | Amazon Polly · `VoiceId=Seoyeon`, `Engine=neural`, `LanguageCode=ko-KR`, PCM 16kHz | `ap-northeast-2` |
| 실시간 음성 | Nova 2.5 Sonic · Bedrock 모델 ID `amazon.nova-2-5-sonic` | `ap-northeast-1` |

Polly의 `Seoyeon`은 목소리 ID이며 다운로드 가능한 모델 저장소 ID가 아닙니다. Sonic의 파라미터 수·정밀도는 이 에셋에서 지정하지 않습니다. `SONIC_MODEL`, `SONIC_REGION` 환경 변수로 대상이 바뀔 수 있습니다. Sonic 응답은 자체 음성을 사용하며 Polly를 거치지 않습니다.

## 목록에는 있지만 현재 연결 대상이 아닌 후보

카탈로그의 전체 목록을 실제 실행 모델 목록으로 읽으면 안 됩니다.

| 정확한 모델 ID | 카탈로그 상태 |
| --- | --- |
| `naver-hyperclovax/HyperCLOVAX-SEED-Text-Instruct-1.5B` | `access-needed` |
| `nvidia/personaplex-7b-v1` | `access-needed` |
| `THUDM/glm-4-voice-9b` | `license-review` |

## 체크포인트 리비전과 코드 근거

다음은 저장소가 고정한 리비전입니다. 같은 Qwen3.5-4B의 정밀도 변형은 하나로 표시합니다. `ready`는 카탈로그의 연결 상태이며 현재 서버의 건강 상태를 뜻하지 않습니다.

| 모델 ID | 고정 리비전 |
| --- | --- |
| `openai/whisper-large-v3-turbo` | `41f01f3fe87f28c78e2fbf8b568835947dd65ed9` |
| `Qwen/Qwen3.5-4B` | `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a` |
| `Qwen/Qwen3.5-2B` | `15852e8c16360a2fea060d615a32b45270f8a8fc` |
| `Qwen/Qwen3.5-0.8B` | `2fc06364715b967f1860aea9cf38778875588b17` |
| `google/gemma-4-E2B-it` | `3e22461f65e89153144f8adb70e3b8c2cc9845a7` |
| `microsoft/Phi-4-mini-instruct` | `cfbefacb99257ffa30c83adab238a50856ac3083` |
| `naver-hyperclovax/HyperCLOVAX-SEED-Text-Instruct-0.5B` | `3da5046fb0195d14f2497de198136987d35fd644` |
| `LGAI-EXAONE/EXAONE-4.0-1.2B` | `3abf2810673c7c0778df64a73c2d52eab32d91c4` |
| `HuggingFaceTB/SmolLM3-3B` | `a07cc9a04f16550a088caea529712d1d335b0ac1` |
| `Qwen/Qwen3-Omni-30B-A3B-Instruct` | `26291f793822fb6be9555850f06dfe95f2d7e695` |
| `openbmb/MiniCPM-o-4_5` | `503e754207c94da6bb26850b4469f367c9ea3582` |
| `stepfun-ai/Step-Audio-2-mini` | `e36fdd5d71e0ea22f09dd94bbab9bfc544ca1e36` |
| `XiaomiMiMo/MiMo-Audio-7B-Instruct` | `c359441c22c2a1c74be5f99a91e83392680e9cc8` |
| `kyutai/moshiko-pytorch-bf16` | `2bfc9ae6e89079a5cc7ed2a68436010d91a3d289` |
| `XiaomiMiMo/MiMo-Audio-Tokenizer` | `5df9914f72d3acda1320d7fecde7d91622edb0c1` |

Nemotron과 Qwen TTS의 로더에는 명시적인 `revision` 인자가 없습니다. 설치·캐시 시점에 따라 받아오는 버전이 달라질 수 있습니다.

- 앱 기본값·모델 크기: [model-catalog.json](../model-catalog.json), [public/catalog.js](../public/catalog.js).
- STT: [runtime/whisper_server.py](../runtime/whisper_server.py), [runtime/model_server.py](../runtime/model_server.py).
- 판단 모델·NF4·Qwen TTS: [runtime/model_server.py](../runtime/model_server.py).
- MiniCPM: [runtime/minicpm_server.py](../runtime/minicpm_server.py).
- 추가 음성 모델·코덱: [runtime/speech_worker.py](../runtime/speech_worker.py), [runtime/speech_manager.py](../runtime/speech_manager.py).
- Polly·Sonic 실제 호출: [server.mjs](../server.mjs), [sonic.mjs](../sonic.mjs). 카탈로그 설명이 호출 코드와 다르면 실행 경로는 이 코드로 확인합니다.
