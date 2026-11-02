#!/bin/bash
# OFL fonts for the UI direction mockups (google/fonts and Departure Mono's own repo).
set -e
cd "$(dirname "$0")"; mkdir -p fonts; cd fonts
G=https://raw.githubusercontent.com/google/fonts/main/ofl
get() { [ -s "$2" ] || curl -fsSL --retry 3 -o "$2" "$1" && echo "ok $2 $(stat -c %s "$2")"; }
get "$G/jersey15/Jersey15-Regular.ttf" Jersey15.ttf
get "$G/jersey25/Jersey25-Regular.ttf" Jersey25.ttf
get "$G/barlowcondensed/BarlowCondensed-Medium.ttf" BarlowCondensed-Medium.ttf
get "$G/barlowcondensed/BarlowCondensed-SemiBold.ttf" BarlowCondensed-SemiBold.ttf
get "$G/barlowcondensed/BarlowCondensed-Bold.ttf" BarlowCondensed-Bold.ttf
get "$G/atkinsonhyperlegiblenext/AtkinsonHyperlegibleNext%5Bwght%5D.ttf" AtkinsonNext.ttf
get "$G/atkinsonhyperlegiblemono/AtkinsonHyperlegibleMono%5Bwght%5D.ttf" AtkinsonMono.ttf
if [ ! -s DepartureMono.otf ]; then
  url=$(curl -fsSL https://api.github.com/repos/rektdeckard/departure-mono/releases/latest | grep -o '"browser_download_url": *"[^"]*\.zip"' | head -1 | cut -d'"' -f4)
  echo "departure: $url"; curl -fsSL -o dm.zip "$url" && python3 -c "import zipfile,sys; z=zipfile.ZipFile('dm.zip'); n=[x for x in z.namelist() if x.lower().endswith(('departuremono-regular.otf','departuremono-regular.ttf'))]; print(n); open('DepartureMono'+n[0][-4:],'wb').write(z.read(n[0]))"
fi
ls -la
