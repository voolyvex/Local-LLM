# Shadow Worker API Integration

This document details the API endpoints available for Shadow Worker integration.

## Base URL

All API endpoints are available at `http://localhost:8002/`

## Endpoints

### Health Check

```
GET /health
```

Returns the service status and model information.

#### Response

```json
{
  "status": "ok",
  "models_loaded": ["psychology", "dialogue", "tile_gen"],
  "uptime": "0:35:12",
  "memory_usage": "5.2GB VRAM, 1.8GB RAM"
}
```

### Character Psychology Analysis

```
POST /psychology/analyze
```

Analyze character psychology based on personality factors, history, and context.

#### Request Body

```json
{
  "character": {
    "name": "Elara",
    "personality_type": 4,  // Enneagram type
    "traits": ["curious", "reserved", "analytical"],
    "history": "Lost her family during the war, became a scholar to understand the world"
  },
  "context": {
    "location": "Grand Library",
    "recent_events": ["Discovered ancient text", "Argued with the librarian"]
  },
  "generation_params": {
    "temperature": 0.7,
    "max_tokens": 256
  }
}
```

#### Response

```json
{
  "analysis": {
    "emotional_state": "Intellectually excited but emotionally guarded",
    "motivations": ["Discovery of knowledge", "Proving self-worth"],
    "internal_conflicts": ["Desire for connection vs fear of loss"],
    "potential_actions": [
      {"action": "Share discovery", "likelihood": 0.7},
      {"action": "Hide discovery", "likelihood": 0.3}
    ]
  }
}
```

### Dialogue Generation

```
POST /dialogue/generate
```

Generate context-aware dialogue for NPCs based on their psychological profile.

#### Request Body

```json
{
  "character": {
    "name": "Elara",
    "personality_type": 4,
    "mood": "suspicious",
    "knowledge": ["Knows about the ancient artifact", "Distrusts strangers"]
  },
  "context": {
    "speaker": "player",
    "previous_dialogue": [
      {"speaker": "player", "text": "I need information about the artifact."},
      {"speaker": "Elara", "text": "What makes you think I would know anything about that?"}
    ],
    "relationship": "neutral",
    "location": "Grand Library"
  },
  "generation_params": {
    "temperature": 0.8,
    "max_tokens": 150,
    "dialogue_style": "cautious"
  }
}
```

#### Response

```json
{
  "dialogue": {
    "text": "I've spent years researching artifacts, and I don't share my knowledge lightly. What's your interest in it? Academic... or something more profitable?",
    "tone": "guarded",
    "intention": "testing_trustworthiness"
  }
}
```

### Procedural Tile Generation

```
POST /tile/generate
```

Generate descriptive text for procedural tile generation, which can be used to influence visual generation.

#### Request Body

```json
{
  "environment": {
    "biome": "ancient_forest",
    "time_of_day": "dusk",
    "weather": "light_rain"
  },
  "mythology": {
    "influences": ["elven_ruins", "nature_spirits"],
    "narrative_elements": ["abandoned_shrine", "forgotten_path"]
  },
  "style_params": {
    "aesthetic": "pixel_art",
    "color_palette": "forest_twilight",
    "detail_level": "medium"
  },
  "generation_params": {
    "temperature": 0.7,
    "max_tokens": 200
  }
}
```

#### Response

```json
{
  "tile_description": {
    "visual_elements": [
      "Moss-covered stone archway with faded elven runes",
      "Twisted ancient trees with glowing blue fungi",
      "Small puddles reflecting the fading light",
      "Fallen stone statues half-buried in the undergrowth"
    ],
    "color_scheme": ["#2A3B4C", "#3E6259", "#BDA355", "#5D4C46"],
    "mood": "mysterious melancholy",
    "lighting": "diffused twilight with blue-tinted shadows"
  }
}
```

## Error Handling

All endpoints return standard HTTP status codes:

- `200 OK`: Request successful
- `400 Bad Request`: Invalid request parameters
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

Error responses include detailed information:

```json
{
  "error": {
    "code": "invalid_request",
    "message": "Invalid personality_type value. Must be between 1 and 9.",
    "details": {
      "field": "character.personality_type",
      "allowed_values": [1, 2, 3, 4, 5, 6, 7, 8, 9]
    }
  }
}
```

## Authentication

Currently, the API does not require authentication as it is designed to run locally and be accessed only by the Shadow Worker game client. 