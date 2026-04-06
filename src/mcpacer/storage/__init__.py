"""Storage modules for the Strava Running Coach."""

from mcpacer.storage.base import BaseStorage, get_data_dir
from mcpacer.storage.coaching import CoachingStorage
from mcpacer.storage.runs import RunStorage
from mcpacer.storage.training_plans import TrainingPlanStorage

__all__ = [
    "BaseStorage",
    "get_data_dir",
    "RunStorage",
    "TrainingPlanStorage",
    "CoachingStorage",
]
