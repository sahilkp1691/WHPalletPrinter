<script>
  import { onMount, tick } from 'svelte'
  import { api, downloadBlob } from '../lib/api.js'

  let packlistLoaded = $state(false)
  let packlistFilename = $state('')
  let packlistLineCount = $state(0)
  let packlistCartonCount = $state(0)
  let assignedCartons = $state(0)
  let remainingCartons = $state(0)
  let packlistWarnings = $state([])
  let importErrors = $state([])
  let importing = $state(false)

  let palletNum = $state('')
  let cartonScan = $state('')
  let scanDetails = $state([])
  let previewRows = $state([])
  let canPrint = $state(false)
  let loading = $state(false)
  let printing = $state(false)
  let error = $state('')

  let palletInput
  let cartonInput
  let importInput

  let printers = $state([])
  let defaultPrinter = $state(null)
  let selectedPrinter = $state('')
  let printFormat = $state('a4')
  let printOrientation = $state('portrait')
  let showConfig = $state(false)
  let savingPrinter = $state(false)

  const palletLocked = $derived(palletNum.trim().length > 0)

  onMount(async () => {
    await Promise.all([loadPrinters(), loadPacklistStatus()])
    focusAfterPacklist()
  })

  async function loadPacklistStatus() {
    try {
      const status = await api.getPacklistStatus()
      packlistLoaded = status.loaded
      packlistFilename = status.filename || ''
      packlistLineCount = status.line_count || 0
      packlistCartonCount = status.carton_count || 0
      assignedCartons = status.assigned_cartons || 0
      remainingCartons = status.remaining_cartons || 0
      packlistWarnings = status.warnings || []
    } catch {
      packlistLoaded = false
    }
  }

  async function focusAfterPacklist() {
    await tick()
    if (packlistLoaded) {
      palletInput?.focus()
    }
  }

  async function loadPrinters() {
    try {
      const info = await api.listPrinters()
      printers = info.printers
      defaultPrinter = info.default
      selectedPrinter = info.selected || ''
      printFormat = info.format || 'a4'
      printOrientation = info.orientation || 'portrait'
    } catch {
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

  async function downloadTemplate() {
    try {
      const blob = await api.downloadPacklistTemplate()
      downloadBlob(blob, 'packlist_template.xlsx')
    } catch (e) {
      error = e.message
    }
  }

  async function handleImportFile(e) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return

    if (palletNum.trim()) {
      const ok = confirm(
        'Importing a new packlist will start a new session. In-progress pallets stay in the previous session. Continue?'
      )
      if (!ok) return
    }

    importing = true
    error = ''
    importErrors = []
    try {
      const result = await api.importPacklist(file)
      importErrors = result.errors || []
      packlistWarnings = result.warnings || []

      if (!result.loaded) {
        packlistLoaded = false
        error = importErrors.join('; ') || 'Packlist import failed'
        return
      }

      packlistLoaded = true
      packlistFilename = result.filename
      packlistLineCount = result.line_count
      packlistCartonCount = result.carton_count
      await loadPacklistStatus()
      clearPalletLocal()
      await focusAfterPacklist()
    } catch (e) {
      error = e.message
      packlistLoaded = false
    } finally {
      importing = false
    }
  }

  async function replacePacklist() {
    importInput?.click()
  }

  async function loadPalletState() {
    const num = palletNum.trim()
    if (!packlistLoaded || !num) {
      scanDetails = []
      previewRows = []
      canPrint = false
      return
    }

    loading = true
    error = ''
    try {
      const result = await api.getPallet(num)
      scanDetails = result.carton_scans
      previewRows = result.rows
      canPrint = result.can_print
      await loadPacklistStatus()
    } catch (e) {
      if (e.message?.includes('not found') || e.message?.includes('404')) {
        scanDetails = []
        previewRows = []
        canPrint = false
      } else {
        error = e.message
        scanDetails = []
        previewRows = []
        canPrint = false
      }
    } finally {
      loading = false
    }
  }

  function onPalletKeydown(e) {
    if (e.key === 'Enter') {
      e.preventDefault()
      if (palletNum.trim()) {
        loadPalletState()
        cartonInput?.focus()
      }
    }
  }

  async function addCartonScan() {
    const scan = cartonScan.trim()
    if (!scan) {
      error = 'Scan or enter a carton number'
      return
    }
    if (!palletNum.trim()) {
      error = 'Scan a pallet number first'
      return
    }

    loading = true
    error = ''
    try {
      const result = await api.addCartonToPallet(palletNum.trim(), scan)
      scanDetails = result.carton_scans
      previewRows = result.rows
      canPrint = result.can_print
      cartonScan = ''
      await loadPacklistStatus()
      cartonInput?.focus()
    } catch (e) {
      error = e.message
    } finally {
      loading = false
    }
  }

  function onCartonKeydown(e) {
    if (e.key === 'Enter') {
      e.preventDefault()
      addCartonScan()
    }
  }

  async function removeCarton(scan) {
    if (!palletNum.trim()) return
    loading = true
    error = ''
    try {
      const result = await api.removeCartonFromPallet(palletNum.trim(), scan)
      scanDetails = result.carton_scans
      previewRows = result.rows
      canPrint = result.can_print
      await loadPacklistStatus()
    } catch (e) {
      error = e.message
    } finally {
      loading = false
    }
  }

  function clearPalletLocal() {
    palletNum = ''
    cartonScan = ''
    scanDetails = []
    previewRows = []
    canPrint = false
    error = ''
    tick().then(() => palletInput?.focus())
  }

  async function clearPallet() {
    if (!palletNum.trim()) {
      clearPalletLocal()
      return
    }
    loading = true
    error = ''
    try {
      await api.clearPallet(palletNum.trim())
      clearPalletLocal()
      await loadPacklistStatus()
    } catch (e) {
      error = e.message
    } finally {
      loading = false
    }
  }

  async function printNow() {
    if (!canPrint || !palletNum.trim()) return
    printing = true
    error = ''
    try {
      await api.print({ pallet_num: palletNum.trim() })
      clearPalletLocal()
      await loadPacklistStatus()
    } catch (e) {
      error = e.message
    } finally {
      printing = false
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
</script>

<div class="page">
  <header class="page-header">
    <div>
      <h1>Pallet Print</h1>
      <p class="subtitle">
        Import a supplier packlist, scan a pallet, then scan each carton to build and print labels.
      </p>
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

  <input
    type="file"
    accept=".xlsx,.xlsm"
    bind:this={importInput}
    onchange={handleImportFile}
    hidden
  />

  {#if !packlistLoaded}
    <section class="card import-card">
      <h2>Import packlist</h2>
      <p class="muted">
        Upload the supplier packlist Excel file before scanning pallets. Columns A–E: Carton Number,
        Stock code, Total Quantity, Qty/Carton, Number of Cartons.
      </p>
      <div class="import-actions">
        <button class="btn-primary" onclick={() => importInput?.click()} disabled={importing}>
          {importing ? 'Importing...' : 'Choose packlist file'}
        </button>
        <button class="btn-ghost" onclick={downloadTemplate}>Download template</button>
      </div>
      {#if importErrors.length > 0}
        <ul class="error-list">
          {#each importErrors as msg}
            <li>{msg}</li>
          {/each}
        </ul>
      {/if}
    </section>
  {:else}
    <section class="card packlist-banner">
      <div>
        <strong>Packlist loaded</strong>
        <span class="muted">
          {packlistFilename ? `${packlistFilename} — ` : ''}{packlistLineCount} lines, {packlistCartonCount} cartons
          · {assignedCartons} on pallets, {remainingCartons} remaining
        </span>
      </div>
      <button class="btn-ghost small" onclick={replacePacklist}>Replace packlist</button>
    </section>

    {#if packlistWarnings.length > 0}
      <div class="banner warn">
        {packlistWarnings.length} packlist warning{packlistWarnings.length === 1 ? '' : 's'} (qty mismatches). Import still succeeded.
      </div>
    {/if}

    <section class="card entry-card">
      <div class="entry-grid">
        <div class="field">
          <label for="pallet-num">Pallet number</label>
          <input
            id="pallet-num"
            type="text"
            bind:value={palletNum}
            bind:this={palletInput}
            onkeydown={onPalletKeydown}
            placeholder="Scan pallet barcode"
            autocomplete="off"
            disabled={printing}
          />
        </div>
        <div class="field">
          <label for="carton-scan">Carton number</label>
          <input
            id="carton-scan"
            type="text"
            bind:value={cartonScan}
            bind:this={cartonInput}
            onkeydown={onCartonKeydown}
            placeholder={palletLocked ? 'Scan carton barcode' : 'Enter pallet first'}
            autocomplete="off"
            disabled={!palletLocked || printing}
          />
        </div>
        <div class="entry-actions">
          <button class="btn-ghost" onclick={addCartonScan} disabled={!palletLocked || printing}>Add</button>
          <button class="btn-ghost" onclick={clearPallet} disabled={printing}>Clear pallet</button>
        </div>
      </div>
    </section>

    {#if scanDetails.length > 0}
      <section class="card">
        <h2 class="section-title">Scanned cartons</h2>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Scan</th>
                <th>Carton</th>
                <th>Stock code</th>
                <th>Qty/Carton</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {#each scanDetails as scan, i}
                <tr class:error-row={scan.error}>
                  <td>{scan.scan}</td>
                  <td>{scan.carton_id ?? '—'}</td>
                  <td>
                    {#if scan.error}
                      —
                    {:else if scan.products?.length > 1}
                      {#each scan.products as product}
                        <div>{product.stock_code}</div>
                      {/each}
                    {:else}
                      {scan.stock_code ?? scan.products?.[0]?.stock_code ?? '—'}
                    {/if}
                  </td>
                  <td>
                    {#if scan.error}
                      <span class="tag tag-danger">{scan.error}</span>
                    {:else if scan.products?.length > 1}
                      {#each scan.products as product}
                        <div>{product.qty_per_carton}</div>
                      {/each}
                    {:else}
                      {scan.qty_per_carton ?? scan.products?.[0]?.qty_per_carton ?? '—'}
                    {/if}
                  </td>
                  <td>
                    <button class="btn-ghost small" onclick={() => removeCarton(scan.scan)}>Remove</button>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </section>
    {/if}

    <section class="card preview-card">
      <div class="preview-header">
        <h2>Print preview</h2>
        <button
          class="btn-primary"
          onclick={printNow}
          disabled={!canPrint || printing || loading}
        >
          {printing ? 'Printing...' : 'Print pallet'}
        </button>
      </div>

      {#if loading}
        <p class="muted">Updating preview...</p>
      {:else if previewRows.length === 0}
        <p class="muted">Scan cartons to see aggregated products for this pallet.</p>
      {:else}
        <p class="pallet-label">Pallet: <strong>{palletNum}</strong></p>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Stock code</th>
                <th>Cartons</th>
                <th>Qty/Carton</th>
                <th>Qty</th>
                <th>Barcode</th>
              </tr>
            </thead>
            <tbody>
              {#each previewRows as row}
                <tr>
                  <td>{row.art_num}</td>
                  <td>{row.cartons}</td>
                  <td>{row.qty_per_carton}</td>
                  <td><strong>{row.qty}</strong></td>
                  <td class="barcode-cell">
                    {#if row.barcode_png_base64}
                      <img
                        src={`data:image/png;base64,${row.barcode_png_base64}`}
                        alt={`Barcode for ${row.art_num}`}
                      />
                    {/if}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </section>
  {/if}
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

  .subtitle {
    color: var(--text-muted);
    font-size: 13px;
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

  .banner.warn {
    background: #fffce7;
    color: #89470a;
    border: 1px solid #ffed86;
  }

  .import-card h2,
  .section-title {
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 8px;
  }

  .import-actions {
    display: flex;
    gap: 10px;
    margin-top: 16px;
    flex-wrap: wrap;
  }

  .error-list {
    margin-top: 14px;
    padding-left: 18px;
    font-size: 13px;
    color: var(--danger);
  }

  .packlist-banner {
    margin-top: 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .packlist-banner strong {
    display: block;
    margin-bottom: 2px;
  }

  .entry-card {
    margin-top: 20px;
  }

  .entry-grid {
    display: grid;
    grid-template-columns: 1fr 1fr auto;
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

  .pallet-label {
    font-size: 13px;
    margin-bottom: 12px;
    color: var(--text-muted);
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

  @media (max-width: 800px) {
    .entry-grid {
      grid-template-columns: 1fr;
    }
    .entry-actions {
      flex-wrap: wrap;
    }
  }
</style>
