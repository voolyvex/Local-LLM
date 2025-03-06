"""
Shadow Worker specific configuration for Local-LLM.

This file contains configurations optimized for integration with the Shadow Worker
game engine, focusing on NPC psychology, dialogue generation, and tile generation.
"""

import os
from pathlib import Path

# Base configuration
SW_CONFIG = {
    # API configuration
    "api": {
        "host": "localhost",
        "port": 8002,
        "log_level": "info",
        "workers": 1,
        "request_timeout": 60
    },
    
    # Model configuration
    "models": {
        "psychology": "mistral-7b-instruct-v0.2.Q4_K_M",  # For character psychology
        "dialogue": "llama3-8b-instruct.Q4_K_M",          # For dialogue generation
        "tile_gen": "phi-3-mini-4k-instruct.Q4_K_M",      # For lightweight tile generation
    },
    
    # Performance settings
    "performance": {
        "gpu_layers": 35,                 # Default GPU layers
        "max_tokens": 2048,               # Default max token limit
        "batch_size": 512,                # Batch size for generation
        "context_window": 4096,           # Context window size
        "thread_count": 4                 # Number of CPU threads
    },
    
    # Shadow Worker specific paths
    "paths": {
        "cache_dir": os.path.join(Path.home(), ".cache", "shadow-worker", "llm"),
        "prompt_templates": os.path.join("resources", "prompts"),
        "logs_dir": os.path.join("logs", "shadow-worker")
    },
    
    # Monitoring settings
    "monitoring": {
        "enable_metrics": True,
        "log_requests": True,
        "performance_tracking": True,
        "max_log_size_mb": 50,
        "log_rotation_count": 5
    }
} 