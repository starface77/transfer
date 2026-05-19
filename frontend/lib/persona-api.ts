// Persona API client

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000'

export interface Persona {
  id: string
  name: string
  description: string
  colors: {
    primary: string
    secondary: string
    accent: string
  }
  tags: string[]
  audio_enabled: boolean
}

export interface PersonasResponse {
  personas: Persona[]
  active_persona: string | null
}

export async function listPersonas(): Promise<PersonasResponse> {
  const response = await fetch(`${BACKEND_URL}/api/personas`)
  return response.json()
}

export async function getActivePersona(): Promise<{ id: string | null; name: string; description: string }> {
  const response = await fetch(`${BACKEND_URL}/api/personas/active`)
  return response.json()
}

export async function activatePersona(personaId: string): Promise<{ status: string; message: string }> {
  const response = await fetch(`${BACKEND_URL}/api/personas/activate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ persona_id: personaId }),
  })
  return response.json()
}

export async function deactivatePersona(): Promise<{ status: string; message: string }> {
  const response = await fetch(`${BACKEND_URL}/api/personas/deactivate`, {
    method: 'POST',
  })
  return response.json()
}

export async function getAgentName(): Promise<{ agent_name: string }> {
  const response = await fetch(`${BACKEND_URL}/api/personas/agent-name`)
  return response.json()
}
