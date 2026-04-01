const API_KEY = 'demo-key-1';
const headers = { 'X-API-Key': API_KEY };

let priceChart = null;

async function loadProduct() {
 
  const parts = window.location.pathname.split('/');
  const productId = parts[parts.length - 1];

  if (!productId || isNaN(productId)) {
    document.getElementById('product-detail').innerHTML = '<p class="error-state">Invalid product ID</p>';
    return;
  }

  try {
    const resp = await fetch(`/api/products/${productId}`, { headers });
    if (resp.status === 404) {
      document.getElementById('product-detail').innerHTML = '<p class="error-state">Product not found</p>';
      return;
    }
    if (!resp.ok) throw new Error(`API error: ${resp.status}`);

    const product = await resp.json();
    renderProduct(product);

  } catch (err) {
    console.error('Failed to load product:', err);
    document.getElementById('product-detail').innerHTML =
      `<p class="error-state">Failed to load product: ${err.message}</p>`;
  }
}

function renderProduct(p) {
  const sourceClass = p.source.replace('1stdibs', 'firstdibs');
  const priceFormatted = '$' + p.current_price.toLocaleString(undefined, { minimumFractionDigits: 2 });

  const originalPriceHtml = p.original_price
    ? `<div class="meta-item"><span class="meta-label">Original Price</span><span class="meta-value">$${p.original_price.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span></div>`
    : '';

  document.getElementById('product-detail').innerHTML = `
    <div class="page-header">
      <p><a href="/products">← Back to Products</a></p>
      <h1>${escapeHtml(p.title)}</h1>
    </div>

    <div class="detail-header">
      <div class="detail-image">🏷️</div>
      <div class="detail-info">
        <div class="detail-meta">
          <div class="meta-item">
            <span class="meta-label">Price</span>
            <span class="meta-value price" style="font-size:1.5rem">${priceFormatted}</span>
          </div>
          ${originalPriceHtml}
          <div class="meta-item">
            <span class="meta-label">Brand</span>
            <span class="meta-value">${escapeHtml(p.brand || '—')}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">Category</span>
            <span class="meta-value">${escapeHtml(p.category || '—')}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">Source</span>
            <span class="source-badge ${sourceClass}">${p.source}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">Condition</span>
            <span class="meta-value">${escapeHtml(p.condition || '—')}</span>
          </div>
        </div>
        <p style="color: var(--text-secondary); margin-top: 0.5rem;">${escapeHtml(p.description || '')}</p>
      </div>
    </div>

    <div class="charts-grid">
      <div class="card">
        <h2>Price History</h2>
        ${p.price_history.length > 0
          ? '<canvas id="price-history-chart"></canvas>'
          : '<p class="empty-state">No price history yet. Refresh data to track price changes.</p>'
        }
      </div>

      <div class="card">
        <h2>Price Change Events</h2>
        ${p.price_events.length > 0
          ? `<ul class="events-list">${p.price_events.map(e => {
              const direction = e.new_price > e.old_price ? 'up' : 'down';
              const arrow = direction === 'up' ? '↑' : '↓';
              const sign = e.change_pct > 0 ? '+' : '';
              return `<li>
                <div>
                  <span class="price-change price-${direction}">
                    $${e.old_price.toLocaleString(undefined, {minimumFractionDigits:2})} → $${e.new_price.toLocaleString(undefined, {minimumFractionDigits:2})}
                    ${arrow} ${sign}${e.change_pct.toFixed(1)}%
                  </span>
                </div>
                <span style="color:var(--text-muted);font-size:0.8rem">${new Date(e.created_at).toLocaleString()}</span>
              </li>`;
            }).join('')}</ul>`
          : '<p class="empty-state">No price changes detected yet.</p>'
        }
      </div>
    </div>

    <div class="card">
      <h2>Details</h2>
      <table class="product-table">
        <tbody>
          <tr><td style="color:var(--text-muted)">External ID</td><td>${escapeHtml(p.external_id)}</td></tr>
          <tr><td style="color:var(--text-muted)">Source</td><td>${escapeHtml(p.source)}</td></tr>
          <tr><td style="color:var(--text-muted)">Currency</td><td>${escapeHtml(p.currency)}</td></tr>
          <tr><td style="color:var(--text-muted)">First Seen</td><td>${p.first_seen_at ? new Date(p.first_seen_at).toLocaleString() : '—'}</td></tr>
          <tr><td style="color:var(--text-muted)">Last Updated</td><td>${p.last_updated_at ? new Date(p.last_updated_at).toLocaleString() : '—'}</td></tr>
          ${p.url ? `<tr><td style="color:var(--text-muted)">Listing URL</td><td><a href="${escapeHtml(p.url)}" target="_blank">${escapeHtml(p.url)}</a></td></tr>` : ''}
        </tbody>
      </table>
    </div>
  `;

  
  if (p.price_history.length > 0) {
    renderPriceChart(p.price_history);
  }
}

function renderPriceChart(history) {
  const ctx = document.getElementById('price-history-chart').getContext('2d');
  if (priceChart) priceChart.destroy();

  priceChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: history.map(h => new Date(h.recorded_at).toLocaleDateString()),
      datasets: [{
        label: 'Price ($)',
        data: history.map(h => h.price),
        borderColor: '#6366f1',
        backgroundColor: 'rgba(99, 102, 241, 0.1)',
        fill: true,
        tension: 0.3,
        pointRadius: 4,
        pointBackgroundColor: '#6366f1',
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
      },
      scales: {
        x: {
          ticks: { color: '#9ca3af' },
          grid: { color: '#2d3148' },
        },
        y: {
          ticks: { color: '#9ca3af', callback: v => '$' + v.toLocaleString() },
          grid: { color: '#2d3148' },
        },
      },
    },
  });
}

function escapeHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}


loadProduct();
