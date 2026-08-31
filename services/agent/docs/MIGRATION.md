# Agent migration decisions

Primary source: `ElevatorAI-Sunybot-win11/ElevatorAI-Sunybot-v2/backend` (Apr 22 snapshot).

`ELEVATOR_AI_AGENT` and the standalone `ElevatorAI-Sunybot-v2` snapshot are earlier near-duplicates. Their source repositories remain untouched. Duplicate `.save`, `.bak`, generated C files, virtual environments, caches, legacy GUI and binary extensions were intentionally excluded from this clean component repository.
