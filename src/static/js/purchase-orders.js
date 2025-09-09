class PurchaseOrdersApp {
    constructor() {
        this.init();
    }

    async init() {
        await this.loadPOs();
    }

    async loadPOs() {
        try {
            const res = await fetch('/api/purchase-orders');
            const data = await res.json();
            const list = data.purchase_orders || [];
            const body = document.getElementById('poTableBody');
            const empty = document.getElementById('poEmptyState');
            if (list.length === 0) {
                body.innerHTML = '';
                empty.style.display = 'flex';
                return;
            }
            empty.style.display = 'none';
            body.innerHTML = list.map(po => {
                // Format date nicely
                const formatDate = (dateStr) => {
                    if (!dateStr) return '-';
                    const date = new Date(dateStr);
                    return date.toLocaleDateString();
                };
                
                return `
                    <tr>
                        <td>${this.escape(po.po_number || po.po_id)}</td>
                        <td>${this.escape(po.supplier_name || '')}</td>
                        <td>${this.badge(po.status)}</td>
                        <td>${formatDate(po.created_at)}</td>
                        <td style="text-align:right">${po.total_lines || po.item_count || 0}</td>
                        <td style="text-align:right">$${Number(po.total_amount || 0).toFixed(2)}</td>
                        <td style="text-align:center"><a class="btn btn-secondary" href="/purchase-orders/${encodeURIComponent(po.po_id)}">View</a></td>
                    </tr>
                `;
            }).join('');
        } catch (e) {
            this.toast('Failed to load purchase orders', 'error');
        }
    }

    badge(status) {
        return `<span class="status-badge">${this.escape(status || 'Unknown')}</span>`;
    }

    toast(message, type = 'info') {
        const el = document.getElementById('toastContainer');
        const div = document.createElement('div');
        div.className = `toast ${type}`;
        div.textContent = message;
        el.appendChild(div);
        setTimeout(() => div.remove(), 4000);
    }

    escape(text) { return (text ?? '').toString().replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', '\'': '&#039;' }[c])); }
}

document.addEventListener('DOMContentLoaded', () => new PurchaseOrdersApp()); 