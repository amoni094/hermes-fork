# Poll chart horizontal stretch with font compensation

Use this when a dashboard user wants the polling lines/points to span much more horizontal space without increasing chart height or making text look stretched.

## Pattern
- Push the inner plot start (`plotLeft`) further right if the user wants the first visible x-axis date/point indented away from the y-axis labels.
- Widen the effective SVG plotting space by increasing the viewBox width (for example `100 -> 250` for a 2.5x span request).
- Keep the chart inside a dedicated horizontal scroll viewport so the larger geometry is usable in a fixed-width card.
- If the user explicitly wants only the plotted geometry stretched, use `preserveAspectRatio="none"` and compensate font/stroke/dot sizes separately.
- Drive the compensation through CSS variables so the SVG can scale horizontally while text, axis strokes, grid strokes, and point markers retain roughly their prior visual size.

## Practical recipe
1. Add a width multiplier (for example `const chartWidthMultiplier = 2.5`).
2. Compute:
   - `visualScaleCompensation = 1 / chartWidthMultiplier`
   - `chartViewBoxWidth = 100 * chartWidthMultiplier`
3. Set a wider plot span, e.g.:
   - `plotLeft = 22`
   - `plotRight = chartViewBoxWidth - 6`
4. Render the SVG with:
   - `viewBox={\`0 0 ${chartViewBoxWidth} 100\`}`
   - `preserveAspectRatio="none"`
5. Pass CSS variables on the SVG root:
   - `--poll-chart-width-multiplier`
   - `--poll-chart-font-compensation`
6. In CSS:
   - make `.poll-chart` width/min-width scale by the width multiplier
   - wrap it in a `.poll-chart-viewport { overflow-x: auto; overflow-y: hidden; }`
   - multiply font sizes and stroke widths by the compensation factor
7. Keep x-axis labels anchored from the same `toPlotX(...)` positions as the dots after widening.

## Why this works
- The line geometry and dot spacing expand horizontally.
- Height remains fixed.
- Fonts do not visually balloon with the wider plot.
- The first date/point can be intentionally indented without decoupling labels from dots.

## Verification cues
- First x-axis date aligns with the first plotted point.
- Left padding is visibly larger than before.
- The graph requires horizontal scroll or otherwise occupies substantially more width.
- Fonts look the same size as before the stretch.
- Build/test still pass after the geometry change.
