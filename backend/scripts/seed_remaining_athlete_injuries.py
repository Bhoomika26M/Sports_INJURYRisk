import asyncio
from datetime import date
from app.database import async_session_factory
from sqlalchemy import text

async def seed_more_injuries():
    async with async_session_factory() as s:
        async with s.begin():
            # Get athlete IDs
            res = await s.execute(text("""
                SELECT a.id, u.full_name
                FROM athletes a
                JOIN users u ON a.user_id = u.id
                WHERE u.full_name IN ('Tyler Brooks', 'Zoe Chen', 'Kiran Patel')
            """))
            athletes = {r.full_name: str(r.id) for r in res.fetchall()}

            injuries_data = [
                (athletes.get('Tyler Brooks'), 'Hamstring strain (Grade 1)', 'left hamstring', date(2025, 8, 12), date(2025, 9, 2), 'minor', 'Overuse sprinting during preseason camp'),
                (athletes.get('Tyler Brooks'), 'Plantar fasciitis', 'left foot', date(2025, 3, 5), date(2025, 4, 15), 'moderate', 'Persistent heel pain, managed with orthotics'),
                (athletes.get('Zoe Chen'), 'Lumbar facet joint sprain', 'lower back', date(2025, 5, 20), date(2025, 7, 1), 'moderate', 'Hyperextension landing impact'),
                (athletes.get('Zoe Chen'), 'Wrist ligament sprain', 'right wrist', date(2024, 10, 10), date(2024, 11, 20), 'minor', 'Floor exercise vault impact'),
                (athletes.get('Kiran Patel'), 'Medial collateral ligament (MCL) sprain', 'right knee', date(2025, 4, 1), date(2025, 5, 18), 'moderate', 'Bowling follow-through twist'),
                (athletes.get('Kiran Patel'), 'Lumbar muscle strain', 'lower back', date(2024, 12, 1), date(2025, 1, 15), 'minor', 'Fast bowling overload'),
            ]

            for ath_id, itype, bpart, idate, rdate, sev, notes in injuries_data:
                if ath_id:
                    await s.execute(text("""
                        INSERT INTO injury_history (athlete_id, injury_type, body_part, injury_date, recovery_date, severity, notes)
                        VALUES (:ath_id, :itype, :bpart, :idate, :rdate, :sev, :notes)
                    """), {
                        "ath_id": ath_id,
                        "itype": itype,
                        "bpart": bpart,
                        "idate": idate,
                        "rdate": rdate,
                        "sev": sev,
                        "notes": notes
                    })
            print("Successfully seeded injuries for Tyler Brooks, Zoe Chen, and Kiran Patel!")

if __name__ == "__main__":
    asyncio.run(seed_more_injuries())
