const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:5000";

async function checkResponse(res) {
  if (!res.ok) {
    const text = await res.text();
    let message = `${res.status} ${res.statusText}`;
    try {
      const body = JSON.parse(text);
      message = body.error || body.message || JSON.stringify(body);
    } catch {
      if (text.trim()) message = text;
    }
    throw new Error(message);
  }
  return res.json();
}

export async function getAllAssignments() {
  const res = await fetch(`${API_BASE}/assignments/`);
  return checkResponse(res);
}

export async function createAssignment(payload) {
  const res = await fetch(`${API_BASE}/assignments/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return checkResponse(res);
}

export async function updateAssignment(id, payload) {
  const res = await fetch(`${API_BASE}/assignments/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return checkResponse(res);
}

export async function deleteAssignment(id) {
  const res = await fetch(`${API_BASE}/assignments/${id}`, {
    method: "DELETE",
  });
  return checkResponse(res);
}
