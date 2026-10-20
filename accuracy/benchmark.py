#!/usr/bin/env python3
"""Run the actual local-transcriber CLI sequentially against fixed paired references."""
import argparse,datetime,hashlib,importlib.metadata,json,os,platform,subprocess,sys,time
from pathlib import Path
from score import score,aggregate
ROOT=Path(__file__).resolve().parent

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--app',type=Path,required=True)
    parser.add_argument('--models',type=Path,required=True)
    parser.add_argument('--threads',type=int,default=4)
    args=parser.parse_args();args.app=args.app.resolve();args.models=args.models.resolve()
    manifest=json.loads((ROOT/'manifest.json').read_text())
    samples=[sample for language in manifest['languages'] for sample in language['samples']]
    snapshot=ROOT/'app_snapshot'/'transcribe.py';snapshot.parent.mkdir(exist_ok=True)
    if not snapshot.exists():snapshot.write_bytes(args.app.read_bytes())
    assert sha(snapshot)==sha(args.app),'Application changed since snapshot'
    env=os.environ.copy();env.update({'HF_HUB_OFFLINE':'1','HF_HUB_DISABLE_TELEMETRY':'1','DO_NOT_TRACK':'1','OMP_NUM_THREADS':str(args.threads),'MKL_NUM_THREADS':str(args.threads)})
    result_file=ROOT/'results'/'per_clip.jsonl';result_file.parent.mkdir(exist_ok=True)
    rows=[json.loads(line) for line in result_file.read_text().splitlines()] if result_file.exists() else []
    completed={(r['model'],r['config'],r['filename']) for r in rows}
    model_metadata={}
    for model in ['small','medium','turbo']:
        modelpath=args.models/model
        model_metadata[model]={'directory_label':model,'files':{p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(modelpath.iterdir()) if p.is_file()}}
        for idx,sample in enumerate(samples):
            key=(model,sample['config'],sample['filename'])
            if key in completed:continue
            audio=ROOT/sample['audio_path'];assert sha(audio)==sample['audio_sha256']
            dest=ROOT/'results'/model/sample['config'];dest.mkdir(parents=True,exist_ok=True)
            output=dest/(Path(sample['filename']).stem+'.txt');log=output.with_suffix('.log')
            cmd=[sys.executable,str(snapshot),'transcribe',str(audio),'--model',str(modelpath),'--language',sample['language'],'--threads',str(args.threads),'--output',str(output),'--force']
            start=time.monotonic()
            proc=subprocess.run(cmd,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            elapsed=time.monotonic()-start
            log.write_text((proc.stdout+proc.stderr).replace(str(ROOT),'accuracy').replace(str(args.models),'MODELS'))
            if proc.returncode!=0:raise RuntimeError(f'CLI failed {model} {sample["config"]} {sample["filename"]}: {proc.stderr}')
            hypothesis=output.read_text()
            row={'model':model,'config':sample['config'],'filename':sample['filename'],'id':sample['id'],'reference_raw':sample['reference_raw'],'reference_dataset_normalized':sample['reference_dataset_normalized'],'hypothesis':hypothesis.strip(),'audio_seconds':sample['num_samples']/16000,'wall_seconds':elapsed,'returncode':proc.returncode,'scores':score(sample['reference_dataset_normalized'],hypothesis)}
            with result_file.open('a') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n');f.flush()
            rows.append(row)
            print(f'{model} {idx+1}/{len(samples)} {sample["config"]} {sample["filename"]}: WER={row["scores"]["word"]["error_rate"]:.4f} CER={row["scores"]["character"]["error_rate"]:.4f} audio={row["audio_seconds"]:.2f}s wall={elapsed:.2f}s',flush=True)
        for config in ['ru_ru','fr_fr']:
            group=[r for r in rows if r['model']==model and r['config']==config]
            print('AGGREGATE',model,config,json.dumps(aggregate(group)),flush=True)
    results={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'dataset':{'id':manifest['dataset'],'revision':manifest['revision'],'split':manifest['split'],'license':manifest['license'],'selection_rule':manifest['selection_rule'],'selection_seed':manifest['selection_seed']},'application':{'source_sha256':sha(snapshot),'cli':'python transcribe.py transcribe AUDIO --model MODELS/MODEL --language ru|fr --threads 4 --output OUTPUT --force','settings':{'device':'cpu','compute_type':'int8','cpu_threads':args.threads,'beam_size':5,'vad_filter':False,'condition_on_previous_text':False,'task':'transcribe','language':'explicit known language, not autodetected'}},'environment':{'python':sys.version,'platform':platform.platform(),'packages':{p:importlib.metadata.version(p) for p in ['faster-whisper','ctranslate2','av','numpy','huggingface-hub']},'processor':'INTEL(R) XEON(R) PLATINUM 8573C; shared cloud VM; not user Mac'},'model_files':model_metadata,'metric_definition':{'reference':'Official FLEURS transcription column; raw_transcription retained separately','normalization':'Unicode NFKC and casefold; keep Unicode letters, marks, numbers; replace punctuation/symbols with spaces; collapse whitespace. Accents and Cyrillic ё preserved. No number-word conversion or phonetic correction.','WER':'Sum of minimum word-level substitutions+deletions+insertions divided by sum of reference words (micro-average, not mean clip WER).','CER':'Same at Unicode character level on normalized strings, including their single word-separator spaces.','tie_breaking':'When several alignments have same minimum cost: prefer substitution, then deletion, then insertion.'},'aggregate':{model:{config:aggregate([r for r in rows if r['model']==model and r['config']==config]) for config in ['ru_ru','fr_fr']} for model in ['small','medium','turbo']},'clips':rows,'limits':['Small deterministic sample, not a full corpus evaluation or statistical proof of one model being best.','Public official test split, not guaranteed unseen by pretrained Whisper. No model tuning was performed.','Short human read-speech utterances, not long recordings, dialogue, overlapping speakers, accents, poor microphones or noisy videos.','Known languages were specified; this does not measure auto-detection accuracy.','WER/CER assess lexical transcription after the stated normalization, not punctuation, casing, timestamps, or semantic correctness.','No private user audio was accessed or uploaded. Models ran locally on the assistant cloud VM, sequentially; wall time includes fresh CLI/model loading per clip.']}
    (ROOT/'results'/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
    print('DONE results/results.json',flush=True)
if __name__=='__main__':main()
