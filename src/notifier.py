"""Notification and escalation helper for alert actions."""

from typing import Any, Dict, List
import json
import httpx
import smtplib
from email.message import EmailMessage
from .config import (
    SLACK_WEBHOOK_URL,
    NOTIFICATION_WEBHOOK_URL,
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USERNAME,
    SMTP_PASSWORD,
    EMAIL_FROM,
    EMAIL_TO,
)
from .models import AlertAction


def build_alert_actions(severity: str) -> List[AlertAction]:
    actions: List[AlertAction] = []
    if severity in ["HIGH", "CRITICAL"]:
        actions.append(AlertAction(type="slack", target="#portfolio-risk-alerts", message="Immediate review required. Please investigate the breached limit and re-balance positions."))
        actions.append(AlertAction(type="ticket", target="Jira: RISK-0001", message="Create a rebalancing ticket for the portfolio breach."))
    else:
        actions.append(AlertAction(type="dashboard", target="risk-dashboard", message="Track the portfolio on the daily risk dashboard."))
    return actions


def record_audit_entry(portfolio_id: str, summary: str) -> Dict[str, str]:
    return {"portfolio_id": portfolio_id, "audit_message": summary}


def send_slack_message(text: str) -> Dict[str, Any]:
    if not SLACK_WEBHOOK_URL:
        return {"adapter": "slack", "status": "skipped", "reason": "missing webhook url"}
    try:
        response = httpx.post(SLACK_WEBHOOK_URL, json={"text": text}, timeout=10.0)
        response.raise_for_status()
        return {"adapter": "slack", "status": "sent", "code": response.status_code}
    except Exception as exc:
        return {"adapter": "slack", "status": "failed", "error": str(exc)}


def send_webhook_notification(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not NOTIFICATION_WEBHOOK_URL:
        return {"adapter": "webhook", "status": "skipped", "reason": "missing notification webhook url"}
    try:
        response = httpx.post(NOTIFICATION_WEBHOOK_URL, json=payload, timeout=10.0)
        response.raise_for_status()
        return {"adapter": "webhook", "status": "sent", "code": response.status_code}
    except Exception as exc:
        return {"adapter": "webhook", "status": "failed", "error": str(exc)}


def send_email_message(subject: str, body: str) -> Dict[str, Any]:
    if not SMTP_HOST or not EMAIL_FROM or not EMAIL_TO:
        return {"adapter": "email", "status": "skipped", "reason": "email configuration missing"}
    try:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = EMAIL_FROM
        message["To"] = EMAIL_TO
        message.set_content(body)

        if SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=20)
        else:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20)
            server.starttls()
        if SMTP_USERNAME and SMTP_PASSWORD:
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(message)
        server.quit()
        return {"adapter": "email", "status": "sent"}
    except Exception as exc:
        return {"adapter": "email", "status": "failed", "error": str(exc)}


def send_notifications(portfolio_id: str, severity: str, actions: List[AlertAction]) -> List[Dict[str, Any]]:
    summary_text = f"Portfolio {portfolio_id} generated a {severity} risk alert with {len(actions)} escalation action(s)."
    output = []

    output.append(send_slack_message(summary_text))
    output.append(send_webhook_notification({
        "portfolio_id": portfolio_id,
        "severity": severity,
        "actions": [action.model_dump() for action in actions],
        "summary": summary_text,
    }))
    output.append(send_email_message(
        subject=f"Portfolio Risk Alert: {portfolio_id} ({severity})",
        body=summary_text,
    ))

    return output
