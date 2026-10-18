import unittest
from speech_protocol import complete_json_text

class SpeechProtocolTests(unittest.TestCase):
    def test_mimo_complete_json_fence_is_preserved_without_changing_actions(self):
        payload='{"heard":"운전석 24도","intent":"control","actions":[{"type":"temperature","zone":"driver","value":24}],"reply":""}'
        self.assertEqual(complete_json_text('```json\n'+payload+'\n```'),payload)
    def test_incomplete_and_prefaced_plans_are_not_repaired(self):
        for raw in ['```json\n{"intent":"control",\n```','Here is the command: {"intent":"control"}']:
            with self.assertRaises(ValueError):complete_json_text(raw)
    def test_only_unused_control_reply_gets_a_default(self):
        import json
        raw='{"heard":"조수석 25도","intent":"control","actions":[{"type":"temperature","zone":"passenger","value":25}]}'
        result=json.loads(complete_json_text(raw,default_control_reply=True))
        self.assertEqual(result['reply'],'')
        self.assertEqual(result['actions'],json.loads(raw)['actions'])
        self.assertNotIn('reply',json.loads(complete_json_text('{"intent":"question","actions":[]}',default_control_reply=True)))

if __name__=='__main__':unittest.main()
