"""Browser-level deployment check with a synthetic microphone; no real microphone recording."""
import argparse,json,wave
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--base',required=True);args=p.parse_args();url=args.base.rstrip('/')
assert url.startswith('https://')
sample=ROOT/'.runtime/browser-mic-sample.wav'
with wave.open(str(ROOT/'public/sample-command.wav'),'rb') as f:params=f.getparams();audio=f.readframes(f.getnframes())
with wave.open(str(sample),'wb') as f:
 f.setparams(params);f.writeframes(bytes(params.framerate*params.sampwidth)+audio+bytes(params.framerate*params.sampwidth*2))
with sync_playwright() as p:
 browser=p.chromium.launch(args=['--no-sandbox','--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream',f'--use-file-for-fake-audio-capture={sample}%noloop'])
 context=browser.new_context(permissions=['microphone'],viewport={'width':1440,'height':1000});page=context.new_page();sessions=[];errors=[]
 page.on('request',lambda r:sessions.append(r.headers.get('x-session-id')) if '/api/turn' in r.url else None)
 page.on('pageerror',lambda e:errors.append(str(e)))
 try:
  page.goto(url+'/?lang=ko');expect(page.locator('#mic')).to_be_enabled(timeout=120000)
  page.locator('.conversation-settings > summary').click()
  labels={}
  for provider in ['qwen17','supertonic']:
   page.select_option('#tts-provider',provider);expect(page.locator('#model-tts')).to_contain_text('1.7B' if provider=='qwen17' else 'Supertonic');labels[provider]=page.locator('#model-tts').inner_text()
  expect(page.locator('#mic')).to_be_enabled();page.click('#mic')
  expect(page.locator('#passenger-temp')).to_contain_text('25',timeout=120000)
  page.click('#mic');page.wait_for_timeout(4000)
  sid=next(s for s in sessions if s)
  def exported():return page.request.get(url+'/api/export',headers={'X-Session-Id':sid}).json()
  data=exported();assert data['state']['temperature']=={'driver':22,'passenger':25},data['state']
  assert data['turns'][-1]['ttsProvider']=='supertonic' and data['turns'][-1].get('ttsModel')=='Supertone/supertonic-3'
  assert data['turns'][-1].get('firstPlaybackMs') is not None,data['turns'][-1]
  playback=data['turns'][-1]['firstPlaybackMs']
  page.select_option('#tts-provider','qwen17');page.fill('#text-input','조수석 온도를 28도로 맞춰줘.');page.click('#send')
  expect(page.locator('#passenger-temp')).to_contain_text('28',timeout=60000)
  page.click('#interrupt');page.wait_for_timeout(7000)
  canceled=exported()['turns'][-1]
  assert canceled.get('interrupted') is True and canceled.get('firstPlaybackMs') is None,canceled
  other=browser.new_context().new_page();other.goto(url);expect(other.locator('#passenger-temp')).to_contain_text('22')
  assert page.request.get(url+'/guide/hands-on.html').status==200
  assert not errors,errors
  result={'passed':True,'syntheticMicrophone':True,'realMicrophoneTested':False,'tts':'supertonic','firstPlaybackMs':playback,'initialCommandState':data['state'],'cancellationVerified':True,'stateAfterCancel':exported()['state'],'secondBrowserInitialTemperature':22,'labels':labels,'pageErrors':errors}
  (ROOT/'.runtime/browser-microphone-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));page.screenshot(path=str(ROOT/'.runtime/browser-microphone.png'),full_page=True)
  print(json.dumps(result,ensure_ascii=False))
 except Exception:
  page.screenshot(path=str(ROOT/'.runtime/browser-failure.png'),full_page=True)
  print('errors',errors,'status',page.locator('#voice-status').inner_text(),'sessionRequests',len(sessions))
  raise
 finally:browser.close()
