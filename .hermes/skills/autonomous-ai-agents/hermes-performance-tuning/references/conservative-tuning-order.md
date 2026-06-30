# Conservative Tuning Order

1. doctor/config-check first
2. inspect cron/watchdog noise
3. identify local auxiliary hotspots
4. trim prompt surface conservatively
5. tune compression/resume/context knobs
6. only then consider model-routing changes

Prefer reversible changes and verify each one before stacking more.
