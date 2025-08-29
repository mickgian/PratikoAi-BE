# file: test_seq_move_is_not_the_fix.py
# Run with: python test_seq_move_is_not_the_fix.py
# (or paste into a Claude Code REPL)

import hashlib

def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]

class FakeStreamer:
    """
    Minimal stand-in for the BE streaming processor *before* real dedup is fixed.
    - _compute_delta() simulates a flawed 'accumulated vs new' logic that can replay head.
    - Two variants of seq handling are tested:
        A) seq increment in format_sse_frame (bad accounting)
        B) seq increment only when a new delta is emitted (the proposed "fix")
    This test shows both still EMIT the same duplicate content payload.
    """

    def __init__(self, seq_in_format: bool):
        self.acc_html = ""
        self.seq_in_format = seq_in_format
        self.seq = 0
        self.emitted = []  # list of dict frames {seq, sha1, content, done}

    # --- flawed delta calc (stand-in for bug) ----------------------------------
    def _compute_delta(self, normalized_html: str) -> str:
        """
        Simulate the bug: if the new buffer contains a 'second start',
        the logic sometimes returns a replay of the head instead of trimming it.
        Specifically, when '### 1.' reappears, we leak it to delta.
        """
        if not self.acc_html:
            return normalized_html

        # Classic replay case: new buffer contains the whole old prefix + restart
        if self.acc_html and normalized_html.startswith(self.acc_html):
            tail = normalized_html[len(self.acc_html):]
            # BUG: fails to trim restart; passes tail as-is
            return tail

        # Fallback: just return everything (buggy discontinuity path)
        return normalized_html

    # --- two seq policies ------------------------------------------------------
    def format_sse_frame(self, content=None, done=False):
        # A) BAD: seq increments even when formatting (old behavior)
        if self.seq_in_format:
            self.seq += 1
        frame = {"seq": self.seq if self.seq_in_format else self.seq, "content": content, "done": done}
        if content:
            frame["sha1"] = sha1(content)
        return frame

    def _emit_delta(self, delta: str):
        if not self.seq_in_format:
            # B) "Fix": seq increments ONLY on actual emission (new delta)
            self.seq += 1
        frame = {"seq": self.seq, "content": delta, "done": False, "sha1": sha1(delta)}
        self.emitted.append(frame)

    # --- public API ------------------------------------------------------------
    def process_chunk(self, raw_chunk: str):
        # (Pretend) normalize to HTML (here just identity to keep test focused)
        normalized_html = raw_chunk
        delta = self._compute_delta(normalized_html)
        if delta:
            # update acc to full buffer (like BE that recomputes from RAW)
            self.acc_html = normalized_html
            self._emit_delta(delta)

    def done(self):
        # Final frame (no extra content)
        self.emitted.append(self.format_sse_frame(done=True))

# --- Test Input ---------------------------------------------------------------
# Simulate a normal stream until end, then a provider "second start" replay.
S1 = "<h3>1. Definizione</h3>\n<p>Intro...</p>"
S2 = "<h3>2. Normativa</h3>\n<p>Legge 190/2014...</p>"
S3 = "<h3>3. Aspetti</h3>\n<p>Coefficiente...</p>"
S4 = "<h3>4. Esempi</h3>\n<p>Esempio 1...</p>"
S5 = "<h3>5. Scadenze</h3>\n<p>Dichiarazione...</p>"

# "Second start" frame arrives after S5, and includes a replay of the beginning (S1,S2)
# followed by some fresh text (FRESH).
FRESH = "<p>In sintesi... [nuovo testo]</p>"
SECOND_START = S1 + S2 + FRESH

def run_case(seq_in_format: bool):
    f = FakeStreamer(seq_in_format=seq_in_format)

    # normal progression (accumulate)
    f.process_chunk(S1)
    f.process_chunk(S1+S2)
    f.process_chunk(S1+S2+S3)
    f.process_chunk(S1+S2+S3+S4)
    f.process_chunk(S1+S2+S3+S4+S5)

    # provider glitch: restarts from the top & appends new text
    f.process_chunk(S1+S2+FRESH)   # NOTE: shorter than full, but restarts from head

    f.done()
    return f.emitted

def show(label, emitted):
    print(f"\n=== {label} ===")
    for e in emitted:
        if e.get("done"):
            print(f"DONE seq={e['seq']}")
        else:
            print(f"EMIT seq={e['seq']} sha={e['sha1']} len={len(e['content'])} prev={e['content'][:40]!r}")

# --- Execute two variants -----------------------------------------------------
emitted_A = run_case(seq_in_format=True)   # old: seq++ in format_sse_frame
emitted_B = run_case(seq_in_format=False)  # "fix": seq++ only on emission

show("A) seq++ in format() [old]", emitted_A)
show("B) seq++ on emission [proposed]", emitted_B)

# --- Assertions that prove the point -----------------------------------------
def payloads(emitted):
    return [e["content"] for e in emitted if not e.get("done")]

pay_A = payloads(emitted_A)
pay_B = payloads(emitted_B)

# The last emitted payload is the tail of SECOND_START = S1+S2+FRESH, which (buggily) includes the replay
# of S1+S2, i.e., duplication leaked into FE bubble. This happens in BOTH variants.
assert pay_A[-1].startswith(S1), "A: Expected duplicate replay (S1) present in last payload"
assert pay_A[-1].find(S2) > 0,    "A: Expected duplicate replay (S2) present in last payload"
assert FRESH in pay_A[-1],        "A: Expected fresh text present alongside replay"

assert pay_B[-1].startswith(S1), "B: Expected duplicate replay (S1) present in last payload"
assert pay_B[-1].find(S2) > 0,   "B: Expected duplicate replay (S2) present in last payload"
assert FRESH in pay_B[-1],       "B: Expected fresh text present alongside replay"

print("\n✅ TEST PASS: Duplicate content leaks into the emitted payload in BOTH cases.")
print("   Moving seq increment changes only numbering, not the duplicate payload itself.")