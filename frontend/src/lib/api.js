const BASE = ''

async function request(method, path, body, options = {}) {
  const headers = { ...(options.headers || {}) }
  const init = { method, headers }

  if (body !== undefined && !(body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
    init.body = JSON.stringify(body)
  } else if (body instanceof FormData) {
    init.body = body
  }

  const res = await fetch(`${BASE}${path}`, init)
  if (!res.ok) {
    let detail = res.statusText
    try {
      const data = await res.json()
      detail = data.detail || data.message || JSON.stringify(data)
      if (typeof detail === 'object') {
        detail = detail.message || JSON.stringify(detail)
      }
    } catch {
      // ignore
    }
    throw new Error(detail)
  }

  const ct = res.headers.get('content-type') || ''
  if (ct.includes('application/json')) {
    return res.json()
  }
  return res.blob()
}

export const api = {
  listArticles: (q = '', limit = 200, offset = 0) =>
    request('GET', `/api/articles?q=${encodeURIComponent(q)}&limit=${limit}&offset=${offset}`),

  getArticle: (artNum) => request('GET', `/api/articles/${encodeURIComponent(artNum)}`),

  upsertArticle: (artNum, qtyPerCarton) =>
    request('PUT', `/api/articles/${encodeURIComponent(artNum)}`, { qty_per_carton: qtyPerCarton }),

  deleteArticle: (artNum) => request('DELETE', `/api/articles/${encodeURIComponent(artNum)}`),

  exportArticles: () => request('GET', '/api/articles/export'),

  downloadTemplate: () => request('GET', '/api/articles/template'),

  importArticles: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return request('POST', '/api/articles/import', fd)
  },

  previewPrint: (lines) => request('POST', '/api/print/preview', lines),

  print: (lines) => request('POST', '/api/print', lines),

  listPrinters: () => request('GET', '/api/print/printers'),

  setPrinter: (settings) => request('PUT', '/api/print/printers', settings),
}

export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
