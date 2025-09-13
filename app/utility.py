from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request
import logging

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

def limitter_logger(request: Request, endpoint: str):
    try:
        #print(request.state.view_rate_limit)
        
        rate_limit_info = request.state.view_rate_limit
        
        limit_str = rate_limit_info[0]
        #limit = int(limit_str.split(' ')[0])
        # current = int(rate_limit_info[1])
        # remaining = limit - current #TODO: Add remaining find out how to do this
        ip = get_remote_address(request)
        
        logging.info(f"Rate limit for IP {ip}: {limit_str} for /{endpoint} endpoint")
    except Exception as e:
        logging.error(f"Error in rate limit logging: {str(e)}")
        # Log the actual structure for debugging
        logging.debug(f"Rate limit info structure: {request.state.view_rate_limit}")
    

