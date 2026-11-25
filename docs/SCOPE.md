# Scope and safe operation

This toolset sends real traffic to whatever target you give it. Use it only against assets you own or have explicit written permission to test. Everything below is general good practice, not tied to any one program.

## Before a run

- Confirm the target is in scope and that you have written authorization.
- Keep one target per run and a separate output dir per target, so traffic for one job never bleeds into another.
- Default to ports 80 and 443 on web targets. Widen only when you are allowed to.
- For host targets, pin hostnames to the IP you are allowed to test.

## Rate and conduct

- Start low. The defaults are 4 threads, at least 0.5 s delay and a 5 req/s cap. Raise only when the target's rules allow and the target can cope.
- Test the real request rate on a box you own before pointing a stage at an engagement.
- Know every payload you send. Avoid blind spraying.
- Avoid denial of service style checks and any test that could modify or destroy data.
- Prefer minimal proof of concept over anything disruptive.

## Data handling

- Treat all output as confidential. The `output/` dir is git ignored for that reason.
- Do not commit credentials or anything recovered from a target to this repo.
