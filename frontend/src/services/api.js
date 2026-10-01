const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {})
    },
    ...options
  })

  const contentType = response.headers.get('content-type') || ''
  const payload = contentType.includes('application/json')
    ? await response.json()
    : await response.text()

  if (!response.ok) {
    const message = typeof payload === 'object' && payload?.detail
      ? payload.detail
      : `Request failed (${response.status})`
    throw new Error(message)
  }

  return payload
}

export const api = {
  get: (path) => request(path),
  post: (path, body) => request(path, { method: 'POST', body: JSON.stringify(body) })
}

export const endpoints = {
  curriculum: '/content/curriculum',
  section: (code) => `/content/sections/${encodeURIComponent(code)}`,
  unitQuestions: (id) => `/content/units/${id}/questions`,
  question: (id) => `/questions/${id}`,
  createLearner: '/learners/',
  startAssessment: '/assessments/start',
  answer: (id) => `/assessments/${id}/answer`,
  result: (id) => `/assessments/${id}/result`,
  evaluate: '/adaptation/evaluate',
  nextQuestion: '/adaptation/next-question',
  scaffold: '/adaptation/scaffold',
  progress: (id) => `/progress/${id}`,
  summary: (id) => `/progress/${id}/summary`
}
