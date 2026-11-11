import argparse
import asyncio
import logging
import os
import aiohttp
from app.core.config import APP_ENV, ENABLE_PAYMENTS, mono_webhook_secret

logger = logging.getLogger(__name__)

async def setup_mono_webhook():
    if APP_ENV!="production" or not ENABLE_PAYMENTS:
        raise RuntimeError("Only enabled in production")
    base=os.getenv("WEB_APP_URL", "").rstrip("/")
    secret=mono_webhook_secret()
    tokens=[os.getenv(name) for name in ("MONO_TOKEN","MONO_TOKEN_2") if os.getenv(name)]
    if not base.startswith("https://") or len(secret)<32 or not tokens:
        raise RuntimeError("Set BOT_TOKEN, WEB_APP_URL and MONO_TOKEN")
    results = []
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as client:
        for index, token in enumerate(tokens,1):
            try:
                async with client.post("https://api.monobank.ua/personal/webhook",headers={"X-Token":token.strip()},json={"webHookUrl":f"{base}/mono/{secret}"}) as response:
                    configured = response.status == 200
                    results.append(configured)
                    if configured:
                        logger.info("Monobank webhook %s configured", index)
                    else:
                        logger.error("Monobank webhook %s not configured (HTTP %s). Check token access and public WEB_APP_URL. Receipt confirmation remains available.", index, response.status)
            except (aiohttp.ClientError, asyncio.TimeoutError) as error:
                results.append(False)
                logger.error("Monobank webhook %s not configured (%s); credentials omitted. Receipt confirmation remains available.", index, type(error).__name__)
    return results


async def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--apply",action="store_true")
    if not parser.parse_args().apply:
        raise SystemExit("Use --apply only after the public API is running")
    if not all(await setup_mono_webhook()):
        raise SystemExit("Not all Monobank webhooks were configured; see HTTP status above")

if __name__=="__main__":
    try:
        asyncio.run(main())
    except aiohttp.ClientError as error:
        raise SystemExit("Webhook registration failed: "+type(error).__name__+"; credentials omitted") from None
