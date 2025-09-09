class PODetailApp {
    constructor() {
        this.poId = this.extractIdFromURL();
        this.init();
    }

    extractIdFromURL() {
        const parts = window.location.pathname.split('/');
        return decodeURIComponent(parts[parts.length - 1] || '');
    }

    async init() {
        await this.loadDetail();
    }

    async loadDetail() {
        try {
            const res = await fetch(`/api/purchase-orders/${encodeURIComponent(this.poId)}`);
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Failed to load PO');
            this.render(data);
        } catch (e) {
            this.toast(e.message, 'error');
        }
    }

    render(po) {
        document.getElementById('poTitle').textContent = `${po.po_id}`;
        const meta = document.getElementById('poMeta');
        
        // Format dates nicely
        const formatDate = (dateStr) => {
            if (!dateStr) return '-';
            const date = new Date(dateStr);
            return date.toLocaleDateString();
        };
        
        meta.innerHTML = `
            <div class="po-summary-meta">
                <div class="meta"><strong>PO Number</strong><div>${this.escape(po.po_number || po.po_id)}</div></div>
                <div class="meta"><strong>Supplier</strong><div>${this.escape(po.supplier_name || '')}</div></div>
                <div class="meta"><strong>Status</strong><div><span class="status-badge">${this.escape(po.status || 'Unknown')}</span></div></div>
                <div class="meta"><strong>Created</strong><div>${formatDate(po.created_at)}</div></div>
                <div class="meta"><strong>Created By</strong><div>${this.escape(po.created_by || '-')}</div></div>
                <div class="meta"><strong>Requested Delivery</strong><div>${formatDate(po.requested_delivery_date)}</div></div>
                <div class="meta"><strong>Total Amount</strong><div>$${Number(po.total_amount || 0).toFixed(2)}</div></div>
            </div>
            <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--border-light);">
                <h3 style="margin-bottom: 8px; font-size: 1.1rem;">Notes</h3>
                <div>${this.escape(po.notes || '-')}</div>
            </div>
        `;

        const linesBody = document.getElementById('poLinesBody');
        // Use 'items' instead of 'lines' for the new database structure
        const items = po.items || po.lines || [];
        linesBody.innerHTML = items.map(item => `
            <tr>
                <td>${this.escape(item.med_name || String(item.med_id))}</td>
                <td>${item.quantity}</td>
                <td>$${Number(item.unit_price || 0).toFixed(2)}</td>
                <td>$${Number(item.total_price || (item.unit_price * item.quantity) || 0).toFixed(2)}</td>
            </tr>
        `).join('');
        
        // Show message if no items
        if (items.length === 0) {
            linesBody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--text-secondary);">No items in this purchase order</td></tr>';
        }
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

document.addEventListener('DOMContentLoaded', () => new PODetailApp()); 