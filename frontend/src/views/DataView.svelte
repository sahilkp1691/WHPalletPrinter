<script>
  import { api, downloadBlob } from '../lib/api.js'

  let search = $state('')
  let items = $state([])
  let total = $state(0)
  let loading = $state(false)
  let error = $state('')
  let toast = $state(null)

  let newArtNum = $state('')
  let newQty = $state('')
  let editingKey = $state(null)
  let editQty = $state('')
  let importInput

  let toastTimer

  function showToast(message, type = 'success') {
    toast = { message, type }
    clearTimeout(toastTimer)
    toastTimer = setTimeout(() => {
      toast = null
    }, 5000)
  }

  async function loadArticles() {
    loading = true
    error = ''
    try {
      const result = await api.listArticles(search)
      items = result.items
      total = result.total
    } catch (e) {
      error = e.message
    } finally {
      loading = false
    }
  }

  async function addArticle() {
    const art = newArtNum.trim()
    const qty = Number(newQty)
    if (!art) {
      error = 'Art Num is required'
      return
    }
    if (!Number.isInteger(qty) || qty <= 0) {
      error = 'Qty/Carton must be a positive whole number'
      return
    }
    error = ''
    try {
      await api.upsertArticle(art, qty)
      newArtNum = ''
      newQty = ''
      showToast(`Saved ${art.toUpperCase()}`)
      await loadArticles()
    } catch (e) {
      error = e.message
    }
  }

  function startEdit(item) {
    editingKey = item.art_num
    editQty = String(item.qty_per_carton)
  }

  function cancelEdit() {
    editingKey = null
    editQty = ''
  }

  async function saveEdit(artNum) {
    const qty = Number(editQty)
    if (!Number.isInteger(qty) || qty <= 0) {
      error = 'Qty/Carton must be a positive whole number'
      return
    }
    error = ''
    try {
      await api.upsertArticle(artNum, qty)
      editingKey = null
      showToast(`Updated ${artNum}`)
      await loadArticles()
    } catch (e) {
      error = e.message
    }
  }

  async function removeArticle(artNum) {
    if (!confirm(`Delete ${artNum}?`)) return
    error = ''
    try {
      await api.deleteArticle(artNum)
      showToast(`Deleted ${artNum}`)
      await loadArticles()
    } catch (e) {
      error = e.message
    }
  }

  async function exportExcel() {
    try {
      const blob = await api.exportArticles()
      downloadBlob(blob, 'article_qty_carton.xlsx')
      showToast('Exported article data')
    } catch (e) {
      error = e.message
    }
  }

  async function downloadTemplate() {
    try {
      const blob = await api.downloadTemplate()
      downloadBlob(blob, 'article_template.xlsx')
      showToast('Downloaded template')
    } catch (e) {
      error = e.message
    }
  }

  async function onImportChange(e) {
    const file = e.target.files?.[0]
    if (!file) return
    error = ''
    try {
      const result = await api.importArticles(file)
      const msg = `Import complete: ${result.inserted} added, ${result.updated} updated`
      showToast(msg, result.errors?.length ? 'error' : 'success')
      if (result.errors?.length) {
        error = result.errors.slice(0, 5).join('; ')
      }
      await loadArticles()
    } catch (e) {
      error = e.message
    } finally {
      e.target.value = ''
    }
  }

  $effect(() => {
    const q = search
    const timer = setTimeout(loadArticles, q ? 250 : 0)
    return () => clearTimeout(timer)
  })
</script>

