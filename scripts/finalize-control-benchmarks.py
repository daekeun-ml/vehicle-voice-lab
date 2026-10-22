"""Apply separately recorded semantic reviews; never change model outputs."""
from pathlib import Path
import json,math
ROOT=Path('research/deployment-benchmarks')
reviews=json.loads((ROOT/'semantic-reviews.json').read_text())
summary=json.loads((ROOT/'summary.json').read_text())
exclusions=json.loads((ROOT/'timing-exclusions.json').read_text())['exclusions'] if (ROOT/'timing-exclusions.json').exists() else []
for m in summary['models']:
    for suite in ['original31','hard48']:
        p=ROOT/suite/(m['id']+'.json')
        if not p.exists():continue
        run=json.loads(p.read_text())
        excluded={x['caseId']:x['reason'] for x in exclusions if x['modelId']==m['id'] and x['suite']==suite}
        if excluded:
            for row in run['rows']:
                if row['id'] in excluded:row['timingExcludedReason']=excluded[row['id']]
            times=sorted(r['firstAudioMs'] for r in run['rows'] if not r.get('modelLoadMs') and r['id'] not in excluded and isinstance(r.get('firstAudioMs'),(int,float)))
            m['suites'][suite].update(timingExcluded=sum(r['id'] in excluded for r in run['rows']),
                medianFirstAudioMs=times[math.ceil(len(times)*.5)-1] if times else None,
                p95FirstAudioMs=times[math.ceil(len(times)*.95)-1] if times else None)
        if run['status']=='complete':run.pop('blockReason',None);m['suites'][suite].pop('blockReason',None)
        if m['id'] in ['qwen3-omni','sonic']:
            run['quantization']='mixed-nf4' if m['id']=='qwen3-omni' else 'managed'
            for row in run['rows']:row['quantization']=run['quantization']
        if suite=='hard48' and m['id'] in reviews['models']:
            review=reviews['models'][m['id']]
            assert run['completedAt']==review['runCompletedAt']
            assert run['audioCorpusHash']==review['audioCorpusHash']
            for row in run['rows']:
                if row.get('semanticReviewRequired'):
                    r=review['rows'][row['id']]
                    assert row.get('reply')==r['evidence']
                    row['semanticReview']={**r,'reviewer':reviews['reviewer']}
                row['passed']=bool(row.get('actionStateCorrect') and row.get('audioValid') and
                                   (not row.get('semanticReviewRequired') or row['semanticReview']['passed']))
            run['strictPassed']=sum(r['passed'] for r in run['rows'])
            run['semanticReviewCompletedAt']=reviews['reviewedAt']
            m['suites'][suite].update(strictPassed=run['strictPassed'],semanticReviewPending=0,semanticReviewer=reviews['reviewer'])
        p.write_text(json.dumps(run,ensure_ascii=False,indent=2)+'\n')
summary['semanticReviewNote']='Assistant review against frozen requirements; objective failures skipped. Not a human listening test or MOS.'
(ROOT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
