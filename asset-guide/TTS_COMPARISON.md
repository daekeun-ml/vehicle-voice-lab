# 한국어 TTS 3종 실행 비교

[24개 생성 음성 직접 비교](tts-comparison.html) · [결과 JSON](../research/tts-comparison/summary.json) · [시험 문장](../research/tts-comparison/cases.json)

**Supertonic 3, Qwen3-TTS 1.7B CustomVoice, CosyVoice 3를 모두 실행했습니다.** 같은 한국어 차량 안내 8문장으로 모델별 1회 생성했고, Whisper로 재인식했습니다. 앱의 기본 TTS는 변경하지 않았습니다.

## 이번 결과

| 모델 | 재인식 완전 일치¹ | 숫자 순서 일치² | 전체 문장 생성 중앙값³ | 실행 |
| --- | --- | --- | --- | --- |
| Supertonic 3 | **6/8** | 2/4 | **0.59초** | CPU, ONNX 4 threads |
| Qwen3-TTS 1.7B | **7/8** | 4/4 | **4.21초** | GPU, BF16, SDPA |
| CosyVoice 3 | **5/8** | 4/4 | **1.46초** | GPU, fp16 설정 |

¹ 공백·문장부호와 명시한 한글 숫자 표기를 정규화한 **ASR 대리 지표**입니다. 사람이 들은 자연스러움·MOS·실제 발음 정확도 점수가 아닙니다. 8문장 1회씩의 소규모 실험이므로 모델 전체 성능 순위로 일반화하지 않습니다.

² 숫자가 들어간 네 문장의 숫자 순서만 검사합니다. 숫자가 맞아도 좌석·동작·부정이 틀릴 수 있습니다. 소수점은 보존합니다.

³ 모델 로딩과 워밍업 이후 **문장 전체가 만들어질 때까지**의 시간입니다. 첫 스트리밍 음성 지연이 아닙니다. CPU/GPU·목소리·출력 길이가 달라 절대 성능 비교가 아닙니다. CosyVoice의 0.08초 생성 실패는 속도 중앙값에서 제외하고, 일치도 분모 8에는 포함했습니다.

## 어떤 차이가 있었나요?

**Supertonic 3:** CPU에서 8개 모두 생성했고 가벼운 실행 후보로 유망했습니다. 다만 “풍량 9단”이 “풍량 구호단”, “3단이에요”가 “센 단위예요”로 재인식된 사례가 있었습니다. 숫자 표기 정규화와 반복 시험이 필요합니다.

**Qwen3-TTS 1.7B:** 숫자·소수·부정·좌석 구분을 포함한 7문장이 정규화 후 완전히 일치했습니다. 남은 한 문장은 “바람 **세기**”가 “바람 **새기**”로 재인식된 표기 차이입니다. 이 차이를 TTS의 확정적인 발음 오류로 단정하지 않습니다. 이번 비스트리밍 SDPA 설정에서는 생성 시간이 길었습니다.

**CosyVoice 3:** 긴 차량 안내와 숫자는 대체로 재인식됐지만 **“안녕하세요.”가 0.08초로 끝나는 실패**가 있었습니다. 100ms 미만이라 해당 산출물의 재인식은 생략하고 실패로 남겼습니다. “풍량 → 폭량”, “세기 → 새기” 차이도 있었습니다. 이 결과는 아래의 합성 참조 음성을 사용한 설정의 결과입니다.

세 모델의 재인식 결과는 [청취 페이지](tts-comparison.html)에 원문과 함께 표시했습니다. 음량을 따로 정규화하지 않은 모델 출력 WAV이므로 청취 시 음량 차이와 발음 차이를 구분하세요. 자동 재인식 검사만 수행했으며 사람의 청취 평가는 아직 완료하지 않았습니다.

## 실행 설정

| 항목 | Supertonic 3 | Qwen3-TTS 1.7B | CosyVoice 3 |
| --- | --- | --- | --- |
| 모델 ID | `Supertone/supertonic-3` | `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` | `FunAudioLLM/Fun-CosyVoice3-0.5B-2512` |
| 목소리 | 고정 preset `F1` | 한국어 `Sohee` | Qwen Sohee로 만든 별도 합성 참조 |
| 언어·경로 | `lang=ko`, steps 8, speed 1.05 | `language=Korean`, `non_streaming_mode=True` | zero-shot, `stream=False`, `text_frontend=False` |
| 실행 환경 | ONNX Runtime CPU, intra-op 4 / inter-op 1 | PyTorch GPU, BF16, SDPA | PyTorch GPU, fp16 옵션, TRT/vLLM 미사용 |
| 출력 | 44.1kHz WAV | 24kHz WAV | 24kHz WAV |
| 라이선스 | 모델 OpenRAIL-M | Apache-2.0 | Apache-2.0 |

