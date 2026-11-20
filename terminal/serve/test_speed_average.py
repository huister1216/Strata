"""The run average of the speed cards (community patch: keinebenutzer/STRATA-average-patch, MIT, made against v0.1.55 c62d5e3a; ported by hand onto rc1).

serve/web/app.js (the Monitor tab's Decode and Prefill cards), serve/web/monitor.js and monitor.html (the API monitor page) and strata_cli/overview.py (the Terminal
Overview) show, when the server is idle, the token-weighted average of the run instead of the last request's speed. Live values stay live. This file runs the
browser code the way a page would (a few lines of node, no browser, no network) and checks that what was added is display only."""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

WEB = Path(__file__).resolve().parent / "web"
NODE = shutil.which("node")


def run_node(source: str) -> object:
    done = subprocess.run([NODE, "-e", source], capture_output=True, text=True, encoding="utf-8", timeout=60, check=True)   # node writes UTF-8; the locale code page (cp1252, cp932 ...) is not what it speaks
    return json.loads(done.stdout)


def function_source(text: str, name: str) -> str:
    """One top-level function of a browser script, by its opening line to its closing brace in column 0."""
    start = text.index(f"function {name}(")
    end = text.index("\n}\n", start) + 3
    return text[start:end]


def cards_block(text: str) -> str:
    """The lines of renderMonitor that make the Decode and Prefill cards."""
    start = text.index("  // the eight cards")
    return text[start:text.index('  spark("sp-speed"', start)]


@unittest.skipUnless(NODE, "node is needed to run the page's own code")
class MonitorTab(unittest.TestCase):
    """serve/web/app.js: the two cards, run with stand-ins for the page's helpers."""

    def cards(self, live, last, totals):
        block = cards_block((WEB / "app.js").read_text(encoding="utf-8"))
        script = ("const calls = []; const setMetric = (...a) => calls.push(a); const fmt = (n, d = 0) => Number(n).toFixed(d);\n"
                  f"function run(live, last, totals) {{\n{block}\n}}\nrun({json.dumps(live)}, {json.dumps(last)}, {json.dumps(totals)});\nconsole.log(JSON.stringify(calls));")
        script = script.replace("spark(", "(() => {})(")
        calls = run_node(script)
        return {c[0]: (c[1], c[3]) for c in calls}

    TOTALS = {"requests": 12, "prompt_tokens": 90000, "reused": 5000, "output_tokens": 40000, "prompt_ms": 120000.0, "decode_ms": 1000000.0}
    LAST = {"decode_tok_s": 50.5, "prompt_ms": 2000.0, "prompt_tokens": 1000, "reused": 0}

    def test_idle_shows_the_run_average_for_both_cards(self):
        cards = self.cards({"state": "idle"}, self.LAST, self.TOTALS)
        self.assertEqual(cards["speed"], ("40.0", "Decode · run average"))
        self.assertEqual(cards["prefill"], ("708", "Prefill · run average"), "(90000 - 5000 reused) tokens in 120 s")

    def test_live_values_stay_live(self):
        self.assertEqual(self.cards({"state": "generating", "tok_s": 31.5, "prefill_tok_s_mean": 600}, self.LAST, self.TOTALS)["speed"], ("31.5", "Decode now"))
        self.assertEqual(self.cards({"state": "generating", "tok_s": 31.5, "prefill_tok_s_mean": 600}, self.LAST, self.TOTALS)["prefill"], ("600", "Prefill this request"))
        self.assertEqual(self.cards({"state": "reading", "prefill_tok_s_mean": 820}, self.LAST, self.TOTALS)["prefill"], ("820", "Prefill now"))

    def test_without_totals_it_is_the_last_request_and_never_an_invented_zero(self):
        for totals in (None, {}, {"output_tokens": 0, "decode_ms": 0, "prompt_tokens": 0, "prompt_ms": 0}):
            cards = self.cards({"state": "idle"}, self.LAST, totals)
            self.assertEqual(cards["speed"], ("50.5", "Decode last request"), totals)
            self.assertEqual(cards["prefill"], ("500", "Prefill last request"), totals)
        cards = self.cards({"state": "idle"}, None, None)
        self.assertEqual(cards["speed"], (None, "Decode"))
        self.assertEqual(cards["prefill"], (None, "Prefill"))


