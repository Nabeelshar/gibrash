"""
Configuration loader with environment variable support
"""

import json
import os


def load_config(config_path='config.json'):
    """Load configuration from JSON file with environment variable overrides"""
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Override sensitive values from environment if available
    if os.environ.get('WORDPRESS_API_KEY'):
        config['api_key'] = os.environ.get('WORDPRESS_API_KEY')
    
    if os.environ.get('GEMINI_API_KEY'):
        config['gemini_api_key'] = os.environ.get('GEMINI_API_KEY')
    
    return config
