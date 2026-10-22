"""Invariants for the experimental audio filter, independent of ASR/model quality."""
import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
from experimental_denoise import denoise,Config

class NoiseFilterTests(unittest.TestCase):
    def test_silence_short_and_constant_energy_do_not_trigger_blind_suppression(self):
        for x in [np.zeros(16000),np.zeros(0),np.array([.1,-.1]),
                  .2*np.sin(2*np.pi*500*np.arange(16000)/16000)]:
            y,meta=denoise(x)
            np.testing.assert_allclose(y,x,atol=1e-7)
            self.assertTrue(meta['mode'].startswith('bypass'),meta)

    def test_invalid_shapes_rates_and_nonfinite_samples_are_rejected(self):
        for x,rate in [(np.zeros((160,2)),16000),(np.zeros(1600),24000),
                       (np.array([np.nan]),16000),(np.array([np.inf]),16000),
                       (np.zeros(16000*31),16000)]:
            with self.assertRaises(ValueError):denoise(x,rate)

    def test_no_noise_only_prefix_required_and_input_is_not_mutated(self):
        # Starts with speech-like tone, then contains pauses later: don't presume initial frames are noise.
        rng=np.random.default_rng(221)
        t=np.arange(64000)/16000
        voiced=((t<1.0)|((t>1.7)&(t<2.7))).astype(float)
        x=(.2*np.sin(2*np.pi*180*t)+.08*np.sin(2*np.pi*360*t))*voiced+.012*rng.standard_normal(len(t))
        original=x.copy();y,meta=denoise(x)
        np.testing.assert_array_equal(x,original)
        self.assertEqual(meta['mode'],'filtered')
        self.assertEqual(y.shape,x.shape)
        self.assertTrue(np.isfinite(y).all())
        self.assertLessEqual(np.max(np.abs(y)),1)
        self.assertGreaterEqual(meta['minimumGain'],10**(-Config().max_attenuation_db/20)-1e-8)
        pause=(t>3.2)&(t<3.8)
        self.assertLess(np.mean(y[pause]**2),np.mean(x[pause]**2))
        # Strong periodic speech remains, rather than being classified entirely as noise.
        active=(t>.1)&(t<.9)
        self.assertGreater(np.sqrt(np.mean(y[active]**2))/np.sqrt(np.mean(x[active]**2)),.7)

    def test_deterministic_and_preserves_unaligned_length(self):
        rng=np.random.default_rng(53)
        x=rng.normal(0,.015,32137);x[6000:18000]+=.2*np.sin(2*np.pi*250*np.arange(12000)/16000)
        a,ma=denoise(x);b,mb=denoise(x)
        self.assertEqual(len(a),32137)
        np.testing.assert_array_equal(a,b)
        self.assertEqual(ma['mode'],mb['mode'])

if __name__=='__main__':unittest.main()
