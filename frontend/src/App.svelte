<script>
  import PrintView from './views/PrintView.svelte'
  import DataView from './views/DataView.svelte'

  let activeTab = $state('print')
</script>

<div class="app">
  <nav class="sidebar">
    <div class="logo-wrap">
      <div class="logo-mark" aria-hidden="true">BGA</div>
      <span class="logo-label">Pallet Printer</span>
    </div>

    <div class="nav-group">
      <button
        class="nav-item"
        class:active={activeTab === 'print'}
        onclick={() => (activeTab = 'print')}
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="6 9 6 2 18 2 18 9"/>
          <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/>
          <rect x="6" y="14" width="12" height="8"/>
        </svg>
        Print
      </button>
      <button
        class="nav-item"
        class:active={activeTab === 'data'}
        onclick={() => (activeTab = 'data')}
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <ellipse cx="12" cy="5" rx="9" ry="3"/>
          <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
          <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
        </svg>
        Article Data
      </button>
    </div>
  </nav>

  <main class="content">
    {#if activeTab === 'print'}
      <PrintView />
    {:else}
      <DataView />
    {/if}
  </main>
</div>

<style>
  .app {
    display: grid;
    grid-template-columns: 210px 1fr;
    min-height: 100vh;
  }

  .sidebar {
    background: var(--bga-green-700);
    display: flex;
    flex-direction: column;
    box-shadow: 2px 0 8px rgba(0, 0, 0, 0.08);
  }

  .logo-wrap {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 20px 16px 22px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.12);
  }

  .logo-mark {
    width: 36px;
    height: 36px;
    border-radius: 6px;
    background: rgba(255, 255, 255, 0.15);
    color: #fff;
    font-size: 11px;
    font-weight: 800;
    display: flex;
    align-items: center;
    justify-content: center;
    letter-spacing: -0.5px;
  }

  .logo-label {
    font-size: 15px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: -0.3px;
    line-height: 1.2;
  }

  .nav-group {
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 14px 10px;
  }

  .nav-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    border-radius: var(--radius);
    background: transparent;
    color: rgba(255, 255, 255, 0.65);
    font-size: 14px;
    font-weight: 500;
    text-align: left;
    transition: background 0.12s, color 0.12s;
    width: 100%;
  }

  .nav-item:hover {
    background: rgba(255, 255, 255, 0.1);
    color: #ffffff;
  }

  .nav-item.active {
    background: rgba(255, 255, 255, 0.15);
    color: #ffffff;
  }

  .content {
    overflow-y: auto;
    background: var(--bg);
  }
</style>
