const API_KEY = 'demo-key-1';
const headers = { 'X-API-Key': API_KEY };

let currentPage = 1;
const perPage = 20;

async function loadProducts(page = 1) {
  currentPage = page;
  const params = new URLSearchParams();
  params.set('page', page);
  params.set('per_page', perPage);

  const source = document.getElementById('filter-source').value;
  const category = document.getElementById('filter-category').value;
  const brand = document.getElementById('filter-brand').value;
  const minPrice = document.getElementById('filter-min-price').value;
  const maxPrice = document.getElementById('filter-max-price').value;
  const search = document.getElementById('filter-search').value;

  if (source) params.set('source', source);
  if (category) params.set('category', category);
  if (brand) params.set('brand', brand);
  if (minPrice) params.set('min_price', minPrice);
  if (maxPrice) params.set('max_price', maxPrice);
  if (search) params.set('search', search);

  const tbody = document.getElementById('products-body');
  tbody.innerHTML = '<tr><td colspan="6" class="loading">Loading products</td></tr>';

  try {
    const resp = await fetch(`/api/products?${params}`, { headers });
    if (!resp.ok) throw new Error(`API error: ${resp.status}`);
    const data = await resp.json();

    if (data.items.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="empty-state">No products found. Try adjusting your filters or refreshing data.</td></tr>';
      document.getElementById('pagination').innerHTML = '';
      return;
    }

    tbody.innerHTML = data.items.map(p => `
      <tr onclick="window.location='/product/${p.id}'">
        <td>
          <div class="product-name">${escapeHtml(p.title)}</div>
        </td>
        <td class="product-brand">${escapeHtml(p.brand || '—')}</td>
        <td>${escapeHtml(p.category || '—')}</td>
        <td class="price">$${p.current_price.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
        <td><span class="source-badge ${p.source.replace('1stdibs', 'firstdibs')}">${p.source}</span></td>
        <td>${escapeHtml(p.condition || '—')}</td>
      </tr>
    `).join('');

    renderPagination(data);

  } catch (err) {
    console.error('Failed to load products:', err);
    tbody.innerHTML = `<tr><td colspan="6" class="error-state">Failed to load products: ${err.message}</td></tr>`;
  }
}

function renderPagination(data) {
  const pag = document.getElementById('pagination');
  if (data.pages <= 1) { pag.innerHTML = ''; return; }

  pag.innerHTML = `
    <button onclick="loadProducts(${data.page - 1})" ${data.page <= 1 ? 'disabled' : ''}>← Prev</button>
    <span class="page-info">Page ${data.page} of ${data.pages} (${data.total} total)</span>
    <button onclick="loadProducts(${data.page + 1})" ${data.page >= data.pages ? 'disabled' : ''}>Next →</button>
  `;
}

function applyFilters() {
  loadProducts(1);
}

function clearFilters() {
  document.getElementById('filter-source').value = '';
  document.getElementById('filter-category').value = '';
  document.getElementById('filter-brand').value = '';
  document.getElementById('filter-min-price').value = '';
  document.getElementById('filter-max-price').value = '';
  document.getElementById('filter-search').value = '';
  loadProducts(1);
}

async function loadCategories() {
  try {
    const resp = await fetch('/api/analytics', { headers });
    if (!resp.ok) return;
    const data = await resp.json();

    const select = document.getElementById('filter-category');
    data.by_category.forEach(c => {
      const opt = document.createElement('option');
      opt.value = c.category;
      opt.textContent = c.category;
      select.appendChild(opt);
    });
  } catch (e) {
    console.error('Failed to load categories:', e);
  }
}

function escapeHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}


loadCategories();
loadProducts();
