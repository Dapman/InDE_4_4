"""
Simplified TRIZ Contradiction Matrix - Coaching Reference

NOT the full 39x39 Altshuller matrix. A coaching-friendly version
covering the 18 most common technical parameters that innovators
encounter. Maps improving/worsening parameter pairs to recommended
inventive principles.

The coach uses this when an innovator identifies conflicting parameters:
"I need it to be stronger [improving] but it gets heavier [worsening]."
The matrix suggests: Principles 1, 8, 15, 40 -> Coach guides exploration.

Parameters selected for coverage of common innovation challenges
across mechanical, software, process, and service domains.
"""

from typing import Dict, List, Tuple


# 18 simplified parameters (covering the most common innovation challenges)
TRIZ_PARAMETERS: Dict[str, Dict] = {
    "strength": {
        "id": 1,
        "description": "Structural integrity, load-bearing capacity",
        "aliases": ["strong", "sturdy", "robust", "rigid"]
    },
    "weight": {
        "id": 2,
        "description": "Mass, heaviness, resource consumption",
        "aliases": ["heavy", "light", "mass", "bulk"]
    },
    "speed": {
        "id": 3,
        "description": "Velocity, throughput, processing rate",
        "aliases": ["fast", "slow", "quick", "rapid", "velocity"]
    },
    "reliability": {
        "id": 4,
        "description": "Consistency, uptime, failure resistance",
        "aliases": ["reliable", "consistent", "uptime", "dependable"]
    },
    "complexity": {
        "id": 5,
        "description": "Number of parts, interdependencies, cognitive load",
        "aliases": ["complex", "simple", "complicated", "intricate"]
    },
    "energy_efficiency": {
        "id": 6,
        "description": "Power consumption, energy per unit output",
        "aliases": ["efficient", "power", "energy", "consumption"]
    },
    "manufacturing_ease": {
        "id": 7,
        "description": "Producibility, assembly simplicity",
        "aliases": ["manufacturable", "producible", "buildable"]
    },
    "precision": {
        "id": 8,
        "description": "Accuracy, tolerance, exactness",
        "aliases": ["accurate", "precise", "exact", "tolerance"]
    },
    "stability": {
        "id": 9,
        "description": "Resistance to perturbation, steady-state",
        "aliases": ["stable", "steady", "balanced", "consistent"]
    },
    "adaptability": {
        "id": 10,
        "description": "Flexibility, configurability, responsiveness to change",
        "aliases": ["flexible", "adaptable", "configurable", "versatile"]
    },
    "durability": {
        "id": 11,
        "description": "Lifespan, wear resistance, longevity",
        "aliases": ["durable", "lasting", "longevity", "wear-resistant"]
    },
    "cost": {
        "id": 12,
        "description": "Financial expense, resource investment",
        "aliases": ["expensive", "cheap", "affordable", "price"]
    },
    "temperature_tolerance": {
        "id": 13,
        "description": "Operating range, thermal resistance",
        "aliases": ["heat", "cold", "thermal", "temperature"]
    },
    "ease_of_use": {
        "id": 14,
        "description": "Usability, learning curve, accessibility",
        "aliases": ["usable", "intuitive", "user-friendly", "accessible"]
    },
    "safety": {
        "id": 15,
        "description": "Harm prevention, risk mitigation",
        "aliases": ["safe", "hazard", "risk", "protection"]
    },
    "throughput": {
        "id": 16,
        "description": "Volume, capacity, production rate",
        "aliases": ["capacity", "volume", "output", "production"]
    },
    "scalability": {
        "id": 17,
        "description": "Growth capacity, performance under load",
        "aliases": ["scalable", "growth", "expansion", "scale"]
    },
    "environmental_impact": {
        "id": 18,
        "description": "Sustainability, waste, emissions",
        "aliases": ["sustainable", "green", "eco-friendly", "emissions"]
    },
}


