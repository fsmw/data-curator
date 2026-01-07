"""Configuration management for the data curation tool."""

import os
from pathlib import Path
from typing import Dict, Any, List
import yaml
from dotenv import load_dotenv


class Config:
    """Manages configuration from YAML and environment variables."""
    
    def __init__(self, config_path: str = "config.yaml", indicators_path: str = "indicators.yaml"):
        """
        Initialize configuration.
        
        Args:
            config_path: Path to YAML configuration file
            indicators_path: Path to indicators mapping file
        """
        load_dotenv()
        self.config_path = Path(config_path)
        self.indicators_path = Path(indicators_path)
        self.config = self._load_config()
        self.indicators = self._load_indicators()
        self.data_root = Path(os.getenv("DATA_ROOT", "."))
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _load_indicators(self) -> Dict[str, Any]:
        """Load indicators mapping from YAML file."""
        if not self.indicators_path.exists():
            return {}
        
        with open(self.indicators_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def get_directory(self, dir_type: str) -> Path:
        """
        Get directory path for a specific type.
        
        Args:
            dir_type: Type of directory (raw, clean, metadata, graphics)
            
        Returns:
            Path object for the directory
        """
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
    
    def get_indicators(self) -> Dict[str, Any]:
        """Get all available indicators."""
        return self.indicators.get('indicators', {})
    
    def get_indicator(self, name: str) -> Dict[str, Any]:
        """Get specific indicator by name."""
        return self.get_indicators().get(name, {})
    
    def get_topic_indicators(self, topic: str) -> List[str]:
        """Get indicators for a specific topic."""
        mappings = self.indicators.get('topic_indicators', {})
        return mappings.get(topic, [])
    
    def get_coverage_countries(self, coverage: str) -> List[str]:
        """Get countries for a specific coverage area."""
        coverage_map = self.indicators.get('coverage_countries', {})
        countries = coverage_map.get(coverage, [])
        if '*' in countries:
            return []  # Return empty list for "all countries"
        return countries
    
    def get_sources(self) -> list:
        """Get list of configured data sources."""
        return self.config['sources']
    
    def get_topics(self) -> list:
        """Get list of configured topics."""
        return self.config['topics']
    
    def initialize_directories(self):
        """Create all required directories if they don't exist."""
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
