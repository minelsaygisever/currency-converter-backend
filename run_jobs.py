# run_jobs.py

import asyncio
import os
import logging
from src.rate_history.jobs import run_hourly_job, run_daily_job

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("job_runner")

async def main():
    job_type = os.environ.get("JOB_TYPE")
    logger.info(f"Job runner started. JOB_TYPE is set to: {job_type}")

    if job_type == "hourly":
        logger.info("--- Running HOURLY job ---")
        await run_hourly_job()
        logger.info("--- HOURLY job finished ---")
    elif job_type == "daily":
        logger.info("--- Running DAILY job ---")
        await run_daily_job()
        logger.info("--- DAILY job finished ---")
    else:
        logger.warning(
            "No valid JOB_TYPE environment variable found. "
            "Set JOB_TYPE to 'hourly' or 'daily'. Exiting."
        )

if __name__ == "__main__":
    asyncio.run(main())