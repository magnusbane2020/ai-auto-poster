"""
personas.py - Multi-persona content generation system.
Loads persona configurations from config/personas.yaml and provides
weighted random selection for diverse content creation.
"""
import os
import yaml
import random
from typing import Optional
from db import log_event

class Persona:
    """Represents a content generation persona."""
    
    def __init__(self, data: dict):
        self.id = data.get("id", "unknown")
        self.name = data.get("name", "Unknown Persona")
        self.weight = data.get("weight", 0.33)
        self.description = data.get("description", "")
        self.tone = data.get("tone", "professional")
        self.style = data.get("style", "general")
        self.sources = data.get("sources", [])
        self.keywords = data.get("keywords", [])
        self.prompt = data.get("prompt", "").strip()
    
    def __repr__(self):
        return f"<Persona {self.id}: {self.name} (weight={self.weight})>"
    
    def to_dict(self):
        """Convert persona to dict for logging/caching."""
        return {
            "id": self.id,
            "name": self.name,
            "weight": self.weight,
            "tone": self.tone,
            "style": self.style
        }

class PersonaManager:
    """Manages loading and selection of content personas."""
    
    def __init__(self, config_path: str = "config/personas.yaml"):
        self.config_path = config_path
        self.personas = []
        self._load_personas()
    
    def _load_personas(self):
        """Load personas from YAML config."""
        if not os.path.exists(self.config_path):
            log_event("personas", "error", f"Personas config not found: {self.config_path}")
            raise FileNotFoundError(f"Personas config not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if not data or "personas" not in data:
            raise ValueError("Invalid personas.yaml: missing 'personas' key")
        
        for p_data in data["personas"]:
            persona = Persona(p_data)
            self.personas.append(persona)
        
        # Validate weights sum to ~1.0
        total_weight = sum(p.weight for p in self.personas)
        if not (0.95 <= total_weight <= 1.05):
            log_event("personas", "warning", 
                     f"Persona weights sum to {total_weight:.2f}, expected ~1.0")
        
        log_event("personas", "info", 
                 f"Loaded {len(self.personas)} personas from {self.config_path}")
    
    def select_persona(self) -> Persona:
        """
        Select a persona using weighted random selection.
        Returns: Persona instance
        """
        if not self.personas:
            raise ValueError("No personas loaded")
        
        weights = [p.weight for p in self.personas]
        selected = random.choices(self.personas, weights=weights, k=1)[0]
        
        log_event("personas", "info", 
                 f"Selected persona: {selected.name} (weight={selected.weight})",
                 {"persona_id": selected.id})
        
        return selected
    
    def get_persona_by_id(self, persona_id: str) -> Optional[Persona]:
        """Get specific persona by ID."""
        for p in self.personas:
            if p.id == persona_id:
                return p
        return None
    
    def list_personas(self) -> list[Persona]:
        """Get all loaded personas."""
        return self.personas.copy()

# Global persona manager instance
_persona_manager = None

def get_persona_manager() -> PersonaManager:
    """Get or create global PersonaManager instance."""
    global _persona_manager
    if _persona_manager is None:
        _persona_manager = PersonaManager()
    return _persona_manager

def select_persona() -> Persona:
    """Convenience function to select a random persona."""
    return get_persona_manager().select_persona()

