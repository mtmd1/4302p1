# Animation brief

The script is recorded and is being cut. This is the shared brief for every graphic in `script.tex`'s `% ANIM` comments. Build them in the style of the approved test clip, `src/examples/box_pixels.py`.

## Rules

**Files.** One file per graphic, one scene per file, in `src/examples/`, named as in the storyboard. Subclass `ClipScene`, or `Clip` + `MovingCameraScene` / `ThreeDScene`. Write only your own section's files. `style.py`, `components.py`, `pixels.py`, `blur.py`, `render.py`, `script/` and `assets/` are frozen: put a helper you need inside your scene file and mention it in your report. Don't commit.

**Read first.** `style.py` (start with its docstring), `components.py`, `box_pixels.py`, `pixels.py`, and the `blur.py` signatures.

**Look.** Match the test clip: dark and quiet, one graphic centred inside `FILL_WIDTH` x `FILL_HEIGHT`, nothing cut off at its edges once settled. Figtree (`Text`) for words, `Mono` for every number and technical value, `MathTex` for equations. A method's colour (`BOX`, `GAUSSIAN`, `KAWASE`, `DUAL_KAWASE`) marks that method everywhere. Clips render on transparent, so never draw a full-frame background.

**Clarity comes first.** Friends who tested faster versions lost track of what had turned into what. One thing changes at a time, in one direction, so the viewer sees what became what. Labels stay short, and text is `TEXT_XS` or larger. If a frame can't be read at a glance, simplify the graphic, and say so in your report. Showing less clearly beats showing all of it badly.

**Timing is flexible.** Only `self.cue(phrase)` decides when things happen relative to the narration. Call it just before the change that phrase triggers:
- Use the storyboard's phrases, in order. Add more if a graphic needs them; each must occur exactly once in the script's spoken text, and a test checks this.
- End each scene by cueing the **first phrase of the next graphic** in the storyboard, which holds the final state until then. The next graphic after `intro_montage` is "Today I will explain"; `outro_uses` ends on "By understanding the hardware".
- Never write narration timing into a scene: no constants for how long a line takes. Internal sequences can use `self.wait(BEAT)` and the like.
- The recording doesn't match the script word for word. A phrase is a label for a moment, so nothing on screen may depend on the exact wording.
- Change durations use the style scales (`QUICK`, `BEAT`, `MOVE`, `SLOW`, `travel()`, `count()`) with `rate_func=EASE`. They may be longer, never shorter. Scene-specific ones are named constants.
- If `cue` warns that a scene is running late, tell me which cue and by how much. Don't shorten changes to fix it; the real timings aren't known yet.

**Numbers.** On-screen figures come from `FIGURES` in `components.py`, not from live measurements, so they match the narration. Images come from real `blur.py` output on `photo()` from `sample.py`. Cache anything slow at module level. Use `LAMP` for any "square vs round" moment.

**Sources.** Anything from a source gets `credit()` on screen. Sound is added in Resolve, so scenes carry no audio.

## Checking your work

Render every scene and look at it. Don't assume it's right.

    uv run render -q l <name>
    uv run python /tmp/claude-1000/-home-mutant-4302p1/f107fd7c-7d7d-452f-8081-ced685ab3170/scratchpad/sheet.py media/resolve/<name>_<Scene>.mov <out.png> 9

The second argument to `sheet.py` is a frame count or comma-separated seconds. Write sheets to `/tmp/claude-1000/-home-mutant-4302p1/f107fd7c-7d7d-452f-8081-ced685ab3170/scratchpad/<section>/`, then Read them. Look for overlaps, cramped or clipped text, numbers colliding with cells, and anything leaving the frame. Stop rendering a scene once it's right. Render only at `-q l`.

Then run `uv run pytest -q tests -k "<your scene file stem>"` for each file. Other sections may be mid-edit, so ignore failures in their files.

**Report:** your files and scenes, what you cut or changed from the storyboard and why, any late cues, and anything you'd have wanted in the shared code. Keep it short.

## Storyboard
Quotes are cue phrases. Each graphic ends holding its final state.

