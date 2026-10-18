"""Refresh public model evidence; discovery never installs or enables a model."""
import argparse,concurrent.futures,datetime,json,pathlib,urllib.parse,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--search',help='Find additional candidates; keep results separate from the reviewed catalog');args=p.parse_args()
def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':'vehicle-voice-research/1.0'})
    with urllib.request.urlopen(req,timeout=20) as response:return json.load(response)
def evidence(repo):
    try:
        d=get('https://huggingface.co/api/models/'+repo);c=d.get('cardData') or {}
        return {'repo':repo,'latestRevision':d['sha'],'gated':d.get('gated'),'metadataLicense':c.get('license'),'licenseName':c.get('license_name'),'languages':c.get('language'),'parameters':d.get('safetensors',{}).get('total'),'pipeline':d.get('pipeline_tag'),'source':'https://huggingface.co/'+repo,'checkedAt':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    except Exception as error:return {'repo':repo,'error':str(error)}
out=ROOT/'research';out.mkdir(exist_ok=True)
if args.search:
    hits=get('https://huggingface.co/api/models?'+urllib.parse.urlencode({'search':args.search,'limit':20,'sort':'downloads','direction':-1}))
    result={'query':args.search,'reviewRequired':True,'models':list(concurrent.futures.ThreadPoolExecutor(6).map(evidence,[m['id'] for m in hits]))}
    (out/'discovered-models.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print('Saved discovery results. Review official source, modalities, language and license before adding to model-catalog.json.')
else:
    catalog=json.loads((ROOT/'model-catalog.json').read_text());result=list(concurrent.futures.ThreadPoolExecutor(6).map(evidence,[m['repo'] for m in catalog['models']]))
    (out/'model-evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(f'Refreshed evidence for {len(result)} models; serving allowlist and pinned revisions unchanged.')
