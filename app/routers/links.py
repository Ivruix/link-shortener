from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.models import Link, ExpiredLink, User
from app.schemas import LinkCreate, LinkResponse, LinkUpdate, LinkStats, ExpiredLinkResponse
from app.auth import get_current_user, get_current_user_optional
from app.utils import generate_short_code
from app.redis_client import redis_client, get_redirect_key, get_search_key
import json

router = APIRouter(prefix="/links", tags=["links"])

@router.post("/shorten", response_model=LinkResponse)
def create_link(link_data: LinkCreate, db: Session = Depends(get_db), current_user: Optional[User] = Depends(get_current_user_optional)):
    if link_data.custom_alias:
        existing_link = db.query(Link).filter(Link.short_code == link_data.custom_alias).first()
        if existing_link:
            raise HTTPException(status_code=400, detail="Custom alias already exists")
        short_code = link_data.custom_alias
    else:
        short_code = generate_short_code()
        while db.query(Link).filter(Link.short_code == short_code).first():
            short_code = generate_short_code()

    new_link = Link(
        short_code=short_code,
        original_url=link_data.original_url,
        user_id=current_user.id if current_user else None,
        expires_at=link_data.expires_at
    )
    db.add(new_link)
    db.commit()
    db.refresh(new_link)

    return new_link

@router.get("/search", response_model=LinkResponse)
def search_link(original_url: str = Query(...), db: Session = Depends(get_db)):
    cache_key = get_search_key(original_url)
    cached = redis_client.get(cache_key)

    if cached:
        short_code = cached.decode()
        link = db.query(Link).filter(Link.short_code == short_code).first()
        if link:
            return LinkResponse(
                id=link.id,
                short_code=link.short_code,
                original_url=link.original_url,
                created_at=link.created_at,
                expires_at=link.expires_at,
                last_accessed_at=link.last_accessed_at,
                access_count=link.access_count
            )

    link = db.query(Link).filter(Link.original_url == original_url).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    redis_client.setex(cache_key, 3600, link.short_code)

    return LinkResponse(
        id=link.id,
        short_code=link.short_code,
        original_url=link.original_url,
        created_at=link.created_at,
        expires_at=link.expires_at,
        last_accessed_at=link.last_accessed_at,
        access_count=link.access_count
    )

@router.get("/expired", response_model=list[ExpiredLinkResponse])
def get_expired_links(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    expired_links = db.query(ExpiredLink).filter(ExpiredLink.user_id == current_user.id).all()
    return [
        ExpiredLinkResponse(
            id=link.id,
            short_code=link.short_code,
            original_url=link.original_url,
            created_at=link.created_at,
            expired_at=link.expired_at,
            deletion_reason=link.deletion_reason
        )
        for link in expired_links
    ]

@router.get("/{short_code}")
def redirect_link(short_code: str, db: Session = Depends(get_db)):
    cache_key = get_redirect_key(short_code)
    cached = redis_client.get(cache_key)

    if cached:
        original_url = cached.decode()
        link = db.query(Link).filter(Link.short_code == short_code).first()
        if link:
            link.access_count += 1
            link.last_accessed_at = datetime.utcnow()
            db.commit()
        return RedirectResponse(url=original_url)

    link = db.query(Link).filter(Link.short_code == short_code).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    if link.expires_at and link.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Link has expired")

    link.access_count += 1
    link.last_accessed_at = datetime.utcnow()
    db.commit()

    redis_client.setex(cache_key, 3600, link.original_url)

    return RedirectResponse(url=link.original_url)

@router.get("/{short_code}/stats", response_model=LinkStats)
def get_link_stats(short_code: str, db: Session = Depends(get_db)):
    cache_key = f"stats:{short_code}"
    cached = redis_client.get(cache_key)

    if cached:
        return LinkStats(**json.loads(cached))

    link = db.query(Link).filter(Link.short_code == short_code).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    stats = LinkStats(
        short_code=link.short_code,
        original_url=link.original_url,
        created_at=link.created_at,
        access_count=link.access_count,
        last_accessed_at=link.last_accessed_at
    )

    redis_client.setex(cache_key, 1800, json.dumps(stats.dict(), default=str))
    return stats

@router.put("/{short_code}", response_model=LinkResponse)
def update_link(short_code: str, link_data: LinkUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    link = db.query(Link).filter(Link.short_code == short_code).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    if link.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this link")

    link.original_url = link_data.original_url
    db.commit()
    db.refresh(link)

    redirect_key = get_redirect_key(short_code)
    redis_client.delete(redirect_key)

    return link

@router.delete("/{short_code}")
def delete_link(short_code: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    link = db.query(Link).filter(Link.short_code == short_code).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    if link.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this link")

    expired_link = ExpiredLink(
        short_code=link.short_code,
        original_url=link.original_url,
        user_id=link.user_id,
        created_at=link.created_at,
        deletion_reason="manual"
    )
    db.add(expired_link)
    db.delete(link)
    db.commit()

    redirect_key = get_redirect_key(short_code)
    redis_client.delete(redirect_key)

    return {"message": "Link deleted successfully"}
