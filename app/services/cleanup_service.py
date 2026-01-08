"""
Cleanup Service for GDPR Soft Delete Automation

Handles automatic permanent deletion of soft-deleted user data after retention period.
This service should be run as a scheduled job (e.g., Cloud Scheduler + Cloud Functions).
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from google.cloud import firestore

logger = logging.getLogger(__name__)


class CleanupService:
    """Service for cleaning up soft-deleted user data after retention period."""
    
    def __init__(self, db: firestore.Client):
        """Initialize cleanup service.
        
        Args:
            db: Firestore client instance
        """
        self.db = db
    
    async def find_users_for_permanent_deletion(self) -> List[Dict[str, Any]]:
        """Find users whose retention period has expired.
        
        Returns:
            List of user documents ready for permanent deletion
        """
        try:
            now = datetime.utcnow()
            
            # Query users marked as deleted with expired retention period
            users_ref = self.db.collection('users')
            query = users_ref.where('deleted', '==', True) \
                             .where('permanent_deletion_date', '<=', now)
            
            users_to_delete = []
            for doc in query.stream():
                user_data = doc.to_dict()
                user_data['user_id'] = doc.id
                users_to_delete.append(user_data)
            
            logger.info(f"Found {len(users_to_delete)} users ready for permanent deletion")
            return users_to_delete
            
        except Exception as e:
            logger.error(f"Error finding users for deletion: {e}", exc_info=True)
            raise
    
    async def permanently_delete_user(self, user_id: str) -> bool:
        """Permanently delete all user data from all collections.
        
        Args:
            user_id: User ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Starting permanent deletion for user {user_id}")
            
            # Collections to delete from
            collections = [
                'users',
                'quiz_results',
                'conversations',
                'study_materials',
                'consent_records',
                'privacy_settings',
                'data_subject_requests',
                'audit_logs'
            ]
            
            deleted_counts = {}
            
            for collection_name in collections:
                try:
                    # Delete all documents for this user in this collection
                    count = await self._delete_user_documents(collection_name, user_id)
                    deleted_counts[collection_name] = count
                    logger.info(f"Deleted {count} documents from {collection_name} for user {user_id}")
                except Exception as e:
                    logger.error(f"Error deleting from {collection_name} for user {user_id}: {e}")
                    # Continue with other collections even if one fails
            
            # Log the permanent deletion
            try:
                self.db.collection('deletion_audit_logs').add({
                    'user_id': user_id,
                    'deletion_timestamp': datetime.utcnow(),
                    'deleted_collections': deleted_counts,
                    'total_documents_deleted': sum(deleted_counts.values())
                })
            except Exception as e:
                logger.error(f"Error logging permanent deletion: {e}")
            
            logger.info(f"Permanent deletion completed for user {user_id}. "
                       f"Total documents deleted: {sum(deleted_counts.values())}")
            return True
            
        except Exception as e:
            logger.error(f"Error permanently deleting user {user_id}: {e}", exc_info=True)
            return False
    
    async def _delete_user_documents(self, collection_name: str, user_id: str) -> int:
        """Delete all documents for a user in a specific collection.
        
        Args:
            collection_name: Name of the collection
            user_id: User ID
            
        Returns:
            Number of documents deleted
        """
        try:
            # Query documents for this user
            docs_ref = self.db.collection(collection_name).where('user_id', '==', user_id)
            docs = docs_ref.stream()
            
            # Delete in batches to avoid timeout
            batch = self.db.batch()
            count = 0
            batch_size = 0
            
            for doc in docs:
                batch.delete(doc.reference)
                count += 1
                batch_size += 1
                
                # Commit batch every 500 documents
                if batch_size >= 500:
                    batch.commit()
                    batch = self.db.batch()
                    batch_size = 0
            
            # Commit remaining documents
            if batch_size > 0:
                batch.commit()
            
            return count
            
        except Exception as e:
            logger.error(f"Error deleting documents from {collection_name}: {e}")
            raise
    
    async def run_cleanup(self, dry_run: bool = False) -> Dict[str, Any]:
        """Run the cleanup process for all expired users.
        
        Args:
            dry_run: If True, only report what would be deleted without actually deleting
            
        Returns:
            Dictionary with cleanup results
        """
        try:
            start_time = datetime.utcnow()
            
            # Find users ready for deletion
            users_to_delete = await self.find_users_for_permanent_deletion()
            
            results = {
                'start_time': start_time.isoformat(),
                'dry_run': dry_run,
                'users_found': len(users_to_delete),
                'users_deleted': 0,
                'users_failed': 0,
                'errors': []
            }
            
            if dry_run:
                logger.info(f"DRY RUN: Would delete {len(users_to_delete)} users")
                results['users_to_delete'] = [u['user_id'] for u in users_to_delete]
                return results
            
            # Delete each user
            for user in users_to_delete:
                user_id = user['user_id']
                try:
                    success = await self.permanently_delete_user(user_id)
                    if success:
                        results['users_deleted'] += 1
                    else:
                        results['users_failed'] += 1
                        results['errors'].append({
                            'user_id': user_id,
                            'error': 'Deletion returned False'
                        })
                except Exception as e:
                    results['users_failed'] += 1
                    results['errors'].append({
                        'user_id': user_id,
                        'error': str(e)
                    })
                    logger.error(f"Failed to delete user {user_id}: {e}")
            
            end_time = datetime.utcnow()
            results['end_time'] = end_time.isoformat()
            results['duration_seconds'] = (end_time - start_time).total_seconds()
            
            logger.info(f"Cleanup completed: {results['users_deleted']} deleted, "
                       f"{results['users_failed']} failed, "
                       f"duration: {results['duration_seconds']}s")
            
            return results
            
        except Exception as e:
            logger.error(f"Error running cleanup: {e}", exc_info=True)
            raise
    
    async def send_deletion_notifications(self, users: List[Dict[str, Any]]) -> None:
        """Send notifications before permanent deletion (optional).
        
        Args:
            users: List of users about to be permanently deleted
        """
        # This could send final notifications to users
        # e.g., "Your data will be permanently deleted in 7 days"
        # Implementation depends on email service
        pass


