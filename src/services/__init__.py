"""Permission checking service for multi-user access control."""

from typing import Optional, List, Dict, Any

from src.config import Config
from src.dataset_catalog import DatasetCatalog
from src.models import User, db


class PermissionService:
    """Service for checking and managing dataset permissions."""

    @staticmethod
    def _catalog() -> DatasetCatalog:
        return DatasetCatalog(Config())

    @staticmethod
    def _username_for_user_id(user_id: int) -> Optional[str]:
        user = db.session.get(User, user_id)
        return user.username if user else None

    @staticmethod
    def can_read(user_id: int, dataset_id: int) -> bool:
        """Check if user can read dataset."""
        username = PermissionService._username_for_user_id(user_id)
        if not username:
            return False
        return PermissionService._catalog().can_access(dataset_id, username, "read")

    @staticmethod
    def can_write(user_id: int, dataset_id: int) -> bool:
        """Check if user can modify dataset."""
        username = PermissionService._username_for_user_id(user_id)
        if not username:
            return False
        return PermissionService._catalog().can_access(dataset_id, username, "write")

    @staticmethod
    def can_admin(user_id: int, dataset_id: int) -> bool:
        """Check if user can administer dataset (share, delete)."""
        username = PermissionService._username_for_user_id(user_id)
        if not username:
            return False
        return PermissionService._catalog().can_access(dataset_id, username, "admin")

    @staticmethod
    def get_user_datasets(user_id: int, include_public: bool = True) -> List[Dict[str, Any]]:
        """Get all datasets accessible by user."""
        username = PermissionService._username_for_user_id(user_id)
        if not username:
            return []
        return PermissionService._catalog().list_accessible_datasets(
            username=username,
            include_public=include_public,
            limit=5000,
        )

    @staticmethod
    def grant_access(owner_id: int, dataset_id: int, user_id: int,
                    access_level: str = 'read') -> bool:
        """Grant access to dataset. Only owner or admin can grant."""
        owner_username = PermissionService._username_for_user_id(owner_id)
        target_username = PermissionService._username_for_user_id(user_id)
        if not owner_username or not target_username:
            return False

        return PermissionService._catalog().grant_access(
            dataset_id=dataset_id,
            granter_username=owner_username,
            target_username=target_username,
            level=access_level,
        )

    @staticmethod
    def revoke_access(revoker_id: int, dataset_id: int, user_id: int) -> bool:
        """Revoke access from dataset."""
        revoker_username = PermissionService._username_for_user_id(revoker_id)
        target_username = PermissionService._username_for_user_id(user_id)
        if not revoker_username or not target_username:
            return False

        return PermissionService._catalog().revoke_access(
            dataset_id=dataset_id,
            revoker_username=revoker_username,
            target_username=target_username,
        )
