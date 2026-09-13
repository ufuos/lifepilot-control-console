"""
AWS Cloud Infrastructure & Bedrock Agent Tools for Strands SDK.

Provides customized Strands tools (@tool) to interact with AWS Bedrock Agents,
CloudWatch metric/log queries, and S3 asset storage.
"""

import json
import logging
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from strands import tool

logger = logging.getLogger("lifepilot.agents.tools.aws")


@tool
def invoke_aws_bedrock_agent(
    agent_id: str,
    agent_alias_id: str,
    session_id: str,
    prompt: str,
    input_text: str = "",
) -> Dict[str, Any]:
    """
    Invoke an AWS Bedrock Agent runtime endpoint for specialized enterprise reasoning or task execution.

    Args:
        agent_id: The unique ID of the AWS Bedrock Agent.
        agent_alias_id: The alias ID (e.g., 'TSTALIASID' or production alias ID).
        session_id: Unique session identifier for maintaining context.
        prompt: User instructions or query to pass to the Bedrock Agent.
        input_text: Additional context or structured payload string.

    Returns:
        Dict containing the agent response completion string and execution metadata.
    """
    try:
        client = boto3.client("bedrock-agent-runtime")
        combined_prompt = f"{prompt}\nContext: {input_text}" if input_text else prompt

        response = client.invoke_agent(
            agentId=agent_id,
            agentAliasId=agent_alias_id,
            sessionId=session_id,
            inputText=combined_prompt,
        )

        completion_text = ""
        for event in response.get("completion", []):
            if "chunk" in event:
                chunk = event["chunk"]
                if "bytes" in chunk:
                    completion_text += chunk["bytes"].decode("utf-8")

        return {
            "status": "success",
            "agent_id": agent_id,
            "session_id": session_id,
            "completion": completion_text or "Agent completed without string payload.",
        }
    except (BotoCoreError, ClientError) as exc:
        logger.error("AWS Bedrock Agent invocation failed: %s", str(exc))
        return {
            "status": "error",
            "agent_id": agent_id,
            "error": str(exc),
        }


@tool
def query_cloudwatch_logs(
    log_group_name: str,
    filter_pattern: str,
    limit: int = 20,
) -> Dict[str, Any]:
    """
    Search and retrieve recent log events from AWS CloudWatch Log Groups for debugging or diagnostic runs.

    Args:
        log_group_name: The target CloudWatch Log Group path (e.g., '/aws/lambda/lifepilot-worker').
        filter_pattern: CloudWatch search filter pattern (e.g., 'ERROR', 'Exception').
        limit: Maximum number of events to fetch (default 20, max 100).

    Returns:
        Dict containing retrieved event messages and timestamps.
    """
    try:
        client = boto3.client("logs")
        response = client.filter_log_events(
            logGroupName=log_group_name,
            filterPattern=filter_pattern,
            limit=min(limit, 100),
        )

        events = [
            {
                "timestamp": event.get("timestamp"),
                "message": event.get("message"),
                "logStreamName": event.get("logStreamName"),
            }
            for event in response.get("events", [])
        ]

        return {
            "status": "success",
            "log_group": log_group_name,
            "count": len(events),
            "events": events,
        }
    except (BotoCoreError, ClientError) as exc:
        logger.error("Failed to fetch CloudWatch logs: %s", str(exc))
        return {
            "status": "error",
            "log_group": log_group_name,
            "error": str(exc),
        }


@tool
def put_s3_report(
    bucket_name: str,
    key: str,
    content: str,
    content_type: str = "text/markdown",
) -> Dict[str, Any]:
    """
    Save generated reports, summaries, or JSON outputs to an AWS S3 bucket.

    Args:
        bucket_name: Target S3 bucket name.
        key: The S3 object key/path where file will be uploaded.
        content: String content (text, Markdown, or serialized JSON) to write.
        content_type: MIME type of the content (default 'text/markdown').

    Returns:
        Dict confirming upload path or error details.
    """
    try:
        s3 = boto3.client("s3")
        s3.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=content.encode("utf-8"),
            ContentType=content_type,
        )

        return {
            "status": "success",
            "bucket": bucket_name,
            "key": key,
            "s3_uri": f"s3://{bucket_name}/{key}",
        }
    except (BotoCoreError, ClientError) as exc:
        logger.error("Failed to upload object to S3: %s", str(exc))
        return {
            "status": "error",
            "bucket": bucket_name,
            "key": key,
            "error": str(exc),
        }


def get_aws_tools(aws_region: str = "us-east-1", agent_id: Optional[str] = None) -> List[Any]:
    """
    Returns the compiled list of AWS-related Strands tools.
    """
    return [
        invoke_aws_bedrock_agent,
        query_cloudwatch_logs,
        put_s3_report,
    ]