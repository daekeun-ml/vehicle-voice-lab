import unittest
from minicpm_protocol import chunk_windows,Conversation

class StreamingBoundaries(unittest.TestCase):
    def test_all_samples_once_and_short_tail_is_padded(self):
        for length in [1,15999,16000,16001,81920]:
            windows=list(chunk_windows(length))
            self.assertEqual(sum(end-start for start,end,_,_ in windows),length)
            self.assertEqual([start for start,_,_,_ in windows],[0]+[w[1] for w in windows[:-1]])
            self.assertEqual(sum(last for *_,last in windows),1)
            for start,end,padding,_ in windows:self.assertEqual(end-start+padding,16000)
    def test_same_client_keeps_context_but_new_client_and_language_do_not(self):
        c=Conversation();self.assertTrue(c.begin('a','en',100));sid=c.session_id;c.finish(101)
        self.assertFalse(c.begin('a','en',102));self.assertEqual(sid,c.session_id)
        self.assertTrue(c.begin('b','en',103));self.assertNotEqual(sid,c.session_id)
        self.assertTrue(c.begin('b','ko',104))
    def test_expiry_limits_reset_and_cancellation_discard_context(self):
        c=Conversation(max_turns=1);c.begin('a','en',100);c.finish(101)
        self.assertTrue(c.begin('a','en',102));c.finish(103)
        self.assertTrue(c.begin('a','en',404));c.invalidate()
        self.assertTrue(c.begin('a','en',405))

if __name__=='__main__':unittest.main()
