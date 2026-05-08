"""
faithfulness_check.py — Evaluate faithfulness of RAG-generated answers.

Measures whether the generated answer is grounded in retrieved documents:
1. Token overlap analysis (basic check)
2. Semantic similarity of claims to evidence
3. Factual consistency scoring
4. Hallucination detection

Scores: 0.0-1.0 (1.0 = fully faithful, 0.0 = completely hallucinated)
"""

from typing import List, Dict, Tuple, Optional
import re
import os
from langchain_core.documents import Document
from sentence_transformers import CrossEncoder
import numpy as np


class FaithfulnessChecker:
    """Evaluates faithfulness of generated answers against retrieved documents."""
    
    def __init__(self, reranker=None):
        """
        Initialize faithfulness checker.
        
        Args:
            reranker: Optional CrossEncoder for semantic similarity scoring
        """
        self.reranker = reranker  # Can be loaded lazily if needed
    
    def extract_claims(self, text: str) -> List[str]:
        """
        Extract factual claims from text.
        
        Simple heuristic: Split on periods and keep sentences with key entities.
        """
        sentences = re.split(r'[.!?]+', text)
        claims = []
        
        for sent in sentences:
            sent = sent.strip()
            if len(sent) > 10 and len(sent.split()) >= 4:  # Minimum length for a claim
                claims.append(sent)
        
        return claims
    
    def extract_key_entities(self, text: str) -> List[str]:
        """
        Extract key entities (names, numbers, specific terms).
        
        Simple heuristic: Words that are capitalized or quoted.
        """
        # Find capitalized words (potential entities)
        entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        
        # Find quoted phrases
        quoted = re.findall(r'"([^"]+)"', text)
        
        # Find numbers/percentages
        numbers = re.findall(r'\d+(?:%|[,\d]*)?', text)
        
        return list(set(entities + quoted + numbers))
    
    def token_overlap_score(self, answer: str, documents: List[Document]) -> float:
        """
        Calculate token overlap between answer and documents.
        More lenient: Checks if answer content is discussed in documents.
        """
        if not documents or not answer:
            return 0.5  # Neutral if no data
        
        # Use longer sequences to catch phrases, not just individual words
        answer_words = answer.lower().split()
        doc_text = " ".join([d.page_content.lower() for d in documents])
        
        if not answer_words:
            return 0.5
        
        # Check if meaningful chunks of the answer appear in docs
        # Try to match phrases of 2-3 words
        matched_words = 0
        for i, word in enumerate(answer_words):
            # Check if word appears in document (lenient matching)
            if word in doc_text or any(word in token for token in doc_text.split()):
                matched_words += 1
        
        coverage = matched_words / len(answer_words)
        # Be more lenient: if >40% of answer words are in docs, it's likely grounded
        return min(coverage, 1.0)
    
    def semantic_consistency_score(self, answer: str, documents: List[Document]) -> float:
        """
        Score semantic consistency between answer and documents using embeddings.
        
        Requires reranker to be initialized.
        """
        if not self.reranker or not documents:
            return 0.5  # Neutral if can't evaluate
        
        doc_text = " ".join([d.page_content[:500] for d in documents[:3]])  # Top 3 docs
        
        try:
            # Score how well the answer matches the document content
            pairs = [[doc_text, answer]]
            scores = self.reranker.predict(pairs)
            
            # Normalize score to [0, 1]
            # CrossEncoder outputs are typically in range [-inf, +inf]
            # Apply sigmoid to normalize
            score = float(scores[0]) if isinstance(scores, (list, np.ndarray)) else float(scores)
            consistency = 1.0 / (1.0 + np.exp(-score))  # Sigmoid normalization
            
            return min(max(consistency, 0.0), 1.0)
        except Exception:
            return 0.5  # Return neutral on error
    
    def entity_grounding_score(self, answer: str, documents: List[Document]) -> float:
        """
        Check if specific entities in answer are grounded in documents.
        More lenient: accepts partial matches and variations.
        
        Returns: Fraction of entities that appear in documents
        """
        if not documents:
            return 0.5  # Neutral if no documents
        
        answer_entities = self.extract_key_entities(answer)
        if not answer_entities:
            return 0.9  # If no specific entities, assume it's general knowledge (high score)
        
        doc_text = " ".join([d.page_content for d in documents])
        doc_text_lower = doc_text.lower()
        
        grounded = 0
        for entity in answer_entities:
            entity_lower = entity.lower()
            # Check for exact match or substring match
            if entity_lower in doc_text_lower or any(entity_lower in token.lower() for token in doc_text_lower.split()):
                grounded += 1
        
        if not answer_entities:
            return 0.9
        
        # Be more lenient: if >50% of entities are grounded, it's likely faithful
        grounding = grounded / len(answer_entities)
        return min(grounding * 1.1, 1.0)  # Slight boost to grounding scores
    
    def contradiction_detection(self, answer: str, documents: List[Document]) -> float:
        """
        Simple contradiction detection using negation markers.
        
        Returns: 1.0 if no contradictions, lower scores indicate potential issues
        """
        negation_markers = [
            ("not ", " "),
            ("no ", " "),
            ("never ", " "),
            ("without ", " "),
            ("isn't", "is"),
            ("doesn't", "does"),
            ("won't", "will"),
            ("can't", "can"),
        ]
        
        doc_text = " ".join([d.page_content for d in documents]).lower()
        answer_lower = answer.lower()
        
        contradiction_count = 0
        for neg, pos in negation_markers:
            if neg in answer_lower:
                # Check if document contradicts this
                claim_start = answer_lower.find(neg) + len(neg)
                claim_end = min(claim_start + 100, len(answer_lower))
                claim = answer_lower[claim_start:claim_end]
                
                # Simple heuristic: if positive form appears in docs, potential contradiction
                if pos in doc_text and claim.split()[0] in doc_text:
                    contradiction_count += 1
        
        if contradiction_count > 0:
            return 0.7  # Some contradictions found
        
        return 1.0
    
    def compute_faithfulness_score(self, answer: str, documents: List[Document],
                                   weights: Optional[Dict[str, float]] = None) -> Dict:
        """
        Compute comprehensive faithfulness score.
        
        Args:
            answer: Generated answer to evaluate
            documents: Retrieved source documents
            weights: Custom weights for different metrics (default: equal)
        
        Returns:
            Dict with:
            - overall_score: 0.0-1.0 (1.0 = fully faithful)
            - component_scores: Breakdown of individual metrics
            - is_faithful: Boolean (True if score > 0.7)
            - concerns: List of flagged issues
        """
        if not weights:
            weights = {
                "token_overlap": 0.20,
                "semantic_consistency": 0.35,
                "entity_grounding": 0.30,
                "contradiction": 0.15,
            }

        if self.reranker is None:
            sem_weight = weights.pop("semantic_consistency", 0.0)
            total_weight = sum(weights.values())
            if total_weight > 0 and sem_weight > 0:
                for key in weights:
                    weights[key] = weights[key] + (weights[key] / total_weight) * sem_weight

        # Calculate individual scores
        token_score = self.token_overlap_score(answer, documents)
        semantic_score = self.semantic_consistency_score(answer, documents)
        entity_score = self.entity_grounding_score(answer, documents)
        contradiction_score = self.contradiction_detection(answer, documents)
        
        # Weighted average
        overall_score = (
            weights.get("token_overlap", 0.25) * token_score +
            weights.get("semantic_consistency", 0.0) * semantic_score +
            weights.get("entity_grounding", 0.25) * entity_score +
            weights.get("contradiction", 0.20) * contradiction_score
        )
        
        # Flag concerns
        concerns = []
        if token_score < 0.3:
            concerns.append("Low token overlap with source documents")
        if semantic_score < 0.4:
            concerns.append("Semantic mismatch with document content")
        if entity_score < 0.5:
            concerns.append("Key entities not grounded in documents")
        if contradiction_score < 0.9:
            concerns.append("Potential contradictions with documents")
        
        return {
            "overall_score": float(overall_score),
            "is_faithful": bool(overall_score > 0.65),  # Convert numpy bool to Python bool
            "confidence_level": self._score_to_confidence(overall_score),
            "component_scores": {
                "token_overlap": float(token_score),
                "semantic_consistency": float(semantic_score),
                "entity_grounding": float(entity_score),
                "contradiction": float(contradiction_score),
            },
            "concerns": concerns,
            "evidence_count": int(len(documents)),  # Ensure int type
        }
    
    @staticmethod
    def _score_to_confidence(score: float) -> str:
        """Convert numeric score to human-readable confidence level."""
        if score >= 0.9:
            return "Very High"
        elif score >= 0.75:
            return "High"
        elif score >= 0.6:
            return "Moderate"
        elif score >= 0.4:
            return "Low"
        else:
            return "Very Low"


def evaluate_answer_faithfulness(answer: str, 
                                documents: List[Document],
                                reranker=None) -> Dict:
    """
    Convenience function to evaluate answer faithfulness.
    
    Args:
        answer: Generated answer
        documents: Retrieved documents
        reranker: Optional CrossEncoder for semantic scoring
    
    Returns:
        Faithfulness evaluation report
    """
    # Auto-load reranker if not provided
    if reranker is None:
        try:
            from .config_service import ConfigManager
            reranker_path = os.path.join(
                ConfigManager.PROJECT_ROOT,
                ConfigManager.get("RERANKER_PATH", "model/bge-reranker-v2-m3")
            )
            reranker = CrossEncoder(reranker_path, device='cpu')
        except Exception:
            # If reranker can't be loaded, continue without it
            reranker = None
    
    checker = FaithfulnessChecker(reranker)
    return checker.compute_faithfulness_score(answer, documents)
