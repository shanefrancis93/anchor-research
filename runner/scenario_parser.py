import yaml
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class Branch:
    """Represents a conversation branch/fork."""
    id: str
    description: str
    
    
@dataclass
class Turn:
    """Represents a single conversation turn."""
    role: str
    content: Optional[str] = None
    
    
@dataclass
class Scenario:
    """Parsed scenario with metadata and conversation structure."""
    name: str
    anchor_question: str
    behavior_tested: str
    max_user_turns: int
    branches: List[Branch]
    turns: List[Turn]
    raw_content: str = ""
    file_path: Optional[Path] = None
    

class ScenarioParser:
    """Parse markdown files with YAML frontmatter into Scenario objects."""
    
    @staticmethod
    def parse_file(file_path: Path) -> Scenario:
        """Parse a scenario file."""
        content = file_path.read_text(encoding='utf-8')
        return ScenarioParser.parse_content(content, file_path)
    
    @staticmethod
    def parse_content(content: str, file_path: Optional[Path] = None) -> Scenario:
        """Parse scenario content with YAML frontmatter."""
        # Extract YAML frontmatter
        yaml_match = re.match(r'^---\n(.*?)\n---\n(.*)', content, re.DOTALL)
        if not yaml_match:
            raise ValueError("Invalid scenario format: missing YAML frontmatter")
        
        yaml_content = yaml_match.group(1)
        markdown_content = yaml_match.group(2)
        
        # Parse YAML
        try:
            metadata = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML frontmatter: {e}")
        
        # Extract required fields
        required_fields = ['name', 'anchor_question', 'behavior_tested', 'turns']
        for field in required_fields:
            if field not in metadata:
                raise ValueError(f"Missing required field: {field}")
        
        # Parse branches
        branches = []
        for branch_data in metadata.get('branches', []):
            branches.append(Branch(
                id=branch_data['id'],
                description=branch_data['description']
            ))
        
        # If no branches specified, create default baseline
        if not branches:
            branches.append(Branch(
                id="baseline",
                description="Default conversation flow"
            ))
        
        # Parse turns
        turns = []
        for turn_data in metadata['turns']:
            role = turn_data.get('role')
            content = turn_data.get('content')
            
            # Handle assistant_expected placeholder
            if role == 'assistant_expected':
                turns.append(Turn(role='assistant', content=None))
            else:
                turns.append(Turn(role=role, content=content))
        
        # Create scenario object
        scenario = Scenario(
            name=metadata['name'],
            anchor_question=metadata['anchor_question'],
            behavior_tested=metadata['behavior_tested'],
            max_user_turns=metadata.get('max_user_turns', 10),
            branches=branches,
            turns=turns,
            raw_content=content,
            file_path=file_path
        )
        
        return scenario
    
    @staticmethod
    def load_all_scenarios(directory: Path) -> List[Scenario]:
        """Load all scenario files from a directory."""
        scenarios = []
        for file_path in directory.glob("*.md"):
            try:
                scenario = ScenarioParser.parse_file(file_path)
                scenarios.append(scenario)
            except Exception as e:
                print(f"Error loading {file_path}: {e}")
        return scenarios