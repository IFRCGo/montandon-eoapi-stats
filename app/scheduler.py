import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.cache import cache
from app.config import settings

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def start() -> None:
    scheduler.add_job(
        cache.refresh,
        trigger=CronTrigger.from_crontab(settings.cron_schedule),
        id="refresh-stats-cache",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started with cron schedule '%s'", settings.cron_schedule)


def stop() -> None:
    scheduler.shutdown(wait=False)
