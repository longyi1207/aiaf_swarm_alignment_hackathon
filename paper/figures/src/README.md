`fig1_scenario.html` is the source of Figure 1 (hand-written SVG). Render it with headless Chrome:

    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --hide-scrollbars \
      --force-device-scale-factor=2.5 --window-size=1300,660 \
      --screenshot="$PWD/paper/figures/fig1_scenario.png" "file://$PWD/paper/figures/src/fig1_scenario.html"
