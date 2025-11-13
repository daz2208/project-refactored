#!/usr/bin/env python3
"""
=============================================================================
SyncBoard 3.0 Knowledge Bank - File to Database Migration (Phase 6)
=============================================================================
Migrates data from file-based storage (storage.json) to PostgreSQL database.
Usage: python scripts/migrate_file_to_db.py [storage_file_path]
=============================================================================
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database import get_db_context, init_db
from backend.db_models import DBUser, DBCluster, DBDocument, DBConcept, DBVectorDocument

def load_storage_file(storage_path: str = "storage.json"):
    """Load data from storage.json file."""
    path = Path(storage_path)
    if not path.exists():
        print(f"❌ ERROR: Storage file not found: {storage_path}")
        sys.exit(1)
    
    with open(path, 'r') as f:
        data = json.load(f)
    
    return data

def migrate_to_database(storage_data: dict):
    """Migrate data from storage.json format to database."""
    
    print("🔄 Starting migration...")
    
    # Initialize database tables
    init_db()
    print("✅ Database initialized")
    
    with get_db_context() as db:
        # Step 1: Migrate users
        print("\n📝 Migrating users...")
        users_data = storage_data.get('users', {})
        user_count = 0
        for username, user_data in users_data.items():
            # Check if user already exists
            existing = db.query(DBUser).filter_by(username=username).first()
            if existing:
                print(f"   ⏭️  Skipping existing user: {username}")
                continue
            
            db_user = DBUser(
                username=username,
                hashed_password=user_data.get('hashed_password', ''),
                created_at=datetime.utcnow()
            )
            db.add(db_user)
            user_count += 1
        
        db.commit()
        print(f"✅ Migrated {user_count} users")
        
        # Step 2: Migrate clusters
        print("\n📝 Migrating clusters...")
        clusters_data = storage_data.get('clusters', [])
        cluster_map = {}  # old_id -> new_id
        cluster_count = 0
        
        for cluster_data in clusters_data:
            old_id = cluster_data.get('id')
            
            db_cluster = DBCluster(
                name=cluster_data.get('name', 'Untitled'),
                primary_concepts=cluster_data.get('primary_concepts', []),
                skill_level=cluster_data.get('skill_level'),
                created_at=datetime.utcnow()
            )
            db.add(db_cluster)
            db.flush()  # Get the new ID
            
            cluster_map[old_id] = db_cluster.id
            cluster_count += 1
        
        db.commit()
        print(f"✅ Migrated {cluster_count} clusters")
        
        # Step 3: Migrate documents and their content
        print("\n📝 Migrating documents...")
        metadata = storage_data.get('metadata', [])
        documents = storage_data.get('documents', {})
        doc_count = 0
        concept_count = 0
        
        for meta in metadata:
            doc_id = meta.get('doc_id')
            old_cluster_id = meta.get('cluster_id')
            new_cluster_id = cluster_map.get(old_cluster_id) if old_cluster_id is not None else None
            
            # Create document metadata
            db_doc = DBDocument(
                doc_id=doc_id,
                owner_username=meta.get('owner', 'unknown'),
                cluster_id=new_cluster_id,
                source_type=meta.get('source_type', 'text'),
                source_url=meta.get('source_url'),
                filename=meta.get('filename'),
                image_path=meta.get('image_path'),
                content_length=meta.get('content_length'),
                skill_level=meta.get('skill_level'),
                ingested_at=datetime.fromisoformat(meta['ingested_at']) if meta.get('ingested_at') else datetime.utcnow()
            )
            db.add(db_doc)
            db.flush()  # Get the database ID
            
            # Migrate concepts
            for concept_data in meta.get('concepts', []):
                db_concept = DBConcept(
                    document_id=db_doc.id,
                    name=concept_data.get('name', 'unknown'),
                    category=concept_data.get('category', 'concept'),
                    confidence=concept_data.get('confidence', 0.8),
                    created_at=datetime.utcnow()
                )
                db.add(db_concept)
                concept_count += 1
            
            # Migrate document content
            content = documents.get(str(doc_id), '')
            if content:
                db_vector_doc = DBVectorDocument(
                    doc_id=doc_id,
                    content=content,
                    created_at=datetime.utcnow()
                )
                db.add(db_vector_doc)
            
            doc_count += 1
        
        db.commit()
        print(f"✅ Migrated {doc_count} documents")
        print(f"✅ Migrated {concept_count} concepts")
    
    print("\n🎉 Migration completed successfully!")
    print("\n📊 Summary:")
    print(f"   Users: {user_count}")
    print(f"   Clusters: {cluster_count}")
    print(f"   Documents: {doc_count}")
    print(f"   Concepts: {concept_count}")

if __name__ == "__main__":
    storage_path = sys.argv[1] if len(sys.argv) > 1 else "storage.json"
    
    print("=" * 80)
    print("SyncBoard 3.0 - File to Database Migration")
    print("=" * 80)
    print(f"\nStorage file: {storage_path}")
    
    # Load storage data
    storage_data = load_storage_file(storage_path)
    print(f"✅ Loaded storage file")
    
    # Migrate
    migrate_to_database(storage_data)
    
    print("\n✅ Migration complete! You can now use database storage.")
    print("   To switch permanently, update DATABASE_URL in .env")
