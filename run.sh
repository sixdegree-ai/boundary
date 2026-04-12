#!/usr/bin/env bash
uv run boundary tool-overload run \
  --run-id 551c14cb3f6d \
  -p grok-4-1-fast-reasoning \
  -p claude-haiku -p gpt-5.4-mini \
  -t 25,50,75,100,150 \
  -n 1 \
  -l 60 \
  -m random
