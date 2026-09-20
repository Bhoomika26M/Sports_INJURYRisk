from sqlalchemy import Column, Integer, String, Float, Text

from app.database import Base


class Athlete(Base):

    __tablename__ = "athletes"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    athlete_id = Column(
        String,
        unique=True,
        nullable=False
    )

    sport_type = Column(String)

    position = Column(String)

    age = Column(Integer)

    height = Column(Float)

    weight = Column(Float)

    injury_history = Column(Text)

    training_load = Column(Float)