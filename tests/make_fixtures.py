"""Generate synthetic media locally for decoder tests; never read personal files."""
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).parents[1]

def make_fixtures():
    target = ROOT / 'test-results'
    target.mkdir(exist_ok=True)
    required = ['speech sample.mkv', 'речь sample.mkv', 'no-audio.mkv', 'changing-layout.mkv']
    if all((target / name).is_file() for name in required):
        return
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        raise RuntimeError('Decoder tests need ffmpeg in the test environment to generate synthetic media.')
    def run(*args):
        subprocess.run([ffmpeg, '-v', 'error', '-y', *map(str,args)], check=True)
    run('-f','lavfi','-i','sine=frequency=440:duration=8','-c:a','pcm_s16le',target/'speech sample.mkv')
    shutil.copy2(target/'speech sample.mkv', target/'речь sample.mkv')
    run('-f','lavfi','-i','color=size=32x32:duration=0.1','-an','-c:v','ffv1',target/'no-audio.mkv')
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        for channels,name in [(1,'mono'),(2,'stereo')]:
            run('-f','lavfi','-i','sine=frequency=440:duration=0.5','-ac',channels,'-c:a','libmp3lame',td/f'{name}.mp3')
        (td/'inputs.txt').write_text("file 'mono.mp3'\nfile 'stereo.mp3'\n")
        run('-f','concat','-safe','0','-i',td/'inputs.txt','-c:a','copy',target/'changing-layout.mkv')

if __name__ == '__main__':
    make_fixtures()
