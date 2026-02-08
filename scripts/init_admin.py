#!/usr/bin/env python3
"""Initialize Flask-Admin database tables."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.web import create_app
from src.models import db


def init_admin():
    """Create admin tables."""
    app = create_app()

    with app.app_context():
        # Create tables
        db.create_all()
        print("✓ Admin tables created successfully")

        # Import existing indicators
        from src.config import Config
        from src.models import Indicator

        config = Config()
        indicators = config.get_indicators()

        count = 0
        for ind in indicators:
            # Check if already exists
            existing = Indicator.query.filter_by(
                indicator_id=ind.get('id', ind.get('indicator_id'))
            ).first()

            if not existing:
                indicator = Indicator(
                    indicator_id=ind.get('id', ind.get('indicator_id')),
                    name=ind.get('name', ind.get('indicator_name', '')),
                    description=ind.get('description'),
                    source=ind.get('source', 'manual'),
                    topic=ind.get('topic'),
                    tags=str(ind.get('tags', [])),
                    active=True
                )
                db.session.add(indicator)
                count += 1

        db.session.commit()
        print(f"✓ Imported {count} indicators")


if __name__ == '__main__':
    init_admin()
