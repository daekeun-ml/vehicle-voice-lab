"""Vehicle Voice Lab: layouts rendered with the aws-diagram-design Canvas."""
from awsdiag import Canvas


def deployment(lang):
    c = Canvas(1280, 720, 'deployment', 'AWS 배포 구성: 화면부터 모델까지',
               '브라우저는 CloudFront를 통해 서울 EC2의 Node 서버에 접속하고, 서버는 선택한 모델과 AWS API를 호출합니다.', lang)
    c.zone(480, 104, 340, 488, '서울 · GPU 1 · g6e.2xlarge', kind='ec2')
    c.zone(920, 288, 320, 304, '도쿄 · 관리형 서비스', kind='region')
    c.node(40, 180, 168, 80, '브라우저', '마이크 · 화면 · 스피커', kind='input')
    c.node(272, 180, 184, 80, 'CloudFront', '공유 HTTPS 진입점', icon='CloudFront')
    c.node(512, 180, 272, 112, 'Node 백엔드', '세션 · 검증 · 가상 차량 상태', kind='focal')
    c.node(512, 432, 272, 80, 'GPU 모델 워커 · VRAM 공유', 'STT · 판단 · Qwen TTS · MiniCPM')
    c.node(512, 336, 272, 64, 'Supertonic / Ppaso', 'CPU · 각각 독립 워커')
    c.node(232, 480, 224, 96, 'EC2 GPU 2', '독립 STT + 음성 워커', icon='EC2')
    c.node(944, 164, 272, 80, 'Amazon Polly', 'Seoyeon · neural · ko-KR', icon='Amazon-Polly', kind='external')
    c.node(944, 340, 272, 80, 'Amazon Bedrock', 'amazon.nova-2-5-sonic', icon='Bedrock', kind='external')
    c.node(944, 480, 272, 80, 'AgentCore Gateway', '선택 확장 · 이번 배포 미구성', icon='Amazon-Bedrock-AgentCore', kind='optional')
    for a,b,y in [(208,272,220),(456,512,220)]:c.path(c.hline(a,y,b),style='link')
    c.label(240,208,'HTTPS');c.label(484,208,'VPC')
    c.path(c.vline(624,292,336));c.label(640,316,'CPU',anchor='start')
    c.path('M 752 292 V 304 Q 752 312 760 312 H 792 Q 800 312 800 320 V 464 Q 800 472 792 472 H 784');c.label(784,416,'GPU',anchor='end')
    c.path(c.L_hv(512,272,344,480),style='link');c.label(360,408,'사설 HTTP',anchor='start')
    c.path(c.hline(784,204,944),style='link');c.label(864,192,'TTS')
    c.path(c.elbow_hvh(784,236,944,380,mid=872),style='link');c.label(888,316,'음성',anchor='start')
    c.path(c.elbow_hvh(784,268,944,520,mid=840),style='link',dashed=True);c.label(856,464,'MCP',anchor='start')
    c.note(40,608,'서버당 NVIDIA L40S × 1 · VRAM 48GB · 8 vCPU · RAM 64GiB',anchor='start',size=16)
    c.note(40,636,'화살표는 요청 방향 · 응답은 같은 연결로 반환 · 전체 모델 ID는 가이드 모델 목록 참조',anchor='start',size=16)
    c.legend([('input','사용자'),('focal','상태 변경 주체'),('step','앱·모델 구성 요소'),('external','관리형 API'),('arrow:link','네트워크 호출'),('arrow','호스트 내부 호출'),('optional','선택 확장')])
    return c


def paths(lang):
    c=Canvas(1280,720,'model-paths','세 가지 AI 경로, 하나의 차량 실행기',
             '단계형, 직접 음성 판단, Sonic은 대안 경로이며 모두 서버의 검증·실행기를 거칩니다.',lang)
    c.node(56,128,360,80,'① 단계형: STT → sLLM','Whisper turbo → Qwen3.5-4B NF4')
    c.node(56,300,360,80,'② 직접 음성 판단','오디오 모델 → 명령 JSON')
    c.node(56,472,360,80,'③ Nova 2.5 Sonic','실시간 음성 → vehicle_control',icon='Bedrock')
    c.node(552,284,256,144,'공통 검증·실행기','검사 성공 → 가상 차량 변경',kind='focal')
    c.node(952,212,280,80,'Polly / Qwen TTS','①·② 실행기 안내 문구를 합성',icon='Amazon-Polly')
    c.node(952,436,280,80,'Sonic 자체 음성','③ 도구 결과를 받아 응답',icon='Bedrock')
    c.path(c.elbow_hvh(416,168,552,316,mid=464))
    c.path(c.hline(416,340,552))
    c.path(c.elbow_hvh(416,512,552,392,mid=488))
    c.path(c.elbow_hvh(808,324,952,252,mid=872))
    c.path(c.elbow_hvh(808,388,952,476,mid=872))
    c.note(56,604,'차량 제어 없는 네이티브 음성 비교 모드는 이 실행기를 호출하지 않습니다.',anchor='start',size=16)
    c.note(56,632,'직접 음성 판단도 제어 후에는 별도 TTS 사용 · 세 경로를 연속 실행하는 구조가 아님',anchor='start',size=16)
    c.legend([('step','선택 가능한 모델·응답 경로'),('focal','서버가 차량 상태 변경'),('arrow','명령 또는 실행 결과')])
    return c


