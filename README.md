# On · Vehicle Voice Lab

A voice-controlled vehicle simulator for comparing self-hosted speech models, small language models, and Amazon Nova 2.5 Sonic. Includes a **Korean / English UI**, shared Korean audio evaluations, and an EC2 + CloudFront reference deployment.

[한국어 안내](README.ko.md) · [Deployment](docs/DEPLOYMENT.md) · [Architecture & tools](docs/ARCHITECTURE.md) · [Model catalog](model-catalog.json) · [License notices](NOTICE)

## What it does

Speak, type, or upload an audio file to change the simulated driver/passenger temperature, climate controls, seat heating, media state, or navigation destination. Follow-up corrections and undo use the conversation and current vehicle state. The server validates commands before applying them.

**This is a functional state simulator, not a connection to a real car.** It does not simulate cabin thermodynamics, physical sensors, CAN traffic, real music playback, or map routing.

- Self-hosted path: Whisper or Nemotron ASR → selected sLLM → validated vehicle executor → Polly or Qwen TTS.
- Audio-model path: selected audio model → validated vehicle executor → selected Korean TTS; native voice-only comparisons are explicitly separate.
- Sonic path: Bedrock bidirectional speech → `vehicle_control` tool → shared executor → Sonic native audio.
- Per-visitor vehicle state and conversation, response interruption, feedback, session export, model comparison tables, and synthetic reply samples.
- **UI language selector** in the header. `/?lang=en` opens English; `/?lang=ko` opens Korean. Selection persists in the browser. UI language does not change speech language, model behavior, evaluation data, or conversation text.

![English interface](docs/screenshots/english-ui.png)

## Run locally

Requires Node.js 22.9+ and npm. The UI and published evaluation tables can be viewed without a GPU; live inference needs reachable workers or Bedrock credentials for Sonic.

```bash
git clone https://github.com/jinuland/vehicle-voice-lab.git
cd vehicle-voice-lab
npm ci
cp .env.example .env
# Edit .env: AWS profile and worker URLs for your deployment.
npm start
```

