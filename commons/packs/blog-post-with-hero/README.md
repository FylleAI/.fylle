# Blog Post with Hero Image

A three-step editorial workflow derived from a Fylle production pack and
generalized for public use:

1. `researcher` finds current, authoritative evidence and drafts an article.
2. `editor` improves structure and produces a visual direction brief.
3. `visual-producer` generates one contextual hero image and returns the final
   article plus the image result.

## Runtime requirements

- a `web_search` capability that returns source URLs;
- an `image_generation` capability that returns an image or image URL;
- runtime-provided `brand`, `audience`, `visual`, and `compliance` context when
  available.

The source graph and packages are validated by `commons/validate.py`. Tool
execution is runtime-dependent and is not covered by the repository's unit
tests.
