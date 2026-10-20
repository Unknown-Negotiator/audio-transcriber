"""Verify the independently obtained public LibriVox source before inference."""
import hashlib,sys
from pathlib import Path
p=Path(sys.argv[1])
assert p.stat().st_size==40902574
assert hashlib.sha256(p.read_bytes()).hexdigest()=='2ef1620a2f38f8ac4e4e06c6cee775c148dbb38725cf500f21dac8cb26412aee'
print('Verified public The Time Machine chapter 5 MP3; 40902574 bytes.')