Open [localhost:8787](http://localhost:8787) or [English UI](http://localhost:8787/?lang=en). Use **Korean audio sample** to test without microphone permissions. Microphone input requires localhost or HTTPS and browser/OS permission.

Workers are not bundled with the Node application. Follow [the GPU and CloudFront deployment guide](docs/DEPLOYMENT.md) to provision your own infrastructure. The repository contains no AWS keys, SSH keys, private infrastructure state, model weights, or user microphone recordings. AWS and model downloads require your own access and applicable licenses.

## Current deployment: direct EC2 GPU serving

The reference deployment uses **two EC2 `g6e.2xlarge` instances in Seoul**, each with an NVIDIA L40S 48 GB GPU. It currently uses EC2, not SageMaker.

| Component | Current placement |
| --- | --- |
| Core speech/planner services | GPU 1: Whisper, Nemotron ASR, swappable planners, Qwen TTS, MiniCPM |
| Additional audio models | GPU 2: Qwen3-Omni, Step-Audio, MiMo, or Moshi; selected model loaded on demand |
| UI, sessions, command validation, tool execution | Node backend on the core EC2 instance; CloudFront HTTPS via a private VPC origin |
| Default response voice | Amazon Polly Seoyeon, Seoul |
| Nova 2.5 Sonic | Amazon Bedrock, Tokyo; Korean remains an unsupported-language experiment in this evaluation |

Visitors have separate application state but share GPU capacity and model residency. Switching between different models can introduce queueing and cold loading. The reference deployment runs independently of a developer laptop. Account-specific addresses and deployment state are deliberately excluded from Git.

## What would improve with SageMaker?

**SageMaker would still run the models on GPU infrastructure. Its main benefit is managed serving and operations.** The current custom model servers can be adapted into SageMaker inference containers; moving them is not a prerequisite for tool calling or MCP.

| Area | Current EC2 reference | Benefit available with a configured SageMaker deployment |
| --- | --- | --- |
| Concurrent users | Shared workers and model switching; capacity is managed manually | Configure replica counts and autoscaling policies for selected models as load grows |
| Model updates | Upload code and restart the corresponding service | Blue/green or canary traffic shifting, with alarm-based rollback for supported endpoint configurations |
| Health and recovery | systemd restarts failed processes; instance recovery is an operational responsibility | Managed hosting health checks and replacement behavior for supported endpoint types |
| Monitoring | Application timing records and service logs | Endpoint metrics in CloudWatch, alarms, and scaling policies |
| Model resource allocation | Hand-managed placement across two GPUs | Inference components can specify model CPU, memory, and accelerator requirements and manage replicas |
| Repeatable deployment | Pinned model revisions and install scripts | Versioned containers/model artifacts and endpoint configurations make releases easier to reproduce |

For this lab, a useful next experiment is to **keep the main Whisper + Qwen4B path resident in a dedicated SageMaker configuration**, while retaining EC2 for rapidly changing research candidates. Allocate enough memory and serving capacity so a Gemma experiment does not evict the main Qwen model. Dedicated EC2 workers can also achieve isolation; SageMaker reduces the amount of serving infrastructure we must operate ourselves.

Migration alone does **not** improve Korean understanding, pronunciation, model accuracy, or single-request GPU inference speed. Cost is workload-dependent: compare steady GPU usage, minimum warm capacity, model loading, and operating effort. Autoscaling new replicas requires startup/loading time and does not make an existing long-lived speech session migrate automatically.

The web UI, sessions, vehicle command executor, and future MCP clients remain in the application backend. The backend would call SageMaker endpoints instead of the current worker URLs. Sonic remains on its existing Bedrock path. SageMaker supports response and bidirectional streaming, but the container and model must implement the appropriate streaming contract; a deployment change does not turn an utterance-based model into full-duplex S2S.

**Status:** this repository implements EC2 + CloudFront deployment. It does not currently contain a production SageMaker migration. GPU type availability, quotas, streaming compatibility, concurrency, and first-audio latency must be verified for the chosen region and endpoint configuration.

AWS references: [custom inference containers](https://docs.aws.amazon.com/sagemaker/latest/dg/your-algorithms-inference-code.html), [autoscaling](https://aws.amazon.com/blogs/machine-learning/configuring-autoscaling-inference-endpoints-in-amazon-sagemaker/), [deployment guardrails](https://docs.aws.amazon.com/sagemaker/latest/dg/deployment-guardrails.html), [inference components](https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_CreateInferenceComponent.html), [bidirectional streaming](https://aws.amazon.com/blogs/machine-learning/introducing-bidirectional-streaming-for-real-time-inference-on-amazon-sagemaker-ai/).

## Evaluation results

The default path is **Whisper large-v3-turbo → Qwen3.5-4B NF4 → vehicle executor → Polly Seoyeon**. The shared evaluation contains 31 synthetic Korean audio cases per control configuration and 10 additional holdout cases for finalists.

| Qwen3.5-4B precision | Application pass rate | Holdout | First audio median / p95 | Planner CUDA allocation |
| --- | --- | --- | --- | --- |
| BF16 | 30/31 · 97/100 | 10/10 | 1.45 s / 2.78 s | 8.46 GiB |
| 4-bit NF4, BF16 compute | 30/31 · 97/100 | 10/10 | 2.04 s / 3.22 s | 3.08 GiB |

These are application-level results including ASR, planning, server validation, complete vehicle state, required replies, and audio output. Raw model actions were correct in 29/31 cases for both precision variants; guards rejected an out-of-range command. The shared benchmark covers 14 control configurations and 434 cases. It is not a speech naturalness MOS, general intelligence score, human microphone test, or road test.

Latency is measured to the first received audio byte, excluding microphone endpointing and browser playback. Model switching/loading is reported separately. Memory numbers are planner-process CUDA allocation, not total GPU use or in-vehicle shared RAM. Edge suitability in the UI is a design estimate; actual vehicle runtime porting and latency remain unmeasured.

See [summary](research/vehicle-benchmark-summary.json), [comparison CSV](research/vehicle-model-comparison.csv), [deployment assumptions](research/deployment-assessment.json), and [configuration audit](research/configuration-audit.json). Older `*-baseline` records preserve earlier conditions and must not be merged into the latest scores.

## Development and verification

```bash
npm test
python3 runtime/test_minicpm_protocol.py
python3 runtime/test_speech_protocol.py
# With a deployed HTTPS backend and synthetic audio:
mkdir -p output
TEST_BASE=https://YOUR_DISTRIBUTION.cloudfront.net node scripts/cloud-deployment-smoke.mjs
TEST_BASE=https://YOUR_DISTRIBUTION.cloudfront.net node scripts/sonic-smoke.mjs
```

Unit and routing tests use local stubs and require no AWS account or GPU. Live smoke tests invoke paid model services and use synthetic samples. `TEST_LONG_SSE=1` adds a Qwen3-Omni model switch and long-stream check. Benchmark generators write to `output/`; run `npm run prepare:samples` to refresh the allowlisted synthetic reply files served by the UI.

## Privacy and licenses

Raw microphone WAVs are not saved to disk. Per-session text and vehicle state live in server memory; submitted feedback persists text, state, and measurements in `.runtime/feedback.jsonl`. Sessions expire after inactivity and are lost on backend restart. The reference shared deployment is a link-access demo with per-session isolation, origin verification, and basic rate limiting; it is not an authenticated production service.

Application code is [MIT licensed](LICENSE). Models, optional upstream runtimes, and generated assets retain applicable third-party terms. **The application license does not grant model access or override model licenses.** Some candidates require gated approval or restrict commercial use, including EXAONE's research/evaluation license. Model weights are downloaded separately and are not redistributed. See [NOTICE](NOTICE) and [model-catalog.json](model-catalog.json).
