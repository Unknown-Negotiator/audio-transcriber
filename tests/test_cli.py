import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('app', Path(__file__).parents[1] / 'transcribe.py')
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)

class CLITests(unittest.TestCase):
    def test_offline_flags(self):
        app.offline_mode()
        self.assertEqual(os.environ['HF_HUB_OFFLINE'], '1')
        self.assertEqual(os.environ['HF_HUB_DISABLE_TELEMETRY'], '1')
    def test_missing_source(self):
        self.assertEqual(app.main(['transcribe', '/does-not-exist.mkv', '--model', '/none']), 1)
    def test_missing_model(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / 'audio.mkv'; f.touch()
            self.assertEqual(app.main(['transcribe', str(f), '--model', td]), 1)
    def test_existing_output_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / 'audio.mkv'; f.touch()
            o = f.with_suffix('.txt'); o.write_text('KEEP')
            self.assertEqual(app.main(['transcribe', str(f), '--model', td]), 1)
            self.assertEqual(o.read_text(), 'KEEP')
    def test_source_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / 'audio.mkv'; f.write_text('KEEP')
            self.assertEqual(app.main(['transcribe', str(f), '--model', td, '--output', str(f), '--force']), 1)
            self.assertEqual(f.read_text(), 'KEEP')
    def test_turbo_model_option(self):
        args = app.parser().parse_args(['download-model', '--size', 'large-v3-turbo', '--directory', 'models/turbo'])
        self.assertEqual(args.size, 'large-v3-turbo')
    def test_parser_track(self):
        self.assertEqual(app.parser().parse_args(['transcribe','x.mkv','--model','m','--audio-track','1']).audio_track, 1)

if __name__ == '__main__': unittest.main()
