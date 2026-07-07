<script>
  import { api } from './api.js'

  let {
    palletNum,
    printers = [],
    defaultPrinter = null,
    savedPrinter = '',
    savedFormat = 'a4',
    savedOrientation = 'portrait',
    ondone = () => {},
    oncancel = () => {},
  } = $props()

  let reprintPrinter = $state('')
  let reprintFormat = $state('a4')
  let reprintOrientation = $state('portrait')
  let printing = $state(false)
  let error = $state('')

  $effect(() => {
    reprintPrinter = savedPrinter
    reprintFormat = savedFormat
    reprintOrientation = savedOrientation
  })

  async function reprint() {
    printing = true
    error = ''
    try {
      await api.print({
        pallet_num: palletNum,
        printer: reprintPrinter || null,
        format: reprintFormat,
        orientation: reprintOrientation,
      })
      ondone()
    } catch (e) {
      error = e.message
    } finally {
      printing = false
    }
  }
</script>

<div class="overlay" role="presentation" onclick={oncancel}>
  <div class="panel" role="dialog" aria-labelledby="reprint-title" onclick={(e) => e.stopPropagation()}>
    <div class="panel-header">
      <h3 id="reprint-title">Reprint pallet {palletNum}</h3>
      <button class="panel-close" onclick={oncancel} aria-label="Close">×</button>
    </div>

    <p class="panel-hint">
      Choose a printer for this job only. Saved print settings are unchanged.
    </p>

    {#if error}
      <div class="banner error">{error}</div>
    {/if}

    <label for="reprint-format">Paper / label size</label>
    <select id="reprint-format" bind:value={reprintFormat} disabled={printing}>
      <option value="a4">A4 sheet (multi-row table)</option>
      <option value="label_10x15">10×15 cm label (one per row)</option>
    </select>

    <label for="reprint-orientation" class="field-spaced">Orientation</label>
    {#if reprintFormat === 'label_10x15'}
      <p class="panel-hint panel-hint-inline">Labels use a fixed 10×15 cm portrait layout.</p>
    {:else}
      <select id="reprint-orientation" bind:value={reprintOrientation} disabled={printing}>
        <option value="portrait">Portrait</option>
        <option value="landscape">Landscape</option>
      </select>
    {/if}

    <label for="reprint-printer" class="field-spaced">Printer</label>
    <select id="reprint-printer" bind:value={reprintPrinter} disabled={printing}>
      <option value="">
        System default{defaultPrinter ? ` (${defaultPrinter})` : ''}
      </option>
      {#each printers as p}
        <option value={p}>{p}</option>
      {/each}
    </select>

    <div class="panel-actions">
      <button class="btn-ghost small" onclick={oncancel} disabled={printing}>Cancel</button>
      <button class="btn-primary small" onclick={reprint} disabled={printing}>
        {printing ? 'Printing...' : 'Reprint'}
      </button>
    </div>
  </div>
</div>

<style>
  .overlay {
    position: fixed;
    inset: 0;
    z-index: 100;
    background: rgba(0, 0, 0, 0.35);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
  }

  .panel {
    width: 100%;
    max-width: 380px;
    background: var(--surface, #fff);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.18);
    padding: 18px;
  }

  .panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
  }

  .panel-header h3 {
    font-size: 15px;
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

  .panel-hint {
    margin: 0 0 14px;
    font-size: 12px;
    color: var(--text-muted);
    line-height: 1.4;
  }

  .panel-hint-inline {
    margin: 0 0 14px;
  }

  label {
    display: block;
    font-size: 12px;
    font-weight: 600;
    color: var(--text-muted);
    margin-bottom: 6px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  label.field-spaced {
    margin-top: 14px;
  }

  select {
    width: 100%;
    padding: 8px 10px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    font-size: 13px;
    background: #fff;
  }

  .banner.error {
    margin-bottom: 12px;
    padding: 10px 12px;
    border-radius: var(--radius);
    background: var(--danger-bg);
    color: var(--danger);
    border: 1px solid #fecaca;
    font-size: 13px;
  }

  .panel-actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin-top: 18px;
  }

  .btn-ghost.small,
  .btn-primary.small {
    padding: 6px 12px;
    font-size: 12px;
  }
</style>
