import redis
import time
from config import Config

# Redis connection
redis_client = redis.StrictRedis(host=Config.REDIS_HOST, port=Config.REDIS_PORT, decode_responses=True)

def store_otp(email, otp):
    """Stores OTP details in Redis"""
    otp_id = f"otp:{email}"
    otp_data = {
        "otp": otp,
        "attempts_left": 5,
        "timestamp": int(time.time())
    }
    redis_client.hmset(otp_id, otp_data)
    redis_client.expire(otp_id, 300)  # OTP valid for 5 minutes

def get_otp(email):
    """Fetch OTP details from Redis"""
    return redis_client.hgetall(f"otp:{email}")

def delete_otp(email):
    """Delete OTP record"""
    redis_client.delete(f"otp:{email}")
