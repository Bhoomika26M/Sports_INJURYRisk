import asyncio
from app.database import async_session_factory
from sqlalchemy import text

async def check():
    async with async_session_factory() as s:
        res = await s.execute(text('''
            SELECT 
                a.id as athlete_id,
                u.id as user_id,
                u.full_name,
                u.email,
                a.sport_type,
                a.position,
                v.id as video_id,
                v.original_filename,
                v.movement_type,
                v.camera_view,
                v.processing_status,
                v.coverage_caveat,
                rs.overall_score,
                rs.risk_category
            FROM athletes a
            LEFT JOIN users u ON a.user_id = u.id
            LEFT JOIN videos v ON a.id = v.athlete_id
            LEFT JOIN risk_scores rs ON v.id = rs.video_id
            ORDER BY u.full_name, v.created_at
        '''))
        rows = res.fetchall()
        for r in rows:
            print(dict(r._mapping))

if __name__ == "__main__":
    asyncio.run(check())