# Cloud Function entry point for scheduled cleanup
async def scheduled_cleanup_handler(event, context):
    """Cloud Function handler for scheduled cleanup.
    
    This function should be triggered by Cloud Scheduler.
    
    Args:
        event: Cloud Scheduler event
        context: Cloud Function context
    """
    from app.services.gcp_service import get_firestore_client
    
    try:
        logger.info("Starting scheduled GDPR cleanup job")
        
        # Initialize Firestore
        db = get_firestore_client()
        
        # Create cleanup service
        cleanup_service = CleanupService(db)
        
        # Run cleanup (not dry run)
        results = await cleanup_service.run_cleanup(dry_run=False)
        
        logger.info(f"Cleanup job completed: {results}")
        
        # Send alert if there were failures
        if results['users_failed'] > 0:
            logger.error(f"Cleanup job had {results['users_failed']} failures: {results['errors']}")
        
        return results
        
    except Exception as e:
        logger.error(f"Cleanup job failed: {e}", exc_info=True)
        raise


# Manual cleanup script
if __name__ == "__main__":
    import asyncio
    from app.services.gcp_service import get_firestore_client
    
    async def main():
        """Run cleanup manually."""
        import sys
        
        dry_run = '--dry-run' in sys.argv
        
        print(f"Running GDPR cleanup (dry_run={dry_run})...")
        
        db = get_firestore_client()
        cleanup_service = CleanupService(db)
        
        results = await cleanup_service.run_cleanup(dry_run=dry_run)
        
        print("\nCleanup Results:")
        print(f"  Users found: {results['users_found']}")
        print(f"  Users deleted: {results['users_deleted']}")
        print(f"  Users failed: {results['users_failed']}")
        print(f"  Duration: {results['duration_seconds']}s")
        
        if results['errors']:
            print("\nErrors:")
            for error in results['errors']:
                print(f"  - {error['user_id']}: {error['error']}")
    
    asyncio.run(main())

