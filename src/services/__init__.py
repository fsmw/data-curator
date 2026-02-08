"""Permission checking service for multi-user access control."""

from typing import Optional, List
from src.models import Dataset, UserDatasetAccess, User, db


class PermissionService:
    """Service for checking and managing dataset permissions."""

    @staticmethod
    def can_read(user_id: int, dataset_id: int) -> bool:
        """Check if user can read dataset."""
        dataset = Dataset.query.get(dataset_id)
        if not dataset:
            return False
        return dataset.can_access(user_id, 'read')

    @staticmethod
    def can_write(user_id: int, dataset_id: int) -> bool:
        """Check if user can modify dataset."""
        dataset = Dataset.query.get(dataset_id)
        if not dataset:
            return False
        return dataset.can_access(user_id, 'write')

    @staticmethod
    def can_admin(user_id: int, dataset_id: int) -> bool:
        """Check if user can administer dataset (share, delete)."""
        dataset = Dataset.query.get(dataset_id)
        if not dataset:
            return False
        return dataset.can_access(user_id, 'admin')

    @staticmethod
    def get_user_datasets(user_id: int, include_public: bool = True) -> List[Dataset]:
        """Get all datasets accessible by user."""
        # User's own datasets
        own_datasets = Dataset.query.filter_by(owner_id=user_id).all()

        # Datasets shared with user
        shared = Dataset.query.join(UserDatasetAccess).filter(
            UserDatasetAccess.user_id == user_id
        ).all()

        # Public datasets
        public = []
        if include_public:
            public = Dataset.query.filter_by(is_public=True).all()

        # Combine and remove duplicates
        all_datasets = {d.id: d for d in own_datasets + shared + public}
        return list(all_datasets.values())

    @staticmethod
    def grant_access(owner_id: int, dataset_id: int, user_id: int,
                    access_level: str = 'read') -> bool:
        """Grant access to dataset. Only owner or admin can grant."""
        dataset = Dataset.query.get(dataset_id)
        if not dataset:
            return False

        # Check if owner or admin
        if dataset.owner_id != owner_id:
            # Check if granter has admin permission
            granter_access = UserDatasetAccess.query.filter_by(
                user_id=owner_id, dataset_id=dataset_id
            ).first()
            if not granter_access or granter_access.access_level != 'admin':
                return False

        # Grant access
        dataset.share_with(user_id, access_level, owner_id)
        db.session.commit()
        return True

    @staticmethod
    def revoke_access(revoker_id: int, dataset_id: int, user_id: int) -> bool:
        """Revoke access from dataset."""
        dataset = Dataset.query.get(dataset_id)
        if not dataset:
            return False

        # Only owner, admin, or the granter can revoke
        if dataset.owner_id != revoker_id:
            revoker_access = UserDatasetAccess.query.filter_by(
                user_id=revoker_id, dataset_id=dataset_id
            ).first()
            if not revoker_access or revoker_access.access_level != 'admin':
                return False

        dataset.revoke_access(user_id)
        db.session.commit()
        return True
