---
name: thompson-ssl-fixture
description: >
  Use when exercising Thompson SSL validator rules. Fixture for
  validate-skill-ssl.py THOMPSON-1/6/8 checks.

ssl_scheduling:
  triggers:
    - User asks to validate Thompson SSL output families
  args:
    format: json
    dest: path
  preconditions:
    - Required binary is installed
    - name: dest_exists
      check: ["test", "-e", "$dest"]
      equals: true
  forall:
    over: dest
    checker: ["test", "-e", "$dest"]
    type_class: Path
  estimated_steps: 3
  output_family:
    - when:
        format: json
      produces:
        kind: application/json
        from: "$format"
    - when:
        format: text
      produces:
        kind: text/plain
        from: "$format"

ssl_structural:
  tools_used:
    - terminal
    - write_file
  subtasks:
    - Validate
    - Report

ssl_logical:
  side_effects:
    - name: write_file
    - name: dest
  resources:
    - name: dest
    - name: terminal
  risk_level: high
  invariants:
    - name: writes_only_dest
      ops: [write_file]
      law: write_file preserves dest
      witness: opaque
    - name: shell_is_scoped
      ops: [terminal]
      law: terminal preserves dest
      witness: transparent
---

# Thompson SSL fixture

Exercises output_family, executable preconditions, forall, and invariants.
