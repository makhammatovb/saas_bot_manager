import asyncio
from core.models import Job
from .client_manager import get_client
from .actions import do_add, do_remove

async def process_job(job: Job):
    client = await get_client(job.company_id)
    
    if job.job_type == 'add':
        status, error = await do_add(client, job)
    else:
        status, error = await do_remove(client, job)
    
    job.status = status
    job.error = error
    await job.asave()
    