### Intro: `intro_montage`
- Three tiles of `sands.jpg`, appearing one per cue, each with a short label naming the effect: frosted-glass panel over the town with `dual_kawase` behind it ("the frosted glass"); bright-pass plus blur added back so the lights glow ("bloom around"); town sharp with sky and beach blurred ("the background of a depth-of-field").

### Box (7)
- `box_pixels`: the approved clip, unchanged visually. Move to cues: "First, let's treat", "one per colour channel", "so we can look at just one".
- `box_average`: 6x6 greyscale `NumberGrid` beside an empty write buffer. A 3x3 `kernel_box` steps in reading order: cells light, values fly to a "sum / 9" readout, the result drops into the matching write cell. A few slow steps, then it speeds up. At a corner, out-of-bounds cells are hatched and the readout says "sum / 4". ("To blur it", "ignoring any positions", "Each result goes")
- `box_41`: the photo with a 41x41 outline drawn to scale. Hold on the unblurred photo with a loading spinner, then the blurred image snaps in, for the TADA added in Resolve. ("Let's try a 41 by 41")
- `box_budget`: "4.5 ms" readout, then `BudgetBar` "1 frame at 60 FPS = 16.6 ms" fills 27%. No GPU name on screen. ("the roughly 4.5 milliseconds")
- `box_taps`: one output pixel with lines fanning to every Nth pixel of its 41x41 window, "x 1681" label, flashing a few at a time then all together. The word "taps" appears on its cue with a small shooting-star flourish. ("every pixel still reads", "which GPU programmers call")
- `box_counter`: `TapCounter` starts: "taps per pixel: 1681". Below, an odometer rolls 1681 x 1920 x 1080 to 3,485,721,600; the frame outline grows to 4K and it rolls to 13,942,886,400. ("That's almost three and a half", "or 14 billion")
- `box_artifact`: zoom on `LAMP` in the box blur: a hard-edged square. Beside it, the same lamp with a disc blur computed in numpy, round and soft, labelled "simulated lens blur". ("You'll also notice")

### Gaussian (5)
- `gauss_weights`: small grid, 3x3 kernel of 1s, readout "sum / count". Offsets appear in cell corners, each 1 morphs into w(x, y), readout becomes "sum / sum of weights". ("Consider our box blur kernel", "pass each pixel's")
- `gauss_bell`: w(x, y) becomes the MathTex formula. A 3D bell rises from the kernel grid and cells take its heights in `magma`. ("For a gaussian blur")
- `gauss_sigma`: photo left, side panel right: 1D bell with the kernel as a fixed window [-r, r]. σ rises at r = 6: bell widens past the window, cut tails shaded `HIGHLIGHT`, remainder flattens, squares appear around lamps. Then the window grows to ±3σ, tails return, squares melt. ("This gives us a second parameter", "until boxes reappear", "To fix this")
- `gauss_compare`: wipe slider, box r = 20 left, Gaussian σ = 7 right, flat vs bell kernel heatmaps beneath. Then both zoom to `LAMP`: square vs round. ("At roughly the same kernel size")
- `gauss_readout`: "4.5 ms" under each half. `TapCounter` adds a Gaussian bar, also 1681. ("But it's just as slow")

### Separation (3)
- `sep_split`: e^(-x²-y²) identity. 3x3 kernel 1 2 1 / 2 4 2 / 1 2 1 splits into column x row. Then two buffers, ping and pong: photo in ping, horizontal-only result (`steps[0]`) in pong, final back in ping. ("it turns out that our kernels", "That means", "Instead of one pass")
- `sep_taps`: the 1681 bar splits into two 41 bars that stack into 82, "separated gaussian". "4.5 ms" rolls to "0.2 ms". 41² = 1681 → 2·41 = 82. "Identical" shown by a difference image going black or an "=" between the outputs. ("The output is exactly identical", "our taps per pixel drop")
- `sep_radius`: radius slider dragged up, 82 bar grows as 2(2r + 1), image blurs more, slider springs back to r = 20. ("That's 95 percent", "but the cost still grows")

