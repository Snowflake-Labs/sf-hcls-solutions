import jwt
import hashlib
import base64
import time
from datetime import datetime, timedelta, timezone
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import logging

logger = logging.getLogger(__name__)

def load_private_key(private_key_path: str, passphrase: str = None):
    """Load RSA private key from file"""
    try:
        with open(private_key_path, 'rb') as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(),
                password=passphrase.encode() if passphrase else None,
                backend=default_backend()
            )
        return private_key
    except Exception as e:
        logger.error(f"Failed to load private key from {private_key_path}: {str(e)}")
        raise

def generate_public_key_fingerprint(private_key):
    """Generate SHA256 fingerprint of the public key"""
    try:
        # Get public key from private key
        public_key = private_key.public_key()
        
        # Serialize public key in DER format (not PEM) - this is what Snowflake uses
        public_key_der = public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # Calculate SHA256 hash
        sha256_hash = hashlib.sha256(public_key_der).digest()
        
        # Encode as base64 and add SHA256: prefix
        fingerprint = f"SHA256:{base64.b64encode(sha256_hash).decode()}"
        
        return fingerprint
    except Exception as e:
        logger.error(f"Failed to generate public key fingerprint: {str(e)}")
        raise

def create_jwt_token(private_key, account: str, user: str, valid_for_hours: int = 1):
    """Create JWT token for Snowflake authentication"""
    try:
        # Generate public key fingerprint
        public_key_fingerprint = generate_public_key_fingerprint(private_key)
        
        # Create qualified username in format ACCOUNT.USER
        qualified_username = f"{account.upper()}.{user.upper()}"
        
        # Create JWT payload according to Snowflake documentation
        # Use timezone-aware datetime to avoid timestamp conversion issues
        now = datetime.now(timezone.utc)
        payload = {
            # Set the issuer to the fully qualified username concatenated with the public key fingerprint
            'iss': f"{qualified_username}.{public_key_fingerprint}",
            # Set the subject to the fully qualified username
            'sub': qualified_username,
            # Set the issue time to now
            'iat': int(now.timestamp()),
            # Set the expiration time (max 1 hour)
            'exp': int((now + timedelta(hours=min(valid_for_hours, 1))).timestamp())
        }
        
        # Sign JWT with private key
        token = jwt.encode(
            payload, 
            private_key, 
            algorithm='RS256'
        )
        
        # Handle different PyJWT versions
        if isinstance(token, bytes):
            token = token.decode('utf-8')
        
        logger.info(f"✅ JWT token created successfully (expires in {min(valid_for_hours, 1)} hour(s))")
        logger.info(f"   Issuer: {payload['iss'][:50]}...")
        logger.info(f"   Subject: {payload['sub']}")
        
        return token
        
    except Exception as e:
        logger.error(f"Failed to create JWT token: {str(e)}")
        raise

def validate_jwt_token(token: str, private_key):
    """Validate JWT token (for debugging purposes)"""
    try:
        public_key = private_key.public_key()
        decoded = jwt.decode(token, public_key, algorithms=['RS256'])
        logger.info(f"JWT token is valid, expires at: {datetime.fromtimestamp(decoded['exp'])}")
        return decoded
    except jwt.ExpiredSignatureError:
        logger.error("JWT token has expired")
        raise
    except jwt.InvalidTokenError as e:
        logger.error(f"JWT token is invalid: {str(e)}")
        raise 