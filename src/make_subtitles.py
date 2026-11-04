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
"""Write subtitles for a cut, using the corrected transcript and forced alignment.

    uv run src/make_subtitles.py resolve/preview.mov

Writes <name>.srt beside the video. script/transcript.txt must match what the cut
says, so re-run this after any edit that changes the audio's timing.
"""

import re
import sys
from pathlib import Path

from align_cues import TRANSCRIPT, align, load_audio, normalise, start_at_sound

LINE = 42  # Characters per line, the usual limit for reading at a glance
LINES = 2
MIN_SECONDS = 1.0
HOLD = 0.2  # Seconds a subtitle stays after its last word, if there's room
GAP = 0.05  # Seconds kept clear between subtitles, so a change is visible
MIN_TAIL = 18  # Characters a sentence's last subtitle should have, so no word is stranded
BREAK_AFTER = re.compile(r"[,;:]$")

# Numbers are spelled in the transcript because that's what the aligner hears. On
# screen they read better as figures. Only unambiguous phrases are listed: most
# "one"s and "two"s are ordinary words.
FIGURES = [
    ("forty-one by forty-one", "41×41"),
    ("four point five milliseconds", "4.5 ms"),
    ("four point five", "4.5"),
    ("sixty frames", "60 frames"),
    ("seventeen hundred", "1700"),
    ("ten eighty p", "1080p"),
    ("three and a half billion", "3.5 billion"),
    ("four K", "4K"),
    ("fourteen billion", "14 billion"),
    ("eighty-two", "82"),
    ("zero point two", "0.2"),
    ("ninety-five percent", "95%"),
    ("two thousand and three", "2003"),
    ("two by two", "2×2"),
    ("twenty taps", "20 taps"),
    ("five point three", "5.3"),
    ("twenty fifteen", "2015"),
    ("twelve taps", "12 taps"),
    ("about nine", "about 9"),
    ("about eighteen", "about 18"),
    ("fifty microseconds", "50 microseconds"),
    ("reduced it to twenty", "reduced it to 20"),
    ("does it in twelve", "does it in 12"),
    ("twenty thousand", "20,000"),
]


def with_figures(words: list[dict]) -> list[dict]:
    """Merge number phrases into one on-screen word, spanning their spoken time."""
    patterns = [([normalise(w) for w in spoken.split()], shown) for spoken, shown in FIGURES]
    out, i = [], 0
    while i < len(words):
        for target, shown in patterns:
            found = [normalise(w["word"]) for w in words[i : i + len(target)]]
            if found == target:
                last = words[i + len(target) - 1]
                tail = re.search(r"[.,;:?!]*$", last["word"]).group()
                out.append({**words[i], "word": shown + tail, "end": last["end"]})
                i += len(target)
                break
        else:
            out.append(words[i])
            i += 1
    return out


def fit_lines(words: list[str]) -> list[str] | None:
    """Split words into at most LINES balanced lines, or None if they can't fit."""
    text = " ".join(words)
    if len(text) <= LINE:
        return [text]
    splits = [(" ".join(words[:k]), " ".join(words[k:])) for k in range(1, len(words))]
    fitting = [s for s in splits if max(map(len, s)) <= LINE]
    if not fitting:
        return None
    return list(min(fitting, key=lambda s: abs(len(s[0]) - len(s[1])) - (8 if BREAK_AFTER.search(s[0]) else 0)))


def group(sentence: list[dict]) -> list[list[dict]]:
    """Fill subtitles greedily, ending early at a comma once one is well filled."""
    cues, current = [], []
    for word in sentence:
        if current and fit_lines([w["word"] for w in current] + [word["word"]]) is None:
            # Move back to the last clause break, if that doesn't leave a scrap
            cut = next((k for k in range(len(current) - 1, len(current) // 2, -1) if BREAK_AFTER.search(current[k]["word"])), None)
            if cut is None:
                cues.append(current)
                current = []
            else:
                cues.append(current[: cut + 1])
                current = current[cut + 1 :]
        current.append(word)
    if current:
        cues.append(current)
    # Borrow from the subtitle before, rather than strand the end of a sentence
    while len(cues) > 1 and len(" ".join(w["word"] for w in cues[-1])) < MIN_TAIL and len(cues[-2]) > 3:
        cues[-1].insert(0, cues[-2].pop())
    return cues


def timestamp(seconds: float) -> str:
    ms = round(seconds * 1000)
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    video = Path(sys.argv[1])
    audio = load_audio(video)
    sentences = [line.split() for line in TRANSCRIPT.read_text().splitlines() if line.strip()]
    aligned = align(audio, sentences)
    start_at_sound(aligned, audio)

    cues, position = [], 0
    for sentence in sentences:
        cues += group(with_figures(aligned[position : position + len(sentence)]))
        position += len(sentence)

    blocks = []
    for n, cue in enumerate(cues):
        limit = cues[n + 1][0]["start"] - GAP if n + 1 < len(cues) else len(audio) / 16000
        start = cue[0]["start"]
        end = min(max(cue[-1]["end"] + HOLD, start + MIN_SECONDS), limit)
        text = "\n".join(fit_lines([w["word"] for w in cue]))
        blocks.append(f"{n + 1}\n{timestamp(start)} --> {timestamp(end)}\n{text}\n")

    srt = video.with_suffix(".srt")
    srt.write_text("\n".join(blocks), encoding="utf-8")
    print(f"{srt}: {len(blocks)} subtitles")


if __name__ == "__main__":
    main()
