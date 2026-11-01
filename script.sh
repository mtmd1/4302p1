#!/usr/bin/env zsh
set -euo pipefail

cd "${0:A:h}/script"

latexmk -pdf -interaction=nonstopmode -halt-on-error script.tex >/dev/null \
|| { echo "Build failed, see script/script.log" >&2; exit 1; }

printf 'Rendered to \e]8;;file://%s\e\\script/script.pdf\e]8;;\e\\\n' "$PWD/script.pdf"

read -r "ans?Open script in Firefox? (Y/n) " || ans=n
if [[ -z $ans || $ans == [Yy]* ]]; then
  firefox "$PWD/script.pdf" >/dev/null 2>&1 &!
fi
