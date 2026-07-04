const BASE_URL = "http://127.0.0.1:8765/api/v1";

export async function chat(message: string, conversationId?: string) {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, conversation_id: conversationId }),
  });
  return res.json();
}
