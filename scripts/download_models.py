#!/usr/bin/env python
"""
Download script for Local-LLM models.

This script downloads the models required for Local-LLM.
Use the --shadow-worker flag to download Shadow Worker specific models.
"""

import os
import sys
import argparse
import subprocess
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("model-downloader")

def download_standard_models(force=False):
    """Download standard Local-LLM models."""
    logger.info("Downloading standard Local-LLM models")
    # Add standard model download logic here
    # This is a placeholder for the standard model download logic
    logger.info("Standard model download completed")
    return True

def download_shadow_worker_models(force=False):
    """Download Shadow Worker specific models."""
    logger.info("Downloading Shadow Worker specific models")
    
    # Get the path to the Shadow Worker model download script
    script_dir = Path(__file__).resolve().parent
    sw_script = script_dir / "download_models_sw.py"
    
    if not sw_script.exists():
        logger.error(f"Shadow Worker model download script not found: {sw_script}")
        return False
    
    # Build command
    cmd = [sys.executable, str(sw_script)]
    if force:
        cmd.append("--force")
    
    # Run the Shadow Worker model download script
    try:
        logger.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True)
        if result.returncode == 0:
            logger.info("Shadow Worker model download completed successfully")
            return True
        else:
            logger.error(f"Shadow Worker model download failed with code {result.returncode}")
            return False
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running Shadow Worker model download: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Download models for Local-LLM")
    parser.add_argument("--force", action="store_true", help="Force download even if models exist")
    parser.add_argument("--shadow-worker", action="store_true", help="Download Shadow Worker specific models")
    parser.add_argument("--all", action="store_true", help="Download all models (standard and Shadow Worker)")
    args = parser.parse_args()
    
    success = True
    
    # Determine which models to download
    download_standard = not args.shadow_worker or args.all
    download_sw = args.shadow_worker or args.all
    
    # Download standard models if requested
    if download_standard:
        if not download_standard_models(args.force):
            success = False
    
    # Download Shadow Worker models if requested
    if download_sw:
        if not download_shadow_worker_models(args.force):
            success = False
    
    if success:
        logger.info("All requested models downloaded successfully")
        return 0
    else:
        logger.error("Some model downloads failed")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 