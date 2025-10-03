"""
SQL models for user-related data.
"""

from sqlalchemy import Boolean, Column, ForeignKey, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    name = Column(String)
    password_hash = Column(String)
    picture = Column(String)
    is_active = Column(Boolean, default=True)
    auth_provider = Column(String, default="local")
    created_at = Column(String, nullable=False)
    last_login = Column(String)


class UserState(Base):
    __tablename__ = "user_states"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)
    state_json = Column(Text, nullable=False)

    # Relationship to User
    user = relationship("User", back_populates="user_state")


# Add the back reference to User
User.user_state = relationship("UserState", uselist=False, back_populates="user")

# Export for easier importing
__all__ = ["Base", "User", "UserState"]
