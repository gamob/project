"""
conversation_context.py — Enhanced chat history memory for RAG context awareness.

Integrates session-based chat history to:
1. Extract contextual information from previous messages
2. Generate context-aware follow-up queries
3. Avoid redundant searches in the same conversation
4. Maintain conversation state for multi-turn interactions
"""

import json
import logging
from collections import Counter
from typing import Optional, List, Dict, Tuple
from ..storage.chat_store import load_session_messages

logger = logging.getLogger(__name__)


class ConversationContext:
    """Manages conversation state and generates context-aware queries."""
    
    def __init__(self, session_id: Optional[int] = None, max_history: int = 10):
        """
        Initialize conversation context.
        
        Args:
            session_id: Current chat session ID (from chat_store)
            max_history: Maximum messages to consider (newer messages prioritized)
        """
        self.session_id = session_id
        self.max_history = max_history
        self.conversation_state = {}
    
    def load_session_context(self) -> List[Dict]:
        """
        Load all messages from current session.
        
        Returns:
            List of message dictionaries. Empty list if no session or on error.
        """
        if not self.session_id:
            return []
        
        try:
            messages = load_session_messages(self.session_id)
            if messages is None:
                logger.warning(f"Session {self.session_id} returned None from database")
                return []
            
            # Keep only recent messages
            return messages[-self.max_history:]
        except Exception as e:
            logger.error(f"❌ Failed to load session context for session {self.session_id}: {e}")
            # Return empty list on error to allow graceful degradation
            return []
    
    def extract_context_entities(self, messages: List[Dict]) -> Dict:
        """
        Extract key entities and topics from conversation history.
        
        Returns dict with:
        - main_topic: The primary subject being discussed
        - mentioned_entities: List of important entities
        - previous_questions: Recent user questions for deduplication
        - last_context: The immediately previous user message
        """
        context = {
            "main_topic": "",
            "mentioned_entities": set(),
            "previous_questions": [],
            "last_context": "",
            "conversation_flow": []
        }
        
        # Process messages in reverse order (most recent first)
        user_messages = [m for m in messages if m.get("role") == "user"]
        assistant_messages = [m for m in messages if m.get("role") == "assistant"]
        
        if user_messages:
            # Most recent user message is the immediate context
            context["last_context"] = user_messages[-1]["content"]
            
            # Extract common words from all user messages as entities (optimized)
            all_user_text = " ".join([m["content"].lower() for m in user_messages])
            
            # Filter and count words in one pass using Counter
            STOPWORDS = {"about", "what", "where", "which", "please", "the", "a", "an", "and", "or"}
            words = [w for w in all_user_text.split() 
                    if len(w) > 4 and w not in STOPWORDS]
            
            # High-frequency words (2+ occurrences) are likely entities
            word_freq = Counter(words)
            context["mentioned_entities"] = {w for w, count in word_freq.items() if count >= 2}
            
            # Previous questions for deduplication check
            context["previous_questions"] = [m["content"][:100] for m in user_messages[-3:]]
        
        # Determine main topic from first user message (most reliable)
        if user_messages:
            first_msg = user_messages[0]["content"].split()[0:10]
            context["main_topic"] = " ".join(first_msg)
        
        context["conversation_flow"] = [
            (m.get("role"), m["content"][:100]) for m in messages[-5:]
        ]
        
        return context
    
    def is_followup_question(self, query: str, context: Dict) -> bool:
        """
        Detect if query is a follow-up vs. new topic.
        
        Returns True if the query seems to be continuing the previous discussion.
        """
        referential_words = {
            "it", "that", "this", "they", "them", "more", "again",
            "explain", "clarify", "elaborate", "tell me more", "what about"
        }
        
        query_lower = query.lower()
        has_referential = any(word in query_lower for word in referential_words)
        
        # Check if similar to previous questions
        if context["previous_questions"]:
            last_q = context["previous_questions"][-1].lower()
            overlap = len(set(query_lower.split()) & set(last_q.split()))
            if overlap > len(query_lower.split()) * 0.4:
                return True
        
        return has_referential
    
    def generate_context_aware_query(self, user_query: str) -> Tuple[str, str]:
        """
        Generate an improved query incorporating conversation context.
        
        Returns:
            (primary_query, context_note)
        """
        if not self.session_id:
            return user_query, ""
        
        messages = self.load_session_context()
        context = self.extract_context_entities(messages)
        
        # If it's a follow-up, enhance with previous context
        if self.is_followup_question(user_query, context):
            # Add context from last message
            enhanced = f"{user_query}. Context: {context['last_context'][:100]}"
            return enhanced, "follow-up"
        
        # If there's a main topic established, add it
        if context["main_topic"]:
            # Check if query is in a different domain
            if not any(entity in user_query.lower() for entity in context["mentioned_entities"]):
                # New topic detected
                return user_query, "new-topic"
        
        return user_query, "standalone"
    
    def get_summary_for_context_window(self, max_chars: int = 1000) -> str:
        """
        Generate a concise summary of conversation for inclusion in LLM context.
        
        Useful for providing conversation state to the LLM without exceeding
        token limits.
        """
        if not self.session_id:
            return ""
        
        messages = self.load_session_context()
        context = self.extract_context_entities(messages)
        
        summary = []
        if context["main_topic"]:
            summary.append(f"Topic: {context['main_topic']}")
        
        if context["mentioned_entities"]:
            summary.append(f"Key entities: {', '.join(list(context['mentioned_entities'])[:5])}")
        
        # Add recent Q&A pairs for context
        summary.append("Recent conversation:")
        for role, content in context["conversation_flow"][-3:]:
            prefix = "Q:" if role == "user" else "A:"
            summary.append(f"{prefix} {content}...")
        
        full_summary = "\n".join(summary)
        if len(full_summary) > max_chars:
            full_summary = full_summary[:max_chars] + "..."
        
        return full_summary


def integrate_conversation_context(query: str, session_id: Optional[int] = None) -> Dict:
    """
    Convenience function to get enhanced query and context info.
    
    Returns dict with:
    - original_query: The input query
    - enhanced_query: Query improved with context
    - context_type: 'follow-up', 'new-topic', or 'standalone'
    - session_summary: Brief conversation state summary
    """
    ctx = ConversationContext(session_id)
    
    enhanced, ctx_type = ctx.generate_context_aware_query(query)
    summary = ctx.get_summary_for_context_window()
    
    return {
        "original_query": query,
        "enhanced_query": enhanced,
        "context_type": ctx_type,
        "session_summary": summary,
        "conversation_context": ctx
    }
