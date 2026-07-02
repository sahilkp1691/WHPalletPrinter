<script>
  import { api } from '../lib/api.js'

  let artNum = $state('')
  let cartons = $state(1)
  let queue = $state([])
  let previewRows = $state([])
  let canPrint = $state(false)
  let loading = $state(false)
  let printing = $state(false)
  let error = $state('')
  let artInput
  let cartonsInput

  async function refreshPreview() {
    if (queue.length === 0) {
      previewRows = []
      canPrint = false
      return
    }
    loading = true
    error = ''
    try {
      const result = await api.previewPrint(queue)
      previewRows = result.rows
      canPrint = result.can_print
    } catch (e) {
      error = e.message
      previewRows = []
      canPrint = false
    } finally {
      loading = false
    }
  }

  function addRow() {
    const trimmed = artNum.trim()
    const count = Number(cartons)
    if (!trimmed) {
      error = 'Enter an Art Num'
      return
    }
    if (!Number.isInteger(count) || count <= 0) {
      error = 'Cartons must be a positive whole number'
      return
    }
    queue = [...queue, { art_num: trimmed, cartons: count }]
    artNum = ''
    cartons = 1
    error = ''
    refreshPreview()
    artInput?.focus()
  }

  function removeRow(index) {
    queue = queue.filter((_, i) => i !== index)
    refreshPreview()
  }

  function clearAll() {
    queue = []
    previewRows = []
    canPrint = false
    error = ''
  }

  async function printNow() {
    if (!canPrint || queue.length === 0) return
    printing = true
    error = ''
    try {
      await api.print(queue)
      clearAll()
    } catch (e) {
      error = e.message
    } finally {
      printing = false
    }
  }

  async function printSingle() {
    const trimmed = artNum.trim()
    const count = Number(cartons)
    if (!trimmed) {
      error = 'Enter an Art Num'
      return
    }
    if (!Number.isInteger(count) || count <= 0) {
      error = 'Cartons must be a positive whole number'
      return
    }
    printing = true
    error = ''
    try {
      const lines = [{ art_num: trimmed, cartons: count }]
      const preview = await api.previewPrint(lines)
      if (!preview.can_print) {
        error = preview.rows[0]?.error || 'Cannot print this row'
        return
      }
      await api.print(lines)
      artNum = ''
      cartons = 1
    } catch (e) {
      error = e.message
    } finally {
      printing = false
    }
  }

  function onArtKeydown(e) {
    if (e.key === 'Enter') {
      e.preventDefault()
      cartonsInput?.focus()
      cartonsInput?.select()
    }
  }

  function onCartonsKeydown(e) {
    if (e.key === 'Enter') {
      e.preventDefault()
      addRow()
    }
  }
</script>

<div class="page">
  <header class="page-header">
    <div>
      <h1>Print Labels</h1>
      <p class="subtitle">Enter Art Num and cartons. Qty is calculated from Qty/Carton data.</p>
    </div>
  </header>

  {#if error}
    <div class="banner error">{error}</div>
  {/if}

  <section class="card entry-card">
    <div class="entry-grid">
      <div class="field">
        <label for="art-num">Art Num</label>
        <input
          id="art-num"
          type="text"
          bind:value={artNum}
          bind:this={artInput}
          onkeydown={onArtKeydown}
          placeholder="e.g. PK1400"
          autocomplete="off"
        />
      </div>
      <div class="field narrow">
        <label for="cartons">Cartons</label>
        <input
          id="cartons"
          type="number"
          min="1"
          step="1"
          bind:value={cartons}
          bind:this={cartonsInput}
          onkeydown={onCartonsKeydown}
        />
      </div>
      <div class="entry-actions">
        <button class="btn-ghost" onclick={addRow} disabled={printing}>Add Row</button>
        <button class="btn-primary" onclick={printSingle} disabled={printing}>
          {printing ? 'Printing...' : 'Print Single'}
        </button>
      </div>
    </div>
  </section>

  <section class="card preview-card">
    <div class="preview-header">
      <h2>Preview</h2>
      <div class="preview-actions">
        <button class="btn-ghost" onclick={clearAll} disabled={queue.length === 0 || printing}>Clear</button>
        <button class="btn-primary" onclick={printNow} disabled={!canPrint || printing || loading}>
          {printing ? 'Printing...' : `Print ${queue.length || ''} Row${queue.length === 1 ? '' : 's'}`}
        </button>
      </div>
    </div>

    {#if loading}
      <p class="muted">Updating preview...</p>
    {:else if previewRows.length === 0}
      <p class="muted">Add rows to build a multi-row print job, or use Print Single above.</p>
    {:else}
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Art Num</th>
              <th>Cartons</th>
              <th>Qty/Carton</th>
              <th>Qty</th>
              <th>Barcode</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {#each previewRows as row, i}
              <tr class:error-row={row.error}>
                <td>{row.art_num}</td>
                <td>{row.cartons}</td>
                <td>{row.qty_per_carton ?? '—'}</td>
                <td>
                  {#if row.error}
                    <span class="tag tag-danger">{row.error}</span>
                  {:else}
                    <strong>{row.qty}</strong>
                  {/if}
                </td>
                <td class="barcode-cell">
                  {#if row.barcode_png_base64}
                    <img
                      src={`data:image/png;base64,${row.barcode_png_base64}`}
                      alt={`Barcode for ${row.art_num}`}
                    />
                  {:else}
                    —
                  {/if}
                </td>
                <td>
                  <button class="btn-ghost small" onclick={() => removeRow(i)}>Remove</button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </section>
</div>

<style>
  .page {
    padding: 28px 32px 40px;
    max-width: 1100px;
  }

  .page-header h1 {
    font-size: 22px;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 4px;
  }

  .subtitle {
    color: var(--text-muted);
    font-size: 13px;
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

  .entry-card {
    margin-top: 20px;
  }

  .entry-grid {
    display: grid;
    grid-template-columns: 1fr 120px auto;
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

  .entry-actions {
    display: flex;
    gap: 8px;
    padding-bottom: 1px;
  }

  .preview-card {
    margin-top: 20px;
  }

  .preview-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
    gap: 12px;
  }

  .preview-header h2 {
    font-size: 16px;
    font-weight: 600;
  }

  .preview-actions {
    display: flex;
    gap: 8px;
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

  tr.error-row td {
    background: #fffafa;
  }

  .barcode-cell img {
    height: 42px;
    max-width: 180px;
    object-fit: contain;
  }

  .small {
    padding: 6px 10px;
    font-size: 12px;
  }

  @media (max-width: 800px) {
    .entry-grid {
      grid-template-columns: 1fr;
    }
    .entry-actions {
      flex-wrap: wrap;
    }
  }
</style>
