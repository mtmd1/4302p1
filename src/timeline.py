"""Place the rendered clips on the cut, for DaVinci Resolve.

    uv run src/timeline.py

Each clip starts on its first cue, from the scene's source and cues.json, so run
align_cues.py on a new cut and the placements follow it. Trims come from the timeline
exported from Resolve (EDL): clips that butted there still butt, and a clip trimmed
short keeps its length. Clip lengths come from media/resolve/, at any size.
Writes:

    script/clip_timeline.csv    each clip's placement, for reference or by hand
    script/clips.fcpxml         the same as a timeline to import, linking each file by path

Not an EDL: those name only reels and timecodes, so Resolve conforms them to whatever
media is already in the pool, which is the greenscreen.

Each clip's opening pause is trimmed, so it starts on its first cue.
"""

import ast
import csv
import json
import re
import sys
from pathlib import Path
from xml.sax.saxutils import quoteattr

import av

ROOT = Path(__file__).resolve().parent.parent
CUES = ROOT / "src" / "examples" / "cues.json"
SCENES = ROOT / "src" / "examples"
CLIPS = ROOT / "media" / "resolve"
EDL = ROOT / "resolve" / "Timeline 1.edl"

FPS = 60
PAUSE = 1.0  # style.PAUSE; style.py imports manim, which this doesn't need
TIMELINE_START = 3600 * FPS  # The cut starts at 01:00:00:00

# The talk's order, which file names can't give
ORDER = """
intro_montage box_pixels box_average box_41 box_budget box_taps box_counter box_artifact
gauss_weights gauss_bell gauss_sigma gauss_compare gauss_readout
sep_split sep_taps sep_radius
kawase_title kawase_twice kawase_convolve kawase_chain kawase_bilinear kawase_four kawase_repeat kawase_offsets kawase_taps
bjorge_lowpass bjorge_shimmer bjorge_diagonal bjorge_up bjorge_dual bjorge_cost
outro_counter outro_uses
""".split()

# Scenes whose first cue sits in a loop, out of sight of the source parser
FIRST_CUE = {"intro_montage": "the frosted glass"}

# Scenes added since the EDL was exported, so they aren't among its events
NOT_IN_EDL = {"kawase_chain"}

# Clips that end ahead of a cue, as (cue, frames early). kawase_taps leaves the presenter
# alone once the sentence after it was cut, as it did when that sentence was there.
OUT = {"kawase_taps": ("Look closely at", 170)}


def timecode(frames: int) -> str:
    seconds, frame = divmod(frames, FPS)
    return f"{seconds // 3600:02d}:{seconds // 60 % 60:02d}:{seconds % 60:02d}:{frame:02d}"


def frames_at(code: str) -> int:
    hours, minutes, seconds, frame = map(int, code.split(":"))
    return (hours * 3600 + minutes * 60 + seconds) * FPS + frame


def edl_events() -> dict[str, tuple[int, int]]:
    """Each scene's (in, out) on the timeline. EDLs name no files here, so they go by order."""
    events = re.findall(r"^\d+\s+\S+\s+V\s+C\s+\S+ \S+ (\S+) (\S+)", EDL.read_text(), flags=re.M)
    stems = [stem for stem in ORDER if stem not in NOT_IN_EDL]
    if len(events) != len(stems):
        sys.exit(f"{EDL.name} has {len(events)} events; expected {len(stems)}")
    return {stem: (frames_at(start) - TIMELINE_START, frames_at(end) - TIMELINE_START) for stem, (start, end) in zip(stems, events)}


def first_cue(stem: str) -> str:
    if stem in FIRST_CUE:
        return FIRST_CUE[stem]
    calls = [
        (node.lineno, node.args[0].value)
        for node in ast.walk(ast.parse((SCENES / f"{stem}.py").read_text()))
        if isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "cue" and node.args and isinstance(node.args[0], ast.Constant)
    ]
    return min(calls)[1]


