from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime


engine = create_engine('sqlite:///pdf_storage.db', echo=True)

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(30), nullable=False)

    def __repr__(self):
        return self.username


class File(Base):
    __tablename__ = 'files'
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    storage_location = Column(String(200), nullable=False)
    upload_date = Column(DateTime, nullable=True, default=datetime.datetime.utcnow)

    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship(User)

    def __repr__(self):
        return self.name


users_table = User.__table__
metadata = Base.metadata


def create_all():
    metadata.create_all(engine)