GPU는 **NVIDIA RTX PRO 4500 Blackwell Server Edition 32GB**입니다. 기존 가이드의 L40S 배포 서버 성능으로 표시하지 않습니다. GPU 모델 생성은 순서대로 수행했습니다.

Supertonic 프로세스의 누적 peak RSS는 약 509MiB였습니다. Qwen과 CosyVoice의 PyTorch CUDA 할당 peak는 각각 약 4,239MiB·4,369MiB였습니다. RSS와 CUDA 할당량은 다른 지표이며, 특히 CosyVoice의 CUDA 수치는 ONNX Runtime·드라이버의 전체 GPU 점유를 포함하지 않습니다.

## CosyVoice 참조 음성과 호환성

실제 사람의 목소리 대신 Qwen3-TTS Sohee로 아래 문장을 별도 합성했습니다. 시험 문장 8개와는 다른 내용입니다.

> 안녕하세요. 차량의 설정과 안내를 도와드릴게요. 편하게 말씀해 주세요.

Whisper 재인식으로 참조 문장의 내용도 확인했습니다. 참조 음성의 목소리·길이가 CosyVoice 결과에 영향을 줄 수 있으며, 특히 짧은 입력이 참조보다 짧다는 경고가 발생했습니다. 따라서 이 시험은 목소리를 통제한 보편적 순위가 아닙니다.

CosyVoice의 중국어·영어 중심 외부 텍스트 정규화를 한국어에 그대로 적용하지 않도록 `text_frontend=False`로 실행했습니다. 숫자를 임의로 한글로 바꿔서 유리한 입력을 주지는 않았습니다. 모든 모델은 같은 원문을 받았습니다.

Blackwell 지원을 위해 CosyVoice 환경에서 PyTorch/torchaudio 2.8.0 + CUDA 12.8을 사용했습니다. upstream의 오래된 전체 requirements를 그대로 실행한 환경은 아닙니다. 소스·하위 모듈 커밋과 실제 패키지는 [CosyVoice 실행 기록](../research/tts-comparison/cosyvoice3.json)과 [환경 목록](../research/tts-comparison/environments/cosyvoice3.txt)에 남겼습니다.

## 현재 추천

- **발음 확인을 우선하는 다음 후보:** Qwen3-TTS 1.7B. 현재 Qwen 0.6B·Polly와 같은 문장으로 더 넓게 비교할 가치가 있습니다.
- **GPU 메모리 부담을 줄이는 후보:** Supertonic 3. 숫자·단위 정규화와 짧은 안내의 반복 안정성을 추가 확인합니다.
- **추가 조정 후 재평가:** CosyVoice 3. 참조 길이·짧은 발화 설정의 영향부터 분리합니다.

기존 0.6B·Polly는 이번 실행에서 재측정하지 않았으므로, 이번 수치만으로 기존 기본 모델보다 낫다고 결론 내리지 않습니다. 이 실험 뒤 Qwen 1.7B·Supertonic은 서울 공유 데모의 선택지로 연동·검증했습니다. 기본 TTS는 Polly를 유지하고 CosyVoice는 실험 후보로 남깁니다. [배포 검증과 실습](HANDS_ON.md)을 참고하세요.

## 파일과 재현 방법

- [Supertonic 생성 코드](../scripts/tts-supertonic-probe.py), [Qwen 생성 코드](../scripts/tts-qwen-probe.py), [CosyVoice 생성 코드](../scripts/tts-cosyvoice-probe.py).
- [공통 기록 함수](../scripts/tts_comparison_common.py), [동일 Whisper 재인식 코드](../scripts/tts-comparison-asr.py), [청취 페이지 생성 코드](../scripts/render-tts-comparison.py).
- [고정 모델 리비전·파일 목록](../research/tts-comparison/model-assets.json), [모델별 패키지 목록](../research/tts-comparison/environments/).

각 모델에 맞는 독립 Python 환경과 고정 모델 snapshot, 기록된 CosyVoice 소스·하위 모듈을 준비한 뒤:

```bash
# 각각 해당 모델의 Python 환경에서 실행
python scripts/tts-supertonic-probe.py --model-dir /path/to/supertonic
python scripts/tts-qwen-probe.py --model-dir /path/to/qwen
# Qwen 실행에서 만들어진 합성 참조 음성이 필요
python scripts/tts-cosyvoice-probe.py \
  --model-dir /path/to/cosyvoice-model \
  --source-dir /path/to/CosyVoice

# Whisper·PyTorch·SciPy 환경에서 실행
python scripts/tts-comparison-asr.py
python scripts/render-tts-comparison.py
```
