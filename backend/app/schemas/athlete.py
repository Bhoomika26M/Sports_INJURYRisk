from pydantic import BaseModel


class AthleteCreate(BaseModel):

    athlete_id: str
    sport_type: str
    position: str
    age: int
    height: float
    weight: float
    injury_history: str
    training_load: float