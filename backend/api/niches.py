# STATUS: COMPLETE
# api/niches.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from db import get_db

router = APIRouter()


class NicheCreate(BaseModel):
    name: str
    priority: Optional[int] = 5


class NicheUpdate(BaseModel):
    enabled: Optional[bool] = None
    priority: Optional[int] = None


class SeedKeywordsPayload(BaseModel):
    keywords: list[str]  # Max 1000 lines from textarea


@router.get("/")
def list_niches():
    res = get_db().table("niches").select("*, seed_keywords(count)").order("priority", desc=True).execute()
    return res.data


@router.post("/")
def create_niche(body: NicheCreate):
    res = get_db().table("niches").insert({"name": body.name, "priority": body.priority}).execute()
    return res.data[0]


@router.patch("/{niche_id}")
def update_niche(niche_id: str, body: NicheUpdate):
    updates = {k: v for k, v in body.dict().items() if v is not None}
    res = get_db().table("niches").update(updates).eq("id", niche_id).execute()
    return res.data[0]


@router.post("/{niche_id}/seeds")
def add_seed_keywords(niche_id: str, body: SeedKeywordsPayload):
    keywords = [k.strip().lower() for k in body.keywords if k.strip()][:1000]
    if not keywords:
        raise HTTPException(status_code=400, detail="No valid keywords provided")
    rows = [{"keyword": kw, "niche_id": niche_id} for kw in keywords]
    # Insert in batches of 100 to avoid payload limits
    inserted = 0
    for i in range(0, len(rows), 100):
        get_db().table("seed_keywords").upsert(rows[i:i+100], on_conflict="keyword,niche_id").execute()
        inserted += len(rows[i:i+100])
    return {"inserted": inserted}
