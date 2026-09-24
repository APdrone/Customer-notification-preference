import pytest
import jwt
from datetime import timedelta, datetime, timezone
import os
from app.config import JWTConfig
from app.auth import TokenValidator


class TestJWTConfiguration:
    """Test JWT configuration setup"""
    
    def test_jwt_config_defaults(self):
        """Test JWT configuration with default values"""
        assert JWTConfig.ALGORITHM == "HS256"
        assert JWTConfig.TOKEN_SCHEME == "Bearer"
        assert isinstance(JWTConfig.TOKEN_EXPIRATION_HOURS, int)
        assert JWTConfig.TOKEN_EXPIRATION_HOURS > 0
    
    def test_jwt_secret_key_set(self):
        """Test that JWT_SECRET_KEY is configured"""
        assert JWTConfig.SECRET_KEY is not None
        assert isinstance(JWTConfig.SECRET_KEY, str)
        assert len(JWTConfig.SECRET_KEY) > 0
    
    def test_jwt_config_validation(self):
        """Test configuration validation"""
        assert JWTConfig.validate_config() is True


class TestTokenCreation:
    """Test JWT token creation"""
    
    def test_create_token_with_customer_id(self):
        """Test creating a token with customer ID"""
        customer_id = "cust_12345"
        token = TokenValidator.create_token({"sub": customer_id})
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_token_includes_expiration(self):
        """Test that created token includes expiration claim"""
        customer_id = "cust_12345"
        token = TokenValidator.create_token({"sub": customer_id})
        
        payload = jwt.decode(
            token,
            JWTConfig.SECRET_KEY,
            algorithms=[JWTConfig.ALGORITHM]
        )
        
        assert "exp" in payload
        assert isinstance(payload["exp"], int)
    
    def test_create_token_with_custom_expiration(self):
        """Test creating a token with custom expiration"""
        customer_id = "cust_12345"
        custom_expiry = timedelta(hours=1)
        token = TokenValidator.create_token({"sub": customer_id}, expires_delta=custom_expiry)
        
        payload = jwt.decode(
            token,
            JWTConfig.SECRET_KEY,
            algorithms=[JWTConfig.ALGORITHM]
        )
        
        assert "exp" in payload
        # Token should expire in approximately 1 hour
        now = datetime.now(timezone.utc).timestamp()
        assert payload["exp"] > now  # Token is in the future
    
    def test_create_token_preserves_data(self):
        """Test that token creation preserves provided claims"""
        data = {"sub": "cust_12345", "email": "customer@example.com", "role": "customer"}
        token = TokenValidator.create_token(data)
        
        payload = jwt.decode(
            token,
            JWTConfig.SECRET_KEY,
            algorithms=[JWTConfig.ALGORITHM]
        )
        
        assert payload["sub"] == "cust_12345"
        assert payload["email"] == "customer@example.com"
        assert payload["role"] == "customer"


class TestTokenValidation:
    """Test JWT token validation"""
    
    def test_validate_valid_token(self):
        """Test validating a valid token"""
        customer_id = "cust_12345"
        token = TokenValidator.create_token({"sub": customer_id})
        
        payload = TokenValidator.validate_token(token)
        
        assert payload is not None
        assert payload["sub"] == customer_id
    
    def test_validate_invalid_signature_raises_error(self):
        """Test that token with invalid signature raises error"""
        # Create a token with one secret
        token = TokenValidator.create_token({"sub": "cust_12345"})
        
        # Try to validate with a different secret
        with pytest.raises(jwt.InvalidTokenError):
            # Temporarily change the secret
            original_secret = JWTConfig.SECRET_KEY
            JWTConfig.SECRET_KEY = "different-secret-key"
            try:
                TokenValidator.validate_token(token)
            finally:
                JWTConfig.SECRET_KEY = original_secret
    
    def test_validate_expired_token_raises_error(self):
        """Test that expired token raises ExpiredSignatureError"""
        # Create a token that expires immediately
        customer_id = "cust_12345"
        expired_expiry = timedelta(seconds=-1)  # Negative = already expired
        token = TokenValidator.create_token({"sub": customer_id}, expires_delta=expired_expiry)
        
        with pytest.raises(jwt.ExpiredSignatureError):
            TokenValidator.validate_token(token)
    
    def test_validate_malformed_token_raises_error(self):
        """Test that malformed token raises DecodeError"""
        malformed_token = "not.a.valid.token"
        
        with pytest.raises((jwt.DecodeError, jwt.InvalidTokenError)):
            TokenValidator.validate_token(malformed_token)
    
    def test_validate_empty_token_raises_error(self):
        """Test that empty token raises error"""
        with pytest.raises((jwt.DecodeError, jwt.InvalidTokenError)):
            TokenValidator.validate_token("")


