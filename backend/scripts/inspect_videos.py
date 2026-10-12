import asyncio
from app.database import async_session_factory
from sqlalchemy import text

async def check():
    async with async_session_factory() as session:
        res = await session.execute(text("SELECT id, movement_type, camera_view, processing_status, athlete_id, coverage_caveat, original_filename FROM videos ORDER BY created_at DESC"))
        rows = res.fetchall()
        print(f"Total videos: {len(rows)}")
        for r in rows:
            print(dict(r._mapping))

if __name__ == "__main__":
    asyncio.run(check())
