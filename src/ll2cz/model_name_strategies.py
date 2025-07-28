# SPDX-FileCopyrightText: Copyright (c), CloudZero, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""Strategy pattern implementation for model name extraction."""

import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Set

import yaml


class ModelNameStrategy(ABC):
    """Abstract base class for model name extraction strategies."""
    
    @abstractmethod
    def matches(self, model: str) -> bool:
        """Check if this strategy should be applied to the model string."""
        pass
    
    @abstractmethod
    def extract(self, model: str) -> str:
        """Extract the model name using this strategy."""
        pass


class ProviderPathStrategy(ModelNameStrategy):
    """Handle provider path prefixes like 'fireworks_ai/accounts/fireworks/models/deepseek-v3'."""
    
    def matches(self, model: str) -> bool:
        return '/' in model
    
    def extract(self, model: str) -> str:
        return model.split('/')[-1]


class AWSBedrockStrategy(ModelNameStrategy):
    """Handle AWS Bedrock format like 'us.amazon.nova-lite-v1:0'."""
    
    def matches(self, model: str) -> bool:
        return ':' in model and '.' in model
    
    def extract(self, model: str) -> str:
        # Extract the model part before the colon and after the provider
        parts = model.split(':')[0].split('.')
        if len(parts) >= 3:
            if parts[1] == 'amazon':
                return '.'.join(parts[2:])  # e.g., "nova-lite-v1"
            elif parts[1] == 'anthropic':
                return '.'.join(parts[2:])  # e.g., "claude-3-7-sonnet-20250219-v1"
        return model


class ProviderDotModelStrategy(ModelNameStrategy):
    """Handle provider.model format like 'amazon.titan-text-lite-v1'."""
    
    def __init__(self, known_providers: Set[str]):
        self.known_providers = known_providers
    
    def matches(self, model: str) -> bool:
        if '.' not in model or model.startswith('gpt') or model.startswith('text-'):
            return False
        
        parts = model.split('.')
        if len(parts) >= 2:
            first_part = parts[0]
            return (first_part in self.known_providers or 
                   (len(first_part) <= 10 and '-' not in first_part and not first_part.isdigit()))
        return False
    
    def extract(self, model: str) -> str:
        parts = model.split('.')
        return '.'.join(parts[1:])


class CommandRStrategy(ModelNameStrategy):
    """Special handling for Command-R models."""
    
    def matches(self, model: str) -> bool:
        return 'command' in model.lower() and 'r' in model.lower()
    
    def extract(self, model: str) -> str:
        return 'command-r'


class VersionPatternStrategy(ModelNameStrategy):
    """Remove version patterns from model names."""
    
    def __init__(self, version_patterns: List[str], version_words: Set[str], model_variants: Set[str]):
        self.version_patterns = [re.compile(pattern) for pattern in version_patterns]
        self.version_words = version_words
        self.model_variants = model_variants
    
    def matches(self, model: str) -> bool:
        return True  # Always apply version removal
    
    def extract(self, model: str) -> str:
        parts = model.lower().split('-')
        if not parts:
            return model.lower()
        
        filtered_parts = []
        
        for part in parts:
            if not part:
                continue
            
            # Check if part matches version patterns
            is_version = any(pattern.match(part) for pattern in self.version_patterns)
            
            # Skip if it's a version word (but not a model variant)
            if part in self.version_words:
                is_version = True
            
            # Preserve model variants even if they might look like versions
            if part in self.model_variants:
                is_version = False
            
            # Special case: preserve letter+number patterns (e.g., "o1", "m7")
            # but remove number+letter patterns (e.g., "4o", "3b")
            if re.match(r'^[a-z]+[0-9]+$', part):
                is_version = False  # This is a model name like "o1"
            elif re.match(r'^[0-9]+[a-z]+$', part):
                is_version = True   # This is a version like "4o"
            
            if not is_version:
                filtered_parts.append(part)
        
        # If we filtered everything out, fall back to the first part
        if not filtered_parts:
            filtered_parts = [parts[0]]
        
        result = '-'.join(filtered_parts)
        
        # Final cleanup - remove any trailing version-like suffixes
        # Note: preview is excluded here since it's a valid model variant (e.g., o1-preview)
        result = re.sub(r'-+(latest|stable|final|v[0-9]+)$', '', result)
        
        return result if result else model.lower()


class ModelNameExtractor:
    """Main class that uses strategies to extract model names."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize with configuration from YAML file."""
        if config_path is None:
            config_path = Path(__file__).parent / 'config' / 'providers.yml'
        
        # Load configuration
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                model_config = config.get('model_extraction', {})
        else:
            # Fallback to defaults if config file doesn't exist
            model_config = {
                'known_providers': ['amazon', 'google', 'microsoft', 'anthropic', 'openai', 'meta', 'cohere'],
                'version_patterns': [r'^[0-9]+$', r'^[0-9]+[a-z]$', r'^[0-9]+\.[0-9]+$'],
                'version_words': {'latest', 'stable', 'preview', 'beta', 'alpha'},
                'model_variants': {'haiku', 'sonnet', 'opus', 'turbo', 'mini', 'chat', 'text'}
            }
        
        # Initialize strategies
        self.strategies = [
            CommandRStrategy(),
            ProviderPathStrategy(),
            AWSBedrockStrategy(),
            ProviderDotModelStrategy(set(model_config.get('known_providers', []))),
            VersionPatternStrategy(
                model_config.get('version_patterns', []),
                set(model_config.get('version_words', [])),
                set(model_config.get('model_variants', []))
            )
        ]
    
    def extract(self, model: str) -> str:
        """Extract model name using the strategy pattern."""
        if not model:
            return 'unknown'
        
        current_model = model
        
        # Apply strategies in order
        for strategy in self.strategies:
            if strategy.matches(current_model):
                current_model = strategy.extract(current_model)
                # Some strategies transform the model, so we continue with the transformed version
                if isinstance(strategy, (ProviderPathStrategy, AWSBedrockStrategy, ProviderDotModelStrategy, CommandRStrategy)):
                    # These strategies do one-time extraction, don't continue
                    if current_model != model:  # If the strategy made a change
                        # Still apply version removal
                        continue
        
        return current_model


# Convenience function to maintain backward compatibility
def extract_model_name(model: str) -> str:
    """Extract the core model name by removing version-related information.
    
    This is a backward-compatible wrapper around ModelNameExtractor.
    """
    extractor = ModelNameExtractor()
    return extractor.extract(model)