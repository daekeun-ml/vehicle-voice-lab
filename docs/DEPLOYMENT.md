# Deployment guide

This repository contains the Node UI/backend, GPU worker adapters, deployment scripts, synthetic evaluation records, and reply samples. Model weights and credentials are downloaded/configured separately. The reference installation was tested on Ubuntu NVIDIA DLAMI, Python 3.12, L40S 48 GB, and Node 22. Pinned model revisions and adapter dependencies are in `runtime/` and `model-catalog.json`. Other images/hardware need compatibility verification; provisioning a brand-new account is not covered by the existing live smoke-test results.

## 1. Local UI and existing workers

```bash
npm ci
cp .env.example .env
# Edit AWS_PROFILE and the worker URLs.
npm start
```

The default URLs expect SSH forwards on localhost:

| Variable | Local port | GPU loopback port | Service |
| --- | --- | --- | --- |
| CORE_URL | 19101 | 9101 | Nemotron ASR / planners |
| TTS_URL | 19102 | 9102 | Qwen TTS |
| MINICPM_URL | 19103 | 9103 | Optional MiniCPM |
| SPEECH_URL | 19104 | 9104 | Optional swappable audio models |
| WHISPER_URL | 19105 | 9105 | Whisper |

Set these URLs directly if workers already exist. Load `.env` explicitly before Python provisioning commands; Node's `npm start` reads it automatically. `AWS_CREDENTIAL_MODE=profile` selects `AWS_PROFILE` (default: `default`). `AWS_CREDENTIAL_MODE=instance` uses the AWS SDK default credential chain, including the EC2 role; do not provide developer credentials to a cloud host.

The UI and checked-in results work without GPU workers. Live commands require a ready selected path. Sonic requires Bedrock access and `bedrock:InvokeModel` for the selected `SONIC_MODEL` in `SONIC_REGION`; its UI can be selected even if local GPU workers are unavailable. Polly requires `polly:SynthesizeSpeech` in `AWS_REGION`.

## 2. Provision reference GPUs in your AWS account

Requirements: AWS CLI v2 credentials, EC2/IAM/CloudFront permissions as needed, a GPU quota, SSH, a VPC with a public subnet and internet gateway, and an Ubuntu NVIDIA DLAMI compatible with the bootstrap scripts. Select a current AMI **in your region** with `/opt/pytorch/bin/python`. Review `runtime/bootstrap*.sh` before installing; models download from Hugging Face and optional pinned upstream repositories. Gated models require your own accepted license and token configured on the worker; tokens are not uploaded by the app deployment.

```bash
set -a
. ./.env
set +a
export AWS_VPC_ID=vpc-YOUR_VPC
export AWS_SUBNET_ID=subnet-YOUR_SUBNET
export AWS_AMI_ID=ami-YOUR_GPU_DLAMI
mkdir -p .runtime
chmod 700 .runtime
ssh-keygen -t ed25519 -f .runtime/vehicle-key -N '' -C vehicle-voice-lab
python3 infra/provision.py
python3 infra/provision_speech.py
python3 scripts/gpu.py status
```

Provisioning creates `g6e.2xlarge` instances and encrypted storage, and allows SSH only from the public IP detected at provisioning time. In a new environment, allow boot and cloud-init to finish before installation. Your account must have the instance type available and sufficient quota. Core and speech state are stored in `.runtime/aws.json` and `.runtime/speech-aws.json`. Re-running provisioning with existing state does not create another worker. Public IPs can change after a stop/start; `scripts/gpu.py status` refreshes them. Update the SSH security group when your developer IP changes.

Install workers:

```bash
python3 scripts/bootstrap-workers.py --worker core
# Optional native MiniCPM research path:
# python3 scripts/bootstrap-workers.py --worker core --with-minicpm
python3 scripts/bootstrap-workers.py --worker speech
python3 scripts/gpu.py tunnel
# Keep the tunnels running. In another terminal:
npm start
```

