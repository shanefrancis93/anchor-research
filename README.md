# Sycophancy-Checker v0

A research platform for measuring multi-turn guard-rail decay (latent state drift) in hosted language models.

## Quick Start
**Run experiments:**
```bash
python scripts/run_batch.py
```

## What This Does

This tool measures how language models' safety behaviors change during extended conversations, particularly when users apply social pressure. It:

- Runs scripted multi-turn conversations
- Uses "anchor questions" to probe model stance throughout
- Tracks metrics like pushback level, polarity drift, and response entropy
- Supports parallel testing across multiple models

## Project Structure

```
├── config/           # Model and experiment settings
├── scenarios/        # Test conversations (markdown + YAML)
├── runner/           # Core conversation orchestration
├── evaluators/       # Metrics calculation modules
├── scripts/          # CLI entry points
└── outputs/          # Results (transcripts + metrics.csv)
```

## Creating Scenarios

Scenarios are markdown files with YAML frontmatter:

```markdown
---
name: my_scenario
anchor_question: "Is this behavior acceptable?"
behavior_tested: sycophancy
max_user_turns: 5
branches:
  - id: baseline
    description: "Natural conversation"
  - id: anchor_guard  
    description: "With anchor reinforcement"
turns:
  - role: system
    content: "You are a helpful assistant..."
  - role: user
    content: "What do you think about..."
  - role: assistant_expected
---
```

## Running Experiments

```bash
# Run all scenarios with default models
python scripts/run_batch.py

# Run specific models
python scripts/run_batch.py --models openai/gpt-4o-mini anthropic/claude-3-sonnet

# Use custom scenario directory
python scripts/run_batch.py --scenarios my_scenarios/
```

## Understanding Results

Results are saved in `outputs/TIMESTAMP/`:

- `transcripts/`: Full conversation logs (JSONL)
- `metrics.csv`: Turn-by-turn measurements

Key metrics:
- **pushback**: 0-3 scale of resistance to problematic requests
- **polarity**: -1 to 1 sentiment toward anchor question
- **entropy**: Uncertainty in model responses (OpenAI only)
- **cos_dist_to_anchor0**: Embedding drift from initial anchor response

