# Shadow Worker Integration for Local-LLM

This branch contains Shadow Worker specific modifications to Local-LLM for integrating AI-powered dialogue, character psychology, and procedural tile generation into the Shadow Worker game engine.

## Setup and Usage

### Prerequisites

- Windows 10 or later
- Python 3.9+ with pip
- CUDA-compatible GPU with at least 8GB VRAM (for optimal performance)
- Git

### Installation

1. Clone this repository:
   ```bash
   git clone -b feature/sw-integration https://github.com/yourusername/Local-LLM.git
   cd Local-LLM
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-sw.txt  # Shadow Worker specific requirements
   ```

3. Download the required models:
   ```bash
   python scripts/download_models.py --shadow-worker
   ```

### Running the Service

Use the Shadow Worker specific launcher:

```batch
scripts\windows\shadow_worker_llm.bat
```

Options:
- `--cpu-only`: Run without GPU acceleration
- `--model-size [small|medium|large]`: Select model size based on available VRAM
- `--debug`: Run in debug mode (console output)

### Integration Points

The Shadow Worker LLM service exposes these endpoints:

- `GET /health`: Service health check 
- `POST /psychology/analyze`: Character psychological analysis
- `POST /dialogue/generate`: Character dialogue generation
- `POST /tile/generate`: Procedural tile generation

See the [API Documentation](docs/shadow-worker/api.md) for full details.

## Optimization for 8GB VRAM

This integration is specifically optimized for GPUs with 8GB VRAM, using:
- Quantized models (Q4_K_M format)
- Efficient context management
- Dynamic GPU layer allocation
- Specialized model selection per task

## Directory Structure

- `config/shadow-worker/`: Shadow Worker specific configurations
- `scripts/windows/`: Windows-specific scripts for Shadow Worker
- `docs/shadow-worker/`: Shadow Worker integration documentation
- `resources/prompts/shadow-worker/`: Prompt templates for Shadow Worker

## Development Notes

See [Shadow Worker Development Guide](docs/shadow-worker/development.md) for information on extending or modifying this integration. 