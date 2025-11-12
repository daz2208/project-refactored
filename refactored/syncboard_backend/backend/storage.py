"""
Persistence layer for documents, metadata, clusters, and users.

Simplified from board-based system to direct document storage with clustering.
"""

import json
import os
import tempfile
import shutil
from typing import Tuple, Dict, List

from .models import DocumentMetadata, Cluster, Concept
from .vector_store import VectorStore


def load_storage(
    path: str,
    vector_store: VectorStore
) -> Tuple[Dict[int, str], Dict[int, DocumentMetadata], Dict[int, Cluster], Dict[str, str]]:
    """
    Load documents, metadata, clusters, and users from JSON file.

    Args:
        path: Path to the JSON file
        vector_store: VectorStore instance where document embeddings will be added

    Returns:
        Tuple of (documents, metadata, clusters, users) where:
        - documents: Dict[doc_id, full_text]
        - metadata: Dict[doc_id, DocumentMetadata]
        - clusters: Dict[cluster_id, Cluster]
        - users: Dict[username, hashed_password]
    """
    documents: Dict[int, str] = {}
    metadata: Dict[int, DocumentMetadata] = {}
    clusters: Dict[int, Cluster] = {}
    users: Dict[str, str] = {}
    
    if not os.path.exists(path):
        return documents, metadata, clusters, users
    
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Load documents and rebuild vector store
    doc_texts: List[str] = data.get('documents', [])
    for idx, text in enumerate(doc_texts):
        vector_store.add_document(text)
        documents[idx] = text
    
    # Load metadata
    for meta_data in data.get('metadata', []):
        # Convert concepts list to Concept objects
        concepts = [Concept(**c) for c in meta_data.get('concepts', [])]
        meta = DocumentMetadata(
            doc_id=meta_data['doc_id'],
            owner=meta_data['owner'],
            source_type=meta_data['source_type'],
            source_url=meta_data.get('source_url'),
            filename=meta_data.get('filename'),
            concepts=concepts,
            skill_level=meta_data.get('skill_level', 'unknown'),
            cluster_id=meta_data.get('cluster_id'),
            ingested_at=meta_data['ingested_at'],
            content_length=meta_data['content_length'],
            image_path=meta_data.get('image_path')
        )
        metadata[meta['doc_id']] = meta
    
    # Load clusters
    for cluster_data in data.get('clusters', []):
        cluster = Cluster(**cluster_data)
        clusters[cluster.id] = cluster
    
    # Load users
    users = data.get('users', {})
    
    return documents, metadata, clusters, users


def save_storage(
    path: str,
    documents: Dict[int, str],
    metadata: Dict[int, DocumentMetadata],
    clusters: Dict[int, Cluster],
    users: Dict[str, str]
) -> None:
    """
    Persist documents, metadata, clusters, and users to disk atomically.

    Uses atomic write (write to temp file, then rename) to prevent corruption
    if the process crashes mid-write.

    Args:
        path: Path to the JSON file to write
        documents: Mapping of doc_id to full text
        metadata: Mapping of doc_id to DocumentMetadata
        clusters: Mapping of cluster_id to Cluster
        users: Mapping of username to hashed password
    """
    data = {
        'documents': [documents[idx] for idx in sorted(documents.keys())],
        'metadata': [meta.dict() for meta in metadata.values()],
        'clusters': [cluster.dict() for cluster in clusters.values()],
        'users': users,
    }

    # Atomic write: write to temp file in same directory, then rename
    # This ensures the file is never partially written
    dir_path = os.path.dirname(os.path.abspath(path)) or '.'

    with tempfile.NamedTemporaryFile(
        mode='w',
        encoding='utf-8',
        dir=dir_path,
        delete=False,
        suffix='.tmp'
    ) as tmp_file:
        json.dump(data, tmp_file, ensure_ascii=False, indent=2)
        tmp_file.flush()
        os.fsync(tmp_file.fileno())  # Force write to disk
        tmp_path = tmp_file.name

    # Atomic rename (POSIX systems guarantee atomicity)
    shutil.move(tmp_path, path)
