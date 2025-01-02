import json

import aws_cdk as cdk
from aws_cdk import (
  Stack,
  aws_opensearchserverless as aws_opss,
  aws_iam as iam
)
from constructs import Construct
from aws_cdk import Aspects
from cdk_nag import NagSuppressions

MODEL_CHOICES = {
   "anthropic.claude-3-5-sonnet-20240620-v1:0": "Claude 3.5 Sonnet v1",
   "anthropic.claude-3-5-haiku-20241022-v1:0": "Claude 3.5 Haiku v1",
   "amazon.titan-text-premier-v1:0":"Amazon Titan Text Premier",
   "mistral.mistral-large-2402-v1:0": "Mistral",
   "ai21.j2-ultra-v1":"Jurassic-2 Ultra",
   "cohere.command-r-plus-v1:0":"Cohere	Command R+",
   "meta.llama3-1-70b-instruct-v1:0":"Meta	Llama 3.1 70b Instruct",
   "amazon.nova-lite-v1:0":"Amazon Nova Lite"
}

class OpsServerlessSearchStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)
    collection_name = self.node.try_get_context('collection_name')
    
    # Add CDK nag suppressions for wildcard permissions
    NagSuppressions.add_stack_suppressions(
      self,
      [
          {
              "id": "AwsSolutions-IAM5",
              "reason": "Wildcard permissions needed for OpenSearch indices API access. Stack also creates data acess policy restricting access to only the relevant collection."
          }
      ]
    )

    # Create IAM role for Bedrock invocation
    llm_translation_playground_role = iam.Role(self, "LLMTranslationPlaygroundAppRole",
      assumed_by=iam.AccountPrincipal(self.account),
    )
    
    # Add policy to allow listing and creating indices
    opensearch_indices_policy = iam.PolicyStatement(
      sid = "OpenSearchIndicesPolicy",
      actions=["aoss:APIAccessAll"],
      resources=["*"]
    )
    llm_translation_playground_role.add_to_principal_policy(opensearch_indices_policy)

    # Add policy to allow Bedrock invocation for specific models
    bedrock_policy = iam.PolicyStatement(
      actions=["bedrock:InvokeModel"],
      resources=[
        f"arn:aws:bedrock:{self.region}::foundation-model/{model_id}"
        for model_id in MODEL_CHOICES.keys()
      ]
    )
    llm_translation_playground_role.add_to_principal_policy(bedrock_policy)
    llm_translation_playground_role_arn = llm_translation_playground_role.role_arn
  
    # Create a custom assume role policy (not attached to any role)
    assume_role_policy = iam.ManagedPolicy(
      self, "LLMTranslationPlaygroundAppRoleAssumePolicy",
      document=iam.PolicyDocument(
        statements=[
          iam.PolicyStatement(
            actions=["sts:AssumeRole"],
            effect=iam.Effect.ALLOW,
            resources=[llm_translation_playground_role.role_arn]  # This allows assuming only the Bedrock invocation role
          )
        ]
      ),
      description="Custom policy to assume the LLMTranslationPlayground Application role"
    )

    # Output the created Bedrock role's ARN
    cdk.CfnOutput(self, "LLMTranslationPlaygroundAppRoleArn",
      value=llm_translation_playground_role.role_arn,
      description="ARN of the IAM role for LLMTranslationPlayground App Role"
    )

    # Output the custom assume role policy ARN
    cdk.CfnOutput(self, "LLMTranslationPlaygroundAppRoleAssumePolicyArn",
      value=assume_role_policy.managed_policy_arn,
      description="ARN of the custom policy to assume LLMTranslationPlayground App Role. Add this policy to your current role/user"
    )

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
          f"{llm_translation_playground_role_arn}"
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
