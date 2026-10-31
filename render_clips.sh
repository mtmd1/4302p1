#!/usr/bin/env zsh
# Render every manim scene in src/examples/ and transcode it to DNxHR HQ,
# which free DaVinci Resolve on Linux can decode (it can't read H.264).
# With -t, render on a transparent background and transcode to ProRes 4444,
# which keeps the alpha channel (DNxHR 4:2:2 would drop it).
#
#   ./render_clips.sh                      # all files, 1080p60
#   ./render_clips.sh -q l                 # all files, 480p15 preview
#   ./render_clips.sh -t src/examples/tap_counter.py
#   ./render_clips.sh src/examples/demo_dual_kawase.py ...
#
# Output: media/resolve/<Scene>.mov, or media/resolve/<Scene>_alpha.mov with -t
set -euo pipefail

cd "${0:A:h}"

quality=h
transparent=0
while getopts "q:t" opt; do
  case $opt in
    q) quality=$OPTARG ;;
    t) transparent=1 ;;
    *) echo "usage: $0 [-q l|m|h|p|k] [-t] [file.py ...]" >&2; exit 2 ;;
  esac
done
shift $((OPTIND - 1))

typeset -A qdirs=(l 480p15 m 720p30 h 1080p60 p 1440p60 k 2160p60)
qdir=${qdirs[$quality]:-}
[[ -n $qdir ]] || { echo "Unknown quality '$quality'" >&2; exit 2; }

# Only files that define a Scene, so helpers like sample.py are skipped
files=(${@:-src/examples/*.py(N)})
files=(${(f)"$(grep -lE '^class \w+\(.*Scene\)' $files || true)"})
(( ${#files} )) || { echo "No scenes found" >&2; exit 1; }

# manim writes .mp4 normally, and QuickTime Animation .mov with -t
if (( transparent )); then
  manim_flags=(-t) ext=mov suffix=_alpha
  codec=(-c:v prores_ks -profile:v 4444 -pix_fmt yuva444p10le -alpha_bits 16)
else
  manim_flags=() ext=mp4 suffix=
  codec=(-c:v dnxhd -profile:v dnxhr_hq -pix_fmt yuv422p)
fi

out=media/resolve
mkdir -p $out

for file in $files; do
  echo "==> Rendering $file ($qdir)"
  uv run manim -q$quality -a $manim_flags --progress_bar none $file >$out/render.log 2>&1 \
    || { tail -20 $out/render.log >&2; echo "Render failed: $file (full log: $out/render.log)" >&2; exit 1; }

  for src in media/videos/${file:t:r}/$qdir/*.$ext(N); do
    mov=$out/${src:t:r}$suffix.mov
    echo "    transcoding -> $mov"
    ffmpeg -loglevel error -y -i $src -map 0:v -map '0:a?' $codec -c:a pcm_s16le $mov
  done
done

printf 'Clips ready in \e]8;;file://%s\e\\%s/\e]8;;\e\\\n' "$PWD/$out" "$out"
