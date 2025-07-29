#!/usr/bin/env python3
"""
PratikoAI Cross-Repository Artifact Coordination System

Advanced system for sharing build artifacts, deployment information,
and version metadata between repositories during orchestrated deployments.

Features:
- Cross-repository artifact sharing
- Deployment metadata coordination
- Version information propagation
- Health status synchronization
- Rollback artifact management
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import requests
import httpx
import zipfile
import tempfile
from pathlib import Path
from github import Github
import boto3
from botocore.exceptions import NoCredentialsError

logger = logging.getLogger(__name__)


class ArtifactType(Enum):
    """Types of artifacts."""
    BUILD_INFO = "build_info"
    DEPLOYMENT_INFO = "deployment_info"
    VERSION_MANIFEST = "version_manifest"
    HEALTH_REPORT = "health_report"
    COMPATIBILITY_REPORT = "compatibility_report"
    ROLLBACK_INFO = "rollback_info"
    TEST_RESULTS = "test_results"
    PERFORMANCE_METRICS = "performance_metrics"


class StorageBackend(Enum):
    """Supported storage backends."""
    GITHUB_ARTIFACTS = "github_artifacts"
    S3 = "s3"
    LOCAL = "local"
    HTTP = "http"


@dataclass
class ArtifactMetadata:
    """Metadata for an artifact."""
    artifact_id: str
    artifact_type: ArtifactType
    deployment_id: str
    service: str
    version: str
    environment: str
    created_at: datetime
    size_bytes: int
    checksum: str
    storage_backend: StorageBackend
    storage_path: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    expiry_date: Optional[datetime] = None


@dataclass
class DeploymentManifest:
    """Complete deployment manifest with all artifacts."""
    deployment_id: str
    environment: str
    created_at: datetime
    services: Dict[str, str]  # service -> version
    artifacts: List[ArtifactMetadata]
    status: str
    coordinator_version: str = "1.0.0"


class ArtifactStorage:
    """Base class for artifact storage backends."""
    
    async def store_artifact(self, content: bytes, metadata: ArtifactMetadata) -> str:
        """Store artifact and return storage path."""
        raise NotImplementedError
    
    async def retrieve_artifact(self, storage_path: str) -> bytes:
        """Retrieve artifact content."""
        raise NotImplementedError
    
    async def delete_artifact(self, storage_path: str) -> bool:
        """Delete artifact."""
        raise NotImplementedError
    
    async def list_artifacts(self, deployment_id: str) -> List[ArtifactMetadata]:
        """List artifacts for a deployment."""
        raise NotImplementedError


class GitHubArtifactStorage(ArtifactStorage):
    """GitHub Actions artifact storage."""
    
    def __init__(self, github_token: str):
        self.github = Github(github_token)
    
    async def store_artifact(self, content: bytes, metadata: ArtifactMetadata) -> str:
        """Store artifact in GitHub Actions artifacts."""
        # GitHub Actions artifacts are typically handled by the workflow itself
        # This is more of a metadata operation
        
        # For now, we'll simulate storage and return a reference
        storage_path = f"github://{metadata.service}/{metadata.deployment_id}/{metadata.artifact_id}"
        
        logger.info(f"GitHub artifact stored: {storage_path}")
        return storage_path
    
    async def retrieve_artifact(self, storage_path: str) -> bytes:
        """Retrieve artifact from GitHub."""
        # This would use the GitHub API to download artifacts
        # Implementation depends on GitHub API capabilities
        
        logger.info(f"Retrieving GitHub artifact: {storage_path}")
        return b"github-artifact-content"  # Placeholder
    
    async def delete_artifact(self, storage_path: str) -> bool:
        """Delete GitHub artifact."""
        logger.info(f"Deleting GitHub artifact: {storage_path}")
        return True
    
    async def list_artifacts(self, deployment_id: str) -> List[ArtifactMetadata]:
        """List GitHub artifacts for deployment."""
        # This would query GitHub API for workflow artifacts
        return []


class S3ArtifactStorage(ArtifactStorage):
    """Amazon S3 artifact storage."""
    
    def __init__(self, bucket_name: str, region: str = 'us-east-1'):
        self.bucket_name = bucket_name
        self.region = region
        try:
            self.s3_client = boto3.client('s3', region_name=region)
        except NoCredentialsError:
            logger.error("AWS credentials not configured")
            self.s3_client = None
    
    async def store_artifact(self, content: bytes, metadata: ArtifactMetadata) -> str:
        """Store artifact in S3."""
        if not self.s3_client:
            raise RuntimeError("S3 client not available")
        
        # Create S3 key with organized structure
        key = f"deployments/{metadata.environment}/{metadata.deployment_id}/{metadata.service}/{metadata.artifact_type.value}/{metadata.artifact_id}"
        
        try:
            # Upload with metadata
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=content,
                Metadata={
                    'deployment-id': metadata.deployment_id,
                    'service': metadata.service,
                    'version': metadata.version,
                    'environment': metadata.environment,
                    'artifact-type': metadata.artifact_type.value,
                    'created-at': metadata.created_at.isoformat()
                },
                ContentType='application/octet-stream'
            )
            
            storage_path = f"s3://{self.bucket_name}/{key}"
            logger.info(f"S3 artifact stored: {storage_path}")
            return storage_path
            
        except Exception as e:
            logger.error(f"Failed to store S3 artifact: {str(e)}")
            raise
    
    async def retrieve_artifact(self, storage_path: str) -> bytes:
        """Retrieve artifact from S3."""
        if not self.s3_client:
            raise RuntimeError("S3 client not available")
        
        # Parse S3 path
        if not storage_path.startswith('s3://'):
            raise ValueError("Invalid S3 storage path")
        
        path_parts = storage_path[5:].split('/', 1)
        bucket = path_parts[0]
        key = path_parts[1]
        
        try:
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            content = response['Body'].read()
            
            logger.info(f"S3 artifact retrieved: {storage_path}")
            return content
            
        except Exception as e:
            logger.error(f"Failed to retrieve S3 artifact: {str(e)}")
            raise
    
    async def delete_artifact(self, storage_path: str) -> bool:
        """Delete S3 artifact."""
        if not self.s3_client:
            return False
        
        try:
            path_parts = storage_path[5:].split('/', 1)
            bucket = path_parts[0]
            key = path_parts[1]
            
            self.s3_client.delete_object(Bucket=bucket, Key=key)
            logger.info(f"S3 artifact deleted: {storage_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete S3 artifact: {str(e)}")
            return False
    
    async def list_artifacts(self, deployment_id: str) -> List[ArtifactMetadata]:
        """List S3 artifacts for deployment."""
        if not self.s3_client:
            return []
        
        try:
            prefix = f"deployments/{deployment_id}/"
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            artifacts = []
            for obj in response.get('Contents', []):
                # Parse metadata from object key and metadata
                key_parts = obj['Key'].split('/')
                if len(key_parts) >= 6:
                    env = key_parts[1]
                    deployment_id = key_parts[2]
                    service = key_parts[3]
                    artifact_type = key_parts[4]
                    artifact_id = key_parts[5]
                    
                    # Get object metadata
                    obj_response = self.s3_client.head_object(
                        Bucket=self.bucket_name,
                        Key=obj['Key']
                    )
                    
                    metadata = ArtifactMetadata(
                        artifact_id=artifact_id,
                        artifact_type=ArtifactType(artifact_type),
                        deployment_id=deployment_id,
                        service=service,
                        version=obj_response.get('Metadata', {}).get('version', 'unknown'),
                        environment=env,
                        created_at=obj['LastModified'],
                        size_bytes=obj['Size'],
                        checksum=obj.get('ETag', '').strip('"'),
                        storage_backend=StorageBackend.S3,
                        storage_path=f"s3://{self.bucket_name}/{obj['Key']}"
                    )
                    artifacts.append(metadata)
            
            return artifacts
            
        except Exception as e:
            logger.error(f"Failed to list S3 artifacts: {str(e)}")
            return []


class LocalArtifactStorage(ArtifactStorage):
    """Local filesystem artifact storage."""
    
    def __init__(self, base_path: str = "/tmp/pratiko-artifacts"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    async def store_artifact(self, content: bytes, metadata: ArtifactMetadata) -> str:
        """Store artifact locally."""
        # Create directory structure
        artifact_dir = self.base_path / metadata.environment / metadata.deployment_id / metadata.service / metadata.artifact_type.value
        artifact_dir.mkdir(parents=True, exist_ok=True)
        
        # Store artifact file
        artifact_path = artifact_dir / metadata.artifact_id
        with open(artifact_path, 'wb') as f:
            f.write(content)
        
        # Store metadata
        metadata_path = artifact_dir / f"{metadata.artifact_id}.metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump({
                'artifact_id': metadata.artifact_id,
                'artifact_type': metadata.artifact_type.value,
                'deployment_id': metadata.deployment_id,
                'service': metadata.service,
                'version': metadata.version,
                'environment': metadata.environment,
                'created_at': metadata.created_at.isoformat(),
                'size_bytes': metadata.size_bytes,
                'checksum': metadata.checksum,
                'metadata': metadata.metadata
            }, f, indent=2)
        
        storage_path = str(artifact_path)
        logger.info(f"Local artifact stored: {storage_path}")
        return storage_path
    
    async def retrieve_artifact(self, storage_path: str) -> bytes:
        """Retrieve artifact from local storage."""
        try:
            with open(storage_path, 'rb') as f:
                content = f.read()
            
            logger.info(f"Local artifact retrieved: {storage_path}")
            return content
            
        except Exception as e:
            logger.error(f"Failed to retrieve local artifact: {str(e)}")
            raise
    
    async def delete_artifact(self, storage_path: str) -> bool:
        """Delete local artifact."""
        try:
            artifact_path = Path(storage_path)
            metadata_path = artifact_path.parent / f"{artifact_path.name}.metadata.json"
            
            if artifact_path.exists():
                artifact_path.unlink()
            if metadata_path.exists():
                metadata_path.unlink()
            
            logger.info(f"Local artifact deleted: {storage_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete local artifact: {str(e)}")
            return False
    
    async def list_artifacts(self, deployment_id: str) -> List[ArtifactMetadata]:
        """List local artifacts for deployment."""
        artifacts = []
        
        try:
            # Search for metadata files
            for metadata_file in self.base_path.rglob(f"*/{deployment_id}/*/*.metadata.json"):
                with open(metadata_file, 'r') as f:
                    data = json.load(f)
                
                metadata = ArtifactMetadata(
                    artifact_id=data['artifact_id'],
                    artifact_type=ArtifactType(data['artifact_type']),
                    deployment_id=data['deployment_id'],
                    service=data['service'],
                    version=data['version'],
                    environment=data['environment'],
                    created_at=datetime.fromisoformat(data['created_at']),
                    size_bytes=data['size_bytes'],
                    checksum=data['checksum'],
                    storage_backend=StorageBackend.LOCAL,
                    storage_path=str(metadata_file.parent / data['artifact_id']),
                    metadata=data.get('metadata', {})
                )
                artifacts.append(metadata)
            
            return artifacts
            
        except Exception as e:
            logger.error(f"Failed to list local artifacts: {str(e)}")
            return []


class CrossRepoArtifactCoordinator:
    """Main coordinator for cross-repository artifact sharing."""
    
    def __init__(self, storage_backend: StorageBackend = StorageBackend.LOCAL,
                 storage_config: Dict[str, Any] = None):
        self.storage_backend = storage_backend
        self.storage_config = storage_config or {}
        self.storage = self._create_storage_client()
        self.manifests: Dict[str, DeploymentManifest] = {}
    
    def _create_storage_client(self) -> ArtifactStorage:
        """Create storage client based on backend type."""
        
        if self.storage_backend == StorageBackend.GITHUB_ARTIFACTS:
            github_token = self.storage_config.get('github_token') or os.getenv('GITHUB_TOKEN')
            if not github_token:
                raise ValueError("GitHub token required for GitHub artifact storage")
            return GitHubArtifactStorage(github_token)
        
        elif self.storage_backend == StorageBackend.S3:
            bucket_name = self.storage_config.get('bucket_name')
            if not bucket_name:
                raise ValueError("S3 bucket name required for S3 storage")
            region = self.storage_config.get('region', 'us-east-1')
            return S3ArtifactStorage(bucket_name, region)
        
        elif self.storage_backend == StorageBackend.LOCAL:
            base_path = self.storage_config.get('base_path', '/tmp/pratiko-artifacts')
            return LocalArtifactStorage(base_path)
        
        else:
            raise ValueError(f"Unsupported storage backend: {self.storage_backend}")
    
    async def create_deployment_manifest(self, deployment_id: str, environment: str,
                                       services: Dict[str, str]) -> DeploymentManifest:
        """Create a new deployment manifest."""
        
        manifest = DeploymentManifest(
            deployment_id=deployment_id,
            environment=environment,
            created_at=datetime.now(timezone.utc),
            services=services,
            artifacts=[],
            status="created"
        )
        
        self.manifests[deployment_id] = manifest
        
        # Store manifest as artifact
        await self._store_manifest(manifest)
        
        logger.info(f"Created deployment manifest: {deployment_id}")
        return manifest
    
    async def store_artifact(self, deployment_id: str, service: str, 
                           artifact_type: ArtifactType, content: Union[bytes, Dict, str],
                           artifact_id: str = None, metadata: Dict[str, Any] = None) -> ArtifactMetadata:
        """Store an artifact for a deployment."""
        
        manifest = self.manifests.get(deployment_id)
        if not manifest:
            raise ValueError(f"Deployment manifest not found: {deployment_id}")
        
        # Convert content to bytes if needed
        if isinstance(content, dict):
            content_bytes = json.dumps(content, indent=2).encode('utf-8')
        elif isinstance(content, str):
            content_bytes = content.encode('utf-8')
        else:
            content_bytes = content
        
        # Generate artifact ID if not provided
        if not artifact_id:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            artifact_id = f"{artifact_type.value}_{timestamp}.json"
        
        # Calculate checksum
        import hashlib
        checksum = hashlib.sha256(content_bytes).hexdigest()
        
        # Create artifact metadata
        artifact_metadata = ArtifactMetadata(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            deployment_id=deployment_id,
            service=service,
            version=manifest.services.get(service, 'unknown'),
            environment=manifest.environment,
            created_at=datetime.now(timezone.utc),
            size_bytes=len(content_bytes),
            checksum=checksum,
            storage_backend=self.storage_backend,
            storage_path="",  # Will be set by storage backend
            metadata=metadata or {}
        )
        
        # Store in backend
        storage_path = await self.storage.store_artifact(content_bytes, artifact_metadata)
        artifact_metadata.storage_path = storage_path
        
        # Add to manifest
        manifest.artifacts.append(artifact_metadata)
        await self._store_manifest(manifest)
        
        logger.info(f"Stored artifact: {artifact_id} for deployment {deployment_id}")
        return artifact_metadata
    
    async def retrieve_artifact(self, deployment_id: str, artifact_id: str) -> tuple[bytes, ArtifactMetadata]:
        """Retrieve an artifact by ID."""
        
        manifest = self.manifests.get(deployment_id)
        if not manifest:
            # Try to load manifest from storage
            manifest = await self._load_manifest(deployment_id)
            if not manifest:
                raise ValueError(f"Deployment manifest not found: {deployment_id}")
        
        # Find artifact metadata
        artifact_metadata = None
        for artifact in manifest.artifacts:
            if artifact.artifact_id == artifact_id:
                artifact_metadata = artifact
                break
        
        if not artifact_metadata:
            raise ValueError(f"Artifact not found: {artifact_id}")
        
        # Retrieve content
        content = await self.storage.retrieve_artifact(artifact_metadata.storage_path)
        
        logger.info(f"Retrieved artifact: {artifact_id} from deployment {deployment_id}")
        return content, artifact_metadata
    
    async def list_artifacts(self, deployment_id: str, 
                           artifact_type: ArtifactType = None,
                           service: str = None) -> List[ArtifactMetadata]:
        """List artifacts for a deployment with optional filtering."""
        
        manifest = self.manifests.get(deployment_id)
        if not manifest:
            manifest = await self._load_manifest(deployment_id)
            if not manifest:
                return []
        
        artifacts = manifest.artifacts
        
        # Apply filters
        if artifact_type:
            artifacts = [a for a in artifacts if a.artifact_type == artifact_type]
        
        if service:
            artifacts = [a for a in artifacts if a.service == service]
        
        return artifacts
    
    async def share_artifact_cross_repo(self, deployment_id: str, artifact_id: str,
                                      target_repo: str, target_workflow: str) -> Dict[str, Any]:
        """Share an artifact with another repository's workflow."""
        
        # Retrieve the artifact
        content, metadata = await self.retrieve_artifact(deployment_id, artifact_id)
        
        # Create sharing payload
        sharing_payload = {
            "deployment_id": deployment_id,
            "artifact_metadata": {
                "artifact_id": metadata.artifact_id,
                "artifact_type": metadata.artifact_type.value,
                "service": metadata.service,
                "version": metadata.version,
                "environment": metadata.environment,
                "created_at": metadata.created_at.isoformat(),
                "size_bytes": metadata.size_bytes,
                "checksum": metadata.checksum,
                "metadata": metadata.metadata
            },
            "artifact_content": content.decode('utf-8') if metadata.artifact_type in [
                ArtifactType.BUILD_INFO, ArtifactType.DEPLOYMENT_INFO, 
                ArtifactType.VERSION_MANIFEST
            ] else content.hex(),  # Hex encode binary content
            "shared_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Store as shared artifact
        shared_artifact_id = f"shared_{artifact_id}_{int(datetime.now().timestamp())}"
        await self.store_artifact(
            deployment_id, 
            "coordinator", 
            ArtifactType.DEPLOYMENT_INFO,
            sharing_payload,
            shared_artifact_id,
            {
                "shared_with": target_repo,
                "target_workflow": target_workflow,
                "original_artifact": artifact_id
            }
        )
        
        logger.info(f"Shared artifact {artifact_id} with {target_repo}")
        
        return {
            "shared_artifact_id": shared_artifact_id,
            "target_repo": target_repo,
            "payload_size": len(json.dumps(sharing_payload)),
            "shared_at": sharing_payload["shared_at"]
        }
    
    async def receive_shared_artifact(self, shared_artifact_data: Dict[str, Any]) -> ArtifactMetadata:
        """Receive a shared artifact from another repository."""
        
        deployment_id = shared_artifact_data["deployment_id"]
        artifact_data = shared_artifact_data["artifact_metadata"]
        
        # Recreate artifact metadata
        metadata = ArtifactMetadata(
            artifact_id=artifact_data["artifact_id"],
            artifact_type=ArtifactType(artifact_data["artifact_type"]),
            deployment_id=deployment_id,
            service=artifact_data["service"],
            version=artifact_data["version"],
            environment=artifact_data["environment"],
            created_at=datetime.fromisoformat(artifact_data["created_at"]),
            size_bytes=artifact_data["size_bytes"],
            checksum=artifact_data["checksum"],
            storage_backend=self.storage_backend,
            storage_path="",
            metadata=artifact_data.get("metadata", {})
        )
        metadata.metadata["shared_from"] = shared_artifact_data.get("source_repo", "unknown")
        metadata.metadata["received_at"] = datetime.now(timezone.utc).isoformat()
        
        # Decode content
        if metadata.artifact_type in [ArtifactType.BUILD_INFO, ArtifactType.DEPLOYMENT_INFO, ArtifactType.VERSION_MANIFEST]:
            content = shared_artifact_data["artifact_content"].encode('utf-8')
        else:
            content = bytes.fromhex(shared_artifact_data["artifact_content"])
        
        # Store locally
        storage_path = await self.storage.store_artifact(content, metadata)
        metadata.storage_path = storage_path
        
        # Update or create manifest
        manifest = self.manifests.get(deployment_id)
        if not manifest:
            # Create minimal manifest for shared artifacts
            manifest = DeploymentManifest(
                deployment_id=deployment_id,
                environment=metadata.environment,
                created_at=datetime.now(timezone.utc),
                services={metadata.service: metadata.version},
                artifacts=[],
                status="shared"
            )
            self.manifests[deployment_id] = manifest
        
        manifest.artifacts.append(metadata)
        await self._store_manifest(manifest)
        
        logger.info(f"Received shared artifact: {metadata.artifact_id}")
        return metadata
    
    async def create_version_manifest(self, deployment_id: str) -> Dict[str, Any]:
        """Create a comprehensive version manifest for cross-repo coordination."""
        
        manifest = self.manifests.get(deployment_id)
        if not manifest:
            raise ValueError(f"Deployment manifest not found: {deployment_id}")
        
        # Collect all version information
        version_manifest = {
            "deployment_id": deployment_id,
            "environment": manifest.environment,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "services": manifest.services,
            "coordinator_version": manifest.coordinator_version,
            "artifacts": [],
            "health_status": {},
            "compatibility_info": {},
            "rollback_info": {}
        }
        
        # Add artifact information
        for artifact in manifest.artifacts:
            version_manifest["artifacts"].append({
                "artifact_id": artifact.artifact_id,
                "artifact_type": artifact.artifact_type.value,
                "service": artifact.service,
                "created_at": artifact.created_at.isoformat(),
                "size_bytes": artifact.size_bytes,
                "checksum": artifact.checksum
            })
        
        # Store version manifest as artifact
        await self.store_artifact(
            deployment_id,
            "coordinator",
            ArtifactType.VERSION_MANIFEST,
            version_manifest,
            f"version_manifest_{int(datetime.now().timestamp())}.json"
        )
        
        return version_manifest
    
    async def cleanup_artifacts(self, deployment_id: str, older_than_days: int = 30) -> int:
        """Clean up old artifacts for a deployment."""
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=older_than_days)
        
        artifacts = await self.list_artifacts(deployment_id)
        cleaned_count = 0
        
        for artifact in artifacts:
            if artifact.created_at < cutoff_date:
                success = await self.storage.delete_artifact(artifact.storage_path)
                if success:
                    cleaned_count += 1
        
        # Update manifest to remove cleaned artifacts
        manifest = self.manifests.get(deployment_id)
        if manifest:
            manifest.artifacts = [
                a for a in manifest.artifacts 
                if a.created_at >= cutoff_date
            ]
            await self._store_manifest(manifest)
        
        logger.info(f"Cleaned up {cleaned_count} artifacts for deployment {deployment_id}")
        return cleaned_count
    
    async def _store_manifest(self, manifest: DeploymentManifest) -> None:
        """Store deployment manifest as artifact."""
        
        manifest_data = {
            "deployment_id": manifest.deployment_id,
            "environment": manifest.environment,
            "created_at": manifest.created_at.isoformat(),
            "services": manifest.services,
            "status": manifest.status,
            "coordinator_version": manifest.coordinator_version,
            "artifacts": [
                {
                    "artifact_id": a.artifact_id,
                    "artifact_type": a.artifact_type.value,
                    "service": a.service,
                    "version": a.version,
                    "created_at": a.created_at.isoformat(),
                    "size_bytes": a.size_bytes,
                    "checksum": a.checksum,
                    "storage_path": a.storage_path,
                    "metadata": a.metadata
                }
                for a in manifest.artifacts
            ]
        }
        
        # Store manifest
        manifest_content = json.dumps(manifest_data, indent=2).encode('utf-8')
        
        import hashlib
        checksum = hashlib.sha256(manifest_content).hexdigest()
        
        manifest_metadata = ArtifactMetadata(
            artifact_id=f"manifest_{manifest.deployment_id}.json",
            artifact_type=ArtifactType.DEPLOYMENT_INFO,
            deployment_id=manifest.deployment_id,
            service="coordinator",
            version=manifest.coordinator_version,
            environment=manifest.environment,
            created_at=datetime.now(timezone.utc),
            size_bytes=len(manifest_content),
            checksum=checksum,
            storage_backend=self.storage_backend,
            storage_path=""
        )
        
        storage_path = await self.storage.store_artifact(manifest_content, manifest_metadata)
        manifest_metadata.storage_path = storage_path
    
    async def _load_manifest(self, deployment_id: str) -> Optional[DeploymentManifest]:
        """Load deployment manifest from storage."""
        
        try:
            # Try to find manifest artifact
            artifacts = await self.storage.list_artifacts(deployment_id)
            manifest_artifact = None
            
            for artifact in artifacts:
                if (artifact.artifact_type == ArtifactType.DEPLOYMENT_INFO and 
                    artifact.service == "coordinator" and
                    artifact.artifact_id.startswith("manifest_")):
                    manifest_artifact = artifact
                    break
            
            if not manifest_artifact:
                return None
            
            # Load manifest content
            content = await self.storage.retrieve_artifact(manifest_artifact.storage_path)
            manifest_data = json.loads(content.decode('utf-8'))
            
            # Recreate manifest object
            manifest = DeploymentManifest(
                deployment_id=manifest_data["deployment_id"],
                environment=manifest_data["environment"],
                created_at=datetime.fromisoformat(manifest_data["created_at"]),
                services=manifest_data["services"],
                artifacts=[],
                status=manifest_data.get("status", "unknown"),
                coordinator_version=manifest_data.get("coordinator_version", "1.0.0")
            )
            
            # Recreate artifact metadata
            for artifact_data in manifest_data["artifacts"]:
                artifact_metadata = ArtifactMetadata(
                    artifact_id=artifact_data["artifact_id"],
                    artifact_type=ArtifactType(artifact_data["artifact_type"]),
                    deployment_id=artifact_data.get("deployment_id", deployment_id),
                    service=artifact_data["service"],
                    version=artifact_data["version"],
                    environment=artifact_data.get("environment", manifest.environment),
                    created_at=datetime.fromisoformat(artifact_data["created_at"]),
                    size_bytes=artifact_data["size_bytes"],
                    checksum=artifact_data["checksum"],
                    storage_backend=self.storage_backend,
                    storage_path=artifact_data["storage_path"],
                    metadata=artifact_data.get("metadata", {})
                )
                manifest.artifacts.append(artifact_metadata)
            
            self.manifests[deployment_id] = manifest
            logger.info(f"Loaded deployment manifest: {deployment_id}")
            return manifest
            
        except Exception as e:
            logger.error(f"Failed to load manifest for {deployment_id}: {str(e)}")
            return None


