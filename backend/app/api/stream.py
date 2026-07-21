import asyncio
import json
import logging
from typing import Optional
import jwt
from fastapi import APIRouter, Request, HTTPException, status, Query, Header
from fastapi.responses import StreamingResponse
import redis.asyncio as aioredis
from app.config import settings

router = APIRouter(tags=["Streaming"])
logger = logging.getLogger(__name__)


def verify_stream_token(token: Optional[str]):
    """
    Validates JWT token for SSE streaming connections.
    """
    if not token:
        if settings.ENVIRONMENT == "development":
            return
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required for event streaming"
        )
    try:
        if token.startswith("Bearer "):
            token = token.split(" ")[1]
        jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired streaming token"
        )


async def event_generator(request: Request):
    """
    Generator for Server-Sent Events (SSE).
    Subscribes to a Redis Pub/Sub channel 'benten-updates' and yields messages to the client.
    """
    client = None
    pubsub = None
    try:
        client = aioredis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)
        pubsub = client.pubsub()
        await pubsub.subscribe("benten-updates")
        logger.info("SSE client connected and subscribed to Redis 'benten-updates'")
    except Exception as e:
        logger.warning(f"Could not connect to Redis for SSE streaming: {e}. Falling back to ping generator.")

    try:
        while True:
            if await request.is_disconnected():
                logger.info("SSE client disconnected")
                break
            
            message = None
            if pubsub:
                try:
                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                except Exception as poll_err:
                    logger.error(f"Error polling Redis pubsub: {poll_err}")

            if message:
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                logger.info(f"SSE sending event: {data}")
                yield f"data: {data}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'ping'})}\n\n"
                await asyncio.sleep(0.05)

                
    except asyncio.CancelledError:
        logger.info("SSE connection cancelled")
    except Exception as e:
        logger.error(f"Error in SSE event generator: {e}")
    finally:
        if pubsub and client:
            try:
                await pubsub.unsubscribe("benten-updates")
                await pubsub.close()
                await client.close()
            except Exception as close_err:
                logger.error(f"Error closing Redis pubsub in SSE: {close_err}")


@router.get("/stream")
async def stream_events(
    request: Request,
    token: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None)
):
    """
    SSE endpoint for the Refine dashboard to listen to live updates.
    Requires JWT token via ?token= parameter or Authorization header.
    """
    auth_token = token or authorization
    verify_stream_token(auth_token)
    return StreamingResponse(event_generator(request), media_type="text/event-stream")
