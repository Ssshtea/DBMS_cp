(function(){
  // ---------- Utilities ----------
  function qs(sel,root=document){ return root.querySelector(sel) }
  function qsa(sel,root=document){ return [...root.querySelectorAll(sel)] }
  function formatINR(n){ return '₹'+ Number(n).toLocaleString('en-IN',{maximumFractionDigits:0}) }
  function titleCase(s){ return s.replace(/-/g,' ').replace(/\b\w/g,c=>c.toUpperCase()) }
  const byId = (arr,id) => arr.find(x=>x.id==id);

  // ---------- Auth ----------
  const loginView = qs('#view-login');
  const appShell = qs('#app-shell');
  const loginForm = qs('#login-form');
  const loginError = qs('#login-error');

  const session = {
    loggedIn: JSON.parse(sessionStorage.getItem('loggedIn')||'false'),
    login(){ this.loggedIn=true; sessionStorage.setItem('loggedIn','true') },
    logout(){ this.loggedIn=false; sessionStorage.removeItem('loggedIn') }
  };

  function gate(){
    if(session.loggedIn){ 
      loginView.classList.add('hidden'); 
      appShell.classList.remove('hidden'); 
      renderAll(); 
      navTo('dashboard'); 
    } else { 
      appShell.classList.add('hidden'); 
      loginView.classList.remove('hidden'); 
    }
  }

  loginForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const u = qs('#login-username').value.trim();
    const p = qs('#login-password').value;

    try {
      const res = await fetch('/api/admin/login', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({username: u, password: p})
      });
      const data = await res.json();

      if(data.success){
        loginError.classList.add('hidden');
        session.login();
        gate();
      } else {
        loginError.classList.remove('hidden');
      }
    } catch(err){
      console.error('Login error', err);
      loginError.classList.remove('hidden');
    }
  });


  qs('#btn-logout')?.addEventListener('click', ()=>{ session.logout(); gate(); });

  // ---------- Navigation ----------
  const navButtons = qsa('.nav-link');
  navButtons.forEach(btn=>btn.addEventListener('click',()=>{
    const target = btn.dataset.target; 
    if(!target) return;
    navButtons.forEach(b=>b.classList.remove('active')); 
    btn.classList.add('active');
    navTo(target);
  }));

  function navTo(target){
    qsa('.view').forEach(v=>v.classList.add('hidden'));
    const view = qs(`#view-${target}`); 
    view?.classList.remove('hidden');
    qs('#top-title').textContent = titleCase(target);
    if(target==='dashboard'){ drawDashboard(); }
    if(target==='products'){ renderProducts(); }
    if(target==='orders'){ renderOrders(); }
    if(target==='customers'){ renderCustomers(); }
    if(target==='sellers'){ renderSellers(); }
    if(target==='reports'){ renderReports(); }
    if(target==='analytics'){ renderAnalytics(); }
    if(target==='returns'){ renderReturns(); }
    if(target==='bills'){ renderBills(); }
  }

  // ---------- Dashboard ----------
  async function drawDashboard(){
  try {
    // ---------- Top stats ----------
    const res = await fetch('/api/admin/dashboard');
    const stats = await res.json();
    qs('#stat-products').textContent = stats.total_products;
    qs('#stat-orders').textContent = stats.total_orders;
    qs('#stat-revenue').textContent = formatINR(stats.total_revenue);

    // ---------- Performance Metrics ----------
    const resMetrics = await fetch('/api/admin/metrics');
    const metrics = await resMetrics.json();
    qs('#stat-conversion').textContent = metrics.conversion_rate + '%';

    // ---------- Monthly Sales ----------
    const resSales = await fetch('/api/admin/dashboard/monthly-sales');
    const monthlySales = await resSales.json();
    renderMonthlySalesChart(monthlySales);

    // ---------- Best Sellers ----------
    const resBest = await fetch('/api/admin/dashboard/best-sellers');
    const bestSellers = await resBest.json();
    renderBestSellers(bestSellers);

    // ---------- Order Statistics ----------
    const resOrderStats = await fetch('/api/admin/orders/statistics');
    const orderStats = await resOrderStats.json();
    if (orderStats.success) {
      qs('#stat-orders-today').textContent = orderStats.statistics.orders_today || 0;
      qs('#stat-revenue-today').textContent = formatINR(orderStats.statistics.revenue_today || 0);
    }

    // ---------- Customer & Seller Counts ----------
    const resCustomers = await fetch('/api/admin/customers');
    const customers = await resCustomers.json();
    qs('#stat-total-customers').textContent = customers.length || 0;

    const resSellers = await fetch('/api/admin/sellers');
    const sellers = await resSellers.json();
    qs('#stat-total-sellers').textContent = sellers.length || 0;

    // ---------- Revenue Summary ----------
    const resRevenue = await fetch('/api/admin/dashboard/revenue-summary');
    const revenueData = await resRevenue.json();
    if (revenueData.success) {
      renderRevenueSummary(revenueData);
    }

    // ---------- Pending Orders (with details) ----------
    const resPendingOrders = await fetch('/api/admin/orders/pending');
    const pendingOrders = await resPendingOrders.json();
    if (pendingOrders.success) {
      renderPendingOrders(pendingOrders.orders || []);
    }

    // ---------- Sales by Category Chart ----------
    const resCategorySales = await fetch('/api/admin/reports/sales-by-category');
    const categorySales = await resCategorySales.json();
    if (categorySales.success) {
      renderCategoryChart(categorySales.data || []);
    }

    // ---------- Top Customers ----------
    const resTopCustomers = await fetch('/api/admin/customers/top?limit=5');
    const topCustomers = await resTopCustomers.json();
    if (topCustomers.success) {
      renderTopCustomers(topCustomers.customers);
    }

    // ---------- Recent Orders ----------
    const resRecentOrders = await fetch('/api/admin/orders/recent?limit=5');
    const recentOrders = await resRecentOrders.json();
    if (recentOrders.success) {
      renderRecentOrders(recentOrders.orders || []);
    }

    // ---------- Low Stock Alerts (for dashboard card) ----------
    const resLowStockAlerts = await fetch('/api/admin/inventory/low-stock?threshold=10');
    const lowStockAlertsData = await resLowStockAlerts.json();
    if (lowStockAlertsData.success && lowStockAlertsData.products) {
      renderLowStockAlerts(lowStockAlertsData.products);
    }
  } catch(err){
    console.error('Dashboard fetch error', err);
  }
}

  function renderTopCustomers(customers) {
    const container = qs('#top-customers');
    if (!container) return;
    container.innerHTML = '';
    
    if (!customers || customers.length === 0) {
      container.innerHTML = '<div class="text-center text-gray-500">No customer data</div>';
      return;
    }
    
    customers.forEach((customer, index) => {
      const li = document.createElement('li');
      li.innerHTML = `
        <div class="flex justify-between items-center">
          <span>${index + 1}. ${customer.name}</span>
          <span class="text-sm text-gray-600">${formatINR(customer.total_spent || 0)}</span>
        </div>
      `;
      container.appendChild(li);
    });
  }

  function renderRevenueSummary(data) {
    const container = qs('#revenue-summary');
    if (!container) return;
    
    container.innerHTML = '';
    
    const items = [
      { label: 'Today', value: data.today || 0, color: '#22c55e' },
      { label: 'This Week', value: data.week || 0, color: '#3b82f6' },
      { label: 'This Month', value: data.month || 0, color: '#f59e0b' },
      { label: 'Total', value: data.total || 0, color: '#8b5cf6' }
    ];
    
    items.forEach(item => {
      const div = document.createElement('div');
      div.style.cssText = 'padding: 16px; border-bottom: 1px solid #eee;';
      div.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div>
            <div style="font-size: 0.85em; color: #666; margin-bottom: 4px;">${item.label}</div>
            <div style="font-size: 1.5em; font-weight: bold; color: ${item.color};">
              ${formatINR(item.value)}
            </div>
          </div>
        </div>
      `;
      container.appendChild(div);
    });
  }

  function renderLowStockProducts(products) {
    const container = qs('#low-stock-list');
    const countBadge = qs('#low-stock-count');
    if (!container) return;
    
    countBadge.textContent = products.length;
    
    if (!products || products.length === 0) {
      container.innerHTML = '<div class="text-center text-gray-500">No low stock items</div>';
      return;
    }
    
      container.innerHTML = '';
    products.forEach(product => {
      const div = document.createElement('div');
      div.className = 'low-stock-item';
      div.style.cssText = 'padding: 12px; border-bottom: 1px solid #eee; cursor: pointer;';
      div.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div>
            <strong>${product.name}</strong>
            <div style="font-size: 0.85em; color: #666;">${product.category}</div>
          </div>
          <div style="text-align: right;">
            <div style="color: ${product.quantityavailable === 0 ? '#ef4444' : '#f59e0b'}; font-weight: bold;">
              ${product.quantityavailable} left
            </div>
            <div style="font-size: 0.85em; color: #666;">${formatINR(product.price)}</div>
          </div>
        </div>
      `;
      div.addEventListener('click', () => {
        // Navigate to products view and highlight this product
        showView('view-products');
        setTimeout(() => {
          const productSearch = qs('#product-search');
          if (productSearch) {
            productSearch.value = product.name;
            productSearch.dispatchEvent(new Event('input'));
          }
        }, 100);
      });
      container.appendChild(div);
    });
  }

  function renderPendingOrders(orders) {
    const container = qs('#pending-orders-list');
    const countBadge = qs('#pending-orders-count');
    if (!container) return;
    
    countBadge.textContent = orders.length;
    
    if (!orders || orders.length === 0) {
      container.innerHTML = '<div class="text-center text-gray-500">No pending orders</div>';
      return;
    }
    
    container.innerHTML = '';
    orders.forEach(order => {
        const div = document.createElement('div');
      div.className = 'pending-order-item';
      div.style.cssText = 'padding: 12px; border-bottom: 1px solid #eee; cursor: pointer;';
        div.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div>
            <strong>Order #${order.order_id}</strong>
            <div style="font-size: 0.85em; color: #666;">${order.customer_name || 'Guest'}</div>
            <div style="font-size: 0.85em; color: #666;">${order.formatted_date || order.order_date || ''}</div>
          </div>
          <div style="text-align: right;">
            <div style="font-weight: bold; color: #22c55e;">${formatINR(order.total_amount)}</div>
            <div style="font-size: 0.85em; color: #666;">${order.status}</div>
          </div>
          </div>
        `;
      div.addEventListener('click', () => {
        // Navigate to orders view
        showView('view-orders');
        setTimeout(() => {
          const orderFilter = qs('#order-filter-status');
          if (orderFilter) {
            orderFilter.value = 'Pending';
            orderFilter.dispatchEvent(new Event('change'));
          }
        }, 100);
      });
        container.appendChild(div);
      });
  }

  function renderCategoryChart(data) {
    const ctx = qs('#category-chart');
    if (!ctx) return;
    
    if (window.categoryChart) {
      window.categoryChart.destroy();
    }
    
    if (!data || data.length === 0) {
      ctx.getContext('2d').clearRect(0, 0, ctx.width, ctx.height);
      return;
    }
    
    const labels = data.map(item => item.category || 'Unknown');
    const values = data.map(item => parseFloat(item.revenue || item.total_revenue || 0));
    
    window.categoryChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: labels,
        datasets: [{
          data: values,
          backgroundColor: [
            '#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6',
            '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1'
          ],
          borderWidth: 2,
          borderColor: '#fff'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom'
          },
          tooltip: {
            callbacks: {
              label: function(context) {
                return context.label + ': ₹' + context.parsed.toLocaleString();
              }
            }
          }
        }
      }
    });
  }

  function renderRecentOrders(orders) {
    const container = qs('#recent-orders-list');
    if (!container) return;
    
    if (!orders || orders.length === 0) {
      container.innerHTML = '<div class="text-center text-gray-500">No recent orders</div>';
      return;
    }
    
    container.innerHTML = '';
    orders.forEach(order => {
      const div = document.createElement('div');
      div.style.cssText = 'padding: 12px; border-bottom: 1px solid #eee; cursor: pointer;';
      div.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div>
            <strong>Order #${order.order_id}</strong>
            <div style="font-size: 0.85em; color: #666;">${order.customer_name || 'Guest'}</div>
            <div style="font-size: 0.85em; color: #666;">${order.formatted_date || order.order_date || ''}</div>
          </div>
          <div style="text-align: right;">
            <div style="font-weight: bold;">${formatINR(order.total_amount)}</div>
            <div style="font-size: 0.85em; color: #666;">
              <span class="status-${order.status?.toLowerCase() || 'pending'}">${order.status || 'Pending'}</span>
            </div>
          </div>
        </div>
      `;
      div.addEventListener('click', () => {
        showView('view-orders');
      });
      container.appendChild(div);
    });
  }

  function renderLowStockAlerts(products) {
    const container = qs('#low-stock-alerts-list');
    if (!container) return;
    
    if (!products || products.length === 0) {
      container.innerHTML = '<div class="text-center text-gray-500">All products are well stocked</div>';
      return;
    }
    
    container.innerHTML = '';
    products.slice(0, 10).forEach(product => {
      const div = document.createElement('div');
      div.style.cssText = 'padding: 12px; border-bottom: 1px solid #eee;';
      const stockLevel = product.quantityavailable || 0;
      const stockColor = stockLevel === 0 ? '#ef4444' : stockLevel <= 5 ? '#f59e0b' : '#3b82f6';
      div.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div>
            <div style="font-weight: 500; margin-bottom: 4px;">${product.name || 'N/A'}</div>
            <div style="font-size: 12px; color: #666;">${product.category || 'N/A'}</div>
          </div>
          <div style="text-align: right;">
            <div style="font-weight: 600; color: ${stockColor};">${stockLevel} left</div>
            <div style="font-size: 12px; color: #666;">${formatINR(product.price || 0)}</div>
          </div>
        </div>
      `;
      container.appendChild(div);
    });
    
    if (products.length > 10) {
      const moreDiv = document.createElement('div');
      moreDiv.style.cssText = 'padding: 12px; text-align: center; color: #666; font-size: 12px;';
      moreDiv.textContent = `+${products.length - 10} more products with low stock`;
      container.appendChild(moreDiv);
    }
  }

  function renderCustomerSegments(segments) {
    const container = qs('#customer-segments-list');
    if (!container) return;
    
    if (!segments || segments.length === 0) {
      container.innerHTML = '<div class="text-center text-gray-500">No segment data</div>';
      return;
    }
    
    container.innerHTML = '';
    segments.forEach(segment => {
      const div = document.createElement('div');
      div.style.cssText = 'padding: 12px; border-bottom: 1px solid #eee;';
      const segmentName = segment.segment || 'Unknown';
      const segmentColor = segmentName === 'VIP' ? '#22c55e' : segmentName === 'Regular' ? '#3b82f6' : '#94a3b8';
      div.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div>
            <strong style="color: ${segmentColor};">${segmentName}</strong>
            <div style="font-size: 0.85em; color: #666;">${segment.count || 0} customers</div>
            <div style="font-size: 0.75em; color: #666;">Avg ${segment.avg_orders || 0} orders</div>
          </div>
          <div style="text-align: right;">
            <div style="font-weight: bold; color: #22c55e;">${formatINR(segment.avg_value || 0)}</div>
            <div style="font-size: 0.85em; color: #666;">Avg Value</div>
            <div style="font-size: 0.75em; color: #666;">Total: ${formatINR(segment.total_value || 0)}</div>
          </div>
        </div>
      `;
      container.appendChild(div);
    });
  }


  // ---------- Inventory Alerts ----------
  async function loadInventoryAlerts(){
    try {
      const res = await fetch('/api/admin/inventory-alerts');
      const alerts = await res.json();
      const container = qs('#inventory-alerts');
      container.innerHTML = '';
      
      if (alerts.length === 0) {
        container.innerHTML = '<div class="text-center text-gray-500">No inventory alerts</div>';
        return;
      }
      
      alerts.forEach(alert => {
        const div = document.createElement('div');
        div.className = 'alert-item';
        div.innerHTML = `
          <div>
            <strong>${alert.product_name}</strong>
            <div>Stock: ${alert.current_stock} (Threshold: ${alert.threshold})</div>
          </div>
        `;
        container.appendChild(div);
      });
    } catch(err){ console.error('Inventory alerts error', err); }
  }

  // ---------- Chart Rendering Functions ----------
  function renderMonthlySalesChart(data) {
    const ctx = qs('#sales-chart');
    if (!ctx) return;
    
    // Destroy existing chart if it exists
    if (window.salesChart) {
      window.salesChart.destroy();
    }
    
    // Handle empty data
    if (!data || data.length === 0) {
      ctx.getContext('2d').clearRect(0, 0, ctx.width, ctx.height);
      return;
    }
    
    const labels = data.map(item => item.month);
    const values = data.map(item => parseFloat(item.total) || 0);
    
    window.salesChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: 'Monthly Sales',
          data: values,
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          tension: 0.4,
          fill: true
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        aspectRatio: 2,
        plugins: {
          legend: {
            display: true,
            position: 'top'
          }
        },
        scales: {
          x: {
            grid: {
              display: false
            }
          },
          y: {
            beginAtZero: true,
            grid: {
              color: 'rgba(0, 0, 0, 0.1)'
            },
            ticks: {
              callback: function(value) {
                return '₹' + value.toLocaleString();
              }
            }
          }
        },
        elements: {
          point: {
            radius: 4,
            hoverRadius: 6
          }
        }
      }
    });
  }

  function renderBestSellers(data) {
    const container = qs('#best-sellers');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (!data || data.length === 0) {
      const li = document.createElement('li');
      li.innerHTML = '<div class="text-center text-gray-500">No sales data available</div>';
      container.appendChild(li);
      return;
    }
    
    data.forEach((item, index) => {
      const li = document.createElement('li');
      li.innerHTML = `
        <div class="flex justify-between items-center">
          <span>${index + 1}. ${item.name}</span>
          <span class="text-sm text-gray-600">${item.total_qty} sold</span>
        </div>
      `;
      container.appendChild(li);
    });
}

  // ---------- Products CRUD ----------
  const productTbody = qs('#products-tbody');
  const tplProduct = qs('#tpl-product-row');
  const productFilter = qs('#product-filter-category');
  const productSearch = qs('#product-search');
  const productSort = qs('#product-sort');
  const datalistCategories = qs('#category-list');
  let products = [];
  let sellers = [];

  async function renderProducts(){
    try {
      const res = await fetch('/api/admin/products');
      products = await res.json();
      // fetch sellers for product modal
      const resSellers = await fetch('/api/admin/sellers');
      sellers = await resSellers.json();

      const categories = [...new Set(products.map(p=>p.category))];
      productFilter.innerHTML = '<option value="all">All Categories</option>' + categories.map(c=>`<option>${c}</option>`).join('');
      datalistCategories.innerHTML = categories.map(c=>`<option value="${c}">`).join('');

      const sellerSel = qs('#product-seller');
      sellerSel.innerHTML = sellers.map(s=>`<option value="${s.id}">${s.name} (${s.company})`).join('');

      drawProductRows();
    } catch(err){ console.error('Products fetch error', err); }
  }

  function drawProductRows(){
    const q = productSearch.value.toLowerCase();
    const cat = productFilter.value;
    const sort = productSort.value;
    let rows = products.filter(p=>
      (cat==='all' || p.category===cat) &&
      (p.name.toLowerCase().includes(q) || p.category.toLowerCase().includes(q))
    );
    rows.sort((a,b)=>{
      if(sort==='name-asc') return a.name.localeCompare(b.name);
      if(sort==='name-desc') return b.name.localeCompare(a.name);
      if(sort==='price-asc') return a.price - b.price;
      if(sort==='price-desc') return b.price - a.price;
      if(sort==='stock-asc') return a.quantityavailable - b.quantityavailable;
      if(sort==='stock-desc') return b.quantityavailable - a.quantityavailable;
      if(sort==='category') return a.category.localeCompare(b.category);
      return 0;
    });

    productTbody.innerHTML='';
    rows.forEach(p=>{
      const tr = tplProduct.content.firstElementChild.cloneNode(true);
      tr.querySelector('.name').textContent = p.name;
      tr.querySelector('.category').textContent = p.category;
      tr.querySelector('.price').textContent = formatINR(p.price);
      tr.querySelector('.stock').textContent = p.quantityavailable;
      const seller = sellers.find(s=>s.id===p.seller_id);
      tr.querySelector('.seller').textContent = seller? seller.name : '-';
      tr.querySelector('[data-action="edit"]').addEventListener('click',()=>openProductModal(p));
      tr.querySelector('[data-action="delete"]').addEventListener('click',()=>deleteProduct(p.product_id));
      productTbody.appendChild(tr);
    });
  }

  productSearch.addEventListener('input', drawProductRows);
  productFilter.addEventListener('change', drawProductRows);
  productSort.addEventListener('change', drawProductRows);
  qs('#btn-new-product').addEventListener('click',()=>openProductModal());

  function openProductModal(p){
    const dlg = qs('#modal-product');
    qs('#product-form-title').textContent = p? 'Edit Product' : 'New Product';
    qs('#product-id').value = p?.product_id || '';
    qs('#product-name').value = p?.name || '';
    qs('#product-category').value = p?.category || '';
    qs('#product-price').value = p?.price ?? '';
    qs('#product-stock').value = p?.quantityavailable ?? '';
    const descField = qs('#product-description');
    if(descField) descField.value = p?.description || '';
    qs('#product-seller').value = p?.seller_id || (sellers[0]?.id || '');
    dlg.showModal();
  }

  async function saveProduct(product){
    const method = product.product_id ? 'PUT' : 'POST';
    const url = '/api/admin/products' + (product.product_id ? `/${product.product_id}` : '');
    try {
      const response = await fetch(url, {
        method,
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify(product)
      });
      const result = await response.json();
      if (result.success) {
        alert('✅ Product ' + (product.product_id ? 'updated' : 'added') + ' successfully!');
        renderProducts();
        qs('#modal-product').close();
      } else {
        alert('❌ Error: ' + (result.error || 'Unknown error'));
      }
    } catch(err){ 
      console.error('Save product error', err);
      alert('❌ Error saving product: ' + err.message);
    }
  }

  qs('#product-form').addEventListener('close', async ()=>{
    if(qs('#product-form').returnValue!=="default") return;
    const obj = {
      product_id: Number(qs('#product-id').value) || null,
      name: qs('#product-name').value.trim(),
      category: qs('#product-category').value.trim(),
      price: Number(qs('#product-price').value),
      quantityavailable: Number(qs('#product-stock').value) || 0,
      description: qs('#product-description')?.value?.trim() || '',
      seller_id: Number(qs('#product-seller').value) || null
    };
    
    // Validate required fields
    if (!obj.name || !obj.price || !obj.category) {
      alert('❌ Please fill in all required fields: Name, Price, and Category');
      return;
    }
    
    await saveProduct(obj);
  });

  // Add cancel/close button functionality for product modal
  qs('#modal-product').addEventListener('click', (e) => {
    if (e.target.value === 'cancel' || e.target.classList.contains('close-modal')) {
      qs('#modal-product').close();
    }
  });
  
  // Close modal on backdrop click
  qs('#modal-product')?.addEventListener('click', (e) => {
    if (e.target === qs('#modal-product')) {
      qs('#modal-product').close();
    }
  });

  async function deleteProduct(id){
    if(!confirm('Delete this product?')) return;
    try {
      await fetch(`/api/admin/products/${id}`, { method:'DELETE' });
      renderProducts();
    } catch(err){ console.error('Delete product error', err); }
  }

  // ---------- Orders ----------
  const ordersTbody = qs('#orders-tbody');
  const tplOrder = qs('#tpl-order-row');
  const orderFilter = qs('#order-filter-status');

  orderFilter.addEventListener('change', renderOrders);

  async function renderOrders(){
    try {
      const res = await fetch('/api/admin/orders');
      const orders = await res.json();
      ordersTbody.innerHTML='';
      const status = orderFilter.value;
      orders.filter(o=>status==='all'||o.status===status)
        .sort((a,b)=>b.order_id-a.order_id)
        .forEach(o=>{
          const tr = tplOrder.content.firstElementChild.cloneNode(true);
          tr.querySelector('.id').textContent = '#'+o.order_id;
          tr.querySelector('.date').textContent = o.date;
          tr.querySelector('.customer').textContent = o.customer_name || '-';
          tr.querySelector('.amount').textContent = formatINR(o.total_amount);
          const statusEl = tr.querySelector('.status');
          statusEl.innerHTML = `<span class="status-${(o.status || '').toLowerCase()}">${o.status || 'N/A'}</span>`;
          tr.querySelector('[data-action="view"]').addEventListener('click',()=>openOrderModal(o));
          ordersTbody.appendChild(tr);
        });
    } catch(err){ console.error('Orders fetch error', err); }
  }

  function openOrderModal(o){
    const dlg = qs('#modal-order');
    const wrap = qs('#order-details');
    wrap.innerHTML = `
      <div class="grid-2">
        <div>
          <div><strong>Order:</strong> #${o.order_id}</div>
          <div><strong>Date:</strong> ${o.date}</div>
          <div><strong>Status:</strong> ${o.status}</div>
        </div>
        <div>
          <div><strong>Customer:</strong> ${o.customer_name || 'N/A'}</div>
          <div><strong>Email:</strong> ${o.customer_email || 'N/A'}</div>
          <div><strong>Phone:</strong> ${o.customer_phone || 'N/A'}</div>
        </div>
      </div>
      <div class="table-wrap mt-4">
        <table class="table">
          <thead><tr><th>Item</th><th>Price</th><th>Qty</th><th>Total</th></tr></thead>
          <tbody>
            ${(o.items || []).map(it=>`<tr><td>${it.name}</td><td>${formatINR(it.price)}</td><td>${it.qty}</td><td>${formatINR(it.price*it.qty)}</td></tr>`).join('')}
          </tbody>
          <tfoot><tr><th colspan="3" style="text-align:right">Grand Total</th><th>${formatINR(o.total_amount)}</th></tr></tfoot>
        </table>
      </div>
    `;
    qs('#order-print').onclick = ()=> printBillForOrder(o);
    dlg.showModal();
    
    // Close on backdrop click
    dlg.addEventListener('click', (e) => {
      if (e.target === dlg) dlg.close();
    });
  }

  // ---------- Customers ----------
  const customersTbody = qs('#customers-tbody');
  const tplCustomer = qs('#tpl-customer-row');
  const customerSearch = qs('#customer-search');
  customerSearch.addEventListener('input', renderCustomers);

  async function renderCustomers(){
    try {
      const res = await fetch('/api/admin/customers');
      const customers = await res.json();
      const q = customerSearch.value.toLowerCase();
      customersTbody.innerHTML='';
      customers.filter(c=> c.name.toLowerCase().includes(q) || c.email.toLowerCase().includes(q))
        .forEach(c=>{
          const tr = tplCustomer.content.firstElementChild.cloneNode(true);
          tr.querySelector('.name').textContent = c.name;
          tr.querySelector('.email').textContent = c.email;
          tr.querySelector('.phone').textContent = c.phone;
          tr.querySelector('.status').textContent = c.blocked ? 'Blocked':'Active';
          tr.querySelector('[data-action="toggle"]').addEventListener('click', async ()=>{
            try {
              await fetch(`/api/admin/customers/${c.customer_id}/toggle`, {method:'PUT'});
              renderCustomers();
            } catch(err){ console.error(err); }
          });
          tr.querySelector('[data-action="history"]').addEventListener('click', async ()=>{
            try {
              const res = await fetch(`/api/admin/customers/${c.customer_id}/history`);
              const data = await res.json();
              if (data.success) {
                showCustomerHistory(c, data.orders);
              } else {
                alert('Error loading customer history: ' + (data.error || 'Unknown error'));
              }
            } catch(err){ 
              console.error(err);
              alert('Error loading customer history: ' + err.message);
            }
          });
          customersTbody.appendChild(tr);
        });
    } catch(err){ console.error('Customers fetch error', err); }
  }

  // ---------- Sellers CRUD ----------
  const sellersTbody = qs('#sellers-tbody');
  const tplSeller = qs('#tpl-seller-row');

  async function renderSellers(){
    try {
      const res = await fetch('/api/admin/sellers');
      sellers = await res.json();
      sellersTbody.innerHTML='';
      sellers.forEach(s=>{
        const tr = tplSeller.content.firstElementChild.cloneNode(true);
        tr.querySelector('.name').textContent = s.name;
        tr.querySelector('.company').textContent = s.company;
        tr.querySelector('.contact').textContent = `${s.email}, ${s.phone}`;
        tr.querySelector('[data-action="edit"]').addEventListener('click',()=>openSellerModal(s));
        tr.querySelector('[data-action="delete"]').addEventListener('click',()=>deleteSeller(s.id));
        sellersTbody.appendChild(tr);
      });
    } catch(err){ console.error('Sellers fetch error', err); }
  }

  qs('#btn-new-seller').addEventListener('click',()=>openSellerModal());
  function openSellerModal(s){
    const dlg = qs('#modal-seller');
    qs('#seller-form-title').textContent = s? 'Edit Seller':'New Seller';
    qs('#seller-id').value = s?.id || '';
    qs('#seller-name').value = s?.name || '';
    qs('#seller-company').value = s?.company || '';
    qs('#seller-email').value = s?.email || '';
    qs('#seller-phone').value = s?.phone || '';
    dlg.showModal();
  }

  qs('#seller-form').addEventListener('close', async ()=>{
    if(qs('#seller-form').returnValue!=="default") return;
    const obj = {
      id: Number(qs('#seller-id').value) || null,
      name: qs('#seller-name').value.trim(),
      company: qs('#seller-company').value.trim(),
      email: qs('#seller-email').value.trim(),
      phone: qs('#seller-phone').value.trim()
    };
    try {
      const method = obj.id ? 'PUT':'POST';
      const url = '/api/admin/sellers' + (obj.id?`/${obj.id}`:'');
      const response = await fetch(url, {method, headers:{'Content-Type':'application/json'}, body: JSON.stringify(obj)});
      const result = await response.json();
      if (result.success) {
        alert('✅ Seller ' + (obj.id ? 'updated' : 'added') + ' successfully!');
        renderSellers(); 
        renderProducts();
        qs('#modal-seller').close();
      } else {
        alert('❌ Error saving seller: ' + (result.error || 'Unknown error'));
      }
    } catch(err){ 
      console.error(err);
      alert('❌ Error saving seller: ' + err.message);
    }
  });

  // Add cancel/close button functionality for seller modal
  qs('#modal-seller').addEventListener('click', (e) => {
    if (e.target.value === 'cancel' || e.target.classList.contains('close-modal')) {
      qs('#modal-seller').close();
    }
  });
  
  // Close modal on backdrop click
  qs('#modal-seller')?.addEventListener('click', (e) => {
    if (e.target === qs('#modal-seller')) {
      qs('#modal-seller').close();
    }
  });

  async function deleteSeller(id){
    if(!confirm('Delete this seller?')) return;
    try {
      await fetch(`/api/admin/sellers/${id}`, {method:'DELETE'});
      renderSellers(); renderProducts();
    } catch(err){ console.error(err); }
  }

  // ---------- Reports & Bills ----------
  async function renderReports(){
    try {
      // Set default date range (last 6 months)
      const to = new Date();
      const from = new Date();
      from.setMonth(from.getMonth() - 6);
      
      qs('#report-from').value = from.toISOString().slice(0, 7);
      qs('#report-to').value = to.toISOString().slice(0, 7);
      
      // Load initial report
      await runReport();
      
      // Load best sellers
      const res = await fetch('/api/admin/dashboard/best-sellers');
      const bestSellers = await res.json();
      const container = qs('#report-best');
      container.innerHTML = '';
      bestSellers.forEach((item, index) => {
        const li = document.createElement('li');
        li.innerHTML = `${index + 1}. ${item.name} - ${item.total_qty} sold`;
        container.appendChild(li);
      });
      
    } catch(err){ console.error('Reports error', err); }
  }

  // ---------- Analytics ----------
  async function renderAnalytics(){
    try {
      // Sales Forecast
      const resForecast = await fetch('/api/admin/analytics/sales-forecast');
      const forecastData = await resForecast.json();
      renderForecastChart(forecastData);

      // Customer Behavior
      const resBehavior = await fetch('/api/admin/analytics/customer-behavior');
      const behaviorData = await resBehavior.json();
      renderBehaviorChart(behaviorData);

      // Category Performance
      const resCategoryPerf = await fetch('/api/admin/analytics/category-performance');
      const categoryPerf = await resCategoryPerf.json();
      if (categoryPerf.success) {
        renderCategoryPerformanceChart(categoryPerf.performance || []);
      }

      // Shipping Status Overview
      const resShipping = await fetch('/api/admin/orders/shipping-status-overview');
      const shippingData = await resShipping.json();
      if (shippingData.success) {
        renderShippingStatusOverview(shippingData.overview || []);
      }

      // Product Performance
      await renderProductPerformance();
      
      // Revenue Trends
      await renderRevenueTrends();
      
      // Order Status Distribution
      await renderOrderStatusChart();
      
      // Customer Lifetime Value
      await renderCustomerLTV();
    } catch(err){ 
      console.error('Analytics error', err);
    }
  }
  
  function renderCategoryPerformanceChart(data) {
    const ctx = qs('#category-performance-chart');
    if (!ctx) return;
    
    if (window.categoryPerformanceChart) {
      window.categoryPerformanceChart.destroy();
    }
    
    if (!data || data.length === 0) {
      ctx.getContext('2d').clearRect(0, 0, ctx.width, ctx.height);
      return;
    }
    
    const labels = data.map(item => item.category || 'Unknown');
    const revenue = data.map(item => parseFloat(item.revenue || 0));
    const sold = data.map(item => parseInt(item.total_sold || 0));
    
    window.categoryPerformanceChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Revenue',
          data: revenue,
          backgroundColor: 'rgba(34, 197, 94, 0.8)',
          borderColor: '#22c55e',
          yAxisID: 'y'
        }, {
          label: 'Units Sold',
          data: sold,
          backgroundColor: 'rgba(59, 130, 246, 0.8)',
          borderColor: '#3b82f6',
          yAxisID: 'y1'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            position: 'top'
          }
        },
        scales: {
          y: {
            type: 'linear',
            display: true,
            position: 'left',
            beginAtZero: true,
            ticks: {
              callback: function(value) {
                return '₹' + value.toLocaleString();
              }
            }
          },
          y1: {
            type: 'linear',
            display: true,
            position: 'right',
            beginAtZero: true,
            grid: {
              drawOnChartArea: false
            }
          }
        }
      }
    });
  }
  
  function renderShippingStatusOverview(overview) {
    const container = qs('#shipping-status-overview');
    if (!container) return;
    
    if (!overview || overview.length === 0) {
      container.innerHTML = '<div class="text-center text-gray-500">No shipping data</div>';
      return;
    }
    
    container.innerHTML = '';
    const total = overview.reduce((sum, item) => sum + (item.count || 0), 0);
    
    overview.forEach(item => {
      const div = document.createElement('div');
      div.style.cssText = 'padding: 12px; border-bottom: 1px solid #eee;';
      const statusName = item.shipping_status || 'Unknown';
      const statusColor = statusName === 'Delivered' ? '#22c55e' : 
                         statusName === 'Shipped' ? '#3b82f6' : 
                         statusName === 'Pending' ? '#f59e0b' : '#ef4444';
      const percentage = total > 0 ? ((item.count || 0) / total * 100).toFixed(1) : 0;
      div.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div style="flex: 1;">
            <strong style="color: ${statusColor};">${statusName}</strong>
            <div style="font-size: 0.85em; color: #666;">${item.count || 0} orders (${percentage}%)</div>
            <div style="margin-top: 4px; height: 4px; background: #1f2937; border-radius: 2px; overflow: hidden;">
              <div style="height: 100%; background: ${statusColor}; width: ${percentage}%;"></div>
            </div>
          </div>
          <div style="text-align: right; margin-left: 16px;">
            <div style="font-weight: bold; color: ${statusColor};">${formatINR(item.total_value || 0)}</div>
            <div style="font-size: 0.85em; color: #666;">Total Value</div>
          </div>
        </div>
      `;
      container.appendChild(div);
    });
  }
  
  async function renderRevenueTrends() {
    try {
      const res = await fetch('/api/admin/analytics/sales-forecast');
      const data = await res.json();
      
      const ctx = qs('#revenue-trends-chart');
      if (!ctx) return;
      
      if (window.revenueTrendsChart) {
        window.revenueTrendsChart.destroy();
      }
      
      if (!data || data.length === 0) {
        ctx.getContext('2d').clearRect(0, 0, ctx.width, ctx.height);
        return;
      }
      
      const labels = data.map(item => item.month);
      const revenue = data.map(item => parseFloat(item.revenue || 0));
      const orders = data.map(item => parseInt(item.orders || 0));
      
      window.revenueTrendsChart = new Chart(ctx, {
        type: 'line',
        data: {
          labels: labels,
          datasets: [{
            label: 'Revenue',
            data: revenue,
            borderColor: '#22c55e',
            backgroundColor: 'rgba(34, 197, 94, 0.1)',
            yAxisID: 'y',
            tension: 0.4,
            fill: true
          }, {
            label: 'Orders',
            data: orders,
            borderColor: '#3b82f6',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            yAxisID: 'y1',
            tension: 0.4,
            fill: true
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: true,
              position: 'top'
            }
          },
          scales: {
            y: {
              type: 'linear',
              display: true,
              position: 'left',
              beginAtZero: true,
              ticks: {
                callback: function(value) {
                  return '₹' + value.toLocaleString();
                }
              }
            },
            y1: {
              type: 'linear',
              display: true,
              position: 'right',
              beginAtZero: true,
              grid: {
                drawOnChartArea: false
              }
            }
          }
        }
      });
    } catch(err) {
      console.error('Revenue trends error', err);
    }
  }
  
  async function renderOrderStatusChart() {
    try {
      const res = await fetch('/api/admin/orders/statistics');
      const data = await res.json();
      
      const ctx = qs('#order-status-chart');
      if (!ctx) return;
      
      if (window.orderStatusChart) {
        window.orderStatusChart.destroy();
      }
      
      if (!data.success || !data.statistics.by_status) {
        ctx.getContext('2d').clearRect(0, 0, ctx.width, ctx.height);
        return;
      }
      
      const statusData = data.statistics.by_status;
      const labels = statusData.map(item => item.status || 'Unknown');
      const values = statusData.map(item => parseInt(item.count || 0));
      const colors = {
        'Pending': '#f59e0b',
        'Shipped': '#3b82f6',
        'Delivered': '#22c55e',
        'Cancelled': '#ef4444'
      };
      
      window.orderStatusChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: labels,
          datasets: [{
            data: values,
            backgroundColor: labels.map(label => colors[label] || '#94a3b8'),
            borderWidth: 2,
            borderColor: '#0f172a'
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'bottom'
            }
          }
        }
      });
    } catch(err) {
      console.error('Order status chart error', err);
    }
  }
  
  async function renderCustomerLTV() {
    try {
      const res = await fetch('/api/admin/customers/top?limit=10');
      const data = await res.json();
      
      const container = qs('#customer-ltv');
      if (!container) return;
      
      if (!data.success || !data.customers || data.customers.length === 0) {
        container.innerHTML = '<div class="text-center text-gray-500">No customer data</div>';
        return;
      }
      
      container.innerHTML = '';
      data.customers.forEach((customer, index) => {
        const div = document.createElement('div');
        div.style.cssText = 'padding: 12px; border-bottom: 1px solid #eee;';
        const ltv = customer.lifetime_value || customer.total_spent || 0;
        const tier = ltv > 50000 ? 'VIP' : ltv > 20000 ? 'Regular' : 'New';
        const tierColor = tier === 'VIP' ? '#22c55e' : tier === 'Regular' ? '#3b82f6' : '#94a3b8';
        div.innerHTML = `
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
              <strong>${index + 1}. ${customer.name}</strong>
              <div style="font-size: 0.85em; color: #666;">${customer.total_orders || 0} orders</div>
              <div style="font-size: 0.75em; color: ${tierColor}; margin-top: 2px;">
                <span style="background: ${tierColor}20; padding: 2px 6px; border-radius: 4px;">${tier}</span>
              </div>
            </div>
            <div style="text-align: right;">
              <div style="font-weight: bold; color: #22c55e; font-size: 1.1em;">${formatINR(ltv)}</div>
              <div style="font-size: 0.85em; color: #666;">Lifetime Value</div>
              <div style="font-size: 0.75em; color: #666;">Avg: ${formatINR(customer.avg_order_value || 0)}</div>
            </div>
          </div>
        `;
        container.appendChild(div);
      });
    } catch(err) {
      console.error('Customer LTV error', err);
    }
  }

  // ---------- Returns ----------
  const returnFilterStatus = qs('#return-filter-status');
  if(returnFilterStatus) {
    returnFilterStatus.addEventListener('change', renderReturns);
  }
  
  async function renderReturns(){
    try {
      const status = returnFilterStatus ? returnFilterStatus.value : 'all';
      const url = status === 'all' ? '/api/admin/returns' : `/api/admin/returns?status=${status}`;
      const res = await fetch(url);
      const returns = await res.json();
      const tbody = qs('#returns-tbody');
      tbody.innerHTML = '';
      
      returns.forEach(return_item => {
        const tr = document.createElement('tr');
        const statusLower = return_item.status.toLowerCase();
        const showActions = return_item.status === 'Requested';
        tr.innerHTML = `
          <td>#${return_item.id}</td>
          <td>#${return_item.order_id}</td>
          <td>${return_item.customer_name}</td>
          <td>${return_item.product_name}</td>
          <td>${return_item.reason}</td>
          <td><span class="status-${statusLower}">${return_item.status}</span></td>
          <td>${formatINR(return_item.refund_amount || 0)}</td>
          <td class="row-actions">
            ${showActions ? `
            <button class="btn small" onclick="updateReturnStatus(${return_item.id}, 'Approved')">Approve</button>
            <button class="btn small danger" onclick="updateReturnStatus(${return_item.id}, 'Rejected')">Reject</button>
            ` : ''}
          </td>
        `;
        tbody.appendChild(tr);
      });
    } catch(err){ console.error('Returns error', err); }
  }
  
  async function renderBills(){
    try {
      const res = await fetch('/api/admin/orders');
      const orders = await res.json();
      const billsTbody = qs('#bills-tbody');
      billsTbody.innerHTML = '';
      
      orders.forEach(order => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>#${order.order_id}</td>
          <td>#${order.order_id}</td>
          <td>${order.date}</td>
          <td>${formatINR(order.total_amount)}</td>
          <td class="row-actions">
            <button class="btn small" onclick="window.printBillForOrder(${JSON.stringify(order).replace(/"/g, '&quot;')})">Print/Export PDF</button>
          </td>
        `;
        billsTbody.appendChild(tr);
      });
    } catch(err){ console.error('Bills error', err); }
  }
  
  async function runReport(){
    try {
      const from = qs('#report-from').value;
      const to = qs('#report-to').value;
      
      if (!from || !to) {
        alert('Please select both start and end dates');
        return;
      }
      
      // Get revenue report
      const res = await fetch(`/api/admin/reports/revenue?from=${from}&to=${to}`);
      const data = await res.json();
      
      qs('#report-revenue').textContent = formatINR(data.total_revenue || 0);
      
      // Calculate total orders and avg order value
      const totalOrders = data.monthly_data?.reduce((sum, item) => sum + (item.order_count || 0), 0) || 0;
      const avgOrderValue = totalOrders > 0 ? (data.total_revenue || 0) / totalOrders : 0;
      qs('#report-orders-count').textContent = totalOrders;
      qs('#report-avg-order').textContent = formatINR(avgOrderValue);
      
      // Update monthly trend chart
      if (data.monthly_data) {
        renderReportChart(data.monthly_data);
      }
      
      // Get sales by category
      const resCategory = await fetch(`/api/admin/reports/sales-by-category?from=${from}&to=${to}`);
      const categoryData = await resCategory.json();
      if (categoryData.success) {
        renderReportCategoryChart(categoryData.data || []);
      }
      
      // Get daily sales
      const resDaily = await fetch(`/api/admin/reports/daily-sales?days=30`);
      const dailyData = await resDaily.json();
      if (dailyData.success) {
        renderDailySalesChart(dailyData.sales || []);
      }
      
      // Get top customers for period
      const resTopCustomers = await fetch(`/api/admin/customers/top?limit=5`);
      const topCustomers = await resTopCustomers.json();
      if (topCustomers.success) {
        renderReportTopCustomers(topCustomers.customers);
      }
      
    } catch(err){ 
      console.error('Report error', err);
      alert('Error generating report: ' + err.message);
    }
  }
  
  function renderReportCategoryChart(data) {
    const ctx = qs('#report-category-chart');
    if (!ctx) return;
    
    if (window.reportCategoryChart) {
      window.reportCategoryChart.destroy();
    }
    
    if (!data || data.length === 0) {
      ctx.getContext('2d').clearRect(0, 0, ctx.width, ctx.height);
      return;
    }
    
    const labels = data.map(item => item.category || 'Unknown');
    const values = data.map(item => parseFloat(item.revenue || item.total_revenue || 0));
    
    window.reportCategoryChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Revenue by Category',
          data: values,
          backgroundColor: 'rgba(34, 197, 94, 0.8)',
          borderColor: '#22c55e',
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              callback: function(value) {
                return '₹' + value.toLocaleString();
              }
            }
          }
        }
      }
    });
  }
  
  function renderDailySalesChart(data) {
    const ctx = qs('#report-daily-chart');
    if (!ctx) return;
    
    if (window.dailySalesChart) {
      window.dailySalesChart.destroy();
    }
    
    if (!data || data.length === 0) {
      ctx.getContext('2d').clearRect(0, 0, ctx.width, ctx.height);
      return;
    }
    
    // Get last 30 days
    const last30Days = data.slice(0, 30).reverse();
    const labels = last30Days.map(item => {
      const date = new Date(item.date);
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });
    const revenue = last30Days.map(item => parseFloat(item.revenue || 0));
    const orders = last30Days.map(item => parseInt(item.order_count || 0));
    
    window.dailySalesChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: 'Revenue',
          data: revenue,
          borderColor: '#22c55e',
          backgroundColor: 'rgba(34, 197, 94, 0.1)',
          yAxisID: 'y',
          tension: 0.4
        }, {
          label: 'Orders',
          data: orders,
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          yAxisID: 'y1',
          tension: 0.4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            position: 'top'
          }
        },
        scales: {
          y: {
            type: 'linear',
            display: true,
            position: 'left',
            beginAtZero: true,
            ticks: {
              callback: function(value) {
                return '₹' + value.toLocaleString();
              }
            }
          },
          y1: {
            type: 'linear',
            display: true,
            position: 'right',
            beginAtZero: true,
            grid: {
              drawOnChartArea: false
            }
          }
        }
      }
    });
  }
  
  function renderReportTopCustomers(customers) {
    const container = qs('#report-top-customers');
    if (!container) return;
    container.innerHTML = '';
    
    if (!customers || customers.length === 0) {
      container.innerHTML = '<div class="text-center text-gray-500">No customer data</div>';
      return;
    }
    
    customers.forEach((customer, index) => {
      const li = document.createElement('li');
      li.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div>
            <strong>${index + 1}. ${customer.name}</strong>
            <div style="font-size: 0.85em; color: #666;">${customer.total_orders || 0} orders</div>
          </div>
          <div style="text-align: right;">
            <div style="font-weight: bold; color: #22c55e;">${formatINR(customer.total_spent || 0)}</div>
            <div style="font-size: 0.85em; color: #666;">Avg: ${formatINR(customer.avg_order_value || 0)}</div>
          </div>
        </div>
      `;
      container.appendChild(li);
    });
  }
  
  function renderReportChart(data) {
    const ctx = qs('#report-chart');
    if (!ctx) return;
    
    if (window.reportChart) {
      window.reportChart.destroy();
    }
    
    const labels = data.map(item => item.month);
    const values = data.map(item => parseFloat(item.total) || 0);
    
    window.reportChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Revenue',
          data: values,
          backgroundColor: 'rgba(34, 197, 94, 0.8)',
          borderColor: '#22c55e',
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              callback: function(value) {
                return '₹' + value.toLocaleString();
              }
            }
          }
        }
      }
    });
  }

  window.printBillForOrder = function(o){
    // Open PDF in new window for printing
    const pdfUrl = `/api/admin/bills/${o.order_id}/pdf`;
    window.open(pdfUrl, '_blank');
  }
  
  // Customer History Modal
  function showCustomerHistory(customer, orders) {
    const modal = document.createElement('dialog');
    modal.className = 'modal';
    modal.innerHTML = `
      <div class="card" style="max-width: 800px; max-height: 80vh; overflow-y: auto;">
        <div class="card-title">Purchase History - ${customer.name}</div>
        <div class="mt-2">
          ${orders.length === 0 ? '<p>No orders found.</p>' : `
            <table class="table">
              <thead>
                <tr><th>Order ID</th><th>Date</th><th>Items</th><th>Total</th><th>Status</th></tr>
              </thead>
              <tbody>
                ${orders.map(o => `
                  <tr>
                    <td>#${o.order_id}</td>
                    <td>${o.formatted_date || o.order_date}</td>
                    <td>${o.items ? o.items.length : 0} item(s)</td>
                    <td>${formatINR(o.total_amount)}</td>
                    <td>${o.status}</td>
                  </tr>
                `).join('')}
              </tbody>
            </table>
          `}
        </div>
        <menu class="modal-actions">
          <button class="btn ghost" onclick="this.closest('dialog').close()">Close</button>
        </menu>
      </div>
    `;
    document.body.appendChild(modal);
    modal.showModal();
    modal.addEventListener('click', (e) => {
      if (e.target === modal) modal.close();
    });
  }
  
  // Add event listeners for reports
  qs('#btn-run-report')?.addEventListener('click', runReport);

  // ---------- Chart Rendering Functions ----------
  function renderForecastChart(data) {
    const ctx = qs('#forecast-chart');
    if (!ctx) return;
    
    if (window.forecastChart) {
      window.forecastChart.destroy();
    }
    
    // Handle empty data
    if (!data || data.length === 0) {
      ctx.getContext('2d').clearRect(0, 0, ctx.width, ctx.height);
      return;
    }
    
    const labels = data.map(item => item.month);
    const revenue = data.map(item => parseFloat(item.revenue) || 0);
    const orders = data.map(item => parseInt(item.orders) || 0);
    
    window.forecastChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: 'Revenue',
          data: revenue,
          borderColor: '#22c55e',
          backgroundColor: 'rgba(34, 197, 94, 0.1)',
          yAxisID: 'y',
          tension: 0.4,
          fill: true
        }, {
          label: 'Orders',
          data: orders,
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          yAxisID: 'y1',
          tension: 0.4,
          fill: true
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        aspectRatio: 2,
        plugins: {
          legend: {
            display: true,
            position: 'top'
          }
        },
        scales: {
          y: {
            type: 'linear',
            display: true,
            position: 'left',
            beginAtZero: true,
            ticks: {
              callback: function(value) {
                return '₹' + value.toLocaleString();
              }
            },
            grid: {
              color: 'rgba(0, 0, 0, 0.1)'
            }
          },
          y1: {
            type: 'linear',
            display: true,
            position: 'right',
            beginAtZero: true,
            grid: {
              drawOnChartArea: false,
            },
          },
          x: {
            grid: {
              display: false
            }
          }
        },
        elements: {
          point: {
            radius: 4,
            hoverRadius: 6
          }
        }
      }
    });
  }

  function renderBehaviorChart(data) {
    const ctx = qs('#behavior-chart');
    if (!ctx) return;
    
    if (window.behaviorChart) {
      window.behaviorChart.destroy();
    }
    
    // Handle empty data
    if (!data || data.length === 0) {
      ctx.getContext('2d').clearRect(0, 0, ctx.width, ctx.height);
      return;
    }
    
    const labels = data.map(item => item.segment);
    const avgOrders = data.map(item => parseFloat(item.avg_orders) || 0);
    const avgValue = data.map(item => parseFloat(item.avg_order_value) || 0);
    
    window.behaviorChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Avg Orders',
          data: avgOrders,
          backgroundColor: 'rgba(34, 197, 94, 0.8)',
          borderColor: '#22c55e',
          borderWidth: 1
        }, {
          label: 'Avg Order Value',
          data: avgValue,
          backgroundColor: 'rgba(59, 130, 246, 0.8)',
          borderColor: '#3b82f6',
          borderWidth: 1
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        aspectRatio: 2,
        plugins: {
          legend: {
            display: true,
            position: 'top'
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            grid: {
              color: 'rgba(0, 0, 0, 0.1)'
            },
            ticks: {
              callback: function(value) {
                return '₹' + value.toLocaleString();
              }
            }
          },
          x: {
            grid: {
              display: false
            }
          }
        }
      }
    });
  }

  function renderCustomerSegments(segments) {
    const container = qs('#customer-segments');
    container.innerHTML = '';
    
    segments.forEach(segment => {
      const div = document.createElement('div');
      div.className = 'segment-item';
      div.innerHTML = `
        <div>
          <strong>${segment.segment}</strong>
          <div>${segment.count} customers</div>
        </div>
        <div>Avg Value: ${formatINR(segment.avg_value)}</div>
      `;
      container.appendChild(div);
    });
  }

  async function renderProductPerformance() {
    try {
      const res = await fetch('/api/admin/products');
      const products = await res.json();
      const container = qs('#product-performance');
      container.innerHTML = '';
      
      // Sort by total_sold
      products.sort((a, b) => (b.total_sold || 0) - (a.total_sold || 0));
      
      products.slice(0, 10).forEach(product => {
        const div = document.createElement('div');
        div.className = 'performance-item';
        div.innerHTML = `
          <div>
            <strong>${product.name}</strong>
            <div>Views: ${product.views || 0}</div>
          </div>
          <div>Sold: ${product.total_sold || 0}</div>
        `;
        container.appendChild(div);
      });
    } catch(err){ console.error('Product performance error', err); }
  }


  // ---------- Bulk Actions Modal ----------
  function showBulkActionsModal() {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
      <div class="card" style="max-width: 500px;">
        <div class="card-title">Bulk Actions</div>
        <div class="grid-2">
          <button class="btn" onclick="bulkUpdateStock()">Update Stock</button>
          <button class="btn" onclick="bulkDeleteProducts()">Delete Products</button>
          <button class="btn" onclick="bulkUpdateOrderStatus()">Update Order Status</button>
          <button class="btn" onclick="bulkExportData()">Export Data</button>
        </div>
        <menu class="modal-actions">
          <button class="btn ghost" onclick="this.closest('.modal').remove()">Close</button>
        </menu>
      </div>
    `;
    document.body.appendChild(modal);
    modal.showModal();
  }

  window.bulkUpdateStock = async function() {
    const newStock = prompt('Enter new stock quantity for all products:');
    if (!newStock || isNaN(newStock)) return;
    
    try {
      const res = await fetch('/api/admin/products');
      const products = await res.json();
      const updates = products.map(p => ({product_id: p.product_id, stock: parseInt(newStock)}));
      
      const response = await fetch('/api/admin/bulk/products/update-stock', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({updates})
      });
      
      const result = await response.json();
      if (result.success) {
        alert(`Updated stock for ${result.updated_count} products!`);
        renderProducts();
      }
    } catch(err) { console.error('Bulk update stock error', err); }
  };

  window.bulkDeleteProducts = async function() {
    if (!confirm('Delete ALL products? This cannot be undone!')) return;
    
    try {
      const res = await fetch('/api/admin/products');
      const products = await res.json();
      const productIds = products.map(p => p.product_id);
      
      const response = await fetch('/api/admin/bulk/products/delete', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({product_ids: productIds})
      });
      
      const result = await response.json();
      if (result.success) {
        alert(`Deleted ${result.deleted_count} products!`);
        renderProducts();
      }
    } catch(err) { console.error('Bulk delete error', err); }
  };

  window.bulkUpdateOrderStatus = async function() {
    const status = prompt('Enter new status (Pending/Shipped/Delivered/Cancelled):');
    if (!status) return;
    
    try {
      const res = await fetch('/api/admin/orders');
      const orders = await res.json();
      const orderIds = orders.map(o => o.order_id);
      
      const response = await fetch('/api/admin/bulk/orders/update-status', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({order_ids: orderIds, status})
      });
      
      const result = await response.json();
      if (result.success) {
        alert(`Updated ${result.updated_count} orders to ${status}!`);
        renderOrders();
      }
    } catch(err) { console.error('Bulk update orders error', err); }
  };

  window.bulkExportData = async function() {
    try {
      const res = await fetch('/api/admin/export/orders');
      const orders = await res.json();
      
      const csvContent = [
        ['Order ID', 'Date', 'Customer', 'Status', 'Amount'].join(','),
        ...orders.map(order => [
          order.order_id,
          order.date,
          order.customer_name,
          order.status,
          order.total_amount
        ].join(','))
      ].join('\n');
      
      const blob = new Blob([csvContent], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'bulk_export.csv';
      a.click();
      window.URL.revokeObjectURL(url);
    } catch(err) { console.error('Bulk export error', err); }
  };

  // ---------- Global Functions ----------
  window.updateReturnStatus = async function(returnId, status) {
    try {
      await fetch(`/api/admin/returns/${returnId}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({status: status})
      });
      renderReturns();
    } catch(err){ console.error('Update return status error', err); }
  };

  // ---------- Global search ----------
  qs('#global-search').addEventListener('input', (e)=>{
    const q = e.target.value.toLowerCase();
    if(!qs('#view-products').classList.contains('hidden')){
      productSearch.value = q; drawProductRows();
    }
  });

  // ---------- Init ----------
  async function renderAll(){
    await drawDashboard();
    await renderProducts();
    await renderOrders();
    await renderCustomers();
    await renderSellers();
    await renderReports();
    await renderBills();
  }

  // Ready
  gate();
})();
