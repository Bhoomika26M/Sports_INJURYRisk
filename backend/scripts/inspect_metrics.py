import asyncio
from app.database import async_session_factory
from sqlalchemy import text

async def check():
    async with async_session_factory() as s:
        res = await s.execute(text("""
            SELECT metric_name, confidence, COUNT(*) as cnt, AVG(metric_value) as avg_val
            FROM biomechanical_metrics
            WHERE video_id = 'ede826b0-bd59-48ad-98af-271227c08d8f'
            GROUP BY metric_name, confidence
        """))
        for r in res.fetchall():
            print(dict(r._mapping))

if __name__ == "__main__":
    asyncio.run(check())
