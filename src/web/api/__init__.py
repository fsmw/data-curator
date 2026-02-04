"""
API Blueprint for the Mises Data Curator.

This module consolidates all API endpoints under a single Blueprint
to improve organization and maintainability.
"""

from flask import Blueprint

# Create the main API blueprint
api_bp = Blueprint(
    "api",
    __name__,
    url_prefix="/api"
)

# Import route modules to register them
from . import search
from . import datasets
from . import download
from . import compare
from . import copilot
from . import analysis
from . import editorial
from . import agent
