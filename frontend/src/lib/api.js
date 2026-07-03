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
  getPacklistStatus: () => request('GET', '/api/packlist'),

  getPacklistDashboard: () => request('GET', '/api/packlist/dashboard'),

  downloadPacklistTemplate: () => request('GET', '/api/packlist/template'),

  importPacklist: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return request('POST', '/api/packlist/import', fd)
  },

  clearPacklist: () => request('DELETE', '/api/packlist'),

  getPallet: (palletNum) =>
    request('GET', `/api/pallet?pallet_num=${encodeURIComponent(palletNum)}`),

  addCartonToPallet: (palletNum, cartonScan) =>
    request('POST', '/api/pallet/carton', { pallet_num: palletNum, carton_scan: cartonScan }),

  removeCartonFromPallet: (palletNum, cartonScan) =>
    request('DELETE', '/api/pallet/carton', { pallet_num: palletNum, carton_scan: cartonScan }),

  clearPallet: (palletNum) =>
    request('DELETE', `/api/pallet?pallet_num=${encodeURIComponent(palletNum)}`),

  previewPrint: (payload) => request('POST', '/api/print/preview', payload),

  print: (payload) => request('POST', '/api/print', payload),

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
