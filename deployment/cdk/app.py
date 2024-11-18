import os
from opensearch_serverless_search import OpsServerlessSearchStack
import aws_cdk as cdk
import cdk_nag
from cdk_nag import NagSuppressions, AwsSolutionsChecks

AWS_ENV = cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION'))

app = cdk.App()

ops_serverless_search_stack = OpsServerlessSearchStack(app, "LLMTranslationPlaygroundStack", env=AWS_ENV)

cdk.Aspects.of(app).add(AwsSolutionsChecks())

app.synth()
