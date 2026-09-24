import jwt
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from app.config import JWTConfig


class TokenValidator:
    """Validates JWT tokens for authentication"""
    
    @staticmethod
    def create_token(
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT token with the provided data.
        
        Args:
            data: Dictionary containing token claims (e.g., {"sub": "customer_id"})
            expires_delta: Optional custom expiration time
            
        Returns:
            Encoded JWT token as string
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(hours=JWTConfig.TOKEN_EXPIRATION_HOURS)
        
        to_encode.update({"exp": expire})
        
        encoded_jwt = jwt.encode(
            to_encode,
            JWTConfig.SECRET_KEY,
            algorithm=JWTConfig.ALGORITHM
        )
        return encoded_jwt
    
    @staticmethod
    def validate_token(token: str) -> Dict[str, Any]:
        """
        Validate and decode a JWT token.
        
        Args:
            token: JWT token string to validate
            
        Returns:
            Decoded token payload as dictionary
            
        Raises:
            jwt.ExpiredSignatureError: If token has expired
            jwt.InvalidTokenError: If token signature is invalid
            jwt.DecodeError: If token cannot be decoded
        """
        try:
            payload = jwt.decode(
                token,
                JWTConfig.SECRET_KEY,
                algorithms=[JWTConfig.ALGORITHM]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise jwt.ExpiredSignatureError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise jwt.InvalidTokenError(f"Invalid token: {str(e)}")
        except jwt.DecodeError as e:
            raise jwt.DecodeError(f"Cannot decode token: {str(e)}")
    
    @staticmethod
    def extract_customer_id(token: str) -> str:
        """
        Extract customer ID from a validated token.
        
        Args:
            token: JWT token string
            
        Returns:
            Customer ID from token 'sub' claim
            
        Raises:
            KeyError: If 'sub' claim is missing
            jwt.InvalidTokenError: If token is invalid
        """
        payload = TokenValidator.validate_token(token)
        
        if "sub" not in payload:
            raise KeyError("Token missing 'sub' (subject/customer ID) claim")
        
        return payload["sub"]