@unittest.skipUnless(NODE, "node is needed to run the page's own code")
class MonitorPage(unittest.TestCase):
    def average(self, rows):
        source = function_source((WEB / "monitor.js").read_text(encoding="utf-8"), "averageDecodeSpeed")
        return run_node(f"{source}\nconsole.log(JSON.stringify(averageDecodeSpeed({json.dumps(rows)})));")

    def test_it_is_token_weighted_over_the_finished_requests(self):
        long_one = {"timings": {"predicted_n": 19511, "predicted_ms": 386000}}
        short_one = {"timings": {"predicted_n": 11, "predicted_ms": 410}}
        self.assertAlmostEqual(self.average([long_one, short_one]), (19511 + 11) / (386410 / 1000), places=6)
        self.assertGreater(self.average([long_one, short_one]), 50, "a plain mean of the two (about 38) would let the short one count as much as the long one")

    def test_requests_without_timings_or_with_one_token_are_left_out(self):
        self.assertIsNone(self.average([]))
        self.assertIsNone(self.average([{}, {"timings": None}, {"timings": {"predicted_n": 1, "predicted_ms": 10}}, {"timings": {"predicted_n": 5, "predicted_ms": 0}},
                                        {"timings": {"predicted_n": "9", "predicted_ms": 5}}]))
        self.assertEqual(self.average([{"timings": {"predicted_n": 100, "predicted_ms": 2000}}, {}]), 50)

    def test_the_card_says_what_it_shows(self):
        html = (WEB / "monitor.html").read_text(encoding="utf-8")
        self.assertIn("Average decode speed", html)
        self.assertIn("Run average", html)
        self.assertNotIn("Last decode speed", html)
        js = (WEB / "monitor.js").read_text(encoding="utf-8")
        self.assertIn('text("speed", speed(averageDecodeSpeed(records.filter(r => !active(r)))))', js)


class AddedCodeIsDisplayOnly(unittest.TestCase):
    """What the patch added reads numbers the page already has and writes text with textContent: no request, no eval, no markup, no address."""

    def test_nothing_but_arithmetic_and_text(self):
        pieces = [cards_block((WEB / "app.js").read_text(encoding="utf-8")), function_source((WEB / "monitor.js").read_text(encoding="utf-8"), "averageDecodeSpeed"),
                  (Path(__file__).resolve().parents[1] / "strata_cli" / "overview.py").read_text(encoding="utf-8")]
        pieces[2] = pieces[2][pieces[2].index("def run_average_speed"):pieces[2].index("def _cards")]
        forbidden = re.compile(r"\b(fetch|XMLHttpRequest|WebSocket|sendBeacon|eval|Function|import|require|innerHTML|insertAdjacentHTML|document\.write|"
                               r"subprocess|socket|urllib|requests|os\.system|open)\s*\(|https?://|\.src\s*=|new Image")
        for piece in pieces:
            self.assertIsNone(forbidden.search(piece), forbidden.search(piece) and forbidden.search(piece).group(0))
        self.assertIn("textContent", (WEB / "monitor.js").read_text(encoding="utf-8"))


def pcie_block():
    """The exact Monitor code that fills the PCIe card, kept in sync with app.js (no regex: the block starts at its
    own line and ends at the next card's)."""
    text = (WEB / "app.js").read_text(encoding="utf-8")
    start = text.index("  const gen = hw.gpu_pcie_gen_max")
    end = text.index('  setMetric("cpu"', start)
    return text[start:end].rstrip()


@unittest.skipUnless(NODE, "node is needed to run the page's own code")
class PcieCard(unittest.TestCase):
    """The card shows a live rate: NVML's traffic counter where the driver has one; where the amdgpu sysfs has
    none (the RX 6600 XT's complaint - a static Gen4 x16), the server's expert-streaming rate instead."""

    def card(self, hw, h=None):
        script = ("const calls = [], sparks = [];"
                  "const setMetric = (...a) => calls.push(a); const spark = (id, s) => sparks.push(s);"
                  "const fmt = (n, d = 0) => Number(n).toFixed(d);\n"
                  f"const hw = {json.dumps(hw)}; const h = {json.dumps(h or {})};\n"
                  "function draw() {\n" + pcie_block() + "\n}\ndraw();\n"
                  "console.log(JSON.stringify([calls, sparks]));")
        out = run_node(script)
        return out[0][0], out[1][0]

    def test_nvml_counter_wins(self):
        call, series = self.card({"gpu_pcie_gen_max": 4, "gpu_pcie_gen": 3, "gpu_pcie_width": 16,
                                  "gpu_pcie_rx_mb": 219.0, "gpu_experts_mb": 12.0},
                                 {"gpu_pcie_rx_mb": [5, 9], "gpu_experts_mb": [1, 2]})
        self.assertEqual((call[1], call[2]), ("Gen4", "x16"))
        self.assertIn("to GPU 219 MB/s", call[3])
        self.assertIn("idle Gen3", call[3])
        self.assertEqual(series, [5, 9])

    def test_amd_falls_back_to_the_expert_rate(self):
        call, series = self.card({"gpu_pcie_gen": 4, "gpu_pcie_width": 8, "gpu_pcie_rx_mb": None,
                                  "gpu_experts_mb": 5.67},
                                 {"gpu_pcie_rx_mb": [None, None], "gpu_experts_mb": [1.2, 5.67]})
        self.assertEqual((call[1], call[2]), ("Gen4", "x8"))
        self.assertIn("experts → GPU 5.7 MB/s", call[3])
        self.assertEqual(series, [1.2, 5.67])

    def test_no_counter_and_no_traffic_shows_no_rate(self):
        call, series = self.card({"gpu_pcie_gen_max": 3, "gpu_pcie_width": 8, "gpu_pcie_rx_mb": None,
                                  "gpu_experts_mb": None})
        self.assertEqual(call[3], "")
        self.assertIsNone(series)


if __name__ == "__main__":
    unittest.main()
