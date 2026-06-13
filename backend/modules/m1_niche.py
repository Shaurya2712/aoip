# STATUS: COMPLETE
# modules/m1_niche.py
from db import get_db


async def get_active_niches() -> list[dict]:
    """Returns all enabled niches, highest priority first."""
    res = (
        get_db()
        .table("niches")
        .select("*")
        .eq("enabled", True)
        .order("priority", desc=True)
        .execute()
    )
    return res.data


async def get_seed_keywords(niche_id: str) -> list[str]:
    """Returns all seed keyword strings for a given niche."""
    res = (
        get_db()
        .table("seed_keywords")
        .select("keyword")
        .eq("niche_id", niche_id)
        .execute()
    )
    return [r["keyword"] for r in res.data]
