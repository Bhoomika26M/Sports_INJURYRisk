import asyncio
from app.database import async_session_factory
from sqlalchemy import text

ATHLETES_TO_REMOVE = [
    "ff19d991-dec0-4923-8db9-933717fd4593",  # Carlos Mendez
    "1ca1a200-cef4-4371-be24-7173a9368767",  # Devon Reed
    "9fa0cbea-b8de-41f9-8051-495924ebe76f",  # Amara Okafor
    "fbf3f028-76ff-449b-b7ed-d0d363426a6d",  # Noah Kim
    "46109f13-46f8-4f1a-9cd9-f916c05c80bf",  # Chloe Bennett
    "5eb8ab70-beae-46f5-80d5-14aecbb322f6",  # Lucas Moreau
    "e6f3982e-3875-4deb-b6d5-85e84efb9a78",  # Isabella Santos
    "9396f561-3f08-4b2b-941a-92d075debb8f",  # Marcus Sterling
    "f2877142-51eb-4029-974e-a95cd9f19930",  # Maya Lin
    "d05b6f69-f392-4276-9d8f-03a0011d1eba",  # Aiden Murphy
    "23dbf8fe-ef1d-4d6f-9293-bdb5bb816d84",  # Emma Watson
    "d74548e2-66ce-4d13-8cca-411a6b7fe55c",  # David Miller
]

EXTRA_VIDEOS_TO_REMOVE = [
    "377663ec-b6fe-43d4-a446-2ad51b3c3154",  # Mateo Silva pending_upload
    "ff6598a3-376b-4c5a-bcfa-e29e3a4cbcc2",  # Mateo Silva unscored jump
]

async def cleanup():
    async with async_session_factory() as s:
        async with s.begin():
            # 1. Clean extra unscored videos
            for vid in EXTRA_VIDEOS_TO_REMOVE:
                await s.execute(text("DELETE FROM videos WHERE id = :vid"), {"vid": vid})
                print(f"Removed extra video {vid}")

            # 2. Get user_ids for athletes to remove
            res = await s.execute(
                text("SELECT id, user_id FROM athletes WHERE id = ANY(:ids)"),
                {"ids": ATHLETES_TO_REMOVE}
            )
            rows = res.fetchall()
            user_ids = [str(r.user_id) for r in rows if r.user_id]
            print(f"Found {len(rows)} athletes and {len(user_ids)} users to remove")

            # 3. Delete athletes (cascades to their videos, injuries, training loads)
            await s.execute(
                text("DELETE FROM athletes WHERE id = ANY(:ids)"),
                {"ids": ATHLETES_TO_REMOVE}
            )
            print("Deleted athletes")

            # 4. Delete corresponding user accounts
            if user_ids:
                await s.execute(
                    text("DELETE FROM users WHERE id = ANY(:uids)"),
                    {"uids": user_ids}
                )
                print(f"Deleted {len(user_ids)} users")

        print("Cleanup transaction committed successfully!")

if __name__ == "__main__":
    asyncio.run(cleanup())
