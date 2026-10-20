"""Run offline CLI, recording elapsed time and child peak RSS. Linux/macOS units differ."""
import hashlib,json,platform,resource,subprocess,sys,time
from pathlib import Path
source, model, language, output, metrics = sys.argv[1:]
sha = hashlib.sha256(Path(source).read_bytes()).hexdigest()
start = time.monotonic()
with open(str(output)+'.log','w') as log:
    result = subprocess.run([sys.executable,str(Path(__file__).with_name('run_offline.py')),
        'transcribe',source,'--model',model,'--language',language,'--timestamps','--output',output],
        stdout=log,stderr=log)
usage=resource.getrusage(resource.RUSAGE_CHILDREN)
data={'exit_code':result.returncode,'elapsed_seconds':time.monotonic()-start,
      'peak_rss_bytes':usage.ru_maxrss*(1 if platform.system()=='Darwin' else 1024),
      'input_bytes':Path(source).stat().st_size,'source_sha256_before':sha,
      'source_sha256_after':hashlib.sha256(Path(source).read_bytes()).hexdigest(),
      'platform':platform.platform(),'python':sys.version,'model_directory':model}
if Path(output).exists(): data['output_bytes']=Path(output).stat().st_size
Path(metrics).write_text(json.dumps(data,indent=2))
print(json.dumps(data,indent=2))
sys.exit(result.returncode)
