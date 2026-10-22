> **보관된 과거 실험입니다.** 사용자 요청으로 Kokoro의 UI·API·실행 서비스를 제거하고 Ppaso-TTS로 교체했습니다. 아래 음성과 수치는 과거 진단 기록이며 현재 선택할 수 없습니다.

# Kokoro-82M 한국어 실행 진단

[생성 음성 직접 듣기](audio-lab.html#kokoro) · [실행 기록](../research/kokoro-korean/probe.json) · [재인식 결과](../research/kokoro-korean/asr-diagnostic.json)

**한국어 음소를 직접 넣으면 오디오를 만들 수는 있었습니다. 하지만 이번 차량 안내 문장에서는 정확한 한국어 낭독을 확인하지 못했습니다.** 공식 한국어 언어 모드와 우회 합성은 구분해야 합니다.

## 시험한 것

- 모델: `hexgrad/Kokoro-82M`, `kokoro-v1_0.pth`.
- 고정 리비전: `f3ff3571791e39611d31c381e3a41a3af07b4987`.
- 패키지: `kokoro==0.9.4`, `misaki==0.9.4`.
- 공식 모드: `KPipeline(lang_code='ko')`, `'k'` 둘 다 지원 코드 검사에서 `AssertionError`.
- 우회 방식 A: eSpeak의 한국어 G2P → Kokoro `generate_from_tokens()`.
- 우회 방식 B: A의 음소 중 `dʑ→ʥ`, `tɕ→ʨ`, `ɫ→l`을 명시적으로 변환한 뒤 같은 합성 함수 호출.
- 목소리: 영어 `af_heart`, 일본어 `jf_alpha`. 한국어 목소리를 새로 학습한 것은 아님.
- 4문장 × 2방식 × 2목소리 = **16개 한국어 시도**, 별도 영어 확인용 1개. WAV 24kHz.
- 실행 GPU: RTX PRO 4500 Blackwell Server Edition. 기존 L40S 배포 인스턴스 결과가 아님.

시험 문장:

1. 안녕하세요.
2. 조수석 온도를 스물네 도로 맞췄어요.
3. 에어컨을 끄지 않았어요.
4. 운전석만 낮추고 조수석은 그대로 뒀어요.

## 관찰

16개 모두 오디오 파일이 생성됐습니다. `Whisper large-v3-turbo`로 재인식했을 때 영어 목소리의 인사말 두 시도는 원문과 일치했지만, 차량 안내 세 문장은 어느 조합도 정규화 후 원문 전체와 일치하지 않았습니다.

| 원문 | 음소 변환 B + 영어 목소리의 재인식 예 |
| --- | --- |
| 안녕하세요. | 안녕하세요. |
| 조수석 온도를 스물네 도로 맞췄어요. | 저 수석, 언더를 심은 내 도로 맥주와서야. |
| 에어컨을 끄지 않았어요. | 에어큰일 쿠지 안이사요. |
| 운전석만 낮추고 조수석은 그대로 뒀어요. | 은젠사님의 나이 추구가 조수석은 그대로 두세여. |

영어 확인용 문장 “The passenger temperature is now twenty four degrees.”는 “The passenger temperature is now 24 degrees.”로 재인식됐습니다. 즉 모델이 전혀 실행되지 않은 실패와는 다릅니다.

이 결과는 **ASR 진단**이며 사람이 직접 청취해 판정한 MOS·자연스러움 점수가 아닙니다. 음소 변환·비한국어 목소리·재인식기의 오류가 섞일 수 있습니다. 한 조건은 ASR이 문구를 길게 반복해 CER가 100%를 넘었습니다. 이 숫자를 일반 한국어 품질 점수로 사용하지 않습니다.

## 판단

- “Kokoro로 한국어 입력에서 음성이 만들어지는가?” → **음소 우회 입력으로 생성 가능**.
- “공식 한국어 모드가 제공되는가?” → **시험한 0.9.4 패키지에서는 ko/k를 거부**.
- “현재 한국어 차량 안내에 바로 써도 되는가?” → **이번 실험으로는 채택 근거가 부족**. Polly Seoyeon·기존 Qwen TTS 대체로 연결하지 않았습니다.
- 다른 한국어 G2P·한국어 학습 가중치·커뮤니티 포크가 같은 결과라고 단정하지 않습니다. 이번 대상은 사용자가 지정한 원본 `hexgrad/Kokoro-82M`입니다.

## 재현

[시험 코드](../scripts/kokoro-korean-probe.py)는 모델·목소리 파일을 같은 리비전으로 고정합니다. Python 3.12 환경과 기록된 라이브러리, 한국어 G2P를 제공하는 eSpeak를 사용했습니다.

```bash
python scripts/kokoro-korean-probe.py
# 잡음 시험 산출물도 준비한 뒤 공통 ASR 진단·청취 페이지 생성
python scripts/audio-probe-asr.py
python scripts/render-audio-probes.py
```

기본 TTS 설정이나 실시간 데모 경로는 변경하지 않았습니다.

## 공유 배포의 실제 출력

- [한국어 음소 실험 음성](../research/kokoro-korean/live-ko.wav): 합성 1.60초, 음성 길이 3.33초
- [영어 대조 음성](../research/kokoro-korean/live-en.wav): 합성 1.46초, 음성 길이 3.55초

공유 CPU의 단건 측정이며 품질 평가나 지연 보장값이 아닙니다. [모델 ID·revision·상태 무변경 검증](../research/kokoro-korean/live-validation.json)을 보존했습니다.
