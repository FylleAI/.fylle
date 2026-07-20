# Social Post with Visuals

A two-step workflow generalized from an internal three-agent pack:

1. `copywriter` produces feed and story copy plus two visual briefs.
2. `visual-producer` generates one square and one vertical visual and returns
   the complete deliverable.

The public version removes the old assumption that a runtime calls image tools
automatically. Tool ownership and the number of expected calls are explicit.

Requires an `image_generation` capability. Source validation is covered by
`commons/validate.py`; live image execution is runtime-dependent.
