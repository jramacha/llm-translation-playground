import json

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_opensearchserverless as aws_opss
)
from constructs import Construct

class OpsServerlessSearchStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    collection_name = self.node.try_get_context('collection_name')
    oss_admin_access_role_arn = self.node.try_get_context('oss_admin_access_role_arn')

    network_security_policy = json.dumps([{
      "Rules": [
        {
          "Resource": [
            f"collection/{collection_name}"
          ],
          "ResourceType": "dashboard"
        },
        {
          "Resource": [
            f"collection/{collection_name}"
          ],
          "ResourceType": "collection"
        }
      ],
      "AllowFromPublic": True
    }], indent=2)

    #XXX: max length of policy name is 32
    network_security_policy_name = f"{collection_name}-security-policy"
    assert len(network_security_policy_name) <= 32, f"Network Security Policy: {network_security_policy_name}"

    cfn_network_security_policy = aws_opss.CfnSecurityPolicy(self, "NetworkSecurityPolicy",
      policy=network_security_policy,
      name=network_security_policy_name,
      type="network"
    )

    encryption_security_policy = json.dumps({
      "Rules": [
        {
          "Resource": [
            f"collection/{collection_name}"
          ],
          "ResourceType": "collection"
        }
      ],
      "AWSOwnedKey": True
    }, indent=2)

    #XXX: max length of policy name is 32
    encryption_security_policy_name = f"{collection_name}-security-policy"
    assert len(encryption_security_policy_name) <= 32, f"Encryption Security Policy: {encryption_security_policy_name}"

    cfn_encryption_security_policy = aws_opss.CfnSecurityPolicy(self, "EncryptionSecurityPolicy",
      policy=encryption_security_policy,
      name=encryption_security_policy_name,
      type="encryption"
    )

    cfn_collection = aws_opss.CfnCollection(self, "OpssSearchCollection",
      name=collection_name,
      description="Collection to be used for search using OpenSearch Serverless",
      type="SEARCH" # [SEARCH, TIMESERIES, VECTORSEARCH]
    )
    cfn_collection.add_dependency(cfn_network_security_policy)
    cfn_collection.add_dependency(cfn_encryption_security_policy)

    data_access_policy = json.dumps([
      {
        "Rules": [
          {
            "Resource": [
              f"collection/{collection_name}"
            ],
            "Permission": [
              "aoss:CreateCollectionItems",
              "aoss:DeleteCollectionItems",
              "aoss:UpdateCollectionItems",
              "aoss:DescribeCollectionItems"
            ],
            "ResourceType": "collection"
          },
          {
            "Resource": [
              f"index/{collection_name}/*"
            ],
            "Permission": [
              "aoss:CreateIndex",
              "aoss:DeleteIndex",
              "aoss:UpdateIndex",
              "aoss:DescribeIndex",
              "aoss:ReadDocument",
              "aoss:WriteDocument"
            ],
            "ResourceType": "index"
          }
        ],
        "Principal": [
          f"{oss_admin_access_role_arn}"
        ],
        "Description": "data-access-rule"
      }
    ], indent=2)

    #XXX: max length of policy name is 32
    data_access_policy_name = f"{collection_name}-access-policy"
    assert len(data_access_policy_name) <= 32

    cfn_access_policy = aws_opss.CfnAccessPolicy(self, "OpssDataAccessPolicy",
      name=data_access_policy_name,
      description="Policy for data access",
      policy=data_access_policy,
      type="data"
    )


    cdk.CfnOutput(self, 'OpenSearchEndpoint',
      value=cfn_collection.attr_collection_endpoint,
      export_name=f'{self.stack_name}-OpenSearchEndpoint')
    cdk.CfnOutput(self, 'DashboardsURL',
      value=cfn_collection.attr_dashboard_endpoint,
      export_name=f'{self.stack_name}-DashboardsURL')
