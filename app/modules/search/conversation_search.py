"""
Conversation Search Service
Full-text search across coaching session history within a pursuit.
Returns contextual results with a 3-turn window around each match.

v3.13: Innovator Experience Polish
"""

import logging
from typing import Optional, List

from fastapi import HTTPException

logger = logging.getLogger(__name__)

# Number of turns before/after a match to include as context
CONTEXT_WINDOW = 1


class ConversationSearchService:
    """
    Full-text search across coaching conversation history.

    Uses MongoDB text indexes for efficient search.
    Returns results with context turns for useful viewing.
    """

    def __init__(self, db):
        """
        Initialize with database connection.

        Args:
            db: Database instance (expects db.db for raw pymongo access)
        """
        self.db = db.db if hasattr(db, 'db') else db

    def search(
        self,
        pursuit_id: str,
        user_id: str,
        query: str,
        limit: int = 20,
        offset: int = 0
    ) -> dict:
        """
        Search coaching conversation history within a pursuit.

        Authorization: user must own the pursuit.
        Returns windowed results with context turns.

        Args:
            pursuit_id: Pursuit to search within
            user_id: Requesting user (must own the pursuit)
            query: Search terms
            limit: Max results to return
            offset: Pagination offset

        Returns:
            {
                "total_matches": int,
                "query": str,
                "pursuit_id": str,
                "results": [
                    {
                        "timestamp": str,
                        "pursuit_phase": str (if available),
                        "match_turn": {
                            "role": "user" | "assistant",
                            "content": str,
                            "score": float
                        },
                        "context_before": [turn, ...],
                        "context_after": [turn, ...]
                    }
                ]
            }
        """
        # Verify pursuit ownership
        self._verify_access(pursuit_id, user_id)

        if not query or len(query.strip()) < 2:
            return {
                "total_matches": 0,
                "query": query,
                "pursuit_id": pursuit_id,
                "results": []
            }

        # MongoDB text search scoped to this pursuit
        # Using $text with textScore for relevance ordering
        pipeline = [
            {
                "$match": {
                    "pursuit_id": pursuit_id,
                    "$text": {"$search": query}
                }
            },
            {
                "$addFields": {
                    "score": {"$meta": "textScore"}
                }
            },
            {"$sort": {"score": -1, "timestamp": -1}},
            {"$skip": offset},
            {"$limit": limit},
            {
                "$project": {
                    "_id": 1,
                    "pursuit_id": 1,
                    "role": 1,
                    "content": 1,
                    "timestamp": 1,
                    "metadata": 1,
                    "score": 1
                }
            }
        ]

        try:
            matches = list(self.db.conversation_history.aggregate(pipeline))
        except Exception as e:
            # Text search may fail if index not yet created
            logger.warning(f"Text search failed: {e}. Falling back to regex.")
            matches = self._fallback_regex_search(pursuit_id, query, limit, offset)

        # For each match, fetch context window
        results = []
        for match in matches:
            match_timestamp = match.get("timestamp")

            context_before = self._get_context_turns(
                pursuit_id,
                match_timestamp,
                direction="before"
            )
            context_after = self._get_context_turns(
                pursuit_id,
                match_timestamp,
                direction="after"
            )

            # Extract phase from metadata if available
            metadata = match.get("metadata", {})
            pursuit_phase = metadata.get("phase", "")

            results.append({
                "timestamp": str(match_timestamp) if match_timestamp else "",
                "pursuit_phase": pursuit_phase,
                "match_turn": {
                    "role": match.get("role", ""),
                    "content": match.get("content", ""),
                    "score": match.get("score", 0.0)
                },
                "context_before": context_before,
                "context_after": context_after
            })

        # Get total count (separate query without pagination)
        try:
            total = self.db.conversation_history.count_documents({
                "pursuit_id": pursuit_id,
                "$text": {"$search": query}
            })
        except Exception:
            # Fallback total count
            total = len(results)

        return {
            "total_matches": total,
            "query": query,
            "pursuit_id": pursuit_id,
            "results": results
        }

    def _get_context_turns(
        self,
        pursuit_id: str,
        reference_timestamp,
        direction: str
    ) -> List[dict]:
        """
        Fetch turns immediately before or after a matched turn.
        Uses timestamp for positioning within a pursuit's conversation.

        Args:
            pursuit_id: The pursuit containing the conversation
            reference_timestamp: Timestamp of the matched turn
            direction: "before" or "after"

        Returns:
            List of context turns
        """
        if not reference_timestamp:
            return []

        if direction == "before":
            query_filter = {
                "pursuit_id": pursuit_id,
                "timestamp": {"$lt": reference_timestamp}
            }
            sort = [("timestamp", -1)]
        else:
            query_filter = {
                "pursuit_id": pursuit_id,
                "timestamp": {"$gt": reference_timestamp}
            }
            sort = [("timestamp", 1)]

        turns = list(self.db.conversation_history.find(
            query_filter,
            {"role": 1, "content": 1, "timestamp": 1, "_id": 0}
        ).sort(sort).limit(CONTEXT_WINDOW))

        # For "before", reverse to get chronological order
        if direction == "before":
            turns.reverse()

        return [
            {
                "role": t.get("role"),
                "content": t.get("content"),
                "timestamp": str(t.get("timestamp", ""))
            }
            for t in turns
        ]

    def _fallback_regex_search(
        self,
        pursuit_id: str,
        query: str,
        limit: int,
        offset: int
    ) -> List[dict]:
        """
        Fallback search using regex when text index is not available.
        Less efficient but functional.
        """
        import re
        # Escape regex special characters
        escaped_query = re.escape(query)

        matches = list(self.db.conversation_history.find(
            {
                "pursuit_id": pursuit_id,
                "content": {"$regex": escaped_query, "$options": "i"}
            },
            {
                "_id": 1,
                "pursuit_id": 1,
                "role": 1,
                "content": 1,
                "timestamp": 1,
                "metadata": 1
            }
        ).sort("timestamp", -1).skip(offset).limit(limit))

        # Add a fake score for compatibility
        for m in matches:
            m["score"] = 1.0

        return matches

    def _verify_access(self, pursuit_id: str, user_id: str) -> None:
        """
        Verify the user owns this pursuit.

        Args:
            pursuit_id: The pursuit to check
            user_id: The user to verify

        Raises:
            HTTPException: 403 if not authorized
        """
        pursuit = self.db.pursuits.find_one({
            "pursuit_id": pursuit_id,
            "user_id": user_id
        })

        if not pursuit:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to search this pursuit's conversations"
            )
