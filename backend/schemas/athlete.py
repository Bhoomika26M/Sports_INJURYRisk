from pydantic import BaseModel


class AthleteCreate(BaseModel):
    name: str
    age: int | None = None
    gender: str | None = None
    sport: str | None = None