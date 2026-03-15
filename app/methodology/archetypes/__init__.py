"""
InDE Methodology Archetypes

v3.7.1 provides 6 archetypes:
1. lean_startup     - "Does this work?"
2. design_thinking  - "Does anyone want this?"
3. stage_gate       - "Can we build this responsibly?"
4. triz             - "How do we solve the impossible?" (v3.6.1)
5. blue_ocean       - "Are we in the right ocean?"      (v3.6.1)
6. ad_hoc           - "What does my best work look like?" (NEW v3.7.1)
"""

from .triz import TRIZ_ARCHETYPE
from .blue_ocean import BLUE_OCEAN_ARCHETYPE
from .adhoc import (
    ADHOC_ARCHETYPE,
    NON_DIRECTIVE_COACHING_MODIFIER,
    is_adhoc_pursuit,
    get_adhoc_confirmation,
    get_nondirective_modifier,
    get_synthesis_message,
)

__all__ = [
    "TRIZ_ARCHETYPE",
    "BLUE_OCEAN_ARCHETYPE",
    "ADHOC_ARCHETYPE",
    "NON_DIRECTIVE_COACHING_MODIFIER",
    "is_adhoc_pursuit",
    "get_adhoc_confirmation",
    "get_nondirective_modifier",
    "get_synthesis_message",
]
