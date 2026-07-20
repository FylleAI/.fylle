# Static Ad Variants

A two-step paid-social workflow:

1. `strategist` designs four variants with explicit persuasion mechanisms,
   placements, compositions, and generation-ready briefs.
2. `image-producer` calls the runtime image capability once per variant and
   returns the real results and exact prompts.

The default is two square feed concepts and two vertical story/reel concepts.
The pack accepts runtime reference images but never infers their contents from
an URL alone.

Requires `image_generation`. Source validation is covered by
`commons/validate.py`; live generation and advertising performance are not.
