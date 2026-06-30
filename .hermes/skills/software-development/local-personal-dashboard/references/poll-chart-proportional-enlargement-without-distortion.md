# Poll-chart proportional enlargement without distortion

Use this when a user wants a polling chart 'bigger' after earlier alignment fixes.

What went wrong in-session
- A 2.5x horizontal widening attempt used a larger SVG viewBox plus `preserveAspectRatio="none"` and CSS width tricks.
- Text/stroke compensation variables were added to keep labels looking normal.
- Result: axis text still felt stretched, most points became barely visible, and only a few dots were effectively legible.

Correct interpretation learned
- 'Make it 1.5x proportionately bigger' means enlarge the rendered chart and reopen the inner plot area, not globally stretch the SVG coordinate space.
- Keep one normal SVG coordinate system (for example `viewBox="0 0 100 100"`) so labels, ticks, dots, and lines all share stable geometry.

Reliable fix pattern
1. Keep x-axis labels inside the SVG and anchor them with the exact same `toPlotX(...)` positions as the dots.
2. Keep each plotted point as its own `<circle>` with a stable id, and connect them with a normal `<polyline>`.
3. If the chart needs to feel bigger, first increase the rendered chart height.
4. Then reopen the inner plot box modestly:
   - move `plotTop` up
   - move `plotBottom` down
   - reduce `plotLeft` slightly if safe
   - extend `plotRight` slightly
5. Keep font sizes and axis stroke widths literal rather than compensating for global stretch.
6. Use `vectorEffect="non-scaling-stroke"` on lines/dots if needed to preserve marker/line legibility.

Geometry invariants to re-check after each sizing pass
- all dots visible
- dots evenly spaced
- first/last dots line up with first/last date labels
- x-axis text sits on the baseline, not below in a separate HTML row
- y-axis labels remain readable and visually subordinate
- the line is simply connecting point-to-point, not visually distorted by global scaling

Failure smell
- If you need CSS custom properties just to counteract a widened viewBox so fonts do not look stretched, you are probably implementing the wrong kind of 'bigger'.