### Kawase (8)
- `kawase_title`: `slot()` credited to the GDC deck and the gameplay video, for Resolve. ("In his 2003 GDC talk")
- `kawase_twice`: Gaussian photo, second pass sweeps across, blurrier. Box photo with `LAMP` circled: second pass softens the square into a round blob. ("What do you think", "What about a box blur", "the boxy artifacts are gone")
- `kawase_convolve`: left, 3x3 grids of 1s slide to fill a 5x5 grid 1 2 3 2 1 / 2 4 6 4 2 / 3 6 9 6 3 …, then a `magma` heatmap. Right, axes of the middle row, normalised: flat line becomes a triangle. Equation (I * W) * W = I * (W * W). Then it speeds up: 7x7, 9x9… triangle → hump → bell; a dashed true Gaussian overlays and matches. Hold there for the meme in Resolve. ("Convolution is associative", "Let's watch that happen", "And if we keep convolving")
- `kawase_bilinear`: four pixels with values, centres dotted, crosshair with (u, v). It drifts; lines to centres thicken with weight; readout interpolates. Then it snaps to the shared corner: all weights 0.25, the 2x2 lights as one, "1 tap". ("When a GPU looks up", "The most common method", "So, when we sample")
- `kawase_four`: 3x3 patch, four crosshairs at the centre pixel's corners, each lighting a 2x2 block translucently. Overlaps add; counts appear 1 2 1 / 2 4 2 / 1 2 1. Slides next to the triangle plot. ("Kawase takes four", "The centre ends up")
- `kawase_repeat`: same pass with no offset on the photo, pass counter racing to 57, blur barely creeping, taps climbing to 228. ("But repeat this as it is", "we'd need 57")
- `kawase_offsets`: five passes on the photo with an offset label 0, 1, 2, 2, 3, crosshairs stepping out along diagonals, gap pixels marked; gaps vanish because the image is already smeared. Inset: one big offset on the sharp photo (`blur.kawase(img, (8,))`) prints a ghost grid. Corner: buffers A and B swap read/write tags. ("So Kawase reaches further", "The gaps between them", "A common choice", "Swapping between two buffers")
- `kawase_taps`: 82 bar shrinks to 70 at σ 5.3, Kawase 20 grows beside it. 5·4 = 20 vs 70. ("Five passes of four taps", "Compared to a separated")

### Bjørge (7)
- `bjorge_lowpass`: `PixelView` zoom into the Kawase result: neighbours nearly identical; a "low-pass filter" label. ("Look closely at", "A blur is a low-pass")
- `bjorge_shimmer`: `downscale_upscale(steps=True)` shrinks then stretches: boxes back. Then a slow pan, naive beside `dual_kawase`: naive blocks crawl, other glides. Check it reads on the photo. ("So let's shrink the image", "Worse, when the scene moves")
- `bjorge_tiles`: source grid splits into hard 2x2 tiles, each flowing into one output pixel. Shift one pixel: every tile regroups, with a flash. ("Why? When we halve", "The blocks never overlap")
- `bjorge_diagonal`: four diagonal taps added one by one, each lighting a 2x2 straddling the tiles; hard borders become overlapping patches. ("So as we shrink", "No hard borders")
- `bjorge_up`: a 3D square pyramid from one bilinear tap; a field shows a faint diamond grid. Eight taps ring the pixel; pyramids round into a soft dome. ("And on the way up", "Instead, take eight taps")
- `bjorge_dual`: `DualKawasePyramid` rebuilt on the current style, with the two tap patterns inset. ("That's exactly what Marius", "Five taps going down", "He called it the dual filter")
- `bjorge_cost`: each level's cost stacks into one bar topping out near 12. Level count steps 4 to 5: σ 9 to 18, cost unmoved, "about 50 µs". ("Each downscale quarters", "And each extra level")

### Conclusion (2)
- `outro_counter`: `TapCounter` in full: 1681, 82, 20, 12, FPS under each, on one linear scale. The 27% budget bar shrinks to a sliver. The 12.3 sum appears on the FPS line. No GPU name, no slot-machine flourish (user's call). ("Our first naive box blur", "Separation took it", "Kawase took it", "And the Dual Kawase", "If my GPU did nothing")
- `outro_uses`: three `slot()`s credited to KWin, Android and DOUBLE-S.T.E.A.L. ("That is why this technique")
