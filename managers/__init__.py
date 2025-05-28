# This file makes the managers directory a Python package
from managers.user_manager_postgres import UserManager

__all__ = ['UserManager']