<div class="page">
  <header class="page-header">
    <div>
      <h1>Article Data</h1>
      <p class="subtitle">Manage Art Num to Qty/Carton lookup. Export, edit in Excel, and reimport.</p>
    </div>
    <div class="header-actions">
      <button class="btn-ghost" onclick={downloadTemplate}>Template</button>
      <button class="btn-ghost" onclick={exportExcel}>Export Excel</button>
      <button class="btn-primary" onclick={() => importInput?.click()}>Import Excel</button>
      <input bind:this={importInput} type="file" accept=".xlsx,.xlsm" hidden onchange={onImportChange} />
    </div>
  </header>

  {#if error}
    <div class="banner error">{error}</div>
  {/if}

  <section class="card add-card">
    <h2>Add Article</h2>
    <div class="add-grid">
      <div class="field">
        <label for="new-art">Art Num</label>
        <input id="new-art" type="text" bind:value={newArtNum} placeholder="e.g. PK1400" />
      </div>
      <div class="field narrow">
        <label for="new-qty">Qty/Carton</label>
        <input id="new-qty" type="number" min="1" step="1" bind:value={newQty} />
      </div>
      <button class="btn-primary" onclick={addArticle}>Add</button>
    </div>
  </section>

  <section class="card table-card">
    <div class="table-toolbar">
      <input
        type="search"
        bind:value={search}
        placeholder="Search Art Num..."
        class="search-input"
      />
      <span class="count">{total} article{total === 1 ? '' : 's'}</span>
    </div>

    {#if loading}
      <p class="muted">Loading...</p>
    {:else if items.length === 0}
      <p class="muted">No articles found. Add one above or import from Excel.</p>
    {:else}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Art Num</th>
              <th>Qty/Carton</th>
              <th>Updated</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {#each items as item}
              <tr>
                <td><strong>{item.art_num}</strong></td>
                <td>
                  {#if editingKey === item.art_num}
                    <input type="number" min="1" step="1" bind:value={editQty} class="inline-input" />
                  {:else}
                    {item.qty_per_carton}
                  {/if}
                </td>
                <td class="muted-cell">{new Date(item.updated_at).toLocaleString()}</td>
                <td class="actions">
                  {#if editingKey === item.art_num}
                    <button class="btn-primary small" onclick={() => saveEdit(item.art_num)}>Save</button>
                    <button class="btn-ghost small" onclick={cancelEdit}>Cancel</button>
                  {:else}
                    <button class="btn-ghost small" onclick={() => startEdit(item)}>Edit</button>
                    <button class="btn-ghost small danger" onclick={() => removeArticle(item.art_num)}>Delete</button>
                  {/if}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </section>
</div>

{#if toast}
  <div class="toast" class:success={toast.type === 'success'} class:error={toast.type === 'error'}>
    {toast.message}
  </div>
{/if}

<style>
  .page {
    padding: 28px 32px 40px;
    max-width: 1100px;
  }

  .page-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    flex-wrap: wrap;
  }

  .page-header h1 {
    font-size: 22px;
    font-weight: 700;
    margin-bottom: 4px;
  }

  .subtitle {
    color: var(--text-muted);
    font-size: 13px;
  }

  .header-actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }

  .banner {
    margin: 16px 0;
    padding: 12px 14px;
    border-radius: var(--radius);
    font-size: 13px;
  }
  .banner.error {
    background: var(--danger-bg);
    color: var(--danger);
    border: 1px solid #fecaca;
  }

  .add-card {
    margin-top: 20px;
  }

  .add-card h2 {
    font-size: 15px;
    font-weight: 600;
    margin-bottom: 14px;
  }

  .add-grid {
    display: grid;
    grid-template-columns: 1fr 140px auto;
    gap: 16px;
    align-items: end;
  }

  .field label {
    display: block;
    font-size: 12px;
    font-weight: 600;
    color: var(--text-muted);
    margin-bottom: 6px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .table-card {
    margin-top: 20px;
  }

  .table-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 14px;
  }

  .search-input {
    max-width: 280px;
  }

  .count {
    color: var(--text-muted);
    font-size: 13px;
  }

  .muted {
    color: var(--text-muted);
    font-size: 13px;
  }

  .table-wrap {
    overflow-x: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }

  th, td {
    padding: 10px 12px;
    text-align: left;
    border-bottom: 1px solid var(--border);
    vertical-align: middle;
  }

  th {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--text-muted);
    background: var(--surface2);
  }

  .muted-cell {
    color: var(--text-muted);
    font-size: 12px;
  }

  .actions {
    display: flex;
    gap: 6px;
    justify-content: flex-end;
    white-space: nowrap;
  }

  .small {
    padding: 6px 10px;
    font-size: 12px;
  }

  .danger {
    color: var(--danger);
    border-color: #fecaca;
  }

  .inline-input {
    width: 90px;
    padding: 6px 8px;
  }

  @media (max-width: 800px) {
    .add-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
