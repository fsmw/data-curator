"""Refactored configuration - simplified for list-based indicators."""

import os
from pathlib import Path
from typing import Dict, Any, List
import yaml
from dotenv import load_dotenv


class Config:
    """Manages configuration with simplified indicator structure."""

    def __init__(self, config_path: str = "config.yaml", indicators_path: str = "indicators.yaml"):
        """Initialize configuration."""
        load_dotenv()
        self.config_path = Path(config_path)
        self.indicators_path = Path(indicators_path)
        self.config = self._load_config()
        self.indicators_data = self._load_indicators()
        self.data_root = Path(os.getenv("DATA_ROOT", "."))

    def _load_config(self) -> Dict[str, Any]:
        """Load main configuration from YAML."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _load_indicators(self) -> Dict[str, Any]:
        """Load indicators from YAML."""
        if not self.indicators_path.exists():
            return {'indicators': [], 'regions': {}}

        with open(self.indicators_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            # Ensure indicators is a list
            if 'indicators' not in data:
                data['indicators'] = []
            elif isinstance(data['indicators'], dict):
                # Convert old dict format to list format
                indicators_list = []
                for key, value in data['indicators'].items():
                    value['id'] = key
                    # Ensure tags exist
                    if 'tags' not in value:
                        value['tags'] = []
                    indicators_list.append(value)
                data['indicators'] = indicators_list
            return data

    def get_directory(self, dir_type: str) -> Path:
        """Get directory path for a specific type."""
        dir_name = self.config['directories'][dir_type]
        return self.data_root / dir_name

    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration."""
        return {
            'api_key': os.getenv('OPENROUTER_API_KEY'),
            'model': os.getenv('OPENROUTER_MODEL', 'anthropic/claude-3.5-sonnet'),
            'max_tokens': self.config['llm']['max_tokens'],
            'temperature': self.config['llm']['temperature'],
            'system_prompt': self.config['llm']['system_prompt']
        }

    def get_indicators(self) -> List[Dict[str, Any]]:
        """Get list of all indicators."""
        return self.indicators_data.get('indicators', [])

    def get_regions(self) -> Dict[str, List[str]]:
        """Get region-to-countries mapping."""
        return self.indicators_data.get('regions', {})

    def get_region_countries(self, region: str) -> List[str]:
        """Get countries for a specific region."""
        regions = self.get_regions()
        return regions.get(region, [])

    def get_sources(self) -> list:
        """Get list of configured data sources."""
        return self.config['sources']

    def get_topics(self) -> list:
        """Get list of configured topics."""
        return self.config['topics']

    def initialize_directories(self):
        """Create all required directories."""
        # Main directories
        for dir_type in ['raw', 'clean', 'metadata', 'graphics']:
            dir_path = self.get_directory(dir_type)
            dir_path.mkdir(parents=True, exist_ok=True)

        # Source subdirectories in raw data
        raw_dir = self.get_directory('raw')
        for source in self.get_sources():
            (raw_dir / source).mkdir(exist_ok=True)

        # Topic subdirectories in clean data
        clean_dir = self.get_directory('clean')
        for topic in self.get_topics():
            (clean_dir / topic).mkdir(exist_ok=True)

        print("✓ Directory structure initialized")