# Example usage and testing
async def main():
    """Example usage of the artifact coordination system."""
    
    # Create coordinator with local storage
    coordinator = CrossRepoArtifactCoordinator(
        storage_backend=StorageBackend.LOCAL,
        storage_config={"base_path": "/tmp/pratiko-artifacts-test"}
    )
    
    deployment_id = "deploy-test-20240115-143022"
    
    # Create deployment manifest
    manifest = await coordinator.create_deployment_manifest(
        deployment_id=deployment_id,
        environment="staging",
        services={"backend": "1.2.0", "frontend-android": "2.1.0"}
    )
    
    print(f"Created manifest: {manifest.deployment_id}")
    
    # Store some example artifacts
    build_info = {
        "service": "backend",
        "version": "1.2.0",
        "build_time": datetime.now().isoformat(),
        "git_commit": "abc123def456",
        "docker_image": "pratiko-backend:1.2.0"
    }
    
    artifact = await coordinator.store_artifact(
        deployment_id=deployment_id,
        service="backend",
        artifact_type=ArtifactType.BUILD_INFO,
        content=build_info,
        metadata={"builder": "github-actions"}
    )
    
    print(f"Stored artifact: {artifact.artifact_id}")
    
    # Create version manifest
    version_manifest = await coordinator.create_version_manifest(deployment_id)
    print(f"Created version manifest with {len(version_manifest['artifacts'])} artifacts")
    
    # List artifacts
    artifacts = await coordinator.list_artifacts(deployment_id)
    print(f"Found {len(artifacts)} artifacts:")
    for a in artifacts:
        print(f"  - {a.artifact_id} ({a.artifact_type.value}, {a.service})")


if __name__ == "__main__":
    from datetime import timedelta
    asyncio.run(main())