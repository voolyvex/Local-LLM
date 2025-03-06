# Shadow Worker Development Guide

This guide provides information on extending or modifying the Shadow Worker integration with Local-LLM.

## Architecture Overview

The Shadow Worker integration follows a modular architecture with these key components:

```
┌─ Shadow Worker Game Client ─┐      ┌─ Local-LLM Service ──────────────────────┐
│                             │      │                                           │
│  • Entity Component System  │      │  ┌─ API Layer ─────────────────────────┐ │
│  • World System             │◄────►│  │ FastAPI endpoints for SW integration │ │
│  • Character System         │      │  └───────────────────┬─────────────────┘ │
│                             │      │                      │                    │
└─────────────────────────────┘      │  ┌─ Model Management ┴─────────────────┐ │
                                     │  │ Dynamic loading/unloading of models  │ │
                                     │  └───────────────────┬─────────────────┘ │
                                     │                      │                    │
                                     │  ┌─ Prompt Templates ┴─────────────────┐ │
                                     │  │ Task-specific prompt engineering     │ │
                                     │  └───────────────────┬─────────────────┘ │
                                     │                      │                    │
                                     │  ┌─ Inference Engine ┴─────────────────┐ │
                                     │  │ Optimized for 8GB VRAM constraints   │ │
                                     │  └─────────────────────────────────────┘ │
                                     │                                           │
                                     └───────────────────────────────────────────┘
```

## Adding New Endpoints

To add a new endpoint to the Shadow Worker integration:

1. Define the endpoint in `src/api/server.py`:

```python
@app.post("/new-endpoint")
async def new_endpoint(request_data: NewEndpointRequest):
    """New endpoint description."""
    try:
        # Process the request
        result = await process_new_endpoint(request_data)
        return result
    except Exception as e:
        logger.error(f"Error in new endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
```

2. Create request/response models in `src/api/models.py`:

```python
class NewEndpointRequest(BaseModel):
    """Request model for new endpoint."""
    parameter1: str
    parameter2: int
    
class NewEndpointResponse(BaseModel):
    """Response model for new endpoint."""
    result: str
    status: str
```

3. Add prompt templates in `resources/prompts/shadow-worker/new_endpoint.txt`

4. Update the API documentation in `docs/shadow-worker/api.md`

## Optimizing for VRAM Constraints

The Shadow Worker integration is designed to work within 8GB VRAM constraints. When extending functionality:

1. **Model Sharing**: Reuse loaded models when possible instead of loading multiple models
2. **Dynamic Loading**: Implement dynamic model loading/unloading based on usage patterns
3. **Quantization**: Use Q4_K_M quantized models for optimal performance/quality balance
4. **Batching**: Batch similar requests to maximize throughput
5. **Context Management**: Implement efficient context window management

Example of dynamic model loading:

```python
async def get_model_for_task(task_type):
    """Get the appropriate model for a specific task."""
    global loaded_models
    
    # Define model mapping
    model_map = {
        "psychology": "mistral-7b-instruct-v0.2.Q4_K_M",
        "dialogue": "llama3-8b-instruct.Q4_K_M",
        "tile_gen": "phi-3-mini-4k-instruct.Q4_K_M"
    }
    
    # Check if we need to unload a model to free VRAM
    if len(loaded_models) >= 2 and task_type not in loaded_models:
        # Unload least recently used model
        lru_model = min(model_usage.items(), key=lambda x: x[1])[0]
        await unload_model(lru_model)
        
    # Load the required model if not already loaded
    if task_type not in loaded_models:
        await load_model(model_map[task_type])
        
    # Update usage timestamp
    model_usage[task_type] = time.time()
    
    return loaded_models[task_type]
```

## Prompt Engineering

Shadow Worker uses specialized prompts for different tasks. When creating new prompts:

1. **Consistency**: Maintain consistent style with existing prompts
2. **Specificity**: Be specific about the desired output format
3. **Context**: Include relevant context from the game state
4. **Examples**: Provide examples of desired outputs
5. **Constraints**: Clearly state any constraints or limitations

Example prompt structure for character psychology:

```
[TASK]
Analyze the psychology of a character with the following traits and history.

[CHARACTER]
Name: {{character.name}}
Personality Type: {{character.personality_type}} (Enneagram)
Traits: {{character.traits}}
History: {{character.history}}

[CONTEXT]
Location: {{context.location}}
Recent Events: {{context.recent_events}}

[OUTPUT FORMAT]
Provide an analysis with the following sections:
1. Emotional State: Current emotional state based on personality and context
2. Motivations: Primary motivations driving the character
3. Internal Conflicts: Any internal struggles or conflicts
4. Potential Actions: Likely actions the character might take in this context

[EXAMPLES]
{{examples}}
```

## Testing and Validation

When extending the Shadow Worker integration, follow these testing practices:

1. **Unit Tests**: Write unit tests for new endpoints and functionality
2. **Integration Tests**: Test the integration between components
3. **Performance Testing**: Validate VRAM usage and response times
4. **Edge Cases**: Test with extreme inputs and error conditions

Example test for a new endpoint:

```python
def test_new_endpoint():
    """Test the new endpoint functionality."""
    # Prepare test data
    test_data = {
        "parameter1": "test value",
        "parameter2": 42
    }
    
    # Call the endpoint
    response = client.post("/new-endpoint", json=test_data)
    
    # Validate response
    assert response.status_code == 200
    assert "result" in response.json()
    assert "status" in response.json()
    assert response.json()["status"] == "success"
```

## Deployment Considerations

When deploying Shadow Worker integration in different environments:

1. **Development**: Use `--debug` mode for detailed logging
2. **Testing**: Use medium-sized models with `--model-size medium`
3. **Production**: Configure for optimal performance with appropriate GPU layers

## Troubleshooting

Common issues and solutions:

1. **VRAM Out of Memory**: Reduce GPU layers or use smaller models
2. **Slow Response Times**: Check for inefficient prompt templates or context management
3. **Model Loading Failures**: Verify model paths and permissions
4. **API Connection Issues**: Check network configuration and firewall settings

## Contributing

When contributing to the Shadow Worker integration:

1. Follow the existing code style and architecture
2. Document new functionality in the appropriate locations
3. Update the API documentation for any changes
4. Add tests for new functionality
5. Consider VRAM constraints in all implementations 