The core bootstrap downloads reviewed planner checkpoints and starts core/TTS/Whisper services. MiniCPM is optional and defaults to disabled until installed. The speech manager loads the selected model on demand; the first request may download large weights. `runtime/cache_speech.py` can prefetch them in the speech environment. Not every candidate in the catalog is deployable without license approval; a catalog score refers to the recorded experiment, not an automatic hardware readiness check on your host.

Fresh instances have a **four-hour auto-stop timer** to limit unattended GPU runtime. For a deliberately persistent shared deployment, disable it on each worker with `sudo systemctl disable --now vehicle-auto-stop.timer` and record that choice in your private state. This incurs continuing GPU charges. Do not expose model ports to the internet.

```bash
python3 scripts/gpu.py status
python3 scripts/gpu.py logs
python3 scripts/gpu.py stop       # Stops both GPUs; also takes down the shared backend
python3 scripts/gpu.py start
```

`GPU중지.command` is a macOS stop shortcut. `시작.command` starts the local environment and browser when private worker state already exists. These are convenience scripts, not prerequisites for cloud operation.

## 3. CloudFront HTTPS sharing

After both workers are installed and healthy:

```bash
python3 infra/deploy_cloudfront.py
```

The script checkpoints created resources in `.runtime/cloud-deployment.json`. It creates dedicated security groups, a least-scoped runtime instance role for Polly and the selected Sonic model, a private CloudFront VPC origin, and a distribution. Re-run after AWS reports the VPC origin ready to create/inspect the distribution; provisioning can take several minutes. The chosen VPC/subnet must satisfy AWS VPC-origin requirements, and CloudFront VPC origins must be available in the region. An unexpected existing instance profile is rejected instead of replaced.

Once the command returns a distribution URL:

```bash
python3 scripts/deploy-web.py
```

The upload contains only allowlisted app files, the public model catalog, summary/CSV, and synthetic audio assets. It installs Node and the `vehicle-web` systemd service on the core GPU host. It also creates a private socket proxy on the speech host, restricted to the backend's security group. Developer AWS keys, SSH keys, `.env`, logs, and private runtime state are excluded.

Cloud configuration uses `PUBLIC_ORIGIN=https://YOUR_DISTRIBUTION.cloudfront.net`, `ORIGIN_HOST` for the private origin hostname, and a random `ORIGIN_VERIFY_SECRET`. CloudFront injects the secret header; the backend validates it. The web port is restricted to the CloudFront VPC service security group after origin deployment. API caching is disabled; SSE sends heartbeats for long loads; Sonic uses WebSockets. The instance role and model ports remain server-side.

For later app updates, run `scripts/deploy-web.py` again. Then invalidate **your own** distribution's static cache:

```bash
aws cloudfront create-invalidation --distribution-id YOUR_DISTRIBUTION_ID --paths '/*'
```

Do not print or commit `.runtime/cloud-deployment.json` or `/etc/vehicle-web.env`: they include the origin verification secret. The reference site is intentionally link-access sharing. Add authentication, per-user authorization, durable state, appropriate limits, and operational monitoring before a production release.

## 4. Verify the deployment

```bash
npm test
python3 runtime/test_minicpm_protocol.py
python3 runtime/test_speech_protocol.py
mkdir -p output
TEST_BASE=https://YOUR_DISTRIBUTION.cloudfront.net node scripts/cloud-deployment-smoke.mjs
TEST_BASE=https://YOUR_DISTRIBUTION.cloudfront.net node scripts/sonic-smoke.mjs
# Optional cold-loading / SSE continuity check:
TEST_BASE=https://YOUR_DISTRIBUTION.cloudfront.net TEST_LONG_SSE=1 node scripts/cloud-deployment-smoke.mjs
```

The cloud smoke checks static assets, model results, synthetic Korean audio control, and session isolation. The Sonic probe tests English and experimental Korean separately. These calls can load models and incur inference charges. Test `?lang=en` and `?lang=ko`, language persistence, state preservation, sample playback, and microphone access manually in the browser.

## 5. SageMaker migration

See [the README comparison](../README.md#what-would-improve-with-sagemaker). A migration requires adapting model workers to SageMaker containers and changing the backend's invocation adapter. Web/session/tool code remains an application service. This repository does not claim to deploy a SageMaker endpoint yet.
