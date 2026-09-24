import os
from datetime import timedelta


APP_VERSION = os.getenv("APP_VERSION", "")


class JWTConfig:
    """JWT configuration settings"""
    
    # JWT Secret key (must be set in environment for production)
    SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
    
    # Token expiration time in hours
    TOKEN_EXPIRATION_HOURS = int(os.getenv("JWT_TOKEN_EXPIRATION_HOURS", "24"))
    
    # Algorithm for token signing
    ALGORITHM = "HS256"
    
    # Expected token scheme
    TOKEN_SCHEME = "Bearer"
    
    @classmethod
    def validate_config(cls):
        """Validate configuration is production-ready"""
        if cls.SECRET_KEY == "dev-secret-key-change-in-production":
            print("WARNING: Using default JWT_SECRET_KEY. Set JWT_SECRET_KEY env variable for production.")
        return True