#!/usr/bin/env python3
"""Optional ONLINE setup: download the exact public model revisions used in this check."""
import argparse,os
from pathlib import Path
os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
from huggingface_hub import snapshot_download
MODELS={
 'small':('Systran/faster-whisper-small','536b0662742c02347bc0e980a01041f333bce120'),
 'medium':('Systran/faster-whisper-medium','08e178d48790749d25932bbc082711ddcfdfbc4f'),
 'turbo':('dropbox-dash/faster-whisper-large-v3-turbo','0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf'),
}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);a=p.parse_args()
 for name,(repo,rev) in MODELS.items():
  snapshot_download(repo_id=repo,revision=rev,local_dir=str(a.directory/name),allow_patterns=['model.bin','config.json','tokenizer.json','preprocessor_config.json','vocabulary.*'])
