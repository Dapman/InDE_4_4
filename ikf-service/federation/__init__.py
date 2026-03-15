"""
InDE v3.2 - IKF Federation Module
Local node implementation for the Innovation Knowledge Federation.
"""

from federation.local_node import LocalFederationNode
from federation.package_submitter import PackageSubmitter
from federation.query_client import FederationQueryClient

__all__ = ["LocalFederationNode", "PackageSubmitter", "FederationQueryClient"]