# Contradiction matrix: {(improving_param, worsening_param): [principle_numbers]}
# Each entry maps a conflict pair to 2-4 recommended inventive principles
# These are the most common innovation contradictions based on TRIZ research
CONTRADICTION_MATRIX: Dict[Tuple[str, str], List[int]] = {
    # Strength contradictions
    ("strength", "weight"): [1, 8, 15, 40],
    ("strength", "cost"): [1, 28, 15, 17],
    ("strength", "manufacturing_ease"): [1, 40, 27, 28],
    ("strength", "complexity"): [40, 26, 27, 1],
    ("strength", "adaptability"): [15, 35, 1, 40],

    # Speed contradictions
    ("speed", "precision"): [10, 13, 28, 38],
    ("speed", "energy_efficiency"): [8, 15, 35, 38],
    ("speed", "reliability"): [21, 35, 11, 28],
    ("speed", "cost"): [10, 28, 35, 7],
    ("speed", "safety"): [21, 35, 11, 28],

    # Reliability contradictions
    ("reliability", "complexity"): [13, 35, 1, 25],
    ("reliability", "cost"): [3, 10, 28, 40],
    ("reliability", "speed"): [11, 35, 27, 28],
    ("reliability", "weight"): [1, 11, 27, 35],
    ("reliability", "adaptability"): [15, 10, 35, 1],

    # Adaptability contradictions
    ("adaptability", "stability"): [15, 35, 18, 34],
    ("adaptability", "cost"): [15, 1, 35, 10],
    ("adaptability", "reliability"): [15, 10, 35, 1],
    ("adaptability", "complexity"): [1, 6, 15, 35],
    ("adaptability", "precision"): [15, 10, 35, 4],

    # Durability contradictions
    ("durability", "weight"): [40, 26, 27, 1],
    ("durability", "cost"): [27, 40, 28, 3],
    ("durability", "manufacturing_ease"): [27, 40, 1, 35],
    ("durability", "adaptability"): [35, 15, 40, 27],

    # Ease of use contradictions
    ("ease_of_use", "complexity"): [2, 5, 13, 25],
    ("ease_of_use", "precision"): [4, 17, 34, 10],
    ("ease_of_use", "cost"): [25, 2, 6, 13],
    ("ease_of_use", "reliability"): [2, 13, 25, 35],

    # Safety contradictions
    ("safety", "cost"): [22, 35, 1, 24],
    ("safety", "speed"): [21, 35, 11, 28],
    ("safety", "throughput"): [35, 22, 1, 11],
    ("safety", "ease_of_use"): [22, 1, 35, 24],

    # Throughput contradictions
    ("throughput", "precision"): [10, 28, 35, 4],
    ("throughput", "cost"): [10, 35, 17, 7],
    ("throughput", "quality"): [10, 35, 28, 24],
    ("throughput", "energy_efficiency"): [35, 38, 19, 20],

    # Scalability contradictions
    ("scalability", "complexity"): [1, 5, 6, 17],
    ("scalability", "cost"): [6, 1, 7, 35],
    ("scalability", "reliability"): [1, 35, 10, 6],
    ("scalability", "performance"): [1, 7, 35, 17],

    # Energy efficiency contradictions
    ("energy_efficiency", "reliability"): [19, 35, 38, 2],
    ("energy_efficiency", "throughput"): [35, 38, 19, 20],
    ("energy_efficiency", "speed"): [35, 38, 8, 15],
    ("energy_efficiency", "strength"): [35, 8, 2, 40],

    # Environmental impact contradictions
    ("environmental_impact", "cost"): [35, 22, 28, 34],
    ("environmental_impact", "throughput"): [35, 22, 15, 34],
    ("environmental_impact", "reliability"): [35, 22, 34, 2],
    ("environmental_impact", "performance"): [35, 22, 2, 34],

    # Manufacturing ease contradictions
    ("manufacturing_ease", "precision"): [1, 10, 25, 13],
    ("manufacturing_ease", "strength"): [28, 40, 1, 27],
    ("manufacturing_ease", "durability"): [27, 1, 40, 35],

    # Cost contradictions (as improving parameter)
    ("cost", "reliability"): [10, 28, 40, 3],
    ("cost", "strength"): [28, 27, 1, 40],
    ("cost", "precision"): [25, 28, 1, 10],
    ("cost", "durability"): [27, 28, 40, 3],

    # Precision contradictions
    ("precision", "speed"): [28, 10, 4, 35],
    ("precision", "cost"): [28, 10, 25, 1],
    ("precision", "throughput"): [28, 10, 4, 35],

    # Weight contradictions (as improving - reducing weight)
    ("weight", "strength"): [8, 1, 40, 15],
    ("weight", "durability"): [27, 40, 1, 8],
    ("weight", "reliability"): [11, 1, 27, 35],

    # Complexity contradictions (as improving - reducing complexity)
    ("complexity", "reliability"): [13, 1, 35, 25],
    ("complexity", "adaptability"): [6, 1, 35, 15],
    ("complexity", "ease_of_use"): [2, 5, 13, 25],
}


