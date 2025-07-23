# Anchor Research: Active Development Guide

## ⚠️ PROJECT UNDER ACTIVE CONSTRUCTION

This codebase is being actively developed. Multiple LLMs may be working on different components simultaneously. This document serves as the coordination point.

## Current State (Last Updated: 2025-07-22)

### ✅ Completed Components
- Basic folder structure created
- Config files (providers.yaml, settings.yaml) 
- Driver interfaces (OpenAI, Anthropic) - **BASIC IMPLEMENTATION ONLY**
- Scenario parser for markdown files
- Core runner with forking logic
- Basic evaluators (pushback, anchor drift)
- CLI batch runner script
- One example scenario (infidelity_conflict.md)

### 🚧 Needs Immediate Work
1. **Error handling** - Current implementations have minimal error recovery
2. **Tests** - Zero test coverage currently
3. **Logging** - Basic logging setup but needs improvement
4. **Cost tracking** - Estimation exists but no real-time tracking

### 🔴 Not Started
- GitHub Actions CI/CD
- Analysis notebooks
- Meta-model evaluators
- Additional scenarios
- Documentation beyond README

## Core Architecture (DO NOT CHANGE WITHOUT DISCUSSION)

### The Big Idea
We're documenting observable behavioral shifts in LLMs during multi-turn conversations. By asking the same anchor questions multiple times at the same conversation point, we can see if and how responses cluster differently as conversations progress.

### What We're Measuring
- **Behavioral consistency**: Do models give similar answers to the same question?
- **Cultural value shifts**: How do responses reflect changing implicit values?
- **Observable decay patterns**: Flattery over helpfulness, abandoning adversarial stances, etc.
- **NOT claiming to measure internal states**: We observe outputs, not mechanisms

### Critical Invariants
1. **Baseline conversations NEVER see anchor content in their future**
2. **All model calls must be async** 
3. **Scenarios use Markdown + YAML frontmatter**
4. **Results go to outputs/TIMESTAMP/ folders**
5. **Multiple anchor probes at same point for clustering**

## If You're Building Components

### Working on Drivers (runner/*_driver.py)
```python
# YOU MUST implement these methods:
async def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
    # Returns: {"role": "assistant", "content": str, "tokens": int, "logprobs": Optional}
    
def estimate_tokens(self, messages: List[Dict[str, str]]) -> int:
    # Returns: estimated token count
```

Current issues to fix:
- No retry logic for rate limits
- No timeout handling
- Token estimation for Anthropic is very rough

### Working on Evaluators (evaluators/*.py)
```python
# YOU MUST implement:
async def evaluate(self, primary_response: Dict, anchor_response: Optional[Dict], **kwargs) -> Dict[str, Any]:
    # Returns: Dictionary of metrics to add to CSV
```

Current issues:
- Pushback detection is pure regex (needs ML approach)
- Polarity calculation is keyword-based (too simple)
- No unit tests for metric accuracy

### Working on Scenarios (scenarios/*.md)
Required YAML fields:
```yaml
name: unique_identifier
anchor_question: "Neutral probe question?"
behavior_tested: what_we're_measuring
turns: [...]  # List of conversation turns
```

Needed scenarios:
- Financial advice (pushing risky investments)
- Medical advice (promoting unproven treatments)  
- Legal advice (encouraging illegal actions)
- Academic integrity (justifying plagiarism)

### Working on the Runner (runner/core.py)
DO NOT MODIFY the forking logic without careful consideration. The current flow:
1. Each turn processed sequentially
2. Branches processed in parallel
3. Anchor probes are transient (asked but not stored in history)
4. Only anchor_guard branch appends anchor Q&A to history

Known issues:
- No graceful handling of partial failures
- Memory usage grows with long conversations
- No checkpointing for resume capability

## File Ownership / Coordination

To avoid conflicts, claim files before major edits:

| Component | Status | Owner | Notes |
|-----------|---------|--------|--------|
| runner/openai_driver.py | Needs retry logic | - | Add exponential backoff |
| runner/anthropic_driver.py | Needs better token counting | - | Use actual tokenizer |
| evaluators/pushback.py | Needs ML version | - | Keep heuristic as fallback |
| evaluators/anchor_drift.py | Needs embedding caching | - | Currently re-embeds everything |
| scripts/run_batch.py | Needs progress bar | - | Users can't see progress |
| tests/* | EMPTY | - | Start with scenario parser tests |

## Integration Points

### Adding a New Model Provider
1. Create `runner/[provider]_driver.py`
2. Implement `ChatDriver` protocol
3. Add to `config/providers.yaml`
4. Update `create_driver()` in `scripts/run_batch.py`
5. Add cost config to `settings.yaml`

### Adding a New Evaluator
1. Create `evaluators/[metric].py`
2. Implement evaluation method
3. Import in `evaluators/__init__.py`
4. Add to evaluator list in `run_batch.py`

### Adding a New Scenario
1. Create `scenarios/[name].md`
2. Follow existing format (see infidelity_conflict.md)
3. Test with: `python scripts/run_batch.py --scenarios scenarios/[name].md`

## Current Blockers & Decisions Needed

1. **Anchor Question Design** - What cultural values do we want to probe?
2. **Response Clustering** - How to group qualitatively similar responses?
3. **Multiple Probe Strategy** - How many times to ask same anchor?
4. **Observable Behaviors** - Which specific decay types to document?
5. **Qualitative Analysis Tools** - Need better than keyword matching

## Testing Your Changes

Before committing:
```bash
# Minimal smoke test (no API calls)
python -c "from runner import OpenAIDriver, AnthropicDriver"
python -c "from runner.scenario_parser import ScenarioParser"

# Parse scenario test
python -c "from runner.scenario_parser import ScenarioParser; from pathlib import Path; ScenarioParser.parse_file(Path('scenarios/infidelity_conflict.md'))"

# Full integration test (requires API keys)
python scripts/run_batch.py --models openai/gpt-4o-mini --scenarios scenarios/infidelity_conflict.md
```

## Debugging Tips

1. **Enable debug logging**: `--log-level DEBUG`
2. **Check outputs folder**: Full transcripts in JSONL format
3. **Common errors**:
   - Missing API keys: Check .env file
   - Import errors: Check PYTHONPATH or run from repo root
   - YAML errors: Validate scenario frontmatter

## Communication Protocol

Since we can't directly communicate:
1. Update this file's "Current State" section when completing work
2. Add TODO comments in code for specific issues
3. Create GitHub issues for major architectural decisions
4. Use descriptive commit messages: "Fix: Add retry logic to OpenAI driver"

## Remember

- Keep core implementation under 1000 LOC
- Maintain backwards compatibility with existing scenarios
- Document any new dependencies in requirements.txt
- This is research code - clarity > cleverness