class TestCustomerIdExtraction:
    """Test extracting customer ID from tokens"""
    
    def test_extract_customer_id_from_valid_token(self):
        """Test extracting customer ID from valid token"""
        customer_id = "cust_12345"
        token = TokenValidator.create_token({"sub": customer_id})
        
        extracted_id = TokenValidator.extract_customer_id(token)
        
        assert extracted_id == customer_id
    
    def test_extract_customer_id_from_token_without_sub_raises_error(self):
        """Test that extracting ID from token without 'sub' claim raises error"""
        # Create token without 'sub' claim
        token = TokenValidator.create_token({"email": "customer@example.com"})
        
        with pytest.raises(KeyError) as exc_info:
            TokenValidator.extract_customer_id(token)
        
        assert "'sub'" in str(exc_info.value)
    
    def test_extract_customer_id_from_expired_token_raises_error(self):
        """Test that extracting ID from expired token raises error"""
        customer_id = "cust_12345"
        expired_expiry = timedelta(seconds=-1)
        token = TokenValidator.create_token({"sub": customer_id}, expires_delta=expired_expiry)
        
        with pytest.raises(jwt.ExpiredSignatureError):
            TokenValidator.extract_customer_id(token)


class TestBearerTokenScheme:
    """Test Bearer token scheme implementation"""
    
    def test_token_scheme_constant(self):
        """Test Bearer token scheme is correctly configured"""
        assert JWTConfig.TOKEN_SCHEME == "Bearer"
    
    def test_valid_bearer_header_format(self):
        """Test creating valid Bearer Authorization header"""
        customer_id = "cust_12345"
        token = TokenValidator.create_token({"sub": customer_id})
        
        # Format should be "Bearer <token>"
        auth_header = f"{JWTConfig.TOKEN_SCHEME} {token}"
        
        assert auth_header.startswith("Bearer ")
        assert len(auth_header.split()) == 2  # Should have Bearer and token
    
    def test_extract_token_from_bearer_header(self):
        """Test extracting token from Bearer Authorization header"""
        customer_id = "cust_12345"
        token = TokenValidator.create_token({"sub": customer_id})
        
        # Simulate Authorization header: "Bearer <token>"
        auth_header = f"{JWTConfig.TOKEN_SCHEME} {token}"
        
        # Extract token (in real middleware, this happens)
        parts = auth_header.split()
        assert len(parts) == 2
        scheme, extracted_token = parts
        
        assert scheme == "Bearer"
        assert extracted_token == token
        
        # Validate extracted token works
        payload = TokenValidator.validate_token(extracted_token)
        assert payload["sub"] == customer_id


class TestIntegration:
    """Integration tests for JWT workflow"""
    
    def test_complete_jwt_workflow(self):
        """Test complete workflow: create, validate, extract"""
        # Step 1: Create token
        customer_id = "cust_12345"
        token = TokenValidator.create_token({"sub": customer_id, "email": "cust@example.com"})
        
        # Step 2: Simulate Bearer header
        auth_header = f"{JWTConfig.TOKEN_SCHEME} {token}"
        _, extracted_token = auth_header.split()
        
        # Step 3: Validate token
        payload = TokenValidator.validate_token(extracted_token)
        assert payload is not None
        
        # Step 4: Extract customer ID
        extracted_id = TokenValidator.extract_customer_id(extracted_token)
        
        # Step 5: Verify identity
        assert extracted_id == customer_id
        assert payload["email"] == "cust@example.com"
