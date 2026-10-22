"""Memory residency policy tests; no models or CUDA allocations are loaded."""
import sys,unittest,types
from pathlib import Path
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'runtime'))
import model_server as core
class MemoryPolicyTests(unittest.TestCase):
 def setUp(self):
  core.model=object();core.processor=object();core.compiled_grammar=object();core.asr=object();core.asr_processor=object()
  core.status={'models':{'llm':'old','quantization':'bf16','asr':core.ASR_MODEL},'asrLoaded':True}
 def test_release_planner_preserves_asr(self):
  asr=core.asr
  with patch.object(core.torch.cuda,'empty_cache'):
   core.release_planner()
  self.assertIsNone(core.model);self.assertIsNone(core.processor);self.assertIs(core.asr,asr)
  self.assertNotIn('llm',core.status['models'])
 def test_large_planner_evicts_idle_asr_before_loading(self):
  loader=Mock();loader.from_pretrained.side_effect=RuntimeError('test loading boundary')
  fake=types.SimpleNamespace(AutoTokenizer=Mock(),AutoModelForImageTextToText=loader,AutoModelForCausalLM=loader,AutoModelForMultimodalLM=loader)
  with patch.dict(sys.modules,{'transformers':fake,'xgrammar':types.SimpleNamespace()}),patch.object(core.torch.cuda,'empty_cache'),patch.object(core.torch.cuda,'mem_get_info',return_value=(9*2**30,44*2**30)),patch.object(core.torch.cuda,'synchronize'),patch.object(core.torch.cuda,'memory_allocated',return_value=0):
   with self.assertRaisesRegex(RuntimeError,'test loading boundary'):core.load_planner('google/gemma-4-E2B-it')
  self.assertIsNone(core.asr);self.assertFalse(core.status['asrLoaded']);self.assertNotIn('asr',core.status['models'])
 def test_asr_reloads_on_demand_and_drops_planner_only_when_needed(self):
  core.asr=None;loaded=Mock();loader=Mock();loader.from_pretrained.return_value.eval.return_value=loaded
  processor=Mock();fake=types.SimpleNamespace(AutoModelForRNNT=loader,AutoProcessor=processor)
  with patch.dict(sys.modules,{'transformers':fake}),patch.object(core.torch.cuda,'empty_cache'),patch.object(core.torch.cuda,'mem_get_info',return_value=(1*2**30,44*2**30)):
   core.load_asr();core.load_asr()
  self.assertIs(core.asr,loaded);self.assertIsNone(core.model);self.assertTrue(core.status['asrLoaded']);self.assertEqual(loader.from_pretrained.call_count,1)
if __name__=='__main__':unittest.main()
