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


class Downloadable:
    def get_storage_location(self):
        raise NotImplemented

    def get_output_filename(self):
        raise NotImplemented


class File(Base, Downloadable):
    __tablename__ = 'files'
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    storage_location = Column(String(200), nullable=False)
    upload_date = Column(DateTime, nullable=True, default=datetime.datetime.utcnow)

    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship(User)

    def get_storage_location(self):
        return self.storage_location

    def get_output_filename(self):
        return self.name

    def __repr__(self):
        return self.name


class Page(Base, Downloadable):
    __tablename__ = 'pages'
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    storage_location = Column(String(200), nullable=False)

    file_id = Column(Integer, ForeignKey('files.id'))
    file = relationship(File)

    def get_storage_location(self):
        return self.storage_location

    def get_output_filename(self):
        return '{f} - {p}'.format(f=self.file.name, p=self.name)

    def __repr__(self):
        return self.name


users_table = User.__table__
metadata = Base.metadata


def create_all():
    metadata.create_all(engine)