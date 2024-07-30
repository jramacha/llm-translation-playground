#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os
import OpsServerlessSearchStack
import aws_cdk as cdk


AWS_ENV = cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'),
  region=os.getenv('CDK_DEFAULT_REGION'))

app = cdk.App()

ops_serverless_search_stack = OpsServerlessSearchStack(app, "OpsServerlessSearchStack",
  env=AWS_ENV)

app.synth()