def probe(path: Path) -> dict:
    with av.open(str(path)) as container:
        stream = container.streams.video[0]
        return {"frames": stream.frames, "rate": stream.average_rate.numerator // stream.average_rate.denominator, "width": stream.width, "height": stream.height}


def duration(frames: int) -> str:
    return f"{frames}/{FPS}s"


def fcpxml(events: list[dict]) -> str:
    """A sequence at the cut's timecode: each clip in a spine, with gaps of presenter alone."""
    formats = {(1080, FPS): "r1"}
    for e in events:
        formats.setdefault((e["height"], e["rate"]), f"r{len(formats) + 1}")
    format_lines = "\n".join(
        f'    <format id="{name}" name="FFVideoFormat{height}p{rate}" frameDuration="1/{rate}s" width="{height * 16 // 9}" height="{height}"/>'
        for (height, rate), name in formats.items()
    )
    assets = "\n".join(
        f'    <asset id="a{n}" name={quoteattr(e["file"])} start="0s" duration="{e["frames"]}/{e["rate"]}s" hasVideo="1" '
        f'format="{formats[e["height"], e["rate"]]}" src={quoteattr((CLIPS / e["file"]).as_uri())}/>'
        for n, e in enumerate(events, 1)
    )
    spine, at = [], TIMELINE_START
    for n, e in enumerate(events, 1):
        place = TIMELINE_START + e["at"]
        if place > at:
            spine.append(f'          <gap name="Gap" offset="{duration(at)}" start="{duration(TIMELINE_START)}" duration="{duration(place - at)}"/>')
        spine.append(
            f'          <asset-clip name={quoteattr(e["file"])} ref="a{n}" offset="{duration(place)}" '
            f'start="{duration(e["source_in"])}" duration="{duration(e["length"])}" format="{formats[e["height"], e["rate"]]}" tcFormat="NDF"/>'
        )
        at = place + e["length"]
    total = at - TIMELINE_START
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fcpxml>
<fcpxml version="1.9">
  <resources>
{format_lines}
{assets}
  </resources>
  <library>
    <event name="blur clips">
      <project name="blur clips">
        <sequence format="r1" duration="{duration(total)}" tcStart="{duration(TIMELINE_START)}" tcFormat="NDF">
          <spine>
{chr(10).join(spine)}
          </spine>
        </sequence>
      </project>
    </event>
  </library>
</fcpxml>
"""


def main():
    cues = json.loads(CUES.read_text())
    trims = edl_events()
    pause = round(PAUSE * FPS)
    clips = []
    for stem in ORDER:
        found = sorted(CLIPS.glob(f"{stem}_*.mov"))
        if len(found) != 1:
            sys.exit(f"Expected one clip for {stem} in {CLIPS}, found {len(found)}")
        cue = first_cue(stem)
        clips.append({"stem": stem, "file": found[0].name, "cue": cue, "at": round(cues[cue] * FPS), **probe(found[0])})

    events = []
    for clip, following in zip(clips, [*clips[1:], None]):
        stem = clip["stem"]
        if stem in OUT:
            phrase, early = OUT[stem]
            end = round(cues[phrase] * FPS) - early
        elif stem in trims and (following is None or following["stem"] not in trims or trims[stem][1] != trims[following["stem"]][0]):
            end = clip["at"] + trims[stem][1] - trims[stem][0]
        else:
            end = following["at"]
        length = end - clip["at"]
        if pause + length > clip["frames"] * FPS // clip["rate"]:
            sys.exit(f"{clip['file']} is too short to reach {timecode(TIMELINE_START + end)}")
        events.append({**clip, "source_in": pause, "source_out": pause + length, "length": length})

    with open(ROOT / "script" / "clip_timeline.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["order", "clip_file", "place_at", "place_at_seconds", "source_in", "source_out", "length_seconds", "starts_on"])
        for n, event in enumerate(events, 1):
            writer.writerow([
                n, event["file"], timecode(TIMELINE_START + event["at"]), f"{event['at'] / FPS:.3f}",
                timecode(event["source_in"]), timecode(event["source_out"]), f"{event['length'] / FPS:.2f}", event["cue"],
            ])

    (ROOT / "script" / "clips.fcpxml").write_text(fcpxml(events))

    overlaps = [a["file"] for a, b in zip(events, events[1:]) if a["at"] + a["length"] > b["at"]]
    if overlaps:
        sys.exit(f"These clips overlap the next one: {overlaps}")
    gaps = [(a["file"], (b["at"] - a["at"] - a["length"]) / FPS) for a, b in zip(events, events[1:]) if a["at"] + a["length"] != b["at"]]
    print(f"{len(events)} clips placed; gaps of presenter alone: {gaps}")


if __name__ == "__main__":
    main()
