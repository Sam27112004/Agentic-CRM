# API Documentation

## Rate Limits by Tier
- **Starter**: 1,000 requests per hour
- **Standard**: 10,000 requests per hour
- **Enterprise**: 100,000 requests per hour

## v1 Deprecation Timeline
API v1 is deprecated and will be sunset on December 31, 2026. Please migrate to v2 before this date.

## v2 Breaking Changes
API v2 introduces a new authentication mechanism (Bearer token) and changes the payload structure for webhooks.

## Header Requirements
All API requests must include the `Authorization` header and the `Content-Type: application/json` header.
