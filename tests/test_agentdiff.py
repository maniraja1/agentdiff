import os
import tempfile
import unittest

from agentdiff import Trace, Recorder, diff_traces
from agentdiff.demo import good_agent, regressed_agent
from agentdiff.cli import main


class TraceTests(unittest.TestCase):
    def test_roundtrip(self):
        t = good_agent()
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.jsonl")
            t.save(p)
            t2 = Trace.load(p)
        self.assertEqual(len(t.steps), len(t2.steps))
        self.assertEqual(t.final_answer, t2.final_answer)

    def test_recorder_captures_errors(self):
        rec = Recorder()
        f = rec.wrap("boom", lambda: 1 / 0)
        with self.assertRaises(ZeroDivisionError):
            f()
        self.assertIn("ZeroDivisionError", rec.trace.steps[0].error)

    def test_bad_json(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "x.jsonl")
            with open(p, "w") as fh:
                fh.write("{nope\n")
            with self.assertRaises(ValueError):
                Trace.load(p)


class DiffTests(unittest.TestCase):
    def test_identical_passes(self):
        r = diff_traces(good_agent(), good_agent())
        self.assertTrue(r.passed)

    def test_regression_detected(self):
        r = diff_traces(good_agent(), regressed_agent())
        codes = {f.code for f in r.findings}
        self.assertFalse(r.passed)
        self.assertTrue({"ANSWER_CHANGED", "LOOP", "TOOL_ADDED"} <= codes)

    def test_strict_fails_on_warnings(self):
        from agentdiff import Trace, Step
        a = Trace(final_answer="x", steps=[Step("t", {"i": 1}, tokens=10)])
        b = Trace(final_answer="x", steps=[Step("t", {"i": 1}, tokens=10),
                                           Step("t", {"i": 2}, tokens=10)])
        self.assertTrue(diff_traces(a, b).passed)
        self.assertFalse(diff_traces(a, b, strict=True).passed)

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            main(["demo", "--dir", d])
            b, c = os.path.join(d, "baseline.jsonl"), os.path.join(d, "candidate.jsonl")
            self.assertEqual(main(["diff", b, b]), 0)
            self.assertEqual(main(["diff", b, c]), 1)
            self.assertEqual(main(["diff", b, "missing.jsonl"]), 2)


if __name__ == "__main__":
    unittest.main()
