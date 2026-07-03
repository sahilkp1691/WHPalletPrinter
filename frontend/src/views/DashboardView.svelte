<script>
  import { api } from '../lib/api.js'

  let { visible = false } = $props()

  let loading = $state(true)
  let error = $state('')
  let dashboard = $state(null)
  let cartonFilter = $state('all')

  $effect(() => {
    if (visible) loadDashboard()
  })

  async function loadDashboard() {
    loading = true
    error = ''
    try {
      dashboard = await api.getPacklistDashboard()
    } catch (e) {
      error = e.message
      dashboard = null
    } finally {
      loading = false
    }
  }

  const filteredCartons = $derived(() => {
    if (!dashboard?.cartons) return []
    if (cartonFilter === 'assigned') {
      return dashboard.cartons.filter((c) => c.status === 'assigned')
    }
    if (cartonFilter === 'remaining') {
      return dashboard.cartons.filter((c) => c.status === 'remaining')
    }
    return dashboard.cartons
  })
</script>

<div class="page">
  <header class="page-header">
    <div>
      <h1>Packlist Dashboard</h1>
      <p class="subtitle">Track carton assignment progress for the active session.</p>
    </div>
    <button class="btn-ghost" onclick={loadDashboard} disabled={loading}>Refresh</button>
  </header>

  {#if error}
    <div class="banner error">{error}</div>
  {/if}

  {#if loading}
    <p class="muted">Loading dashboard...</p>
  {:else if !dashboard?.loaded}
    <section class="card empty-card">
      <p class="muted">No active packlist session. Import a packlist on the Pallet Print tab to begin.</p>
    </section>
  {:else}
    <section class="summary-grid">
      <div class="stat-card">
        <span class="stat-label">Total cartons</span>
        <strong class="stat-value">{dashboard.summary.total_cartons}</strong>
      </div>
      <div class="stat-card assigned">
        <span class="stat-label">On pallets</span>
        <strong class="stat-value">{dashboard.summary.assigned_cartons}</strong>
      </div>
      <div class="stat-card remaining">
        <span class="stat-label">Remaining</span>
        <strong class="stat-value">{dashboard.summary.remaining_cartons}</strong>
      </div>
      <div class="stat-card">
        <span class="stat-label">Pallets</span>
        <strong class="stat-value">{dashboard.summary.pallet_count}</strong>
        <span class="stat-sub">{dashboard.summary.printed_pallet_count} printed</span>
      </div>
    </section>

    <section class="card">
      <div class="card-header">
        <h2>Session</h2>
      </div>
      <dl class="meta-grid">
        <div><dt>File</dt><dd>{dashboard.session.filename}</dd></div>
        <div><dt>Imported</dt><dd>{new Date(dashboard.session.imported_at).toLocaleString()}</dd></div>
        <div><dt>Packlist lines</dt><dd>{dashboard.summary.line_count}</dd></div>
      </dl>
    </section>

    <section class="card">
      <div class="card-header">
        <h2>Pallets</h2>
      </div>
      {#if dashboard.pallets.length === 0}
        <p class="muted">No pallets started yet.</p>
      {:else}
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Pallet</th>
                <th>Cartons</th>
                <th>Status</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {#each dashboard.pallets as pallet}
                <tr>
                  <td><strong>{pallet.pallet_num}</strong></td>
                  <td>{pallet.carton_count}</td>
                  <td>
                    {#if pallet.printed}
                      <span class="tag tag-success">Printed</span>
                    {:else}
                      <span class="tag tag-muted">In progress</span>
                    {/if}
                  </td>
                  <td>{new Date(pallet.created_at).toLocaleString()}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </section>

    <section class="card">
      <div class="card-header">
        <h2>Cartons</h2>
        <div class="filter-tabs">
          <button class:active={cartonFilter === 'all'} onclick={() => (cartonFilter = 'all')}>All</button>
          <button class:active={cartonFilter === 'remaining'} onclick={() => (cartonFilter = 'remaining')}>Remaining</button>
          <button class:active={cartonFilter === 'assigned'} onclick={() => (cartonFilter = 'assigned')}>Assigned</button>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Carton</th>
              <th>Spec</th>
              <th>Products</th>
              <th>Status</th>
              <th>Pallet</th>
            </tr>
          </thead>
          <tbody>
            {#each filteredCartons() as carton}
              <tr class:assigned-row={carton.status === 'assigned'}>
                <td><strong>{carton.carton_id}</strong></td>
                <td>{carton.carton_spec}</td>
                <td>
                  {#each carton.products as product}
                    <div>{product.stock_code} ({product.qty_per_carton}/ctn)</div>
                  {/each}
                </td>
                <td>
                  {#if carton.status === 'assigned'}
                    {#if carton.printed}
                      <span class="tag tag-success">Printed</span>
                    {:else}
                      <span class="tag tag-warn">On pallet</span>
                    {/if}
                  {:else}
                    <span class="tag tag-muted">Remaining</span>
                  {/if}
                </td>
                <td>{carton.pallet_num ?? '—'}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>

    <section class="card">
      <div class="card-header">
        <h2>Packlist lines</h2>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Row</th>
              <th>Carton spec</th>
              <th>Stock code</th>
              <th>Total qty</th>
              <th>Qty/ctn</th>
              <th># Cartons</th>
            </tr>
          </thead>
          <tbody>
            {#each dashboard.lines as line}
              <tr>
                <td>{line.row_num}</td>
                <td>{line.carton_spec}</td>
                <td>{line.stock_code}</td>
                <td>{line.total_qty}</td>
                <td>{line.qty_per_carton}</td>
                <td>{line.num_cartons}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>
  {/if}
</div>

<style>
  .page {
    padding: 28px 32px 40px;
    max-width: 1200px;
  }

  .page-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 20px;
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

  .banner.error {
    margin-bottom: 16px;
    padding: 12px 14px;
    border-radius: var(--radius);
    background: var(--danger-bg);
    color: var(--danger);
    border: 1px solid #fecaca;
    font-size: 13px;
  }

  .summary-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
    margin-bottom: 20px;
  }

  .stat-card {
    background: var(--surface, #fff);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px;
  }

  .stat-card.assigned {
    border-color: #a1d4a2;
    background: #f3faf3;
  }

  .stat-card.remaining {
    border-color: #ffed86;
    background: #fffce7;
  }

  .stat-label {
    display: block;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--text-muted);
    margin-bottom: 6px;
  }

  .stat-value {
    font-size: 28px;
    line-height: 1;
    color: var(--text);
  }

  .stat-sub {
    display: block;
    margin-top: 6px;
    font-size: 12px;
    color: var(--text-muted);
  }

  .card {
    background: var(--surface, #fff);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 18px;
    margin-bottom: 20px;
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 14px;
  }

  .card-header h2 {
    font-size: 16px;
    font-weight: 600;
  }

  .meta-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    font-size: 13px;
  }

  .meta-grid dt {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--text-muted);
    margin-bottom: 4px;
  }

  .filter-tabs {
    display: flex;
    gap: 6px;
  }

  .filter-tabs button {
    padding: 6px 10px;
    font-size: 12px;
    border-radius: 999px;
    border: 1px solid var(--border);
    background: #fff;
    color: var(--text-muted);
  }

  .filter-tabs button.active {
    background: var(--bga-green-700, #326633);
    border-color: var(--bga-green-700, #326633);
    color: #fff;
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
    vertical-align: top;
  }

  th {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--text-muted);
    background: var(--surface2);
  }

  tr.assigned-row td {
    background: #f8fdf8;
  }

  .tag {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 600;
  }

  .tag-success {
    background: #e4f4e4;
    color: #326633;
  }

  .tag-warn {
    background: #fff8c1;
    color: #89470a;
  }

  .tag-muted {
    background: #f3f4f6;
    color: #6b7280;
  }

  .muted {
    color: var(--text-muted);
    font-size: 13px;
  }

  .empty-card {
    padding: 24px;
  }

  @media (max-width: 900px) {
    .summary-grid {
      grid-template-columns: repeat(2, 1fr);
    }
    .meta-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
