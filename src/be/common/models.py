"""
SQLAlchemy ORM models for InsightFlow.

These models represent the database schema and serve as the return type
for InsightRepository adapters. They are consumed by route handlers and
processing services through the repository interface.
"""

from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship

Base = declarative_base()


class FileMetadata(Base):
    """Stores metadata about uploaded files."""

    __tablename__ = "file_metadata"

    id = Column(Integer, primary_key=True)
    file_id = Column(String(255), unique=True, index=True)
    user_id = Column(String(255))
    filename = Column(String(255))
    file_size = Column(Integer)
    file_type = Column(String(255))
    upload_time = Column(DateTime, default=datetime.now)
    stored_filename = Column(String(255))


class Chunk(Base):
    """Represents a processed segment of a file."""

    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True)
    user_id = Column(String(255))
    name = Column(String(255))
    file_id = Column(String(255), ForeignKey("file_metadata.file_id"), index=True)
    file_name = Column(String(255))
    content = Column(Text)
    summary = Column(Text)
    size = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    questions = relationship("Question", back_populates="chunk")


class Question(Base):
    """Stores a question generated from a file chunk."""

    __tablename__ = "questions"

    id = Column(Integer, primary_key=True)
    file_id = Column(String(255), ForeignKey("file_metadata.file_id"), index=True)
    user_id = Column(String(255))
    chunk_id = Column(Integer, ForeignKey("chunks.id"))
    question = Column(Text)
    label = Column(String(255))
    answered = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    chunk = relationship("Chunk", back_populates="questions")
