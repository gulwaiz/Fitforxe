const BASE = process.env.REACT_APP_API_URL; // comes from Render env var

export async function getProfile() {
  const res = await fetch(`${BASE}/api/profile`);
  if (!res.ok) throw new Error('API error');
  return res.json();
}
