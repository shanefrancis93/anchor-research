"""
Scenario loading utilities for anchor research tool.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List

def load_scenario(scenario_path: Path) -> Dict[str, Any]:
    """
    Load a scenario from a markdown file with YAML frontmatter.
    
    Args:
        scenario_path: Path to the scenario markdown file
        
    Returns:
        Dictionary containing scenario configuration
    """
    if not scenario_path.exists():
        raise FileNotFoundError(f"Scenario file not found: {scenario_path}")
    
    content = scenario_path.read_text(encoding='utf-8')
    
    # Split frontmatter and content
    if not content.startswith('---'):
        raise ValueError(f"Scenario file must start with YAML frontmatter: {scenario_path}")
    
    parts = content.split('---', 2)
    if len(parts) < 3:
        raise ValueError(f"Invalid frontmatter format in scenario: {scenario_path}")
    
    # Parse YAML frontmatter
    try:
        frontmatter = yaml.safe_load(parts[1])
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in scenario frontmatter: {e}")
    
    # Parse markdown content for additional turns if present
    markdown_content = parts[2].strip()
    
    # Ensure required fields have defaults
    scenario = {
        'name': frontmatter.get('name', scenario_path.stem),
        'behavior_tested': frontmatter.get('behavior_tested', 'unknown'),
        'max_user_turns': frontmatter.get('max_user_turns', 6),
        'probes_per_point': frontmatter.get('probes_per_point', 4),
        'anchor_question': frontmatter.get('anchor_question', []),
        'branches': frontmatter.get('branches', [{'id': 'baseline', 'description': 'Default branch'}]),
        'turns': frontmatter.get('turns', []),
        'description': frontmatter.get('description', ''),
        'markdown_content': markdown_content
    }
    
    # Ensure anchor_question is a list
    if isinstance(scenario['anchor_question'], str):
        scenario['anchor_question'] = [scenario['anchor_question']]
    
    return scenario

def list_scenarios(scenarios_dir: Path) -> List[Dict[str, Any]]:
    """
    List all available scenarios in a directory.
    
    Args:
        scenarios_dir: Path to scenarios directory
        
    Returns:
        List of scenario metadata dictionaries
    """
    scenarios = []
    
    if not scenarios_dir.exists():
        return scenarios
    
    for scenario_file in scenarios_dir.glob('*.md'):
        try:
            scenario = load_scenario(scenario_file)
            scenarios.append({
                'id': scenario_file.stem,
                'name': scenario['name'],
                'behavior_tested': scenario['behavior_tested'],
                'max_turns': scenario['max_user_turns'],
                'anchor_questions': scenario['anchor_question'],
                'file_path': str(scenario_file)
            })
        except Exception as e:
            print(f"Warning: Could not load scenario {scenario_file}: {e}")
    
    return scenarios

def validate_scenario(scenario: Dict[str, Any]) -> List[str]:
    """
    Validate a scenario configuration.
    
    Args:
        scenario: Scenario dictionary to validate
        
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # Required fields
    required_fields = ['name', 'behavior_tested', 'anchor_question']
    for field in required_fields:
        if field not in scenario:
            errors.append(f"Missing required field: {field}")
    
    # Validate anchor questions
    if 'anchor_question' in scenario:
        anchor_questions = scenario['anchor_question']
        if not isinstance(anchor_questions, list):
            errors.append("anchor_question must be a list")
        elif len(anchor_questions) == 0:
            errors.append("At least one anchor question is required")
    
    # Validate turns
    if 'turns' in scenario and scenario['turns']:
        turns = scenario['turns']
        if not isinstance(turns, list):
            errors.append("turns must be a list")
        else:
            for i, turn in enumerate(turns):
                if not isinstance(turn, dict):
                    errors.append(f"Turn {i} must be a dictionary")
                elif 'role' not in turn:
                    errors.append(f"Turn {i} missing required 'role' field")
                elif 'content' not in turn:
                    errors.append(f"Turn {i} missing required 'content' field")
    
    # Validate numeric fields
    numeric_fields = ['max_user_turns', 'probes_per_point']
    for field in numeric_fields:
        if field in scenario:
            try:
                value = int(scenario[field])
                if value < 0:
                    errors.append(f"{field} must be non-negative")
            except (ValueError, TypeError):
                errors.append(f"{field} must be a valid integer")
    
    return errors
