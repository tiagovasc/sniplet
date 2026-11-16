from pathlib import Path
import shutil
import tempfile
import unittest
from sniplet import media


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
class RenderTests(unittest.TestCase):
    def test_render_duration_source_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'source.mp4'
            out=Path(tmp)/'out.mp4'
            media.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=size=160x120:rate=30:duration=4','-f','lavfi','-i','sine=frequency=440:duration=4','-c:v','libx264','-c:a','aac',str(source)])
            digest=media.fingerprint(source)
            info=media.probe(source)
            result=media.render(source,out,[dict(start=1.,end=2.)],info)
            self.assertAlmostEqual(result['output_duration'],3,delta=.1)
            self.assertEqual(digest,media.fingerprint(source))
            with self.assertRaises(ValueError):
                media.render(source,out,[],info)
            with self.assertRaises(ValueError):
                media.render(source,source,[],info)

    def test_silence_scan(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'silence.mp4'
            media.run(['ffmpeg','-v','error','-f','lavfi','-i','color=size=160x120:rate=30:duration=3','-f','lavfi','-i','aevalsrc=if(between(t\\,1\\,2)\\,0\\,0.2*sin(440*2*PI*t)):d=3','-c:v','libx264','-c:a','aac',str(source)])
            pauses=media.silences(source,3)
            self.assertEqual(len(pauses),1)
            self.assertAlmostEqual(pauses[0][0],1,delta=.05)
            self.assertAlmostEqual(pauses[0][1],2,delta=.05)
