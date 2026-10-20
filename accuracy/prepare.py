#!/usr/bin/env python3
"""Download a fixed public test set; no outcome-dependent selection."""
import concurrent.futures,csv,hashlib,io,json,tarfile,time,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REV='70bb2e84b976b7e960aa89f1c648e09c59f894dd'
BASE=f'https://huggingface.co/datasets/google/fleurs/resolve/{REV}/'
COUNT=12
SEED='local-transcriber-accuracy-2026-10-20-v1'
HASHES={'ru_ru':'8a0d6a0d23c3421f50c575bcf65d875cd19dadae2f7cabb415024f81b65178b1','fr_fr':'d23690e102f373554d1b544cd2ff1e76e4fedeb04953c0b72751a1b7c518cfdd'}
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def download(url,path):
 if path.exists():return
 for attempt in range(3):
  try:
   with urllib.request.urlopen(url,timeout=120) as response,open(str(path)+'.part','wb') as out:
    while b:=response.read(1024*1024):out.write(b)
   Path(str(path)+'.part').replace(path);return
  except Exception:
   if attempt==2:raise
   time.sleep(2**attempt)
def prepare(config):
 dest=ROOT/'data'/config;dest.mkdir(parents=True,exist_ok=True)
 tsv=dest/'test.tsv';download(BASE+f'data/{config}/test.tsv',tsv)
 rows=list(csv.reader(io.StringIO(tsv.read_text()),delimiter='\t',quoting=csv.QUOTE_NONE))
 for r in rows:assert len(r)==7,(len(r),r)
 chosen=sorted(enumerate(rows),key=lambda x:hashlib.sha256(f'{SEED}\0{config}\0{x[1][1]}'.encode()).digest())[:COUNT]
 manifest=[]
 for idx,r in chosen:
  manifest.append({'config':config,'language':config[:2],'original_tsv_row_0_based':idx,'id':int(r[0]),'filename':r[1],'reference_raw':r[2],'reference_dataset_normalized':r[3],'num_samples':int(r[5]),'gender':r[6],'audio_path':str((dest/r[1]).relative_to(ROOT))})
 print(config,'selected',len(manifest),'from',len(rows),'test rows; filenames',[m['filename'] for m in manifest],flush=True)
 (dest/'selection_before_inference.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
 archive=dest/'test.tar.gz';download(BASE+f'data/{config}/audio/test.tar.gz',archive)
 digest=sha(archive);assert digest==HASHES[config],(config,digest)
 print(config,'archive verified',archive.stat().st_size,flush=True)
 selected={m['filename']:m for m in manifest}
 with tarfile.open(archive,'r:gz') as tar:
  for member in tar:
   name=Path(member.name).name
   if name in selected:
    assert member.isfile()
    with tar.extractfile(member) as src,open(dest/name,'wb') as out:out.write(src.read())
    selected[name]['archive_member']=member.name
 for m in manifest:
  p=ROOT/m['audio_path'];assert p.is_file(),p
  m['audio_sha256']=sha(p);m['audio_bytes']=p.stat().st_size
 print(config,'extracted',len(manifest),'clips',flush=True)
 return {'config':config,'test_rows':len(rows),'tsv_url':BASE+f'data/{config}/test.tsv','tsv_sha256':sha(tsv),'archive_url':BASE+f'data/{config}/audio/test.tar.gz','archive_sha256':digest,'samples':manifest}
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(2) as pool:languages=list(pool.map(prepare,['ru_ru','fr_fr']))
 result={'dataset':'google/fleurs','revision':REV,'split':'test','license':'CC-BY-4.0','license_url':'https://creativecommons.org/licenses/by/4.0/','paper_url':'https://arxiv.org/abs/2205.12446','sample_count_per_language':COUNT,'selection_rule':'Take the 12 lowest SHA-256 digests of UTF-8 seed + NUL + config + NUL + original filename, without content, duration, quality, or output filtering. Order is ascending digest.','selection_seed':SEED,'languages':languages,'held_out_definition':'Official test partition; no tuning or fine-tuning was performed. It is not possible to establish that the original Whisper training data excluded these public recordings.'}
 (ROOT/'manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
 print('DONE manifest.json',flush=True)
