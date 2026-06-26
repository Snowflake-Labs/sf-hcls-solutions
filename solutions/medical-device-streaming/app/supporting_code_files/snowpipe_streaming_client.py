import requests
import json
import time
import logging
import gzip
import base64
from datetime import datetime
from typing import Optional
import pandas as pd
from supporting_code_files.config import SnowflakeConfig
from supporting_code_files.jwt_utils import load_private_key, create_jwt_token
import pytz

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SnowpipeStreamingClient:
    """
    High-performance Snowpipe Streaming client for medical device data ingestion.
    Uses the REST API for direct ingestion to Snowflake.
    Updated to support dynamic pipe and schema configuration.
    """
    
    def __init__(self, config: SnowflakeConfig = None):
        self.config = config or SnowflakeConfig()
        self.control_host = f"https://{self.config.ACCOUNT}.snowflakecomputing.com"
        self.ingest_host = None
        self.session = requests.Session()
        # Configure session for low-latency streaming with aggressive timeouts
        self.session.request = lambda *args, **kwargs: requests.Session.request(
            self.session, *args, timeout=(2, 5), **kwargs  # 2s connect, 5s read timeout
        )
        
        # Dynamic pipe and schema configuration
        self.pipe_name = None  # Will be set by caller
        self.schema = None     # Will be set by caller
        self.channel_name = "default_channel"  # Will be set by caller
        
        self.continuation_token = None
        self.offset_token = 0
        self.scoped_token = None
        self.stats = {
            'batches_sent': 0,
            'records_sent': 0,
            'bytes_sent': 0,
            'errors': 0,
            'start_time': None,
            'session_requests': 0  # Track requests to refresh session periodically
        }
    
    def _refresh_session_if_needed(self):
        """Refresh HTTP session periodically to prevent degradation"""
        self.stats['session_requests'] += 1
        
        # Refresh session every 1000 requests to prevent degradation
        if self.stats['session_requests'] % 1000 == 0:
            logger.debug(f"Refreshing HTTP session after {self.stats['session_requests']} requests")
            self.session.close()
            self.session = requests.Session()
            # Reapply session configuration for low-latency streaming
            self.session.request = lambda *args, **kwargs: requests.Session.request(
                self.session, *args, timeout=(2, 5), **kwargs  # 2s connect, 5s read timeout
            )
        
    def authenticate(self) -> str:
        """Generate fresh JWT token using config for high-performance streaming authentication"""
        logger.debug("🔐 Generating fresh JWT token for streaming authentication...")
        
        if not self.config.PRIVATE_KEY_PATH:
            raise Exception("SNOWFLAKE_PRIVATE_KEY_PATH not configured. Key-pair authentication is required for high-performance streaming.")
        
        try:
            # Use the config's fresh JWT token generation
            jwt_token = self.config.get_fresh_jwt_token()
            
            logger.debug("✅ Fresh JWT token generated successfully for streaming")
            return jwt_token
            
        except Exception as e:
            logger.error(f"❌ JWT token generation failed: {str(e)}")
            logger.error("Make sure you have:")
            logger.error("1. Generated an RSA key pair")
            logger.error("2. Assigned the public key to your Snowflake user")
            logger.error("3. Set SNOWFLAKE_PRIVATE_KEY_PATH in your .env file")
            raise
    
    def discover_ingest_host(self, jwt_token: str) -> str:
        """Discover the ingest host for streaming"""
        logger.debug("Discovering ingest host...")
        
        hostname_url = f"{self.control_host}/v2/streaming/hostname"
        
        headers = {
            'Authorization': f'Bearer {jwt_token}',
            'X-Snowflake-Authorization-Token-Type': 'KEYPAIR_JWT'
        }
        
        try:
            response = self.session.get(hostname_url, headers=headers)
            response.raise_for_status()
            
            # The response should be a plain text hostname
            self.ingest_host = f"https://{response.text.strip()}"
            
            logger.debug(f"✅ Discovered ingest host: {self.ingest_host}")
            return self.ingest_host
            
        except Exception as e:
            logger.error(f"Failed to discover ingest host: {str(e)}")
            raise
    
    def get_scoped_token(self, jwt_token: str) -> str:
        """Get scoped token for streaming operations (V1 compatible)"""
        logger.debug("Getting scoped token...")
        
        token_url = f"{self.control_host}/oauth/token"
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Bearer {jwt_token}'
        }
        
        # Extract hostname from ingest_host for scope (V1 method)
        hostname = self.ingest_host.replace('https://', '').replace('http://', '')
        
        data = {
            'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
            'scope': hostname
        }
        
        try:
            response = self.session.post(token_url, headers=headers, data=data)
            response.raise_for_status()
            
            # Snowflake returns the JWT token directly, not as JSON (V1 method)
            self.scoped_token = response.text.strip()
            
            if not self.scoped_token:
                raise Exception("No scoped token received")
            
            logger.debug("✅ Scoped token obtained successfully")
            return self.scoped_token
            
        except Exception as e:
            logger.error(f"Failed to get scoped token: {str(e)}")
            raise
    
    def create_channel(self, scoped_token: str) -> bool:
        """Create streaming channel using pipe-based approach (V1 compatible)"""
        if not self.pipe_name or not self.schema:
            raise Exception("Pipe name and schema must be configured before creating channel")

        # Store the scoped token for use in send_data_batch
        self.scoped_token = scoped_token

        # Auto-discover ingest host if not already set
        if not self.ingest_host:
            logger.debug("Discovering ingest host...")
            self.ingest_host = self.discover_ingest_host(scoped_token)

        logger.debug(f"Creating pipe-based channel '{self.channel_name}' for pipe {self.pipe_name}...")
        
        # Use pipe-based channel URL like V1
        pipe_channel_url = f"{self.ingest_host}/v2/streaming/databases/{self.config.DATABASE}/schemas/{self.schema}/pipes/{self.pipe_name}/channels/{self.channel_name}"
        
        headers = {
            'Authorization': f'Bearer {scoped_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = self.session.put(pipe_channel_url, headers=headers, json={})
            response.raise_for_status()
            
            channel_data = response.json()
            self.continuation_token = channel_data.get('next_continuation_token')
            # Handle None offset token for new channels
            offset_token_raw = channel_data.get('channel_status', {}).get('last_committed_offset_token')
            self.offset_token = int(offset_token_raw) if offset_token_raw is not None else 0
            
            logger.debug(f"✅ Pipe-based channel '{self.channel_name}' created for pipe {self.pipe_name}")
            logger.debug(f"   Continuation token: {self.continuation_token[:50]}..." if self.continuation_token else "None")
            logger.debug(f"   Offset token: {self.offset_token}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create pipe-based channel: {str(e)}")
            logger.error(f"Pipe: {self.pipe_name}")
            logger.error(f"Channel: {self.channel_name}")
            
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    logger.error(f"Error response: {json.dumps(error_data, indent=2)}")
                except:
                    logger.error(f"Error response: {e.response.text}")
            return False

    def send_data_batch(self, data_batch: list[dict]) -> bool:
        """Send data batch using pipe-based streaming (V1 compatible)"""
        if not self.continuation_token:
            logger.error("Channel not opened. Call create_channel() first.")
            return False

        try:
            # Prepare the data as NDJSON (same as V1)
            ndjson_data = self.prepare_batch_data(data_batch)
            
            # Increment offset token for this batch
            current_offset = self.offset_token + 1
            
            # Use pipe-based streaming URL like V1
            pipe_stream_url = f"{self.ingest_host}/v2/streaming/data/databases/{self.config.DATABASE}/schemas/{self.schema}/pipes/{self.pipe_name}/channels/{self.channel_name}/rows"
            
            headers = {
                'Authorization': f'Bearer {self.scoped_token}',
                'Content-Type': 'application/x-ndjson'
            }
            
            # Parameters as per V1 documentation
            params = {
                'continuationToken': self.continuation_token,
                'offsetToken': current_offset
            }
            
            # Send the batch
            # Refresh session periodically to prevent degradation
            self._refresh_session_if_needed()
            
            start_time = time.time()
            response = self.session.post(pipe_stream_url, headers=headers, params=params, data=ndjson_data)
            response.raise_for_status()
            
            response_data = response.json()
            
            # Update continuation token for next batch
            self.continuation_token = response_data.get('next_continuation_token', self.continuation_token)
            self.offset_token = current_offset
            
            # Update stats
            duration = time.time() - start_time
            self.stats['batches_sent'] += 1
            self.stats['records_sent'] += len(data_batch)
            self.stats['bytes_sent'] += len(ndjson_data)
            
            logger.debug(f"✅ Batch sent successfully: {len(data_batch)} records in {duration:.3f}s")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send batch via pipe: {str(e)}")
            logger.error(f"Pipe: {self.pipe_name}")
            logger.error(f"Channel: {self.channel_name}")
            logger.error(f"URL: {pipe_stream_url}")
            logger.error(f"Params: {params}")
            
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    logger.error(f"Error response: {json.dumps(error_data, indent=2)}")
                except:
                    logger.error(f"Error response: {e.response.text}")
            
            self.stats['errors'] += 1
            return False

    def configure_for_pipe(self, pipe_name: str, schema: str, channel_name: str):
        """Configure client for specific pipe and schema (V1 compatible)"""
        self.pipe_name = pipe_name
        self.schema = schema
        self.channel_name = channel_name
        logger.debug(f"Configured client for pipe: {schema}.{pipe_name}, channel: {channel_name}")

    def prepare_batch_data(self, data_batch: list[dict]) -> str:
        """Prepare batch data for streaming ingestion as NDJSON (same as V1)"""
        processed_batch = []
        for record in data_batch:
            processed_record = {}
            
            # Add application-level ingestion timestamp for granular tracking
            processed_record['app_ingestion_timestamp'] = datetime.now(pytz.UTC).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            
            # Process each field in the record
            for key, value in record.items():
                if value is None:
                    processed_record[key] = None
                elif hasattr(value, 'strftime'):
                    # TIMEZONE-NEUTRAL: Convert all timestamps to UTC for Snowflake storage
                    
                    if hasattr(value, 'tzinfo') and value.tzinfo is not None:
                        # Already timezone-aware - convert to UTC
                        utc_value = value.astimezone(pytz.UTC)
                        processed_record[key] = utc_value.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                    else:
                        # Naive datetime - our generators create UTC timestamps as naive
                        # Add UTC timezone info and format for Snowflake
                        utc_value = pytz.UTC.localize(value)
                        processed_record[key] = utc_value.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                elif hasattr(value, 'date') and hasattr(value.date, '__call__'):
                    # Handle date objects
                    processed_record[key] = value.date().isoformat()
                elif hasattr(value, 'isoformat'):
                    # Handle other datetime-like objects
                    processed_record[key] = value.isoformat()
                elif hasattr(value, 'timestamp'):
                    # Handle pandas Timestamp objects specifically
                    processed_record[key] = pd.Timestamp(value).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                else:
                    # Keep other values as-is
                    processed_record[key] = value
            
            # Note: DO NOT send load_utc_timestamp field - let Snowflake populate it via DEFAULT CONVERT_TIMEZONE('UTC', CURRENT_TIMESTAMP())
            # This ensures the timestamp reflects exactly when Snowflake processes each record in proper UTC timezone
            # Note: ingestion_timestamp will also be set by Snowflake DEFAULT CURRENT_TIMESTAMP()
            # This provides batch-level ingestion tracking which is appropriate for monitoring
            
            processed_batch.append(processed_record)
        
        # Create NDJSON format (newline-delimited JSON)
        ndjson_data = '\n'.join(json.dumps(record) for record in processed_batch)
        return ndjson_data
    
    def close_channel(self, scoped_token: str) -> bool:
        """Close the streaming channel"""
        if not self.channel_name:
            return True
        
        logger.debug(f"Closing channel '{self.channel_name}'...")
        
        try:
            close_url = f"{self.ingest_host}/v2/streaming/channels/{self.channel_name}"
            
            headers = {
                'Authorization': f'Bearer {scoped_token}',
                'Content-Type': 'application/json'
            }
            
            response = self.session.delete(close_url, headers=headers)
            response.raise_for_status()
            
            logger.debug(f"✅ Channel '{self.channel_name}' closed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to close channel: {str(e)}")
            return False
    
    def get_channel_status(self, scoped_token: str) -> dict:
        """Get channel status information"""
        if not self.channel_name:
            return {}
        
        try:
            status_url = f"{self.ingest_host}/v2/streaming/channels/{self.channel_name}"
            
            headers = {
                'Authorization': f'Bearer {scoped_token}'
            }
            
            response = self.session.get(status_url, headers=headers)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to get channel status: {str(e)}")
            return {}
    
    def reset_stats(self):
        """Reset streaming statistics"""
        self.stats = {
            'batches_sent': 0,
            'records_sent': 0,
            'bytes_sent': 0,
            'errors': 0,
            'start_time': datetime.now(pytz.UTC)
        }
    
    def get_stats(self) -> dict:
        """Get current streaming statistics"""
        stats = self.stats.copy()
        if stats['start_time']:
            elapsed = (datetime.now(pytz.UTC) - stats['start_time']).total_seconds()
            stats['elapsed_seconds'] = elapsed
            stats['records_per_second'] = stats['records_sent'] / elapsed if elapsed > 0 else 0
            stats['bytes_per_second'] = stats['bytes_sent'] / elapsed if elapsed > 0 else 0
        return stats

def main():
    """Test the updated streaming client"""
    from config import MedicalDeviceConfig
    
    config = SnowflakeConfig()
    device_config = MedicalDeviceConfig()
    
    print("🔄 Testing Updated Snowpipe Streaming Client")
    print("=" * 50)
    
    # Test with ECG configuration
    client = SnowpipeStreamingClient(config)
    client.configure_for_pipe(
        pipe_name=config.DEVICE_TABLES['ECG'],
        schema=config.CLINICAL_SCHEMA,
        channel_name=config.get_clinical_channel_name('ECG')
    )
    
    try:
        # Test authentication
        jwt_token = client.authenticate()
        print("✅ Authentication successful")
        
        # Test host discovery
        client.discover_ingest_host(jwt_token)
        print(f"✅ Ingest host discovered: {client.ingest_host}")
        
        # Test scoped token
        scoped_token = client.get_scoped_token(jwt_token)
        print("✅ Scoped token obtained")
        
        # Test channel creation
        channel_created = client.create_channel(scoped_token)
        if channel_created:
            print(f"✅ Channel created: {client.channel_name}")
            
            # Test with sample data
            sample_data = [{
                'timestamp': datetime.now(pytz.UTC),
                'device_id': 'ECG_001',
                'patient_id': 'TEST_PATIENT',
                'session_id': 'TEST_SESSION',
                'heart_rate': 75,
                'lead_I': 0.5,
                'signal_quality': 0.95
            }]
            
            success = client.send_data_batch(sample_data)
            if success:
                print("✅ Test data sent successfully")
                print(f"Stats: {client.get_stats()}")
            else:
                print("❌ Failed to send test data")
            
            # Close channel
            client.close_channel(scoped_token)
            print("✅ Channel closed")
        else:
            print("❌ Failed to create channel")
        
        print("\n✅ Streaming client test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Streaming client test failed: {str(e)}")

if __name__ == "__main__":
    main() 