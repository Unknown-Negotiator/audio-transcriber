"""End-to-end test harness: forbid Python network connections during transcription."""
import runpy
import socket
import sys
from pathlib import Path

def denied(*a, **kw):
    raise RuntimeError('TEST: network socket connection forbidden')

socket.socket.connect = denied
socket.socket.connect_ex = denied
socket.create_connection = denied
sys.argv = [str(Path(__file__).parents[1] / 'transcribe.py')] + sys.argv[1:]
runpy.run_path(sys.argv[0], run_name='__main__')
