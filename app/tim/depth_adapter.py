"""
TIM Depth Adapter — v4.3

Translates TIM milestone events to depth-framed labels for novice users.

The adapter maps internal milestone keys to Display Label Registry entries
in 'tim_depth_labels'. For example:
  - VISION_FIRST     → "Your story first took shape"
  - FEAR_SURFACED    → "You started protecting your idea"
  - FIRST_HYPOTHESIS → "You formed your first real question"

This allows TIM to remain unchanged internally while presenting
depth-framed milestone labels to novice users.
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class TIMDepthAdapter:
    """
    Adapts TIM milestone data to depth-framed display labels.

    Usage:
        adapter = TIMDepthAdapter(experience_mode='novice')
        label = adapter.get_milestone_label('vision_first')
        # Returns: "Your story first took shape"
    """

    def __init__(self, experience_mode: str = 'novice'):
        self.experience_mode = experience_mode
        self._labels = None

    def _get_display_labels(self):
        """Lazy-load display labels."""
        if self._labels is None:
            from shared.display_labels import DisplayLabels
            self._labels = DisplayLabels
        return self._labels

    def get_milestone_label(self, milestone_key: str) -> str:
        """
        Returns the depth-framed label for a TIM milestone.

        Args:
            milestone_key: Internal milestone key (e.g., 'vision_first')

        Returns:
            Display label from registry, or formatted fallback
        """
        labels = self._get_display_labels()

        # Try to get from tim_depth_labels
        label = labels.get('tim_depth_labels', milestone_key.lower(), 'label')

        # If not found, format the key nicely
        if label == milestone_key.lower():
            # Convert snake_case to title case
            label = milestone_key.replace('_', ' ').title()

        return label

    def adapt_milestone(self, milestone: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adapts a TIM milestone document for frontend display.

        Args:
            milestone: TIM milestone document with 'key', 'timestamp', etc.

        Returns:
            Milestone with depth-framed 'display_label' added
        """
        key = milestone.get('key', milestone.get('milestone_key', ''))

        adapted = {
            **milestone,
            'display_label': self.get_milestone_label(key),
            'experience_mode': self.experience_mode,
        }

        # For expert mode, also include internal key
        if self.experience_mode == 'expert':
            adapted['internal_key'] = key

        return adapted

    def adapt_timeline(self, milestones: list) -> list:
        """
        Adapts a list of TIM milestones for frontend display.

        Args:
            milestones: List of TIM milestone documents

        Returns:
            List of adapted milestones with depth-framed labels
        """
        return [self.adapt_milestone(m) for m in milestones]


# Convenience function for one-off label lookups
def get_depth_label(milestone_key: str, experience_mode: str = 'novice') -> str:
    """
    Get depth-framed label for a milestone key.

    Args:
        milestone_key: Internal milestone key
        experience_mode: User's experience mode

    Returns:
        Display label string
    """
    adapter = TIMDepthAdapter(experience_mode)
    return adapter.get_milestone_label(milestone_key)
