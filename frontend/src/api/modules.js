import { api } from './http'

export const appointmentApi = {
  list: () => api.get('/api/appointments'),
  create: (payload) => api.post('/api/appointments', payload),
  updateStatus: (id, status) => api.patch(`/api/appointments/${id}`, { status }),
  batches: (params = {}) => {
    const query = new URLSearchParams(params)
    const suffix = query.toString() ? `?${query}` : ''
    return api.get(`/api/appointments/batches${suffix}`)
  }
}

export const batchApi = {
  list: () => api.get('/api/batches'),
  stats: (params = {}) => {
    const query = new URLSearchParams(params)
    const suffix = query.toString() ? `?${query}` : ''
    return api.get(`/api/batches/stats${suffix}`)
  },
  create: (payload) => api.post('/api/batches', payload),
  update: (id, payload) => api.patch(`/api/batches/${id}`, payload),
  delete: (id) => api.delete(`/api/batches/${id}`)
}

export const examApi = {
  questions: (subject) => api.get(`/api/exams/questions?subject=${encodeURIComponent(subject)}`),
  submit: (payload) => api.post('/api/exams/submit', payload)
}

export const scoreApi = {
  list: (params = {}) => {
    const query = new URLSearchParams(params)
    const suffix = query.toString() ? `?${query}` : ''
    return api.get(`/api/scores${suffix}`)
  }
}

export const makeupApi = {
  list: () => api.get('/api/makeups'),
  create: (payload) => api.post('/api/makeups', payload),
  update: (id, payload) => api.patch(`/api/makeups/${id}`, payload)
}

export const ruleApi = {
  list: () => api.get('/api/rules'),
  update: (id, payload) => api.patch(`/api/rules/${id}`, payload)
}
