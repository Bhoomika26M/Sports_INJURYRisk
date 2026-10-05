from fastapi import FastAPI
from routes.general import router
from database.database import test_connection
from models.athlete import Athlete
from models.user import User
from database.database import test_connection, create_tables


app = FastAPI(
    title="Sports Injury Risk Detection API",
    version="1.0.0"
)

app.include_router(router)


test_connection()

test_connection()
create_tables()