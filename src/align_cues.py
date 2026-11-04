# /// script
# requires-python = "==3.12.*"
# dependencies = ["numpy", "soundfile", "torch==2.5.1", "torchaudio==2.5.1"]
#
# [[tool.uv.index]]
# name = "pytorch-cpu"
# url = "https://download.pytorch.org/whl/cpu"
# explicit = true
#
# [tool.uv.sources]
# torch = { index = "pytorch-cpu" }
# torchaudio = { index = "pytorch-cpu" }
# ///
"""Time every cue against a cut: force-align the transcript, then write cues.json.

    uv run src/align_cues.py resolve/cut-1.mov

Reads what was actually said from script/transcript.txt, one sentence per line,
and which words each cue means from script/cue_anchors.json. Writes:

    src/examples/cues.json    cue phrase -> seconds, which style.cue_time reads
    script/transcript.json    every word with its start, end and alignment score

After re-recording a line: edit transcript.txt to match, then run this on the new
cut. It has its own environment (torch), so the project doesn't depend on torch.
"""

import ast
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile
import torch
import torchaudio

ROOT = Path(__file__).resolve().parent.parent
TRANSCRIPT = ROOT / "script" / "transcript.txt"
ANCHORS = ROOT / "script" / "cue_anchors.json"
WORDS = ROOT / "script" / "transcript.json"
CUES = ROOT / "src" / "examples" / "cues.json"
SCENES = ROOT / "src" / "examples"

RATE = 16000
CHUNK = 30 * RATE  # The model runs in chunks, to stay well inside memory
CONTEXT = 2 * RATE  # Heard either side of a chunk, then discarded

# The noise gate leaves digital silence between phrases, and the aligner can spread
# a word's first letter across it. A word can't start until its audio does.
SILENCE_DB = -45
MIN_SHIFT_MS = 20

LOW_SCORE = 0.5  # Worth a listen, though numbers score low even when well placed

# How words sound, where their spelling doesn't say
SPOKEN = {
    "2d": "two dee",
    "bjørge": "byerge",
    "gdc": "gee dee see",
    "gpu": "gee pee you",
    "gpus": "gee pee yous",
    "k": "kay",
    "kde": "kay dee ee",
    "p": "pee",
    "siggraph": "sig graph",
    "x": "ex",
}


def normalise(word: str) -> str:
    return re.sub(r"[^\w'-]", "", word.lower().replace(".", ""))


def letters(word: str) -> list[str]:
    """The aligner's tokens for one written word: lowercase letters, one per spoken part."""
    key = normalise(word).replace("-", "")
    return [re.sub(r"[^a-z']", "", part) for part in SPOKEN.get(key, key).split()]


def load_audio(path: Path) -> np.ndarray:
    pcm = subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-map", "0:a:0", "-ac", "1", "-ar", str(RATE), "-f", "wav", "-"],
        capture_output=True,
        check=True,
    ).stdout
    import io

    audio, _ = soundfile.read(io.BytesIO(pcm), dtype="float32")
    return audio


def align(audio: np.ndarray, sentences: list[list[str]]) -> list[dict]:
    bundle = torchaudio.pipelines.MMS_FA
    model = bundle.get_model(with_star=True)
    samples = torch.from_numpy(audio)[None]
    total = samples.shape[1]
    chunks = []
    with torch.inference_mode():
        for start in range(0, total, CHUNK):
            lo, hi = max(0, start - CONTEXT), min(total, start + CHUNK + CONTEXT)
            emission, _ = model(samples[:, lo:hi])
            per_frame = (hi - lo) / emission.shape[1]
            chunks.append(emission[:, round((start - lo) / per_frame) : round((min(total, start + CHUNK) - lo) / per_frame)])
    emission = torch.cat(chunks, 1)
    seconds_per_frame = total / emission.shape[1] / RATE

    # A wildcard between sentences absorbs pauses, sound effects and breaths
    tokens, words = [], []
    for sentence in sentences:
        tokens.append("*")
        for word in sentence:
            parts = letters(word)
            words.append((word, len(parts)))
            tokens += parts
    tokens.append("*")
    spans = bundle.get_aligner()(emission[0], bundle.get_tokenizer()(tokens))
    spans = iter(span for span, token in zip(spans, tokens) if token != "*")

    aligned = []
    for word, parts in words:
        pieces = [piece for _ in range(parts) for piece in next(spans)]
        score = sum(p.score * (p.end - p.start) for p in pieces) / sum(p.end - p.start for p in pieces)
        aligned.append({
            "word": word,
            "start": pieces[0].start * seconds_per_frame,
            "end": pieces[-1].end * seconds_per_frame,
            "score": round(float(score), 3),
        })
    return aligned


def start_at_sound(aligned: list[dict], audio: np.ndarray):
    """Move each word's start past any silence at its beginning."""
    per_ms = RATE // 1000
    power = (audio[: len(audio) // per_ms * per_ms].reshape(-1, per_ms) ** 2).mean(1)
    loud = 10 * np.log10(np.maximum(power, 1e-14)) > SILENCE_DB
    for word in aligned:
        first, last = int(word["start"] * 1000), int(word["end"] * 1000)
        heard = np.flatnonzero(loud[first:last])
        if len(heard) and heard[0] > MIN_SHIFT_MS:
            word["start"] = (first + int(heard[0])) / 1000


def find_anchor(anchor: str, spoken: list[str]) -> int:
    target = [normalise(w) for w in anchor.split()]
    found = [i for i in range(len(spoken) - len(target) + 1) if spoken[i : i + len(target)] == target]
    if len(found) != 1:
        raise SystemExit(f"Anchor {anchor!r} occurs {len(found)} times in {TRANSCRIPT.name}; it must occur once")
    return found[0]


def scene_cues() -> set[str]:
    """Cue phrases written literally in the scenes. Cues from loops aren't seen here."""
    cues = set()
    for path in SCENES.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "cue" and node.args:
                if isinstance(node.args[0], ast.Constant):
                    cues.add(node.args[0].value)
    return cues


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    audio = load_audio(Path(sys.argv[1]))
    sentences = [line.split() for line in TRANSCRIPT.read_text().splitlines() if line.strip()]
    aligned = align(audio, sentences)
    start_at_sound(aligned, audio)
    for word in aligned:
        word["start"], word["end"] = round(word["start"], 3), round(word["end"], 3)
    WORDS.write_text(json.dumps(aligned, indent=0, ensure_ascii=False) + "\n")

    anchors = json.loads(ANCHORS.read_text())
    spoken = [normalise(word["word"]) for word in aligned]
    timed = sorted(((aligned[find_anchor(anchor, spoken)], phrase) for phrase, anchor in anchors.items()), key=lambda t: t[0]["start"])
    CUES.write_text(json.dumps({phrase: word["start"] for word, phrase in timed}, indent=2, ensure_ascii=False) + "\n")

    print(f"{len(aligned)} words over {len(audio) / RATE:.1f} s; {len(timed)} cues written to {CUES.relative_to(ROOT)}")
    for word, phrase in timed:
        if word["score"] < LOW_SCORE:
            print(f"  low score {word['score']:.2f} at {word['start']:7.2f} s: {phrase!r} (heard as {word['word']!r})")
    missing = scene_cues() - anchors.keys()
    if missing:
        print(f"Scenes use cues with no anchor, which will fall back to a rough estimate: {sorted(missing)}")


if __name__ == "__main__":
    main()
