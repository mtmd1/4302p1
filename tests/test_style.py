"""Scenes must use style.py's scales and colours, not literal numbers.

Checked statically, so no scene is rendered. A line ending in "# style: ignore"
is exempt. Scene-specific values belong in named module constants (RADIUS = 6),
which pass because the check only looks inside styled arguments.
"""

import ast
import json
import re
import sys
from pathlib import Path

import manim
import pytest

import render

# Arguments that must come from style.py's scales. 0 is allowed: buff=0 means
# "touching", not a size.
SCALED = {"font_size", "buff", "stroke_width", "run_time", "shift"}
COLOURED = {"color", "fill_color", "stroke_color", "background_color"}

STYLE = render.EXAMPLES / "style.py"
MANIM_COLOURS = {name for name, value in vars(manim).items() if isinstance(value, manim.ManimColor)}


def style_colours() -> set[str]:
    """Names style.py assigns a ManimColor to."""
    names = set()
    for node in ast.parse(STYLE.read_text()).body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            if getattr(node.value.func, "id", None) == "ManimColor":
                names |= {t.id for t in node.targets if isinstance(t, ast.Name)}
    return names


def magic_numbers(node: ast.AST) -> list[ast.Constant]:
    return [
        n
        for n in ast.walk(node)
        if isinstance(n, ast.Constant) and type(n.value) in (int, float) and n.value != 0
    ]


def is_technical(node: ast.AST) -> bool:
    """An interpolated value, or a string of nothing but numbers and units."""
    if isinstance(node, ast.JoinedStr):
        return any(isinstance(part, ast.FormattedValue) for part in node.values)
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and bool(re.fullmatch(r"[\d\s.,x×*/=+%-]*\d[\d\s.,x×*/=+%-]*( ?(ms|µs|FPS|fps|taps))?", node.value))
    )


def violations(source: str, allowed_colours: set[str]) -> list[str]:
    lines = source.splitlines()
    found = []

    def report(node, message):
        if not lines[node.lineno - 1].rstrip().endswith("# style: ignore"):
            found.append((node.lineno, f"line {node.lineno}: {message}"))

    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        if getattr(node.func, "id", None) in ("Text", "MarkupText") and node.args:
            first = node.args[0]
            if is_technical(first):
                report(first, "numbers and technical values belong in Mono, not Text")
        for keyword in node.keywords:
            if keyword.arg in SCALED:
                for number in magic_numbers(keyword.value):
                    report(number, f"{keyword.arg} uses {number.value!r}; use a style.py scale")
            elif keyword.arg in COLOURED:
                value = keyword.value
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    report(value, f"{keyword.arg}={value.value!r}; use a style.py colour")
                elif isinstance(value, ast.Name) and value.id in MANIM_COLOURS - allowed_colours:
                    report(value, f"{keyword.arg}={value.id} is a manim colour; use a style.py colour")
        if getattr(node.func, "attr", None) == "wait":
            for argument in node.args:
                for number in magic_numbers(argument):
                    report(number, f"wait({number.value!r}); use a style.py duration")
    return [message for _, message in sorted(found)]


@pytest.mark.parametrize("path", render._scene_files(), ids=lambda p: p.name)
def test_scenes_use_style(path: Path):
    found = violations(path.read_text(), style_colours())
    assert not found, f"{path.name} hardcodes style values:\n  " + "\n  ".join(found)


def cue_phrases(path: Path) -> list[tuple[int, str]]:
    return [
        (node.lineno, node.args[0].value)
        for node in ast.walk(ast.parse(path.read_text()))
        if isinstance(node, ast.Call)
        and getattr(node.func, "attr", None) == "cue"
        and node.args
        and isinstance(node.args[0], ast.Constant)
    ]


@pytest.mark.parametrize("path", render._scene_files(), ids=lambda p: p.name)
def test_cues_name_one_moment_in_the_script(path: Path):
    """A cue must be findable, and mean only one moment, or it can't be aligned."""
    sys.path.insert(0, str(render.EXAMPLES))
    import style

    words = style.spoken_words()
    timed = json.loads(style.CUES.read_text()) if style.CUES.exists() else {}
    for line, phrase in cue_phrases(path):
        if phrase in timed:
            continue  # Timed from the cut, whose wording can differ from the script
        found = style.find_phrase(phrase, words)
        assert len(found) == 1, f"{path.name} line {line}: {phrase!r} occurs {len(found)} times in the script"


# MARK: The checker itself


@pytest.mark.parametrize(
    "line",
    [
        "Text('a', font_size=28)",
        "x.next_to(y, DOWN, buff=0.4)",
        "self.play(FadeIn(a), run_time=0.6)",
        "self.play(FadeIn(a, shift=RIGHT * 0.3))",
        "self.play(a.animate.shift(UP), run_time=2 * SLOW)",
        "Arrow(a, b, stroke_width=3)",
        "self.wait(0.5)",
        "Text('a', color=YELLOW)",
        "Square(fill_color='#ff0000')",
        "Text(f'{ms:.2f} ms')",
        "Text('1681')",
        "Text('4.5 ms')",
    ],
)
def test_checker_flags(line):
    assert violations(line, style_colours()), line


@pytest.mark.parametrize(
    "line",
    [
        "Text('a', font_size=TEXT_SM, color=HIGHLIGHT)",
        "SurroundingRectangle(a, buff=0, stroke_width=STROKE_THIN, color=MUTED)",
        "self.play(FadeIn(a, shift=RIGHT * SPACE_2), run_time=travel(d))",
        "self.wait()",
        "self.wait(BEAT)",
        "Square(fill_color=magma(t))",
        "ImageMobject(p).scale(2)",
        "Text('a', font_size=99)  # style: ignore",
        "Text('Dual Kawase')",
        "Mono(f'{ms:.2f} ms')",
    ],
)
def test_checker_allows(line):
    assert not violations(line, style_colours()), line
