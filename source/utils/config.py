import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables immediately upon module import
load_dotenv()

# Initialize all parameters as module-level variables
HOST: Optional[str] = os.getenv('HOST')
REGION: Optional[str] = os.getenv('REGION', default="us-east-1")
APP_ROLE_ARN: Optional[str] = os.getenv('APP_ROLE_ARN')

# Convert numeric values during initialization
_oss_limit = os.getenv('OSS_INGESTION_LIMIT')
OSS_INGESTION_LIMIT: Optional[int] = int(_oss_limit) if _oss_limit is not None else None

_faiss_limit = os.getenv('FAISS_INGESTION_LIMIT')
FAISS_INGESTION_LIMIT: Optional[int] = int(_faiss_limit) if _faiss_limit is not None else None

_oss_port = os.getenv('OSS_PORT', default=443)
OSS_PORT: Optional[int] = int(_oss_port) if _oss_port is not None else None

_session_ttl = os.getenv('SESSION_TTL', default=3000)
SESSION_TTL: Optional[int] = int(_session_ttl) if _session_ttl is not None else None

# Getter functions if you still want them
def get_host() -> Optional[str]:
    """Return the OpenSearch Serverless host"""
    return HOST

def get_region() -> Optional[str]:
    """Return the AWS region"""
    return REGION

def get_oss_ingestion_limit() -> Optional[int]:
    """Return the OpenSearch Serverless ingestion limit"""
    return OSS_INGESTION_LIMIT

def get_faiss_ingestion_limit() -> Optional[int]:
    """Return the FAISS ingestion limit"""
    return FAISS_INGESTION_LIMIT

def get_oss_port() -> Optional[int]:
    """Return the OpenSearch Serverless port number"""
    return OSS_PORT

def get_app_role_arn() -> Optional[str]:
    """Return the application IAM role ARN"""
    return APP_ROLE_ARN

def get_session_ttl() -> Optional[int]:
    """Return the STS Session TTL"""
    return SESSION_TTL