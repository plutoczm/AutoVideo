# AutoVideo System Architecture

## Overview

AutoVideo is a human-in-the-loop AIGC video production workflow. It separates planning, generation, review, and rendering stages so expensive media generation can be controlled and resumed.

## Architecture

```text
User
 |
 v
Gradio Creator Review UI
 |
 v
Workflow Orchestrator
 |
 +----------------+
 |                |
 v                v
Planner Agent   Media Agents
 |                |
 v                +----------------+
Story/Scene      | Image Provider |
Planning         | Video Provider |
                 | TTS Provider   |
                 +----------------+
 |
 v
Project Store
 |
 v
FFmpeg Composer
 |
 v
Final 9:16 Video
```

## Core Design Principles

### Provider Abstraction

LLM and media providers are isolated behind adapters. New providers can be added without changing the workflow layer.

### Human-in-the-loop Quality Control

The pipeline supports candidate generation and approval checkpoints before expensive video rendering.

### Stateful Generation

Each episode stores intermediate artifacts:

- storyboard
- character references
- keyframes
- motion candidates
- audio assets
- final renders

This enables partial regeneration instead of restarting the whole pipeline.

## Future Engineering Improvements

- workflow state machine persistence
- automated generation quality evaluation
- async task queue for long-running generation jobs
- Docker based deployment
