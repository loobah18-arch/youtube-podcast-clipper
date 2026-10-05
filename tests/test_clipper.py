import unittest
from core.vtt_parser import timestamp_to_seconds, clean_vtt_text, parse_vtt
from core.analyzer import ClipAnalyzer
from core.cloud_dispatcher import CloudDispatcher

SAMPLE_VTT = """WEBVTT
Kind: captions
Language: en

00:00:01.000 --> 00:00:04.500 align:start position:0%
There<00:00:01.500><c> are</c><00:00:02.000><c> decades</c> where nothing happens

00:00:04.500 --> 00:00:08.000 align:start position:0%
and weeks where decades happen in programming

00:00:08.000 --> 00:00:35.000 align:start position:0%
The biggest lie people tell themselves is that AI will replace everything tomorrow.

00:00:35.000 --> 00:00:50.000 align:start position:0%
In truth, high-agency engineers are building more software than ever before in history.
"""

class TestPodcastClipper(unittest.TestCase):

    def test_timestamp_to_seconds(self):
        # 1 hour, 2 minutes, 3 seconds, 500 ms
        sec = timestamp_to_seconds(1, 2, 3, 500)
        self.assertEqual(sec, 3723.5)

    def test_clean_vtt_text(self):
        raw = "There<00:00:01.500><c> are</c> decades align:start position:0%"
        cleaned = clean_vtt_text(raw)
        self.assertEqual(cleaned, "There are decades")

    def test_parse_vtt(self):
        segments = parse_vtt(SAMPLE_VTT)
        self.assertTrue(len(segments) >= 3)
        self.assertEqual(segments[0]["start"], 1.0)
        self.assertIn("decades", segments[0]["text"])

    def test_clip_analyzer(self):
        segments = parse_vtt(SAMPLE_VTT)
        analyzer = ClipAnalyzer()
        candidates = analyzer.find_heuristic_candidates(segments, top_k=2)
        self.assertTrue(len(candidates) >= 1)
        top = candidates[0]
        self.assertGreaterEqual(top["duration"], 30.0)
        self.assertGreaterEqual(top["score"], 50.0)
        self.assertIn("start", top)
        self.assertIn("end", top)

    def test_cloud_dispatcher(self):
        dispatcher = CloudDispatcher(repo="loobah18-arch/youtube-podcast-clipper")
        clip = {
            "start": 10.0,
            "end": 65.0,
            "duration": 55.0,
            "viral_title": "The Decades Rule of AI",
            "score": 92.0
        }
        spec = dispatcher.generate_clip_spec("https://www.youtube.com/watch?v=TEST1234", clip)
        cmd = dispatcher.get_dispatch_command(spec)
        self.assertIn("gh workflow run render_podcast_clips.yml", cmd)
        self.assertIn("--repo loobah18-arch/youtube-podcast-clipper", cmd)
        self.assertIn("start_time=\"10.0\"", cmd)

if __name__ == "__main__":
    unittest.main()
