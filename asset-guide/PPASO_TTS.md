# Ppaso-TTS 한국어 경량 음성 합성

Kokoro를 UI·API·실행 서비스에서 제거하고 **akamotaco/ppaso-tts-v1**로 교체했습니다. [TTS 비교 화면](https://d2ub6bbyf1c3sv.cloudfront.net/#model-lab)에서 **Ppaso-TTS · 한국어 · ONNX CPU**를 선택하세요.

| 항목 | 현재 배포 |
|---|---|
| 모델 | [akamotaco/ppaso-tts-v1](https://huggingface.co/akamotaco/ppaso-tts-v1) |
| 고정 revision | `53d09664c4f636a5fb6f2ebe3ec22cd83ee249b9` |
| 언어·음성 | 한국어 전용, 단일 여성 음성 |
| 실행 | ONNX Runtime CPU, 세션당 intra-op 2 / inter-op 1 스레드 |
| 출력 | 22,050Hz 모노 PCM WAV |
| 모델 파일 | ONNX 4개 모듈과 외부 가중치, 약 39MB(십진 단위), 사전 별도 |
| 호스트 | 서울 GPU1 EC2의 CPU 사용; GPU/NPU 사용 안 함 |
| 서비스·포트 | `vehicle-tts-ppaso`, loopback `9108` |
| 라이선스 | Apache-2.0; 모델 폴더에 원본 LICENSE·README 보존 |

한국어 텍스트를 mecab-ko와 발음 사전으로 음소화한 뒤 text encoder → variance → acoustic → vocoder → CPU iSTFT 순서로 합성합니다. 음성 복제나 여러 화자 선택은 지원하지 않습니다. 제작자가 자연스러움보다 속도·크기를 우선했다고 명시하므로 기계적인 음색이 남을 수 있습니다.

## 직접 시험

1. **새 모델 테스트**에서 Ppaso 카드의 **이 모델로 생성**을 누릅니다.
2. 재생·음성 다운로드로 발음을 확인합니다.
3. 온도, 부정 표현, 소수·좌석, 목적지 예제를 각각 시험합니다.
4. **차량 대화에 사용**을 누르면 이후 차량 응답에 Ppaso를 사용합니다.

비교 카드의 단독 합성은 차량 상태를 변경하지 않습니다. 기본 응답 음성은 Polly를 유지합니다. Kokoro를 요청하면 다른 모델로 대체하지 않고 잘못된 선택으로 거부합니다.

## 속도와 품질 해석

모델 카드의 **305ms / RTF 0.052**는 RK3576 NPU 측정값이며 이 EC2 결과가 아닙니다. 여기서는 ONNX CPU로 별도 측정합니다. 모델의 문장 단위 스트리밍 기능과 현재 앱 통합도 구분해야 합니다. **현재 앱은 입력 문장의 합성이 끝난 뒤 WAV를 반환**합니다.

8개 고정 한국어 문장으로 실제 합성하고, 기존 Whisper large-v3-turbo에 재입력해 숫자·좌석·부정 표현을 진단합니다. 재인식 결과는 발음 오류 탐지의 보조 지표이며 사람이 평가한 자연스러움이나 MOS가 아닙니다.

## 설치·재현

코어 호스트 `/opt/vehicle-voice`에 `runtime/tts_worker.py`, `runtime/ppaso_text.py`, `runtime/bootstrap_ppaso.sh`를 배치하고 다음을 실행합니다.

```bash
bash /opt/vehicle-voice/bootstrap_ppaso.sh
```

별도 Python 3.12 `ppaso-env`에 `onnxruntime`, `python-mecab-ko`, `numpy`, `soundfile` 등을 설치합니다. 모델 revision은 워커에서 고정합니다. Hugging Face 캐시의 심볼릭 링크가 ONNX 외부 가중치 경로 검사에 걸리지 않도록, 해당 snapshot을 실제 파일 디렉터리로 복사한 후 로드합니다. 경로 검사는 비활성화하지 않습니다.

웹 서버 환경 변수는 `PPASO_TTS_URL=http://127.0.0.1:9108`입니다. 개발용 SSH 터널은 로컬 `19108`을 사용합니다.

```bash
python3 scripts/probe-ppaso-live.py
```

위 스크립트는 8문장 합성·Whisper 재인식·모델 ID/revision·차량 상태 무변경·Kokoro 선택 거부를 검증하고 `research/tts-comparison/ppaso.json`에 저장합니다.

## 이번 배포 실측

8개 고정 문장의 합성 중앙값은 **64.0ms**입니다. 초기 호출을 포함한 범위는 63~183ms입니다. 네트워크 왕복과 브라우저 재생 대기는 포함하지 않습니다.

Whisper 재인식의 정규화 문장 일치는 **6/8**입니다. 소수점 누락을 확인해 소수·음수 전처리를 보완한 개발 세트 결과이며, 수정 전 원음과 결과는 `ppaso-before-text-fix.json`에 보존합니다. 현재 남은 불일치는 `목적지 → 목적치`, `바람 세기 → 바람 새기`입니다. 모델 발음과 재인식 모델 오류를 분리한 사람 청취 평가는 아직 하지 않았습니다.

| 문장 | 합성 | 음성 길이 | 재인식 일치 |
|---|---:|---:|---|
| [안녕하세요.](../research/tts-comparison/ppaso/greeting.wav) | 183ms | 1.44s | 일치 |
| [조수석 온도를 스물네 도로 맞췄어요.](../research/tts-comparison/ppaso/temperature.wav) | 71ms | 3.23s | 일치 |
| [에어컨을 끄지 않았어요.](../research/tts-comparison/ppaso/negation.wav) | 70ms | 2.23s | 일치 |
| [운전석만 낮추고 조수석은 그대로 뒀어요.](../research/tts-comparison/ppaso/seat-scope.wav) | 64ms | 3.81s | 일치 |
| [운전석은 22.5도, 조수석은 24도로 설정했어요.](../research/tts-comparison/ppaso/decimal.wav) | 64ms | 5.02s | 일치 |
| [풍량 9단은 지원하지 않아요. 설정을 변경하지 않았어요.](../research/tts-comparison/ppaso/rejection.wav) | 63ms | 4.74s | 일치 |
| [목적지를 서울역에서 서울숲으로 바꿨어요.](../research/tts-comparison/ppaso/destination.wav) | 63ms | 3.78s | 불일치 |
| [운전석은 19도, 조수석은 27도, 바람 세기는 3단이에요.](../research/tts-comparison/ppaso/compound.wav) | 63ms | 5.47s | 불일치 |

소수는 `22.5 → 22점오`, 음수는 `-1 → 마이너스 1`로 바꾼 뒤 원본 G2P의 정수 읽기를 적용합니다. 모델 가중치나 평가 정답은 수정하지 않았습니다.
