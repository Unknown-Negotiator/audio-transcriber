#!/usr/bin/env python3
"""Independently cross-check every reported edit distance with jiwer 4.0.0."""
import hashlib,importlib.metadata,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'metric_validation_lib'))
import jiwer
from score import normalize

def main():
 data=json.loads((ROOT/'results'/'results.json').read_text())
 assert len(data['clips'])==72
 assert len({(r['model'],r['config'],r['filename']) for r in data['clips']})==72
 for r in data['clips']:
  ref,hyp=r['scores']['reference_normalized'],r['scores']['hypothesis_normalized']
  assert normalize(r['reference_raw'])==ref
  w=jiwer.process_words(ref,hyp);c=jiwer.process_characters(ref,hyp)
  assert w.substitutions+w.deletions+w.insertions==r['scores']['word']['errors']
  assert c.substitutions+c.deletions+c.insertions==r['scores']['character']['errors']
  assert abs(w.wer-r['scores']['word']['error_rate'])<1e-12
  assert abs(c.cer-r['scores']['character']['error_rate'])<1e-12
  output=ROOT/'results'/r['model']/r['config']/(Path(r['filename']).stem+'.txt')
  assert output.read_text().strip()==r['hypothesis']
 for model,languages in data['aggregate'].items():
  for config,a in languages.items():
   group=[r for r in data['clips'] if r['model']==model and r['config']==config]
   assert len(group)==12
   ref=[r['scores']['reference_normalized'] for r in group];hyp=[r['scores']['hypothesis_normalized'] for r in group]
   assert abs(jiwer.process_words(ref,hyp).wer-a['word']['error_rate'])<1e-12
   assert abs(jiwer.process_characters(ref,hyp).cer-a['character']['error_rate'])<1e-12
 validation={'status':'passed','jiwer_version':importlib.metadata.version('jiwer'),'rapidfuzz_version':importlib.metadata.version('rapidfuzz'),'per_clip_pairs_checked':72,'model_language_aggregates_checked':6,'checks':['All word and character total edit distances agree with independent jiwer calculation','All per-clip WER/CER values agree within 1e-12','All six micro-averaged WER/CER pairs agree within 1e-12','All hypotheses match the saved application output files','Raw and corpus-normalized references agree under the scoring normalization','Exactly 72 unique model/language/clip results']}
 (ROOT/'results'/'metric_verification.json').write_text(json.dumps(validation,indent=2))
 data['validation']['independent_metric_verification']=validation
 (ROOT/'results'/'results.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
 aggregate=json.loads((ROOT/'results'/'aggregate.json').read_text());aggregate['validation']=data['validation'];(ROOT/'results'/'aggregate.json').write_text(json.dumps(aggregate,ensure_ascii=False,indent=2))
 report=ROOT/'REPORT.md';text=report.read_text();marker='- Error-count ties use substitution';text=text.replace(marker,'- Independent verification: jiwer 4.0.0 agrees with every one of the 72 word/character edit totals and all six aggregate WER/CER pairs (tolerance 1e-12). See `results/metric_verification.json`.\n'+marker);report.write_text(text)
 print(json.dumps(validation,indent=2))
if __name__=='__main__':main()
