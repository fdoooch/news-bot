from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_MISSED
from typing import Callable, Any
import pytz
import logging
import asyncio
from functools import wraps

from app.core.config import settings

logger = logging.getLogger(settings.LOGGER_NAME)

def create_async_job_wrapper(async_func: Callable) -> Callable:
    """
    Creates a wrapper for async functions to work with APScheduler.
    Ensures proper coroutine execution in the thread pool executor.
    """
    @wraps(async_func)
    def job_wrapper(**kwargs):
        try:
            # Get or create event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Create future to run in the background
            future = asyncio.run_coroutine_threadsafe(
                async_func(**kwargs),
                loop
            )
            
            # Wait for the result
            return future.result()
            
        except Exception as e:
            logger.error(f"Error in async job {async_func.__name__}: {str(e)}")
            raise
    
    return job_wrapper

class SchedulerManager:
    """Manages scheduling of jobs using APScheduler."""
    
    def __init__(self):
        self.settings = settings
        self.scheduler: AsyncIOScheduler = None
        self._configure_scheduler()

    def _configure_scheduler(self) -> None:
        """Configure the APScheduler with SQLAlchemy job store and thread pool executor."""
        try:
            

            self.scheduler = AsyncIOScheduler(
                timezone=pytz.UTC
            )

            # Add error listener
            self.scheduler.add_listener(
                self._job_error_listener,
                EVENT_JOB_ERROR | EVENT_JOB_MISSED
            )

        except Exception as e:
            logger.error(f"Failed to configure scheduler: {str(e)}")
            raise

    def _job_error_listener(self, event):
        """Handle job execution errors and missed job runs."""
        if event.code == EVENT_JOB_ERROR:
            logger.error(f"Job {event.job_id} raised an error: {str(event.exception)}")
        elif event.code == EVENT_JOB_MISSED:
            logger.warning(f"Job {event.job_id} missed its execution time")

    def schedule_job(
        self,
        job_func: Callable,
        job_id: str,
        hours: int,
        minutes: int,
        **kwargs: Any
    ) -> bool:
        """Schedule a job to run at specified hours and minutes."""
        if not self.scheduler:
            raise RuntimeError("Scheduler not initialized")

        # Validate time parameters
        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            raise ValueError(f"Invalid time parameters: hours={hours}, minutes={minutes}")

        try:
            # Remove existing job if it exists
            self._remove_job_if_exists(job_id)
            
            # Create a cron trigger
            trigger = CronTrigger(
                hour=hours,
                minute=minutes,
                timezone=pytz.UTC,
                jitter=30  # Add small random delay to prevent concurrent executions
            )

            # wrapped_job = create_async_job_wrapper(job_func)

            # Add the job
            self.scheduler.add_job(
                func=job_func,
                trigger=trigger,
                id=job_id,
                kwargs=kwargs,
                replace_existing=True,
                name=f"Job {job_id} at {hours:02d}:{minutes:02d} UTC"
            )
            
            logger.info(
                f"Successfully scheduled job {job_id} for {hours:02d}:{minutes:02d} UTC"
            )
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to schedule job {job_id} for {hours:02d}:{minutes:02d} UTC: {str(e)}"
            )
            return False

    def _remove_job_if_exists(self, job_id: str) -> None:
        """Safely remove a job if it exists."""
        try:
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.debug(f"Removed existing job {job_id}")
        except Exception as e:
            logger.error(f"Error removing job {job_id}: {str(e)}")

    def start(self) -> None:
        """Start the scheduler."""
        if not self.scheduler:
            raise RuntimeError("Scheduler not initialized")
            
        if not self.scheduler.running:
            try:
                self.scheduler.start()
                logger.info("Scheduler started successfully")
            except Exception as e:
                logger.error(f"Failed to start scheduler: {str(e)}")
                raise

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the scheduler."""
        if self.scheduler and self.scheduler.running:
            try:
                self.remove_all_jobs()
                self.scheduler.shutdown(wait=wait)
                logger.info("Scheduler shutdown successfully")
            except Exception as e:
                logger.error(f"Error during scheduler shutdown: {str(e)}")
                raise

    def get_jobs(self):
        """Get all scheduled jobs."""
        return self.scheduler.get_jobs() if self.scheduler else []

    def get_jobs_report(self) -> str:
        """Get a formatted report of all scheduled jobs."""
        if not self.scheduler:
            return "Scheduler not initialized"

        try:
            jobs = self.get_jobs()
            if not jobs:
                return "No jobs scheduled"

            report_lines = ["Scheduled Jobs:", "---------------------------------------"]
            
            for job in jobs:
                next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S UTC") if job.next_run_time else "Not scheduled"
                report_lines.extend([
                    f"ID: {job.id}",
                    f"Name: {job.name}",
                    f"Next run time: {next_run}",
                    f"Function: {job.func.__name__}",
                    "---------------------------------------"
                ])
            
            return "\n".join(report_lines)
            
        except Exception as e:
            logger.error(f"Error generating jobs report: {str(e)}")
            return f"Error generating jobs report: {str(e)}"

    def remove_all_jobs(self) -> None:
        """Remove all scheduled jobs."""
        if self.scheduler:
            try:
                self.scheduler.remove_all_jobs()
                logger.info("All jobs removed successfully")
            except Exception as e:
                logger.error(f"Error removing all jobs: {str(e)}")
                raise

    @property
    def is_running(self) -> bool:
        """Check if the scheduler is running."""
        return bool(self.scheduler and self.scheduler.running)