def lookup_principles(improving: str, worsening: str) -> List[int]:
    """
    Look up recommended inventive principles for a contradiction.

    Returns list of principle numbers, or empty list if the parameter
    pair isn't in the simplified matrix. In that case, the coach falls
    back to LLM reasoning about the contradiction.

    Args:
        improving: The parameter the innovator wants to improve
        worsening: The parameter that gets worse when improving

    Returns:
        List of recommended principle numbers (1-40)
    """
    # Normalize parameter names
    improving = improving.lower().replace("-", "_").replace(" ", "_")
    worsening = worsening.lower().replace("-", "_").replace(" ", "_")

    key = (improving, worsening)
    reverse_key = (worsening, improving)

    # Check direct lookup first
    if key in CONTRADICTION_MATRIX:
        return CONTRADICTION_MATRIX[key]

    # Try reverse lookup (some contradictions are symmetric)
    if reverse_key in CONTRADICTION_MATRIX:
        return CONTRADICTION_MATRIX[reverse_key]

    return []


def get_parameter_info(param_name: str) -> Dict:
    """
    Get information about a contradiction parameter.

    Args:
        param_name: Name of the parameter

    Returns:
        Parameter dict with id, description, aliases
    """
    normalized = param_name.lower().replace("-", "_").replace(" ", "_")
    return TRIZ_PARAMETERS.get(normalized, {})


def find_parameter_by_alias(alias: str) -> str:
    """
    Find a parameter name by its alias.

    Args:
        alias: An alias or keyword for the parameter

    Returns:
        The canonical parameter name, or empty string if not found
    """
    normalized = alias.lower()
    for param_name, param_info in TRIZ_PARAMETERS.items():
        if normalized in param_info.get("aliases", []):
            return param_name
    return ""


def get_all_contradictions_for_parameter(param_name: str) -> List[Tuple[str, str, List[int]]]:
    """
    Get all contradictions involving a specific parameter.

    Args:
        param_name: The parameter to search for

    Returns:
        List of (improving, worsening, principles) tuples
    """
    normalized = param_name.lower().replace("-", "_").replace(" ", "_")
    results = []

    for (improving, worsening), principles in CONTRADICTION_MATRIX.items():
        if improving == normalized or worsening == normalized:
            results.append((improving, worsening, principles))

    return results


def format_contradiction_for_coaching(
    improving: str,
    worsening: str,
    principles: List[int]
) -> str:
    """
    Format a contradiction and its principles for coaching context.

    Args:
        improving: The parameter being improved
        worsening: The parameter getting worse
        principles: List of recommended principle numbers

    Returns:
        Formatted string for coaching context
    """
    improving_info = get_parameter_info(improving)
    worsening_info = get_parameter_info(worsening)

    lines = [
        f"Contradiction: Improving {improving} ({improving_info.get('description', '')}) "
        f"worsens {worsening} ({worsening_info.get('description', '')})",
        f"Recommended inventive principles: {', '.join(str(p) for p in principles)}"
    ]

    return "\n".join(lines)
