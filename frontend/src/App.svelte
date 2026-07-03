<script>
  import PrintView from './views/PrintView.svelte'
  import DashboardView from './views/DashboardView.svelte'

  let activeTab = $state('print')
</script>

<div class="app">
  <nav class="sidebar">
    <div class="logo-wrap">
      <img src="/bga-logo.png" alt="BGA" class="logo-img" />
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
        Pallet Print
      </button>
      <button
        class="nav-item"
        class:active={activeTab === 'dashboard'}
        onclick={() => (activeTab = 'dashboard')}
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="3" width="7" height="7"/>
          <rect x="14" y="3" width="7" height="7"/>
          <rect x="14" y="14" width="7" height="7"/>
          <rect x="3" y="14" width="7" height="7"/>
        </svg>
        Dashboard
      </button>
    </div>
  </nav>

  <main class="content">
    <div class="tab-panel" class:hidden={activeTab !== 'print'} aria-hidden={activeTab !== 'print'}>
      <PrintView />
    </div>
    <div class="tab-panel" class:hidden={activeTab !== 'dashboard'} aria-hidden={activeTab !== 'dashboard'}>
      <DashboardView visible={activeTab === 'dashboard'} />
    </div>
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

  .logo-img {
    width: 36px;
    height: 36px;
    object-fit: contain;
    flex-shrink: 0;
    border-radius: 6px;
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

  .tab-panel.hidden {
    display: none;
  }
</style>
