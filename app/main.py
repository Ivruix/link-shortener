from fastapi import FastAPI
from apscheduler.schedulers.background import BackgroundScheduler
from app.database import engine, Base, SessionLocal
from app.models import Link, ExpiredLink
from app.routers import auth, links
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Link Shortener")

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    scheduler.start()

@app.on_event("shutdown")
def shutdown():
    scheduler.shutdown()

app.include_router(auth.router)
app.include_router(links.router)

def delete_expired_links():
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        expired = db.query(Link).filter(Link.expires_at < now).all()

        for link in expired:
            expired_link = ExpiredLink(
                short_code=link.short_code,
                original_url=link.original_url,
                user_id=link.user_id,
                created_at=link.created_at,
                deletion_reason="expired"
            )
            db.add(expired_link)
            db.delete(link)
            logger.info(f"Deleted expired link: {link.short_code}")

        db.commit()
        logger.info(f"Deleted {len(expired)} expired links")
    except Exception as e:
        logger.error(f"Error deleting expired links: {e}")
        db.rollback()
    finally:
        db.close()

def delete_unused_links():
    db = SessionLocal()
    try:
        threshold = datetime.utcnow() - timedelta(days=30)
        unused = db.query(Link).filter(
            Link.last_accessed_at < threshold,
            Link.access_count > 0
        ).all()

        for link in unused:
            expired_link = ExpiredLink(
                short_code=link.short_code,
                original_url=link.original_url,
                user_id=link.user_id,
                created_at=link.created_at,
                deletion_reason="unused"
            )
            db.add(expired_link)
            db.delete(link)
            logger.info(f"Deleted unused link: {link.short_code}")

        db.commit()
        logger.info(f"Deleted {len(unused)} unused links")
    except Exception as e:
        logger.error(f"Error deleting unused links: {e}")
        db.rollback()
    finally:
        db.close()

scheduler = BackgroundScheduler()
scheduler.add_job(delete_expired_links, 'interval', minutes=1)
scheduler.add_job(delete_unused_links, 'interval', days=1)

@app.get("/")
def root():
    return {"message": "Link Shortener API"}
