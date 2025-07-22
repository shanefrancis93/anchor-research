#!/usr/bin/env python3
"""
Batch runner for sycophancy-checker experiments.
Runs multiple scenarios across multiple models in parallel.
"""

import asyncio
import argparse
import sys
import logging
from pathlib import Path
import yaml
import pandas as pd
from datetime import datetime
import os
from typing import List, Dict, Any

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from runner import OpenAIDriver, AnthropicDriver, ConversationRunner
from runner.scenario_parser import ScenarioParser
from runner.utils import create_output_dir, estimate_scenario_cost
from evaluators import PushbackEvaluator, AnchorDriftEvaluator, EmbeddingDriver


def setup_logging(level: str = "INFO"):
    """Configure logging."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def load_config() -> Dict[str, Any]:
    """Load configuration files."""
    config_dir = Path(__file__).parent.parent / "config"
    
    with open(config_dir / "providers.yaml") as f:
        providers = yaml.safe_load(f)
    
    with open(config_dir / "settings.yaml") as f:
        settings = yaml.safe_load(f)
    
    return {"providers": providers, "settings": settings}


def create_driver(provider: str, model: str, config: Dict[str, Any]):
    """Create appropriate driver instance."""
    if provider == "openai":
        return OpenAIDriver(model=model)
    elif provider == "anthropic":
        return AnthropicDriver(model=model)
    else:
        raise ValueError(f"Unknown provider: {provider}")


async def run_model_scenarios(
    model_config: Dict[str, str],
    scenarios: List[Any],
    output_dir: Path,
    config: Dict[str, Any]
) -> pd.DataFrame:
    """Run all scenarios for a single model."""
    provider = model_config["provider"]
    model = model_config["model"]
    
    logger = logging.getLogger(__name__)
    logger.info(f"Running scenarios for {provider}/{model}")
    
    # Create driver
    driver = create_driver(provider, model, config)
    
    # Create evaluators
    evaluators = [PushbackEvaluator()]
    
    # Add embedding evaluator for OpenAI
    if provider == "openai":
        embedding_driver = EmbeddingDriver(driver.client)
        evaluators.append(AnchorDriftEvaluator(embedding_driver))
    else:
        evaluators.append(AnchorDriftEvaluator())
    
    # Run scenarios
    all_metrics = []
    
    for scenario in scenarios:
        logger.info(f"Running scenario: {scenario.name}")
        
        # Create runner
        runner_config = {
            **config["settings"],
            "model": model
        }
        runner = ConversationRunner(driver, output_dir, runner_config)
        
        # Run scenario
        try:
            states = await runner.run_scenario(scenario, evaluators)
            
            # Collect metrics
            for branch_id, state in states.items():
                for turn_metrics in state.metrics:
                    metric_row = {
                        "run_id": runner.run_id,
                        "model": model,
                        "provider": provider,
                        "scenario": scenario.name,
                        "branch": branch_id,
                        **turn_metrics
                    }
                    all_metrics.append(metric_row)
                    
        except Exception as e:
            logger.error(f"Error in scenario {scenario.name}: {e}")
    
    return pd.DataFrame(all_metrics)


async def main():
    """Main batch runner."""
    parser = argparse.ArgumentParser(description="Run sycophancy-checker experiments")
    parser.add_argument(
        "--scenarios", 
        default="scenarios",
        help="Path to scenarios directory"
    )
    parser.add_argument(
        "--models",
        nargs="+",
        help="Specific models to run (format: provider/model)"
    )
    parser.add_argument(
        "--output",
        default="outputs",
        help="Output directory"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level"
    )
    
    args = parser.parse_args()
    
    # Setup
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    # Load config
    config = load_config()
    
    # Load scenarios
    scenario_dir = Path(args.scenarios)
    if not scenario_dir.exists():
        logger.error(f"Scenario directory not found: {scenario_dir}")
        sys.exit(1)
    
    scenarios = ScenarioParser.load_all_scenarios(scenario_dir)
    if not scenarios:
        logger.error("No scenarios found")
        sys.exit(1)
    
    logger.info(f"Loaded {len(scenarios)} scenarios")
    
    # Determine models to run
    model_configs = []
    
    if args.models:
        # Parse specified models
        for model_spec in args.models:
            if "/" in model_spec:
                provider, model = model_spec.split("/", 1)
            else:
                logger.error(f"Invalid model format: {model_spec} (use provider/model)")
                sys.exit(1)
            model_configs.append({"provider": provider, "model": model})
    else:
        # Use default models from config
        for provider, pconfig in config["providers"].items():
            model_configs.append({
                "provider": provider,
                "model": pconfig["default_model"]
            })
    
    # Check cost estimate
    total_cost = 0.0
    cost_config = config["settings"]["cost_per_1k_tokens"]
    
    for mconfig in model_configs:
        model = mconfig["model"]
        for scenario in scenarios:
            total_cost += estimate_scenario_cost(scenario, [model], cost_config)
    
    budget = config["settings"]["budget_usd"]
    logger.info(f"Estimated cost: ${total_cost:.2f} (budget: ${budget:.2f})")
    
    if total_cost > budget:
        logger.error(f"Estimated cost exceeds budget!")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Create output directory
    output_base = Path(args.output)
    output_dir = await create_output_dir(output_base)
    logger.info(f"Output directory: {output_dir}")
    
    # Run experiments
    tasks = []
    for model_config in model_configs:
        tasks.append(
            run_model_scenarios(model_config, scenarios, output_dir, config)
        )
    
    results = await asyncio.gather(*tasks)
    
    # Combine results
    all_metrics = pd.concat(results, ignore_index=True)
    
    # Save metrics
    metrics_file = output_dir / "metrics.csv"
    all_metrics.to_csv(metrics_file, index=False)
    logger.info(f"Saved metrics to {metrics_file}")
    
    # Print summary
    print("\n=== Summary ===")
    print(f"Total turns evaluated: {len(all_metrics)}")
    print(f"Models tested: {', '.join(m['model'] for m in model_configs)}")
    print(f"Scenarios run: {len(scenarios)}")
    print(f"Output saved to: {output_dir}")


if __name__ == "__main__":
    asyncio.run(main())