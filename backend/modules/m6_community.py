# STATUS: COMPLETE
# modules/m6_community.py
# PURPOSE: Scrape Reddit for niche-relevant posts and extract insights via AI.
# RUNS: Every 8 hours via scheduler.
# OUTPUT: Writes to community_posts and community_insights tables.

import asyncio
import praw
from db import get_db
from ai_client import ai_analyze
from modules.m1_niche import get_active_niches
from config import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT, is_reddit_configured
from job_exceptions import JobSkipped

# Subreddit mapping per niche — add more as needed
NICHE_SUBREDDITS = {
    "Finance":      ["personalfinance", "IndiaInvestments", "india"],
    "Productivity": ["productivity", "androidapps", "selfimprovement"],
    "Students":     ["college", "india", "indian_academia", "learnprogramming"],
    "Fitness":      ["fitness", "india", "IndianFitness", "bodyweightfitness"],
    "Health":       ["Health", "india", "AskDocs"],
    "AI":           ["artificial", "MachineLearning", "ChatGPT"],
    "Education":    ["education", "india", "learnprogramming"],
    "Construction": ["Construction", "civilengineering", "india"],
    "Agriculture":  ["farming", "india", "agriculture"],
    "Real Estate":  ["realestateinvesting", "india", "RealEstate"],
    "Business":     ["smallbusiness", "Entrepreneur", "india"],
}

INSIGHT_PROMPT = """
You are a mobile app product researcher analysing Reddit posts for the "{niche}" market.

Here are Reddit posts from users discussing apps, tools, and problems in this space:
{posts_text}

Extract insights that would help an Android app developer understand what to build.

Return ONLY this JSON, nothing else:
{{
  "pain_points": [
    {{"text": "specific problem users face", "confidence": 0.9}}
  ],
  "feature_requests": [
    {{"text": "something users wish existed", "confidence": 0.8}}
  ],
  "emerging_trends": [
    {{"text": "a growing topic or behaviour", "confidence": 0.7}}
  ]
}}

Maximum 8 items per category. Confidence is 0.0-1.0. Only include items with confidence > 0.5.
"""


async def run():
    if not is_reddit_configured():
        print("[m6] Skipping community research — Reddit credentials not configured")
        raise JobSkipped("Reddit credentials not configured")

    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
    )
    db = get_db()
    niches = await get_active_niches()

    for niche in niches:
        subreddits = NICHE_SUBREDDITS.get(niche["name"], ["androidapps", "india"])
        all_posts = []

        for sub in subreddits:
            await asyncio.sleep(2)
            try:
                for post in reddit.subreddit(sub).search(
                    niche["name"] + " app", limit=15, sort="top", time_filter="month"
                ):
                    all_posts.append({
                        "title": post.title,
                        "text": post.selftext[:300],
                        "upvotes": post.score,
                        "url": post.url,
                        "subreddit": sub,
                    })
                    # Store raw post
                    try:
                        db.table("community_posts").upsert(
                            {
                                "niche_id": niche["id"],
                                "source": "reddit",
                                "subreddit": sub,
                                "title": post.title[:500],
                                "content": post.selftext[:500],
                                "upvotes": post.score,
                                "url": post.url,
                            },
                            on_conflict="url",
                        ).execute()
                    except Exception:
                        pass  # Duplicate URL — ignore

            except Exception as e:
                print(f"[m6] Reddit error on r/{sub}: {e}")
                continue

        if not all_posts:
            print(f"[m6] No posts found for niche: {niche['name']}")
            continue

        # Sort by upvotes, take top 30
        all_posts.sort(key=lambda x: x["upvotes"], reverse=True)
        posts_text = "\n".join([
            f"[{p['upvotes']}↑ r/{p['subreddit']}] {p['title']}: {p['text']}"
            for p in all_posts[:30]
        ])

        try:
            insights = await ai_analyze(
                INSIGHT_PROMPT.format(niche=niche["name"], posts_text=posts_text)
            )

            for category, itype in [
                ("pain_points", "pain_point"),
                ("feature_requests", "feature_request"),
                ("emerging_trends", "trend"),
            ]:
                for item in insights.get(category, []):
                    db.table("community_insights").insert({
                        "niche_id": niche["id"],
                        "type": itype,
                        "text": item["text"],
                        "confidence": item.get("confidence", 0.5),
                    }).execute()

            print(f"[m6] {niche['name']}: {len(all_posts)} posts → insights stored")

        except Exception as e:
            print(f"[m6] AI analysis error for {niche['name']}: {e}")
