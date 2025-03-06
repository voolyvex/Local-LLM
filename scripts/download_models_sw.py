#!/usr/bin/env python
"""
Download script for Shadow Worker specific models.

This script downloads the quantized models required for Shadow Worker integration:
- mistral-7b-instruct-v0.2.Q4_K_M (for character psychology)
- llama3-8b-instruct.Q4_K_M (for dialogue generation)
- phi-3-mini-4k-instruct.Q4_K_M (for tile generation)

These models are optimized for 8GB VRAM constraints.
"""

import os
import sys
import argparse
import requests
import hashlib
import tqdm
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("sw-model-downloader")

# Model information
MODELS = {
    "mistral-7b-instruct-v0.2.Q4_K_M": {
        "url": "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf",
        "size": 4_200_000_000,  # Approximate size in bytes
        "md5": "a5b2ffd6d7a5f4df401e2c7a2f407d2e",  # Example MD5, replace with actual
        "description": "Mistral 7B Instruct v0.2 (Q4_K_M) - For character psychology analysis"
    },
    "llama3-8b-instruct.Q4_K_M": {
        "url": "https://huggingface.co/TheBloke/Llama-3-8B-Instruct-GGUF/resolve/main/llama-3-8b-instruct.Q4_K_M.gguf",
        "size": 4_800_000_000,  # Approximate size in bytes
        "md5": "b7f3b1d9c2e3a4f5b6a7c8d9e0f1a2b3",  # Example MD5, replace with actual
        "description": "Llama 3 8B Instruct (Q4_K_M) - For dialogue generation"
    },
    "phi-3-mini-4k-instruct.Q4_K_M": {
        "url": "https://huggingface.co/TheBloke/phi-3-mini-4k-instruct-GGUF/resolve/main/phi-3-mini-4k-instruct.Q4_K_M.gguf",
        "size": 2_100_000_000,  # Approximate size in bytes
        "md5": "c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6",  # Example MD5, replace with actual
        "description": "Phi-3 Mini 4K Instruct (Q4_K_M) - For tile generation"
    }
}

def get_models_dir():
    """Get the models directory, creating it if it doesn't exist."""
    # Get project root directory
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    
    # Check for models directory in config
    try:
        import json
        config_path = project_root / "config.json"
        if config_path.exists():
            with open(config_path, "r") as f:
                config = json.load(f)
                models_dir = config.get("paths", {}).get("models", "models")
                models_dir = Path(project_root) / models_dir
        else:
            models_dir = project_root / "models"
    except Exception as e:
        logger.warning(f"Error reading config, using default models directory: {e}")
        models_dir = project_root / "models"
    
    # Create models directory if it doesn't exist
    if not models_dir.exists():
        logger.info(f"Creating models directory: {models_dir}")
        models_dir.mkdir(parents=True, exist_ok=True)
    
    return models_dir

def download_file(url, destination, description=None):
    """Download a file with progress bar."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        desc = description or os.path.basename(url)
        
        with open(destination, 'wb') as f, tqdm.tqdm(
            desc=desc,
            total=total_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for chunk in response.iter_content(chunk_size=1024*1024):
                size = f.write(chunk)
                bar.update(size)
        
        return True
    except Exception as e:
        logger.error(f"Error downloading {url}: {e}")
        if os.path.exists(destination):
            os.remove(destination)
        return False

def verify_file(file_path, expected_md5):
    """Verify file integrity using MD5 checksum."""
    if not expected_md5:
        logger.warning(f"No MD5 checksum provided for {file_path}, skipping verification")
        return True
    
    logger.info(f"Verifying {file_path}...")
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    
    calculated_md5 = md5_hash.hexdigest()
    if calculated_md5 != expected_md5:
        logger.error(f"MD5 verification failed for {file_path}")
        logger.error(f"Expected: {expected_md5}")
        logger.error(f"Calculated: {calculated_md5}")
        return False
    
    logger.info(f"MD5 verification successful for {file_path}")
    return True

def download_models(models_to_download=None, force=False):
    """Download the specified models."""
    models_dir = get_models_dir()
    logger.info(f"Using models directory: {models_dir}")
    
    # If no models specified, download all
    if not models_to_download:
        models_to_download = list(MODELS.keys())
    
    # Download each model
    success = True
    for model_name in models_to_download:
        if model_name not in MODELS:
            logger.error(f"Unknown model: {model_name}")
            success = False
            continue
        
        model_info = MODELS[model_name]
        model_path = models_dir / model_name
        
        # Check if model already exists
        if model_path.exists() and not force:
            logger.info(f"Model {model_name} already exists, skipping download")
            continue
        
        # Download the model
        logger.info(f"Downloading {model_name}: {model_info['description']}")
        if download_file(model_info['url'], model_path, model_info['description']):
            # Verify the download
            if verify_file(model_path, model_info['md5']):
                logger.info(f"Successfully downloaded and verified {model_name}")
            else:
                logger.error(f"Failed to verify {model_name}")
                success = False
        else:
            logger.error(f"Failed to download {model_name}")
            success = False
    
    return success

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Download Shadow Worker models")
    parser.add_argument("--force", action="store_true", help="Force download even if models exist")
    parser.add_argument("--models", nargs="+", help="Specific models to download")
    args = parser.parse_args()
    
    logger.info("Starting Shadow Worker model download")
    success = download_models(args.models, args.force)
    
    if success:
        logger.info("All models downloaded successfully")
        return 0
    else:
        logger.error("Some models failed to download")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 