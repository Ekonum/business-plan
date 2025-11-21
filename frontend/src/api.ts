export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

export async function fetchProjection(startYear: number, years: number, initialCash: number) {
  const params = new URLSearchParams({ start_year: String(startYear), years: String(years), initial_cash: String(initialCash) })
  const res = await fetch(`${API_URL}/projections?${params.toString()}`)
  if (!res.ok) throw new Error('Erreur lors du calcul de projection')
  return res.json()
}

export async function createEntity<T>(path: string, payload: T) {
  const res = await fetch(`${API_URL}/${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  if (!res.ok) throw new Error('Erreur de sauvegarde')
  return res.json()
}
