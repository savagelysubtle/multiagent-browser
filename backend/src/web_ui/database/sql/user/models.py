"""
SQL models for user-related data.
"""

from sqlalchemy import Column, String, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    name = Column(String)
    password_hash = Column(String)
    picture = Column(String)
    is_active = Column(Boolean, default=True)
    auth_provider = Column(String, default='local')
    created_at = Column(String, nullable=False)
    last_login = Column(String)

    # Relationship to UserState
    user_state = relationship("UserState", uselist=False, back_populates="user")

class UserState(Base):
    __tablename__ = 'user_states'

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, unique=True)
    state_json = Column(Text, nullable=False)

    # Relationship to User
    user = relationship("User", back_populates="user_state")