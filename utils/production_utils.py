import time
import logging
from datetime import datetime, timedelta
from functools import wraps
from cachetools import TTLCache
import streamlit as st
from utils.monitoring import monitor

# Session Management
SESSION_TIMEOUT = 3600  # 1 hour
session_store = {}

def check_session_timeout():
    """Check and clean expired sessions"""
    current_time = time.time()
    expired_sessions = [
        session_id for session_id, session_data in session_store.items()
        if current_time - session_data['last_activity'] > SESSION_TIMEOUT
    ]
    for session_id in expired_sessions:
        cleanup_session(session_id)

def cleanup_session(session_id):
    """Clean up expired session data"""
    if session_id in session_store:
        monitor.log_performance_metric(
            "session_cleanup",
            time.time() - session_store[session_id]['last_activity'],
            {"session_id": session_id}
        )
        del session_store[session_id]

# Response Caching
response_cache = TTLCache(maxsize=100, ttl=3600)  # Cache responses for 1 hour

def cache_response(func):
    """Cache decorator for API responses"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        cache_key = str(args) + str(kwargs)
        if cache_key in response_cache:
            monitor.log_performance_metric("cache_hit", 1, {"function": func.__name__})
            return response_cache[cache_key]
        
        result = func(*args, **kwargs)
        response_cache[cache_key] = result
        monitor.log_performance_metric("cache_miss", 1, {"function": func.__name__})
        return result
    return wrapper

# Rate Limiting
class RateLimiter:
    def __init__(self, max_requests=60, time_window=60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = {}
    
    def is_allowed(self, client_id):
        current_time = time.time()
        if client_id not in self.requests:
            self.requests[client_id] = []
        
        # Clean old requests
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if current_time - req_time < self.time_window
        ]
        
        if len(self.requests[client_id]) >= self.max_requests:
            return False
        
        self.requests[client_id].append(current_time)
        return True

rate_limiter = RateLimiter()

# Health Check
def get_health_status():
    """Get system health status"""
    metrics = monitor.get_metrics()
    health_data = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "metrics": metrics,
        "cache_info": {
            "size": len(response_cache),
            "maxsize": response_cache.maxsize,
            "ttl": response_cache.ttl
        },
        "active_sessions": len(session_store)
    }
    
    # Check if error rate is too high
    total_requests = metrics['successful_responses'] + metrics['failed_responses']
    if total_requests > 0:
        error_rate = metrics['failed_responses'] / total_requests
        if error_rate > 0.1:  # More than 10% error rate
            health_data["status"] = "degraded"
    
    return health_data

def init_session():
    """Initialize or recover session"""
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(hash(time.time()))
    
    session_id = st.session_state.session_id
    if session_id not in session_store:
        session_store[session_id] = {
            'created_at': time.time(),
            'last_activity': time.time(),
            'request_count': 0
        }
    else:
        session_store[session_id]['last_activity'] = time.time()
        session_store[session_id]['request_count'] += 1
    
    # Cleanup expired sessions periodically
    if session_store[session_id]['request_count'] % 10 == 0:  # Check every 10 requests
        check_session_timeout()
    
    return session_id
