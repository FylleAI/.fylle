# Video Ad 10s

A two-step workflow for a simple ten-second paid-social video:

1. `strategist` chooses text-to-video, image-to-video, or reference-to-video
   and produces a timed plan and generation prompt.
2. `video-producer` maps the plan to the runtime's video tool and generates one
   ten-second result.

The portable version deliberately avoids hard-coded vendor endpoint names.
The runtime must provide a `video_generation` capability that supports the
requested duration and relevant reference-image mode.

Source validation is covered by `commons/validate.py`; live video execution,
creative performance, and provider compatibility are not.
