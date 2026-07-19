import asyncio
import json
import logging
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import redis.asyncio as aioredis
from app.config import settings

router = APIRouter(tags=["Streaming"])
logger = logging.getLogger(__name__)

async def event_generator(request: Request):
    """
    Generator for Server-Sent Events (SSE).
    Subscribes to a Redis Pub/Sub channel 'benten-updates' and yields messages to the client.
    """
    client = aioredis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)
    pubsub = client.pubsub()
    await pubsub.subscribe("benten-updates")
    logger.info("SSE client connected and subscribed to Redis 'benten-updates'")
    
    try:
        while True:
            if await request.is_disconnected():
                logger.info("SSE client disconnected")
                break
            
            # Listen to pubsub with a short timeout to allow checks for disconnection
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message:
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                logger.info(f"SSE sending event: {data}")
                yield f"data: {data}\n\n"
            else:
                # Send periodic ping to prevent connection timeout and keep connection alive
                yield f"data: {json.dumps({'type': 'ping'})}\n\n"
                
    except asyncio.CancelledError:
        logger.info("SSE connection cancelled")
    except Exception as e:
        logger.error(f"Error in SSE event generator: {e}")
    finally:
        try:
            await pubsub.unsubscribe("benten-updates")
            await pubsub.close()
            await client.close()
        except Exception as close_err:
            logger.error(f"Error closing Redis pubsub in SSE: {close_err}")

@router.get("/stream")
async def stream_events(request: Request):
    """
    SSE endpoint for the Refine dashboard to listen to live updates.
    """
    return StreamingResponse(event_generator(request), media_type="text/event-stream")
