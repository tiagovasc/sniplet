import json
from pathlib import Path
import tempfile
import unittest
from sniplet.core import candidates, plan
from sniplet.transcript import Word, load, validate


class PlanningTests(unittest.TestCase):
    def test_default_keeps_half_second(self):
        c = candidates(1, 3, 30)[0]
        self.assertEqual(c['kind'], 'silence')
        self.assertGreaterEqual((c['start']-1)+(3-c['end']), .5)

    def test_trailing_extension_keeps_real_gap(self):
        words = [Word('um,', 3.05, 3.3), Word('yes', 3.5, 4)]
        c = candidates(1, 3, 30, words=words)[0]
        self.assertEqual(c['kind'], 'silence+trailing-filler')
        self.assertGreaterEqual(c['start']-1, .5)
        self.assertGreaterEqual(c['end'], 3.3)
        self.assertLess(c['end'], 3.5)

    def test_leading_extension(self):
        c = candidates(1, 3, 30, words=[Word('uh', .7, .97)])[0]
        self.assertEqual(c['kind'], 'leading-filler+silence')
        self.assertLessEqual(c['start'], .7)
        self.assertGreaterEqual(3-c['end'], .5)

    def test_nonadjacent_not_removed(self):
        self.assertEqual(len(candidates(1, 3, 30, words=[Word('um',3.3,3.6)])), 1)

    def test_ambiguous_response_not_default(self):
        self.assertEqual(len(candidates(1,3,30,words=[Word('hmm',3.02,3.4)])), 1)

    def test_does_not_cross_real_word(self):
        words=[Word('yes',3.01,3.2), Word('um',3.21,3.5)]
        self.assertEqual(len(candidates(1,3,30,words=words)),1)

    def test_both_edges_never_remove_whole_pause(self):
        for c in candidates(1,3,30,words=[Word('um',.7,.98),Word('uh',3.02,3.3)]):
            removed = max(0,min(3,c['end'])-max(1,c['start']))
            self.assertGreaterEqual(2-removed,.5)

    def test_expansion_rechecked_then_falls_back(self):
        calls=[]
        def judge(a,b):
            calls.append((a,b))
            return dict(accepted=b<3,reason='test')
        cuts,_=plan([(1,3)],30,5,judge,words=[Word('um',3.02,3.4)])
        self.assertEqual(len(calls),2)
        self.assertEqual(cuts[0]['kind'],'silence')
        self.assertNotEqual(calls[0],calls[1])

    def test_no_standalone_fillers(self):
        cuts,_=plan([],30,5,lambda a,b:dict(accepted=True),words=[Word('um',1,1.5)])
        self.assertEqual(cuts,[])

    def test_opening_closing_silence_untouched(self):
        cuts,_=plan([(0,2),(4,6)],30,6,lambda a,b:dict(accepted=True))
        self.assertEqual(cuts,[])

    def test_meaningful_speech_inside_detected_silence_protected(self):
        self.assertEqual(candidates(1,3,30,words=[Word('quietly',2,2.3)]),[])

    def test_contiguous_filler_chain(self):
        c=candidates(1,3,30,words=[Word('um',3.01,3.2),Word('uh',3.25,3.5)])[0]
        self.assertGreaterEqual(c['end'],3.5)

    def test_frame_rounding_removes_complete_filler(self):
        c=candidates(1,3,30,words=[Word('um',3.01,3.317)])[0]
        self.assertGreaterEqual(c['end'],3.317)

    def test_word_inside_silence_not_partially_cut(self):
        self.assertEqual(candidates(1,3,30,words=[Word('um',2,2.3)]),[])


class TranscriptTests(unittest.TestCase):
    def read(self, content, ext):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/('words'+ext)
            p.write_text(content,encoding='utf-8')
            return load(p,10)

    def test_word_srt(self):
        w=self.read('1\n00:00:01,123 --> 00:00:01,456\num\n','.srt')[0]
        self.assertEqual(w.start,1.123)

    def test_word_vtt(self):
        w=self.read('WEBVTT\n\n00:01.123 --> 00:01.456\nuh\n','.vtt')[0]
        self.assertEqual(w.end,1.456)

    def test_sentence_rejected(self):
        with self.assertRaises(ValueError):
            self.read('1\n00:00:01,000 --> 00:00:03,000\nwell um yes\n','.srt')

    def test_coarse_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            self.read('1\n00:00:01 --> 00:00:03\num\n','.srt')

    def test_json_explicit_milliseconds(self):
        w=self.read(json.dumps(dict(time_unit='milliseconds', words=[dict(word='um',start=1123,end=1456)])),'.json')[0]
        self.assertEqual(w.start,1.123)

    def test_invalid_times(self):
        for words in [[Word('um',-1,2)],[Word('um',1,float('nan'))],[Word('um',1,11)],[Word('um',1,2),Word('uh',1.5,3)]]:
            with self.assertRaises(ValueError):
                validate(words,10)


if __name__=='__main__':
    unittest.main()
