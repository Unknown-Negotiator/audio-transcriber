import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
import wave

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location('app', ROOT / 'transcribe.py')
app = importlib.util.module_from_spec(spec); spec.loader.exec_module(app)

class MediaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('fixtures', ROOT / 'tests/make_fixtures.py')
        fixtures = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixtures)
        fixtures.make_fixtures()

    def test_decode_unicode_and_preserve_input(self):
        source = ROOT / 'test-results' / 'речь sample.mkv'
        before = hashlib.sha256(source.read_bytes()).digest()
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'out.wav'
            app.decode_audio(source, out, 0)
            with wave.open(str(out)) as w:
                self.assertEqual((w.getnchannels(), w.getsampwidth(), w.getframerate()), (1, 2, 16000))
                self.assertGreater(w.getnframes(), 100000)
        self.assertEqual(before, hashlib.sha256(source.read_bytes()).digest())
    def test_midstream_channel_change(self):
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / 'out.wav'
            app.decode_audio(ROOT / 'test-results/changing-layout.mkv', output, 0)
            with wave.open(str(output)) as wav:
                self.assertEqual(wav.getnchannels(), 1)
                self.assertGreater(wav.getnframes(), 15000)
                self.assertLess(wav.getnframes(), 20000)
    def test_no_audio(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError, '0 audio tracks'):
                app.decode_audio(ROOT / 'test-results/no-audio.mkv', Path(td) / 'o.wav', 0)
    def test_invalid_track(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError, '1 audio tracks'):
                app.decode_audio(ROOT / 'test-results/speech sample.mkv', Path(td) / 'o.wav', 5)

if __name__ == '__main__': unittest.main()
