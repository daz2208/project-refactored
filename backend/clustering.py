"""
Automatic clustering of documents by similarity.
Groups related content together based on concepts and topics.
"""

import logging
from typing import List, Dict, Optional
from collections import Counter
from .models import Cluster, Concept

logger = logging.getLogger(__name__)


class ClusteringEngine:
    """Manages document clustering."""
    
    def __init__(self):
        self.similarity_threshold = 0.5  # How similar to join existing cluster
    
    def find_best_cluster(
        self,
        doc_concepts: List[Dict],
        suggested_name: str,
        existing_clusters: Dict[int, Cluster]
    ) -> Optional[int]:
        """
        Find best matching cluster for new document.
        
        Args:
            doc_concepts: Concepts from new document
            suggested_name: AI's suggested cluster name
            existing_clusters: Current clusters
        
        Returns:
            cluster_id if match found, None if should create new
        """
        if not existing_clusters:
            return None
        
        doc_concept_names = {c["name"].lower() for c in doc_concepts}
        
        best_match = None
        best_score = 0.0
        
        for cluster_id, cluster in existing_clusters.items():
            # Compare concepts
            cluster_concepts = {c.lower() for c in cluster.primary_concepts}
            
            if not doc_concept_names or not cluster_concepts:
                continue
            
            # Jaccard similarity
            intersection = len(doc_concept_names & cluster_concepts)
            union = len(doc_concept_names | cluster_concepts)
            similarity = intersection / union if union > 0 else 0
            
            # Boost if suggested name matches
            if suggested_name.lower() in cluster.name.lower():
                similarity += 0.2
            
            if similarity > best_score:
                best_score = similarity
                best_match = cluster_id
        
        # Only return match if above threshold
        if best_score >= self.similarity_threshold:
            logger.info(f"Found matching cluster {best_match} (similarity: {best_score:.2f})")
            return best_match
        
        return None
    
    def create_cluster(
        self,
        doc_id: int,
        name: str,
        concepts: List[Dict],
        skill_level: str,
        existing_clusters: Dict[int, Cluster]
    ) -> int:
        """Create new cluster."""
        cluster_id = max(existing_clusters.keys()) + 1 if existing_clusters else 0
        
        # Extract most common concepts (up to 5)
        concept_names = [c["name"] for c in concepts]
        primary = [name for name, _ in Counter(concept_names).most_common(5)]
        
        cluster = Cluster(
            id=cluster_id,
            name=name,
            primary_concepts=primary,
            doc_ids=[doc_id],
            skill_level=skill_level,
            doc_count=1
        )
        
        existing_clusters[cluster_id] = cluster
        logger.info(f"Created new cluster {cluster_id}: {name}")
        
        return cluster_id
    
    def add_to_cluster(
        self,
        cluster_id: int,
        doc_id: int,
        clusters: Dict[int, Cluster]
    ):
        """Add document to existing cluster."""
        if cluster_id not in clusters:
            logger.error(f"Cluster {cluster_id} not found")
            return
        
        cluster = clusters[cluster_id]
        if doc_id not in cluster.doc_ids:
            cluster.doc_ids.append(doc_id)
            cluster.doc_count = len(cluster.doc_ids)
            logger.info(f"Added doc {doc_id} to cluster {cluster_id} ({cluster.name})")
