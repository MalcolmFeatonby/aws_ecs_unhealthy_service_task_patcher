#!/bin/bash
set -eo pipefail
FUNCTION=$(aws cloudformation describe-stack-resource --stack-name blank-python --logical-resource-id function --query 'StackResourceDetail.PhysicalResourceId' --output text)

aws lambda invoke --function-name $FUNCTION out.json
cat out.json
echo ""
