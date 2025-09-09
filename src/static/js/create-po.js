class CreatePOApp {
    constructor() {
        this.selectedMedIds = [];
        this.meds = {};
        this.suppliers = [];
        this.itemsState = []; // [{ med_id, total_quantity, allocations: [{ supplier_id, quantity, unit_price }] }]
        this.init();
    }

    async init() {
        // Check if coming from AI generation
        const urlParams = new URLSearchParams(window.location.search);
        const isAI = urlParams.get('ai') === 'true';

        if (isAI && sessionStorage.getItem('aiPOResult')) {
            await this.loadFromAIResult();
        } else {
            this.loadSelectionFromSession();
        }

        await this.loadSuppliers();
        await this.loadMedDetails();
        this.buildForm();
        this.setupEvents();

        // Show AI badge if AI generated
        if (isAI) {
            this.showAIBadge();
        }
    }

    loadSelectionFromSession() {
        try {
            const ids = JSON.parse(sessionStorage.getItem('poSelectedMedicationIds') || '[]');
            this.selectedMedIds = Array.isArray(ids) ? ids : [];
        } catch {
            this.selectedMedIds = [];
        }
    }

    async loadSuppliers() {
        const res = await fetch('/api/suppliers');
        const data = await res.json();
        this.suppliers = data.suppliers || [];
    }

    async loadMedDetails() {
        const requests = this.selectedMedIds.map(id => fetch(`/api/medication/${id}`).then(r => r.json()));
        const results = await Promise.all(requests);
        results.forEach((detail, idx) => {
            const id = this.selectedMedIds[idx];
            if (detail) {
                this.meds[id] = detail;
            }
        });
    }

    setupEvents() {
        const cancel = document.getElementById('cancelCreateBtn');
        if (cancel) cancel.addEventListener('click', () => window.location.href = '/');

        const review = document.getElementById('reviewOrderBtn');
        if (review) review.addEventListener('click', () => this.handleReview());

        const back = document.getElementById('backToEditBtn');
        if (back) back.addEventListener('click', () => this.toggleReview(false));

        const submit = document.getElementById('submitOrderBtn');
        if (submit) submit.addEventListener('click', () => this.handleSubmit());

        const addDefaults = document.getElementById('addAllDefaultSuppliersBtn');
        if (addDefaults) addDefaults.addEventListener('click', () => this.addDefaultSuppliers());
    }

    buildForm() {
        const container = document.getElementById('poItemsContainer');
        container.innerHTML = '';
        this.itemsState = [];

        const medsToRender = this.selectedMedIds.length > 0 ? this.selectedMedIds : Object.keys(this.meds).map(Number);
        medsToRender.forEach(med_id => {
            const detail = this.meds[med_id];
            if (!detail) return;

            const itemState = { med_id, total_quantity: 0, allocations: [] };
            this.itemsState.push(itemState);

            const el = document.createElement('div');
            el.className = 'po-item';
            el.dataset.medId = med_id;
            el.innerHTML = `
                <div class="po-item-header">
                    <div>
                        <strong>${this.escape(detail.name)}</strong>
                        <div class="text-muted">Pack size: ${detail.pack_size || '-'} • Category: ${this.escape(detail.category || '')}</div>
                    </div>
                    <div class="text-muted">Quantity sums from splits</div>
                </div>
                <div class="po-allocations"></div>
                <div class="allocation-actions">
                    <button class="btn btn-secondary add-allocation">Add Supplier Split</button>
                </div>
            `;

            const allocationsContainer = el.querySelector('.po-allocations');
            el.querySelector('.add-allocation').addEventListener('click', () => {
                this.addAllocationRow(allocationsContainer, itemState);
                this.renderLiveSummary();
            });

            container.appendChild(el);
        });
        this.renderLiveSummary();
    }

    async fetchPricesForMed(med_id) {
        try {
            const res = await fetch(`/api/medications/${med_id}/supplier-prices`);
            const data = await res.json();
            return data.prices || [];
        } catch { return []; }
    }

    async addAllocationRow(container, itemState, preselectSupplierId = null) {
        const row = document.createElement('div');
        row.className = 'allocation-row';
        row.innerHTML = `
            <select class="supplier-select"></select>
            <input type="number" min="0" class="alloc-qty" placeholder="Quantity" />
            <input type="number" min="0" step="0.01" class="alloc-price" placeholder="Unit Price" disabled />
            <span class="supplier-info"></span>
            <button class="btn btn-link remove">Remove</button>
        `;
        container.appendChild(row);

        const supplierSelect = row.querySelector('.supplier-select');
        const supplierInfo = row.querySelector('.supplier-info');

        // Create options with supplier details
        supplierSelect.innerHTML = '<option value="">Select supplier</option>' +
            this.suppliers.map(s => {
                return `<option value="${s.supplier_id}" data-lead-time="${s.avg_lead_time}" data-status="${s.status}">
                    ${this.escape(s.name)} (${s.avg_lead_time}d lead time)
                </option>`;
            }).join('');
        if (preselectSupplierId) supplierSelect.value = String(preselectSupplierId);

        const allocation = { supplier_id: preselectSupplierId || null, quantity: 0, unit_price: 0 };
        itemState.allocations.push(allocation);

        const prices = await this.fetchPricesForMed(itemState.med_id);
        const priceDataBySupplier = Object.fromEntries(prices.map(p => [String(p.supplier_id), p]));

        const updateTotal = () => {
            itemState.total_quantity = itemState.allocations.reduce((s, a) => s + (a.quantity || 0), 0);
            this.renderLiveSummary();
        };

        const setPriceForSupplier = (sid) => {
            const priceData = priceDataBySupplier[String(sid)];
            let price = priceData?.price_per_unit;

            // Update supplier info display (remove emojis)
            if (priceData) {
                const leadTime = priceData.avg_lead_time || 0;
                const status = priceData.supplier_status || 'Unknown';
                const statusColor = status === 'OK' ? 'green' : (status === 'Shortage' ? 'orange' : 'gray');
                supplierInfo.innerHTML = `
                    <span style="color: ${statusColor}; margin-left: 10px;">
                        ${status} | Lead: ${leadTime.toFixed(1)}d
                    </span>
                `;
            } else {
                supplierInfo.innerHTML = '';
            }

            // Fallback to base med price if supplier-specific price missing
            if (price == null) {
                const medPrice = this.meds[itemState.med_id]?.price?.price_per_unit;
                price = (medPrice != null) ? Number(medPrice) : 0;
            }
            allocation.unit_price = Number(price || 0);
            row.querySelector('.alloc-price').value = allocation.unit_price ? allocation.unit_price.toFixed(2) : '';
        };

        supplierSelect.addEventListener('change', (e) => {
            allocation.supplier_id = e.target.value ? parseInt(e.target.value) : null;

            // Store supplier details for later use
            const selectedOption = e.target.selectedOptions[0];
            if (selectedOption && allocation.supplier_id) {
                allocation.lead_time = parseFloat(selectedOption.dataset.leadTime || 0);
                allocation.supplier_status = selectedOption.dataset.status || 'Unknown';
            }

            setPriceForSupplier(allocation.supplier_id);
            updateTotal();
        });
        row.querySelector('.alloc-qty').addEventListener('input', (e) => {
            allocation.quantity = parseInt(e.target.value || '0');
            updateTotal();
        });
        row.querySelector('.remove').addEventListener('click', (e) => {
            e.preventDefault();
            container.removeChild(row);
            const idx = itemState.allocations.indexOf(allocation);
            if (idx >= 0) itemState.allocations.splice(idx, 1);
            updateTotal();
        });

        // Initialize price if preselected
        if (preselectSupplierId) setPriceForSupplier(preselectSupplierId);
    }

    handleReview() {
        // Basic validation and totals
        for (const item of this.itemsState) {
            const sumAlloc = item.allocations.reduce((s, a) => s + (a.quantity || 0), 0);
            if (sumAlloc !== (item.total_quantity || 0)) {
                this.toast('Allocation quantities must sum to total quantity', 'error');
                return;
            }
            for (const a of item.allocations) {
                if (!a.supplier_id) { this.toast('Each allocation must have a supplier', 'error'); return; }
            }
        }
        this.renderReview();
        this.toggleReview(true);
    }

    renderReview() {
        const summary = document.getElementById('poReviewSummary');
        const meta = this.getMeta();

        const groups = this.groupBySupplier(this.itemsState);
        const sections = Object.entries(groups).map(([supplier_id, lines]) => {
            const supplier = this.suppliers.find(s => s.supplier_id === parseInt(supplier_id));
            const supplierName = supplier ? supplier.name : `Supplier ${supplier_id}`;
            const total = lines.reduce((sum, l) => sum + l.unit_price * l.quantity, 0);
            const avgLeadTime = supplier ? supplier.avg_lead_time : 0;
            const supplierStatus = supplier ? supplier.status : 'Unknown';
            const statusColor = supplierStatus === 'OK' ? 'green' : (supplierStatus === 'Shortage' ? 'orange' : 'gray');

            // Calculate estimated delivery date based on lead time
            const requestedDate = meta.requested_delivery_date ? new Date(meta.requested_delivery_date) : new Date();
            const estimatedDelivery = new Date(requestedDate);
            estimatedDelivery.setDate(estimatedDelivery.getDate() + Math.ceil(avgLeadTime || 7));

            return `
                <div class="po-summary">
                    <div class="po-summary-meta">
                        <div class="meta"><strong>Supplier</strong><div>${this.escape(supplierName)}</div></div>
                        <div class="meta"><strong>Status</strong><div><span class="status-badge" style="background: ${statusColor}">${supplierStatus}</span></div></div>
                        <div class="meta"><strong>Lead Time</strong><div>${avgLeadTime ? avgLeadTime.toFixed(1) : '-'} days</div></div>
                        <div class="meta"><strong>Est. Delivery</strong><div>${estimatedDelivery.toLocaleDateString()}</div></div>
                    </div>
                    <div class="po-summary-lines">
                        <table class="po-table po-review-table">
                            <thead><tr><th>Medication</th><th>Quantity</th><th>Unit Price</th><th>Amount</th></tr></thead>
                            <tbody>
                                ${lines.map(l => `<tr>
                                    <td>${this.escape(this.meds[l.med_id]?.name || String(l.med_id))}</td>
                                    <td>${l.quantity}</td>
                                    <td>${l.unit_price.toFixed(2)}</td>
                                    <td>${(l.unit_price * l.quantity).toFixed(2)}</td>
                                </tr>`).join('')}
                            </tbody>
                            <tfoot>
                                <tr><td colspan="3" style="text-align:right"><strong>Total</strong></td><td><strong>${total.toFixed(2)}</strong></td></tr>
                            </tfoot>
                        </table>
                    </div>
                </div>
            `;
        }).join('');

        summary.innerHTML = `
            <div style="margin-bottom: 16px;">
                <h3 style="margin-bottom: 12px;">Order Summary</h3>
                <div class="po-summary-meta">
                    <div class="meta"><strong>Buyer</strong><div>${this.escape(meta.buyer || '-')}</div></div>
                    <div class="meta"><strong>Notes</strong><div>${this.escape(meta.notes || '-')}</div></div>
                </div>
            </div>
            ${sections}
        `;
    }

    getMeta() {
        return {
            requested_delivery_date: document.getElementById('requestedDeliveryDate')?.value || '',
            buyer: document.getElementById('buyerName')?.value || '',
            notes: document.getElementById('poNotes')?.value || ''
        };
    }

    toggleReview(isReview) {
        const edit = document.getElementById('poEditContainer');
        if (edit) edit.style.display = isReview ? 'none' : '';
        document.getElementById('poReviewSection').style.display = isReview ? '' : 'none';
        this.updateStepper(isReview ? 3 : 2);
    }

    groupBySupplier(items) {
        const result = {};
        items.forEach(item => {
            item.allocations.forEach(a => {
                const key = String(a.supplier_id);
                result[key] = result[key] || [];
                result[key].push({
                    med_id: item.med_id,
                    quantity: a.quantity,
                    unit_price: a.unit_price
                });
            });
        });
        return result;
    }

    async handleSubmit() {
        const meta = this.getMeta();
        const payload = {
            items: this.itemsState,
            meta
        };

        // Show sending overlay
        const overlay = document.createElement('div');
        overlay.id = 'emailOverlay';
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.45);display:flex;align-items:center;justify-content:center;z-index:9999;';
        overlay.innerHTML = `
            <div style="background:#111827;color:#e5e7eb;padding:20px 24px;border-radius:10px;min-width:280px;text-align:center;box-shadow:0 10px 30px rgba(0,0,0,0.35);">
                <div style="font-weight:700;margin-bottom:6px;">Preparing Supplier Emails</div>
                <div style="font-size:13px;color:#9ca3af;">Drafting and sending purchase request…</div>
            </div>
        `;
        document.body.appendChild(overlay);

        try {
            // Pre-send supplier emails (non-blocking for UX, but awaited here)
            const emailRes = await fetch('/api/purchase-orders/send-emails', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const emailData = await emailRes.json().catch(() => ({}));
            if (!emailRes.ok) {
                // Log but proceed with submission
                console.warn('Email send failed:', emailData);
            }
        } catch (e) {
            console.warn('Email step error:', e);
        } finally {
            // Hide overlay
            const el = document.getElementById('emailOverlay');
            if (el) el.remove();
        }

        // Now submit the PO(s)
        try {
            const res = await fetch('/api/purchase-orders', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Failed to submit');
            this.toast('Purchase order submitted');
            window.location.href = '/purchase-orders';
        } catch (e) {
            this.toast(e.message, 'error');
        }
    }

    toast(message, type = 'info') {
        if (window.app && window.app.showToast) return window.app.showToast(message, type);
        const el = document.getElementById('toastContainer');
        const div = document.createElement('div');
        div.className = `toast ${type}`;
        div.textContent = message;
        el.appendChild(div);
        setTimeout(() => div.remove(), 4000);
    }

    escape(text) { return (text ?? '').toString().replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', '\'': '&#039;' }[c])); }

    renderLiveSummary() {
        const container = document.getElementById('liveSummaryContainer');
        if (!container) return;

        const groups = this.groupBySupplier(this.itemsState);
        const supplierCount = Object.keys(groups).length;
        let grandTotal = 0;
        let totalUnits = 0;
        let totalItems = 0;

        // Generate supplier blocks with medication details
        const supplierBlocks = Object.entries(groups).map(([supplier_id, lines]) => {
            const supplier = this.suppliers.find(s => s.supplier_id === parseInt(supplier_id));
            const supplierName = supplier ? supplier.name : `Supplier ${supplier_id}`;

            // Filter out items with zero quantity
            const validLines = lines.filter(l => l.quantity > 0);
            if (validLines.length === 0) return '';

            const subtotal = validLines.reduce((s, l) => s + (Number(l.unit_price || 0) * Number(l.quantity || 0)), 0);
            const unitsCount = validLines.reduce((s, l) => s + Number(l.quantity || 0), 0);

            grandTotal += subtotal;
            totalUnits += unitsCount;
            totalItems += validLines.length;

            // Build medication list for this supplier
            const medicationLines = validLines.map(line => {
                const med = this.meds[line.med_id];
                const medName = med ? med.name : `Item ${line.med_id}`;
                const lineTotal = Number(line.unit_price || 0) * Number(line.quantity || 0);

                return `
                    <div class="summary-med-line">
                        <div class="med-name">${this.escape(medName)}</div>
                        <div class="med-details">
                            <span class="qty">${line.quantity} units</span>
                            <span class="price">@ $${Number(line.unit_price || 0).toFixed(2)}</span>
                            <span class="line-total">$${lineTotal.toFixed(2)}</span>
                        </div>
                    </div>
                `;
            }).join('');

            return `
                <div class="summary-supplier-block">
                    <div class="supplier-header">
                        <span class="supplier-name">${this.escape(supplierName)}</span>
                        <span class="item-count">${validLines.length} ${validLines.length === 1 ? 'item' : 'items'}</span>
                    </div>
                    <div class="supplier-meds">
                        ${medicationLines}
                    </div>
                    <div class="supplier-subtotal">
                        <span>Subtotal</span>
                        <span class="amount">$${subtotal.toFixed(2)}</span>
                    </div>
                </div>
            `;
        }).filter(block => block !== '').join('');

        // Build the complete summary
        let summaryHTML = '';

        if (supplierBlocks) {
            // Add summary stats at the top
            summaryHTML = `
                <div class="summary-stats">
                    <div class="stat-line">
                        <span class="stat-label">Suppliers:</span>
                        <span class="stat-value">${supplierCount}</span>
                    </div>
                    <div class="stat-line">
                        <span class="stat-label">Total Items:</span>
                        <span class="stat-value">${totalItems}</span>
                    </div>
                    <div class="stat-line">
                        <span class="stat-label">Total Units:</span>
                        <span class="stat-value">${totalUnits}</span>
                    </div>
                </div>
                ${supplierBlocks}
                <div class="summary-grand-total">
                    <span class="total-label">Grand Total</span>
                    <span class="total-amount">$${grandTotal.toFixed(2)}</span>
                </div>
            `;
        } else {
            summaryHTML = '<div class="summary-empty">No items added yet</div>';
        }

        container.innerHTML = summaryHTML;
    }

    updateStepper(stepIndex) {
        const steps = document.querySelectorAll('#poStepper .step');
        steps.forEach((el, idx) => {
            el.classList.toggle('active', (idx + 1) === stepIndex);
        });
    }

    addDefaultSuppliers() {
        document.querySelectorAll('.po-item').forEach(async itemEl => {
            const med_id = parseInt(itemEl.dataset.medId);
            const itemState = this.itemsState.find(i => i.med_id === med_id);
            const allocationsContainer = itemEl.querySelector('.po-allocations');
            const med = this.meds[med_id];
            const defaultSupplierId = med?.supplier?.supplier_id || med?.supplier_id || null;
            if (defaultSupplierId && !itemState.allocations.some(a => a.supplier_id === defaultSupplierId)) {
                await this.addAllocationRow(allocationsContainer, itemState, defaultSupplierId);
                this.renderLiveSummary();
            }
        });
    }

    async loadFromAIResult() {
        try {
            const aiResult = JSON.parse(sessionStorage.getItem('aiPOResult'));
            if (!aiResult || !aiResult.po_items) return;

            // Extract unique medication IDs
            const medIds = [...new Set(aiResult.po_items.map(item => item.med_id))];
            this.selectedMedIds = medIds;

            // Store AI result for later use
            this.aiResult = aiResult;

            // Store AI allocations to apply after form build
            this.aiAllocations = {};
            aiResult.po_items.forEach(item => {
                if (!this.aiAllocations[item.med_id]) {
                    this.aiAllocations[item.med_id] = [];
                }
                this.aiAllocations[item.med_id].push({
                    supplier_id: item.supplier_id,
                    quantity: item.quantity,
                    unit_price: item.unit_price
                });
            });

        } catch (e) {
            console.error('Failed to load AI result:', e);
            this.loadSelectionFromSession();
        }
    }

    showAIBadge() {
        const header = document.querySelector('.content-header h2') || document.querySelector('.page-header h2');
        if (header && !document.querySelector('.ai-badge-header')) {
            const badge = document.createElement('span');
            badge.className = 'ai-badge-header';
            badge.innerHTML = 'AI Generated';
            badge.style.cssText = '';
            header.appendChild(badge);
        }

        // Show AI reasoning if available
        if (this.aiResult && this.aiResult.reasoning) {
            this.showAIReasoning();
        }
    }

    showAIReasoning() {
        const container = document.getElementById('poEditContainer');
        if (!container) return;

        const reasoningDiv = document.createElement('div');
        reasoningDiv.className = 'ai-reasoning-panel card-section';
        reasoningDiv.style.cssText = '';

        let reasoningHTML = '<div class="section-header"><h3>AI Agent Reasoning</h3></div>';

        for (const [agent, data] of Object.entries(this.aiResult.reasoning)) {
            const agentName = agent.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            const decisions = (data.decision_points || []).map(p => `<li>${this.escape(p)}</li>`).join('');
            reasoningHTML += `
                <details class="ai-reasoning-item" open>
                    <summary class="ai-reasoning-summary">${agentName} <span class="confidence">${(Number(data.confidence) * 100).toFixed(0)}% confidence</span></summary>
                    <div class="ai-reasoning-content">
                        ${data.summary ? `<p>${this.escape(data.summary)}</p>` : ''}
                        ${decisions ? `<ul>${decisions}</ul>` : ''}
                    </div>
                </details>
            `;
        }

        reasoningDiv.innerHTML = reasoningHTML;
        const leftColumn = container.querySelector('.po-left') || container;
        leftColumn.insertBefore(reasoningDiv, leftColumn.firstChild);
    }

    buildForm() {
        const container = document.getElementById('poItemsContainer');
        container.innerHTML = '';
        this.itemsState = [];

        const medsToRender = this.selectedMedIds.length > 0 ? this.selectedMedIds : Object.keys(this.meds).map(Number);
        medsToRender.forEach(med_id => {
            const detail = this.meds[med_id];
            if (!detail) return;

            const itemState = { med_id, total_quantity: 0, allocations: [] };
            this.itemsState.push(itemState);

            const el = document.createElement('div');
            el.className = 'po-item';
            el.dataset.medId = med_id;
            el.innerHTML = `
                <div class="po-item-header">
                    <div>
                        <strong>${this.escape(detail.name)}</strong>
                        <div class="text-muted">Pack size: ${detail.pack_size || '-'} • Category: ${this.escape(detail.category || '')}</div>
                    </div>
                    <div class="text-muted">Quantity sums from splits</div>
                </div>
                <div class="po-allocations"></div>
                <div class="allocation-actions">
                    <button class="btn btn-secondary add-allocation">Add Supplier Split</button>
                </div>
            `;

            const allocationsContainer = el.querySelector('.po-allocations');
            el.querySelector('.add-allocation').addEventListener('click', () => {
                this.addAllocationRow(allocationsContainer, itemState);
                this.renderLiveSummary();
            });

            container.appendChild(el);

            // Apply AI allocations if available
            if (this.aiAllocations && this.aiAllocations[med_id]) {
                this.aiAllocations[med_id].forEach(async alloc => {
                    await this.addAllocationRow(allocationsContainer, itemState, alloc.supplier_id);
                    // Set quantity after row is added
                    setTimeout(() => {
                        const rows = allocationsContainer.querySelectorAll('.allocation-row');
                        const lastRow = rows[rows.length - 1];
                        if (lastRow) {
                            const qtyInput = lastRow.querySelector('.alloc-qty');
                            const priceInput = lastRow.querySelector('.alloc-price');
                            if (qtyInput) {
                                qtyInput.value = alloc.quantity;
                                qtyInput.dispatchEvent(new Event('input'));
                            }
                            if (priceInput && alloc.unit_price) {
                                priceInput.value = alloc.unit_price.toFixed(2);
                            }
                        }
                    }, 100);
                });
            }
        });
        this.renderLiveSummary();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new CreatePOApp();
}); 