import logging
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import os
from app.api.video_handlers.yt_video_search import get_all_youtube_videos
from app.api.video_handlers.yt_video_search_filtering import classify_video_agent, get_final_front_page_videos
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import HTTPException
from app.config import get_settings

logger = logging.getLogger(__name__)

# Path to the JSON file you want to update daily.
JSON_FILE_PATH = Path("daily_update.json")


async def update_json_file():
    """Example task that updates a JSON file with the last run time."""
    """Slideshow videos endpoint that fetches videos from multiple categories using config file."""
    try:
        logging.info("Slideshow videos endpoint called")
        
        # Get the path to the config file (relative to the project root)
        config_path = os.path.join("config", "video_queries.json")
        
        # Fetch cleaned videos from all categories and queries in the config
        videos = await get_all_youtube_videos(config_path)
        
        output_path = os.path.join("config", "raw_front_page_videos.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(videos, f, indent=2, ensure_ascii=False)
        
        # # Read existing videos from file instead of fetching
        # videos_path = os.path.join("config", "raw_front_page_videos.json")
        # with open(videos_path, "r", encoding="utf-8") as f:
        #     videos = json.load(f)
        
        logging.info(f"Successfully loaded {len(videos) if videos else 0} videos from file")
        
        # Group videos by category for better organization
        videos_by_category = {}
        for video in videos:
            category = video.get("category", "unknown")
            if category not in videos_by_category:
                videos_by_category[category] = []
            videos_by_category[category].append(video)
        
        slideshow_videos = {
            "videos": videos,
            "count": len(videos) if videos else 0,
            "categories": list(videos_by_category.keys()),
            "videos_by_category": videos_by_category
        }
        
        classified_videos = await classify_video_agent(slideshow_videos)
        
        output_path = os.path.join("config", "classified_video_claims.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(classified_videos, f, indent=2, ensure_ascii=False)
        
        final_front_page_videos = await get_final_front_page_videos(classified_videos)
        
        # Save the final front page videos to a JSON file
        output_path = os.path.join("config", "final_front_page_videos.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(final_front_page_videos, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Saved final front page videos to {output_path}")
        
    except Exception as e:
        logging.error(f"Error in night update: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching videos: {str(e)}")                 


def start_scheduler():
    """Start an AsyncIO scheduler.

    • In production: run nightly at 8:55 AM Central Time.
    • In dev: ALSO schedule a one-off run 1 minute after startup so you can
      watch it execute without waiting until 8:55 AM.
    """
    scheduler = AsyncIOScheduler(timezone="America/Chicago")

    # Nightly job (always enabled)
    nightly_trigger = CronTrigger(hour=13, minute=20, second=0)
    scheduler.add_job(update_json_file, nightly_trigger, id="daily_json_update", replace_existing=True)

    #Uncomment this to run the job immediately
    # Extra immediate run in dev environment
    settings = get_settings()
    if settings.environment.lower() == "dev":
        run_at = datetime.now(timezone.utc) + timedelta(minutes=1)
        scheduler.add_job(
            update_json_file,
            "date",
            run_date=run_at,
            id="dev_one_off",
            replace_existing=True,
        )
        logger.info("Dev mode: scheduled one-off update_json_file for %s UTC", run_at.isoformat())

    scheduler.start()
    logger.info("APScheduler started (timezone=UTC)")

    return scheduler 