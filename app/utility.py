from fastapi import Request
import logging

logger = logging.getLogger(__name__)

def get_client_ip(request: Request):
    # Check for X-Forwarded-For header (used by most proxies)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # The first IP in the list is the client IP
        client_ip = forwarded_for.split(",")[0].strip()
        logger.info(f"Client IP from X-Forwarded-For: {client_ip}")
        return client_ip
    
    # Fallback to direct client IP
    client_ip = request.client.host
    logger.info(f"Client IP from request: {client_ip}")
    return client_ip
