import json
import uuid
import asyncio
from datetime import datetime
from sqlalchemy import update, insert
from app.core.models import QRPass, ScanLog
from app.core.redis_client import redis_client

async def process_redis_queue(session_factory):
    while True:
        # База "спить" 15 хвилин (900 секунд) між записами
        await asyncio.sleep(900) 
        
        # Перевіряємо, чи є що записувати
        queue_len = await redis_client.llen("scan_logs_queue")
        if queue_len == 0:
            continue
            
        # Атомарно витягуємо всі лог-записи з черги
        logs_data = await redis_client.lpop("scan_logs_queue", count=queue_len)
        if not logs_data:
            continue
        
        parsed_logs = [json.loads(log) for log in logs_data]
        scan_logs_insert = []
        latest_statuses = {}
        
        for log in parsed_logs:
            scan_logs_insert.append({
                "id": uuid.uuid4(),
                "telegram_id": log["telegram_id"],
                "scanner_id": log["scanner_id"],
                "action_type": log["action_type"],
                "scanned_at": datetime.fromisoformat(log["scanned_at"])
            })
            # Визначаємо фінальний статус перепустки на кінець 15-хвилинного вікна
            latest_statuses[log["pass_id"]] = (log["action_type"] == "in")
        
        # Відкриваємо з'єднання з базою лише на мить
        async with session_factory() as session:
            # Масовий запис усіх логів
            if scan_logs_insert:
                await session.execute(insert(ScanLog), scan_logs_insert)
            
            # Масове оновлення статусів перепусток
            for pass_id_str, status in latest_statuses.items():
                await session.execute(
                    update(QRPass)
                    .where(QRPass.pass_id == uuid.UUID(pass_id_str))
                    .values(is_on_territory=status)
                )
            
            await session.commit()