def command(lang):
    c=Canvas(1280,720,'command-sequence','명령 한 번의 처리 순서: 조수석 25도',
             '단계형 경로에서 음성 인식과 명령 판단 후 서버가 상태를 바꾸고, 그 결과를 음성으로 합성합니다.',lang)
    actors=[(40,200,'브라우저','녹음 · 화면 · 재생',None,'input'),
            (320,200,'Node 서버','세션 · 검증 · 실행',None,'focal'),
            (584,184,'Whisper','large-v3-turbo · FP16',None,'step'),
            (816,184,'Qwen3.5-4B','NF4 · BF16 연산',None,'step'),
            (1056,184,'Amazon Polly','Seoyeon · neural','Amazon-Polly','step')]
    for x,w,name,sub,ico,kind in actors:
        c.node(x,48,w,80,name,sub,icon=ico,kind=kind)
        c.lifeline(x+w/2,128,644)
    def msg(a,b,y,label,dashed=False,style='default',lx=None):
        c.path(c.hline(a,y,b),dashed=dashed,style=style)
        c.label(lx if lx is not None else (a+b)/2,y-12,label)
    msg(140,420,168,'① 음성 + 세션 ID')
    msg(420,676,216,'② 음성 인식 요청')
    msg(676,420,264,'인식된 한국어 문장',True)
    msg(420,908,312,'③ 요청 + 상태 + 맥락',lx=780)
    msg(908,420,360,'조수석 25도 명령 JSON',True,lx=780)
    c.path('M 420 392 H 444 Q 452 392 452 400 V 432 Q 452 440 444 440 H 420')
    c.note(472,412,'④ 검증 후 상태 변경',anchor='start',size=16)
    c.note(472,436,'조수석 22 → 25°C',anchor='start')
    msg(420,140,480,'⑤ 변경된 상태 전달',style='accent')
    msg(420,1148,528,'⑥ 성공 안내 문구',lx=1028)
    msg(1148,420,580,'응답 오디오',True,lx=1028)
    msg(420,140,628,'음성 재생',True)
    c.legend([('focal','상태 변경 주체'),('input','사용자 화면'),('step','모델·합성 서비스'),('arrow','요청·처리'),('arrow-dashed','반환'),('arrow:accent','차량 화면 갱신')])
    return c


def build(lang):
    return [('deployment',deployment(lang)),('model-paths',paths(lang)),('command-sequence',command(lang)),('gpu-residency',residency(lang))]


def residency(lang):
    c=Canvas(1280,720,'gpu-residency','GPU 상주와 요청 실행은 서로 다릅니다',
             'GPU 1의 독립 워커들은 같은 GPU 메모리를 공유하고 GPU 2는 STT 2개를 독립 실행하고 직접 음성 모델만 교체합니다.',lang)
    c.zone(40,80,768,508,'GPU 1 · g6e.2xlarge · L40S 48GB 공유',kind='ec2')
    c.zone(864,80,376,508,'GPU 2 · g6e.2xlarge',kind='ec2')
    c.node(64,176,344,96,'Core 워커','판단 모델 + 필요 시 ASR')
    c.node(440,176,344,96,'Whisper 워커','whisper-large-v3-turbo · FP16')
    c.note(64,308,'Core 내부의 판단 모델 교체',anchor='start',size=16)
    c.note(64,336,'Nemotron은 필요 시 적재·해제',anchor='start')
    c.node(64,384,344,96,'Qwen TTS 워커 ×2','0.6B + 1.7B · 각각 별도 적재')
    c.node(440,384,344,96,'MiniCPM 워커','MiniCPM-o-4_5 · BF16')
    c.note(64,536,'활성화·로딩 성공한 GPU 워커들이 같은 VRAM을 점유',anchor='start',size=16)
    c.node(888,144,328,112,'Qwen3-ASR 워커 ×2','0.6B + 1.7B · 각각 독립 적재')
    c.node(888,312,328,96,'추가 음성 모델 1개','Speech manager가 프로세스 교체',kind='focal')
    c.note(888,448,'Qwen3-Omni / Step-Audio',anchor='start',size=16)
    c.note(888,480,'MiMo / Moshi 중 하나 선택',anchor='start',size=16)
    c.note(888,536,'STT와 직접 음성 모델의 잠금 분리',anchor='start',size=14)
    c.note(40,624,'Supertonic·Ppaso는 GPU 1 호스트의 CPU/RAM에서 별도 실행 · GPU VRAM을 사용하는 모델이 아님',anchor='start',size=16)
    c.legend([('step','활성화 시 적재되는 독립 워커'),('focal','선택 모델 하나씩 교체'),('EC2','각 서버에 GPU 1개 · 메모리 별도')])
    return c
