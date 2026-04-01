const API_KEY = 'demo-key-1';
const headers = { 'X-API-Key': API_KEY };

let sourceChart = null;
let categoryChart = null;

async function loadAnalytics() {
  try {
    const resp = await fetch('/api/analytics', { headers });
    if (!resp.ok) throw new Error(`API error: ${resp.status}`);
    const data = await resp.json();

    
    document.getElementById('stat-total').textContent = data.total_products.toLocaleString();
    document.getElementById('stat-sources').textContent = data.total_sources;
    document.getElementById('stat-avg').textContent = '$' + data.overall_avg_price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    document.getElementById('stat-events').textContent = data.price_change_events.toLocaleString();

    
    const tbody = document.getElementById('source-table-body');
    tbody.innerHTML = data.by_source.map(s => `
      <tr>
        <td><span class="source-badge ${s.source.replace('1stdibs', 'firstdibs')}">${s.source}</span></td>
        <td>${s.count}</td>
        <td class="price">$${s.avg_price.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
        <td>$${s.min_price.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
        <td>$${s.max_price.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
      </tr>
    `).join('');

    
    renderSourceChart(data.by_source);

    
    renderCategoryChart(data.by_category);

  } catch (err) {
    console.error('Failed to load analytics:', err);
    document.getElementById('stat-total').textContent = 'Error';
  }
}

function renderSourceChart(bySource) {
  const ctx = document.getElementById('source-chart').getContext('2d');
  if (sourceChart) sourceChart.destroy();

  const colors = ['#6366f1', '#eab308', '#22c55e', '#ef4444', '#06b6d4'];
  sourceChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: bySource.map(s => s.source),
      datasets: [{
        data: bySource.map(s => s.count),
        backgroundColor: colors.slice(0, bySource.length),
        borderColor: '#0f1117',
        borderWidth: 3,
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: 'bottom', labels: { color: '#9ca3af', padding: 16 } },
      },
    },
  });
}

function renderCategoryChart(byCategory) {
  const ctx = document.getElementById('category-chart').getContext('2d');
  if (categoryChart) categoryChart.destroy();

  
  const sorted = byCategory.sort((a, b) => b.avg_price - a.avg_price).slice(0, 10);

  categoryChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: sorted.map(c => c.category),
      datasets: [{
        label: 'Avg Price ($)',
        data: sorted.map(c => c.avg_price),
        backgroundColor: 'rgba(99, 102, 241, 0.6)',
        borderColor: '#6366f1',
        borderWidth: 1,
        borderRadius: 6,
      }]
    },
    options: {
      responsive: true,
      indexAxis: 'y',
      plugins: {
        legend: { display: false },
      },
      scales: {
        x: {
          ticks: { color: '#9ca3af', callback: v => '$' + v.toLocaleString() },
          grid: { color: '#2d3148' },
        },
        y: {
          ticks: { color: '#9ca3af' },
          grid: { display: false },
        },
      },
    },
  });
}

async function triggerRefresh() {
  const btn = document.getElementById('refresh-btn');
  btn.disabled = true;
  btn.textContent = '⟳ Refreshing...';

  try {
    const resp = await fetch('/api/refresh', { method: 'POST', headers });
    if (!resp.ok) throw new Error(`Refresh failed: ${resp.status}`);
    const data = await resp.json();

    showToast(`Refreshed ${data.total_products_processed} products, ${data.total_price_changes} price changes`, 'success');

    
    await loadAnalytics();

  } catch (err) {
    console.error('Refresh failed:', err);
    showToast('Refresh failed: ' + err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = '⟳ Refresh Data';
  }
}

function showToast(message, type = 'success') {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}


loadAnalytics();
