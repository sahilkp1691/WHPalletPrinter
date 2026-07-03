<script>
  import { onMount } from 'svelte'
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

  let printers = $state([])
  let defaultPrinter = $state(null)
  let selectedPrinter = $state('')
  let printFormat = $state('a4')
  let printOrientation = $state('portrait')
  let showConfig = $state(false)
  let savingPrinter = $state(false)

  onMount(loadPrinters)

  async function loadPrinters() {
    try {
      const info = await api.listPrinters()
      printers = info.printers
      defaultPrinter = info.default
      selectedPrinter = info.selected || ''
      printFormat = info.format || 'a4'
      printOrientation = info.orientation || 'portrait'
    } catch (e) {
      // Non-fatal: printing still falls back to the system default.
    }
  }

  async function savePrinter() {
    savingPrinter = true
    error = ''
    try {
      const info = await api.setPrinter({
        printer: selectedPrinter || null,
        format: printFormat,
        orientation: printOrientation,
      })
      printers = info.printers
      defaultPrinter = info.default
      selectedPrinter = info.selected || ''
      printFormat = info.format || 'a4'
      printOrientation = info.orientation || 'portrait'
      showConfig = false
    } catch (e) {
      error = e.message
    } finally {
      savingPrinter = false
    }
  }

  const activePrinterLabel = $derived(
    selectedPrinter || (defaultPrinter ? `${defaultPrinter} (default)` : 'System default')
  )

  const layoutLabel = $derived(
    printFormat === 'label_10x15'
      ? '10×15 cm label'
      : `A4, ${printOrientation === 'landscape' ? 'landscape' : 'portrait'}`
  )

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
    <div class="printer-config">
      <span class="printer-current" title={`${activePrinterLabel} — ${layoutLabel}`}>
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="6 9 6 2 18 2 18 9"/>
          <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/>
          <rect x="6" y="14" width="12" height="8"/>
        </svg>
        {activePrinterLabel}
      </span>
      <span class="layout-badge" title="Print layout">{layoutLabel}</span>
      <button class="btn-ghost small" onclick={() => (showConfig = !showConfig)}>
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="3"/>
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
        </svg>
        Printer
      </button>

      {#if showConfig}
        <div class="printer-panel">
          <div class="panel-header">
            <h3>Print settings</h3>
            <button class="panel-close" onclick={() => (showConfig = false)} aria-label="Close">×</button>
          </div>

          <label for="print-format">Paper / label size</label>
          <select id="print-format" bind:value={printFormat}>
            <option value="a4">A4 sheet (multi-row table)</option>
            <option value="label_10x15">10×15 cm label (one per row)</option>
          </select>

          <label for="print-orientation" class="field-spaced">Orientation</label>
          {#if printFormat === 'label_10x15'}
            <p class="panel-hint panel-hint-inline">
              Labels use a fixed 10×15 cm portrait layout (one label per row).
            </p>
          {:else}
            <select id="print-orientation" bind:value={printOrientation}>
              <option value="portrait">Portrait</option>
              <option value="landscape">Landscape</option>
            </select>
            <p class="panel-hint">
              Portrait: standard A4. Landscape: A4 rotated 90°.
            </p>
          {/if}

          <label for="printer-select" class="field-spaced">Printer</label>
          <select id="printer-select" bind:value={selectedPrinter}>
            <option value="">
              System default{defaultPrinter ? ` (${defaultPrinter})` : ''}
            </option>
            {#each printers as p}
              <option value={p}>{p}</option>
            {/each}
          </select>
          <div class="panel-actions">
            <button class="btn-ghost small" onclick={loadPrinters} disabled={savingPrinter}>Refresh</button>
            <button class="btn-primary small" onclick={savePrinter} disabled={savingPrinter}>
              {savingPrinter ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>
      {/if}
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

  .page-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
  }

  .page-header h1 {
    font-size: 22px;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 4px;
  }

  .printer-config {
    position: relative;
    display: flex;
    align-items: center;
    gap: 10px;
    flex-shrink: 0;
  }

  .printer-current {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    max-width: 220px;
    font-size: 12px;
    color: var(--text-muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .printer-current svg {
    flex-shrink: 0;
  }

  .layout-badge {
    font-size: 11px;
    color: var(--text-muted);
    background: var(--surface2, #f3faf3);
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 3px 8px;
    white-space: nowrap;
  }

  .btn-ghost.small,
  .btn-primary.small {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 10px;
    font-size: 12px;
  }

  .printer-panel {
    position: absolute;
    top: calc(100% + 8px);
    right: 0;
    z-index: 20;
    width: 340px;
    background: var(--surface, #fff);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
    padding: 16px;
  }

  .panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
  }

  .panel-header h3 {
    font-size: 14px;
    font-weight: 600;
  }

  .panel-close {
    background: transparent;
    border: none;
    font-size: 20px;
    line-height: 1;
    color: var(--text-muted);
    cursor: pointer;
    padding: 0 4px;
  }

  .printer-panel label {
    display: block;
    font-size: 12px;
    font-weight: 600;
    color: var(--text-muted);
    margin-bottom: 6px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .printer-panel select {
    width: 100%;
    padding: 8px 10px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    font-size: 13px;
    background: #fff;
  }

  .printer-panel label.field-spaced {
    margin-top: 14px;
  }

  .panel-hint {
    margin: 8px 0 0;
    font-size: 11px;
    color: var(--text-muted);
    line-height: 1.4;
  }

  .panel-hint-inline {
    margin-top: 0;
  }

  .panel-actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin-top: 14px;
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
