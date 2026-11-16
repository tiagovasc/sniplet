import unittest
import numpy as np
from sniplet.vision import compare


class VisualTests(unittest.TestCase):
    def sample(self):
        return dict(pose=np.column_stack([np.zeros((33,2)),np.ones(33)]),face=np.zeros((478,2)))

    def test_matching_landmarks(self):
        self.assertTrue(compare(self.sample(),self.sample())['accepted'])

    def test_mouth_veto_despite_matching_body(self):
        a,b=self.sample(),self.sample()
        b['face'][13,1]=10
        result=compare(a,b)
        self.assertFalse(result['accepted'])
        self.assertEqual(result['reason'],'mouth movement')

    def test_missing_shoulders(self):
        a,b=self.sample(),self.sample()
        b['pose'][11,2]=0
        self.assertFalse(compare(a,b)['accepted'])

    def test_invisible_wrists_reported_as_unmeasured(self):
        a,b=self.sample(),self.sample()
        a['pose'][[15,16],2]=0
        self.assertIsNone(compare(a,b)['metrics']['wrists'])
