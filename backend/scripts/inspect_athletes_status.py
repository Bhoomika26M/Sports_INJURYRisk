import asyncio
from app.database import async_session_factory
from sqlalchemy import text

async def check():
    async with async_session_factory() as s:
        res = await s.execute(text('''
            SELECT a.id, u.full_name, u.email, a.sport_type, a.position,
                   COUNT(v.id) as total_videos,
                   COUNT(CASE WHEN v.processing_status = 'completed' THEN 1 END) as completed_videos,
                   COUNT(CASE WHEN v.processing_status = 'failed' THEN 1 END) as failed_videos,
                   COUNT(rs.id) as scored_videos
            FROM athletes a
            LEFT JOIN users u ON a.user_id = u.id
            LEFT JOIN videos v ON a.id = v.athlete_id
            LEFT JOIN risk_scores rs ON v.id = rs.video_id
            GROUP BY a.id, u.full_name, u.email, a.sport_type, a.position
            ORDER BY scored_videos DESC, completed_videos DESC, u.full_name ASC
        '''))
        rows = res.fetchall()
        print(f"Total athletes: {len(rows)}")
        for r in rows:
            print(dict(r._mapping))

if __name__ == "__main__":
    asyncio.run(check())
