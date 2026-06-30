# Poll chart compact axis labels

Use this when a polling chart is already geometrically correct but the x-axis feels cluttered.

Pattern
- Keep one shared x-position mapping for dots, line vertices, ticks, and labels.
- Reduce label payload before changing chart geometry.
- Format date labels as compact `dd/mm` strings.
- Shrink only the x-axis font slightly; do not scale the whole SVG or compensate fonts via transforms.
- Keep the label lane close to the baseline so the chart does not look disconnected from the axis.

Concrete implementation moves
- Add a small formatter helper that reuses the chart's existing date normalizer and emits `dd/mm`.
- Map axis labels from the source date to the formatted date only at render time; keep original source dates for ids/keys/data rows.
- Reduce `.poll-chart__label--x` font size independently from the shared y-axis label style.

Why
- The user asked for more legible, space-efficient axis dates without reintroducing distortion.
- Compact dates plus a small font reduction usually solve clutter without upsetting point alignment or chart proportions.

Pitfall
- Do not respond to x-axis clutter by widening or stretching the chart first. That often solves spacing by creating new distortion, drift, or point-visibility problems.
