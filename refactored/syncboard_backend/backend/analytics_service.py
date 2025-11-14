"""
Analytics service for knowledge bank insights (Phase 7.1).

Provides comprehensive analytics including:
- Overview statistics
- Time-series data (document growth)
- Distribution metrics (clusters, concepts, skill levels)
- Activity tracking
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import Counter, defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from .db_models import (
    DBDocument,
    DBCluster,
    DBConcept,
    DBUser,
    DBVectorDocument
)

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for generating analytics and insights."""

    def __init__(self, db: Session):
        """Initialize analytics service with database session."""
        self.db = db

    def get_overview_stats(self, username: Optional[str] = None) -> Dict[str, Any]:
        """
        Get high-level overview statistics.

        Args:
            username: Optional username to filter by user's documents only

        Returns:
            Dictionary with overview stats
        """
        query = self.db.query(DBDocument)
        if username:
            query = query.filter(DBDocument.owner_username == username)

        total_docs = query.count()

        # Get cluster count
        cluster_query = self.db.query(DBCluster)
        total_clusters = cluster_query.count()

        # Get concept count
        concept_query = self.db.query(DBConcept)
        if username:
            # Count distinct concepts from user's documents
            concept_query = concept_query.join(DBDocument).filter(
                DBDocument.owner_username == username
            )
        total_concepts = concept_query.distinct().count()

        # Documents added today
        today = datetime.utcnow().date()
        docs_today = query.filter(
            func.date(DBDocument.created_at) == today
        ).count()

        # Documents added this week
        week_ago = datetime.utcnow() - timedelta(days=7)
        docs_this_week = query.filter(
            DBDocument.created_at >= week_ago
        ).count()

        # Documents added this month
        month_ago = datetime.utcnow() - timedelta(days=30)
        docs_this_month = query.filter(
            DBDocument.created_at >= month_ago
        ).count()

        return {
            "total_documents": total_docs,
            "total_clusters": total_clusters,
            "total_concepts": total_concepts,
            "documents_today": docs_today,
            "documents_this_week": docs_this_week,
            "documents_this_month": docs_this_month,
            "last_updated": datetime.utcnow().isoformat()
        }

    def get_time_series_data(
        self,
        days: int = 30,
        username: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get time-series data for document additions.

        Args:
            days: Number of days to look back
            username: Optional username to filter by user's documents

        Returns:
            Dictionary with daily document counts
        """
        start_date = datetime.utcnow() - timedelta(days=days)

        query = self.db.query(
            func.date(DBDocument.created_at).label('date'),
            func.count(DBDocument.doc_id).label('count')
        ).filter(
            DBDocument.created_at >= start_date
        )

        if username:
            query = query.filter(DBDocument.owner_username == username)

        results = query.group_by(
            func.date(DBDocument.created_at)
        ).order_by('date').all()

        # Fill in missing dates with 0
        date_counts = {str(r.date): r.count for r in results}

        labels = []
        data = []
        current_date = start_date.date()
        end_date = datetime.utcnow().date()

        while current_date <= end_date:
            labels.append(current_date.strftime('%Y-%m-%d'))
            data.append(date_counts.get(str(current_date), 0))
            current_date += timedelta(days=1)

        return {
            "labels": labels,
            "data": data,
            "period_days": days
        }

    def get_cluster_distribution(
        self,
        username: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get distribution of documents across clusters.

        Args:
            username: Optional username to filter by user's documents

        Returns:
            Dictionary with cluster names and document counts
        """
        query = self.db.query(
            DBCluster.name,
            func.count(DBDocument.doc_id).label('doc_count')
        ).join(
            DBDocument,
            DBDocument.cluster_id == DBCluster.id
        )

        if username:
            query = query.filter(DBDocument.owner_username == username)

        results = query.group_by(
            DBCluster.name
        ).order_by(
            func.count(DBDocument.doc_id).desc()
        ).limit(10).all()  # Top 10 clusters

        return {
            "labels": [r.name for r in results],
            "data": [r.doc_count for r in results]
        }

    def get_skill_level_distribution(
        self,
        username: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get distribution of documents by skill level.

        Args:
            username: Optional username to filter by user's documents

        Returns:
            Dictionary with skill levels and counts
        """
        query = self.db.query(
            DBDocument.skill_level,
            func.count(DBDocument.doc_id).label('count')
        )

        if username:
            query = query.filter(DBDocument.owner_username == username)

        results = query.group_by(
            DBDocument.skill_level
        ).all()

        return {
            "labels": [r.skill_level or "Unknown" for r in results],
            "data": [r.count for r in results]
        }

    def get_source_type_distribution(
        self,
        username: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get distribution of documents by source type.

        Args:
            username: Optional username to filter by user's documents

        Returns:
            Dictionary with source types and counts
        """
        query = self.db.query(
            DBDocument.source_type,
            func.count(DBDocument.doc_id).label('count')
        )

        if username:
            query = query.filter(DBDocument.owner_username == username)

        results = query.group_by(
            DBDocument.source_type
        ).all()

        return {
            "labels": [r.source_type or "Unknown" for r in results],
            "data": [r.count for r in results]
        }

    def get_top_concepts(
        self,
        limit: int = 10,
        username: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get most frequently occurring concepts.

        Args:
            limit: Maximum number of concepts to return
            username: Optional username to filter by user's documents

        Returns:
            List of concepts with their occurrence counts
        """
        query = self.db.query(
            DBConcept.name,  # FIX: Field is 'name' not 'concept_text'
            func.count(DBConcept.id).label('count')
        )

        if username:
            query = query.join(DBDocument).filter(
                DBDocument.owner_username == username
            )

        results = query.group_by(
            DBConcept.name  # FIX: Field is 'name' not 'concept_text'
        ).order_by(
            func.count(DBConcept.id).desc()
        ).limit(limit).all()

        return [
            {"concept": r.name, "count": r.count}  # FIX: Field is 'name' not 'concept_text'
            for r in results
        ]

    def get_recent_activity(
        self,
        limit: int = 10,
        username: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent document activity.

        Args:
            limit: Maximum number of activities to return
            username: Optional username to filter by user's documents

        Returns:
            List of recent document additions
        """
        query = self.db.query(DBDocument).order_by(
            DBDocument.created_at.desc()
        )

        if username:
            query = query.filter(DBDocument.owner_username == username)

        results = query.limit(limit).all()

        return [
            {
                "doc_id": doc.doc_id,
                "source_type": doc.source_type,
                "skill_level": doc.skill_level,
                "cluster_id": doc.cluster_id,
                "created_at": doc.created_at.isoformat() if doc.created_at else None
            }
            for doc in results
        ]

    def get_complete_analytics(
        self,
        username: Optional[str] = None,
        time_period_days: int = 30
    ) -> Dict[str, Any]:
        """
        Get all analytics in a single call.

        Args:
            username: Optional username to filter by user's documents
            time_period_days: Number of days for time-series data

        Returns:
            Complete analytics dictionary
        """
        return {
            "overview": self.get_overview_stats(username),
            "time_series": self.get_time_series_data(time_period_days, username),
            "cluster_distribution": self.get_cluster_distribution(username),
            "skill_level_distribution": self.get_skill_level_distribution(username),
            "source_type_distribution": self.get_source_type_distribution(username),
            "top_concepts": self.get_top_concepts(10, username),
            "recent_activity": self.get_recent_activity(10, username)
        }
