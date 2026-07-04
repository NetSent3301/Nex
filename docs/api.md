# API Reference

## Health
`GET /api/v1/health`

## Chat
`POST /api/v1/chat`

Request:
```json
{
  "message": "string",
  "conversation_id": "string | null"
}
```

Response:
```json
{
  "reply": "string",
  "conversation_id": "string"
}
```
