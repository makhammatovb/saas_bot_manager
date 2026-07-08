import asyncio
from telethon import TelegramClient
from core.models import Company

clients = {}

async def get_client(company_id: int):
    if company_id in clients:
        return clients[company_id]

    company = await Company.objects.aget(id=company_id)
    
    client = TelegramClient(
        company.session_name, 
        company.api_id, 
        company.api_hash
    )
    
    await client.start()
    clients[company_id] = client
    return client