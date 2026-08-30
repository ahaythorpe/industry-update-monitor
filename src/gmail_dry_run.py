"""Run a read-only local assessment of the advice-monitor Gmail label."""

import argparse

from gmail_reader import build_gmail_service, read_label
from monitor import assess_email, format_assessment


def main():
    parser = argparse.ArgumentParser(description="Assess recent advice-monitor Gmail messages")
    parser.add_argument("--credentials", default="credentials.json")
    parser.add_argument("--token", default="token.json")
    parser.add_argument("--max-messages", type=int, default=5)
    parser.add_argument("--newer-than-days", type=int, default=14)
    args = parser.parse_args()

    service = build_gmail_service(args.credentials, args.token)
    emails = read_label(
        service,
        max_messages=args.max_messages,
        newer_than_days=args.newer_than_days,
    )
    print(format_assessment([assess_email(email) for email in emails]))


if __name__ == "__main__":
    main()