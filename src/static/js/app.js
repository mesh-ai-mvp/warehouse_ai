// Main application JavaScript
class InventoryApp {
    constructor() {
        this.currentPage = 1;
        this.pageSize = 20;
        this.totalPages = 0;
        this.totalItems = 0;
        this.selectedItems = new Set();
        this.filters = {
            search: '',
            category: '',
            supplier: '',
            stock_level: ''
        };
        this.filterOptions = {};

        this.init();
    }

    async init() {
        await this.loadFilterOptions();
        this.setupEventListeners();
        await this.loadInventoryData();
    }

    setupEventListeners() {
        // Filter events
        document.getElementById('searchInput').addEventListener('input',
            this.debounce((e) => this.handleFilterChange('search', e.target.value), 300));

        document.getElementById('categoryFilter').addEventListener('change',
            (e) => this.handleFilterChange('category', e.target.value));

        document.getElementById('supplierFilter').addEventListener('change',
            (e) => this.handleFilterChange('supplier', e.target.value));

        document.getElementById('stockLevelFilter').addEventListener('change',
            (e) => this.handleFilterChange('stock_level', e.target.value));

        document.getElementById('clearFilters').addEventListener('click',
            () => this.clearAllFilters());

        // Pagination events
        document.getElementById('pageSize').addEventListener('change',
            (e) => this.changePageSize(parseInt(e.target.value)));

        document.getElementById('firstPage').addEventListener('click',
            () => this.goToPage(1));

        document.getElementById('prevPage').addEventListener('click',
            () => this.goToPage(this.currentPage - 1));

        document.getElementById('nextPage').addEventListener('click',
            () => this.goToPage(this.currentPage + 1));

        document.getElementById('lastPage').addEventListener('click',
            () => this.goToPage(this.totalPages));

        // Selection events
        document.getElementById('selectAll').addEventListener('change',
            (e) => this.handleSelectAll(e.target.checked));

        // Generate PO button
        document.getElementById('generatePoBtn').addEventListener('click',
            () => this.handleGeneratePO());
    }

    async loadFilterOptions() {
        try {
            const response = await fetch('/api/filters');
            this.filterOptions = await response.json();
            this.populateFilterDropdowns();
        } catch (error) {
            console.error('Error loading filter options:', error);
            this.showToast('Failed to load filter options', 'error');
        }
    }

    populateFilterDropdowns() {
        // Populate category filter
        const categoryFilter = document.getElementById('categoryFilter');
        categoryFilter.innerHTML = '<option value="">All Categories</option>';
        this.filterOptions.categories.forEach(category => {
            if (category) {
                const option = document.createElement('option');
                option.value = category;
                option.textContent = category;
                categoryFilter.appendChild(option);
            }
        });

        // Populate supplier filter
        const supplierFilter = document.getElementById('supplierFilter');
        supplierFilter.innerHTML = '<option value="">All Suppliers</option>';
        this.filterOptions.suppliers.forEach(supplier => {
            if (supplier) {
                const option = document.createElement('option');
                option.value = supplier;
                option.textContent = supplier;
                supplierFilter.appendChild(option);
            }
        });

        // Populate stock level filter
        const stockLevelFilter = document.getElementById('stockLevelFilter');
        stockLevelFilter.innerHTML = '<option value="">All Stock Levels</option>';
        this.filterOptions.stock_levels.forEach(level => {
            if (level) {
                const option = document.createElement('option');
                option.value = level;
                option.textContent = level;
                stockLevelFilter.appendChild(option);
            }
        });
    }

    async loadInventoryData() {
        this.showLoading(true);

        try {
            const params = new URLSearchParams({
                page: this.currentPage,
                page_size: this.pageSize,
                ...this.filters
            });

            const response = await fetch(`/api/inventory?${params}`);
            const data = await response.json();

            this.totalPages = data.total_pages;
            this.totalItems = data.total_items;

            this.renderTable(data.items);
            this.updatePagination();
            this.updateSelectionState();

        } catch (error) {
            console.error('Error loading inventory data:', error);
            this.showToast('Failed to load inventory data', 'error');
        } finally {
            this.showLoading(false);
        }
    }

    renderTable(items) {
        const tbody = document.getElementById('inventoryTableBody');
        const emptyState = document.getElementById('emptyState');
        const tableContainer = document.getElementById('tableContainer');

        if (items.length === 0) {
            tbody.innerHTML = '';
            emptyState.style.display = 'flex';
            tableContainer.querySelector('table').style.display = 'none';
            return;
        }

        emptyState.style.display = 'none';
        tableContainer.querySelector('table').style.display = 'table';

        tbody.innerHTML = items.map(item => this.createTableRow(item)).join('');

        // Add click event listeners to rows
        tbody.querySelectorAll('tr').forEach(row => {
            row.addEventListener('click', (e) => {
                if (e.target.type === 'checkbox') return;
                const medId = parseInt(row.dataset.medId);
                this.navigateToMedication(medId);
            });
        });

        // Add checkbox event listeners
        tbody.querySelectorAll('input[type=\"checkbox\"]').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const medId = parseInt(e.target.closest('tr').dataset.medId);
                if (e.target.checked) {
                    this.selectedItems.add(medId);
                } else {
                    this.selectedItems.delete(medId);
                }
                this.updateSelectionState();
            });
        });
    }

    createTableRow(item) {
        const isSelected = this.selectedItems.has(item.med_id);
        const stockBadgeClass = item.stock_category.toLowerCase().replace(/\\s+/g, '-');
        const categoryBadgeClass = item.category.toLowerCase();
        const supplierStatusClass = item.supplier_status.toLowerCase();

        const specialAttributes = [];
        if (item.is_cold_chain) {
            specialAttributes.push('<span class=\"attribute-icon cold-chain\" title=\"Cold Chain\">❄️</span>');
        }
        if (item.is_controlled) {
            specialAttributes.push('<span class=\"attribute-icon controlled\" title=\"Controlled Substance\">🔒</span>');
        }

        return `
            <tr data-med-id=\"${item.med_id}\" class=\"${isSelected ? 'selected' : ''}\">
                <td data-label=\"Select\">
                    <input type=\"checkbox\" ${isSelected ? 'checked' : ''}>
                </td>
                <td data-label=\"Medication\">
                    <div>
                        <strong>${this.escapeHtml(item.name)}</strong>
                        <div class=\"special-attributes\">${specialAttributes.join('')}</div>
                    </div>
                </td>
                <td data-label=\"Category\">
                    <span class=\"category-badge ${categoryBadgeClass}\">${item.category}</span>
                </td>
                <td data-label=\"Stock\">
                    <strong>${item.current_stock.toLocaleString()}</strong>
                </td>
                <td data-label=\"Stock Level\">
                    <span class=\"status-badge ${stockBadgeClass}\">${item.stock_category}</span>
                </td>
                <td data-label=\"Reorder Point\">
                    ${item.reorder_point ? item.reorder_point.toLocaleString() : '-'}
                </td>
                <td data-label=\"Days Until Stockout\">
                    ${item.days_until_stockout > 0 ?
                `<span class=\"stockout-warning ${item.days_until_stockout <= 7 ? 'critical' : item.days_until_stockout <= 14 ? 'warning' : ''}\">${item.days_until_stockout} days</span>`
                : '<span class=\"text-muted\">N/A</span>'
            }
                </td>
                <td data-label=\"Supplier\">
                    <div class=\"supplier-status\">
                        <span class=\"supplier-status-indicator ${supplierStatusClass}\"></span>
                        ${this.escapeHtml(item.supplier_name)}
                    </div>
                </td>
                <td data-label=\"Pack Size\">${item.pack_size}</td>
                <td data-label=\"Avg Daily Pick\">${item.avg_daily_pick.toFixed(1)}</td>
                <td data-label=\"Location\">${this.escapeHtml(item.storage_location)}</td>
                <td data-label=\"Actions\">
                    <div class=\"table-actions\">
                        <button class=\"btn-table\" title=\"View Details\" onclick=\"app.navigateToMedication(${item.med_id})\">
                            👁️
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }

    navigateToMedication(medId) {
        // Store the medication ID in sessionStorage for the detail page
        sessionStorage.setItem('selectedMedicationId', medId);
        window.location.href = `/medication/${medId}`;
    }

    updatePagination() {
        // Update pagination info
        const start = (this.currentPage - 1) * this.pageSize + 1;
        const end = Math.min(this.currentPage * this.pageSize, this.totalItems);
        document.getElementById('paginationInfo').textContent =
            `Showing ${start} - ${end} of ${this.totalItems.toLocaleString()} items`;

        // Update pagination buttons
        const firstBtn = document.getElementById('firstPage');
        const prevBtn = document.getElementById('prevPage');
        const nextBtn = document.getElementById('nextPage');
        const lastBtn = document.getElementById('lastPage');

        firstBtn.disabled = this.currentPage <= 1;
        prevBtn.disabled = this.currentPage <= 1;
        nextBtn.disabled = this.currentPage >= this.totalPages;
        lastBtn.disabled = this.currentPage >= this.totalPages;

        // Update page numbers
        this.renderPageNumbers();
    }

    renderPageNumbers() {
        const pageNumbers = document.getElementById('pageNumbers');
        const maxVisiblePages = 5;
        let pages = [];

        if (this.totalPages <= maxVisiblePages) {
            for (let i = 1; i <= this.totalPages; i++) {
                pages.push(i);
            }
        } else {
            const half = Math.floor(maxVisiblePages / 2);
            let start = Math.max(1, this.currentPage - half);
            let end = Math.min(this.totalPages, start + maxVisiblePages - 1);

            if (end - start + 1 < maxVisiblePages) {
                start = Math.max(1, end - maxVisiblePages + 1);
            }

            if (start > 1) {
                pages.push(1);
                if (start > 2) pages.push('...');
            }

            for (let i = start; i <= end; i++) {
                pages.push(i);
            }

            if (end < this.totalPages) {
                if (end < this.totalPages - 1) pages.push('...');
                pages.push(this.totalPages);
            }
        }

        pageNumbers.innerHTML = pages.map(page => {
            if (page === '...') {
                return '<span class=\"page-ellipsis\">...</span>';
            }
            return `<button class=\"page-number ${page === this.currentPage ? 'active' : ''}\" 
                            onclick=\"app.goToPage(${page})\">${page}</button>`;
        }).join('');
    }

    updateSelectionState() {
        const selectAllCheckbox = document.getElementById('selectAll');
        const generatePoBtn = document.getElementById('generatePoBtn');
        const selectedCount = this.selectedItems.size;
        const visibleRows = document.querySelectorAll('#inventoryTableBody tr').length;

        // Update select all checkbox
        if (selectedCount === 0) {
            selectAllCheckbox.indeterminate = false;
            selectAllCheckbox.checked = false;
        } else if (selectedCount === visibleRows && visibleRows > 0) {
            selectAllCheckbox.indeterminate = false;
            selectAllCheckbox.checked = true;
        } else {
            selectAllCheckbox.indeterminate = true;
            selectAllCheckbox.checked = false;
        }

        // Update Generate PO button
        generatePoBtn.disabled = selectedCount === 0;
        generatePoBtn.textContent = selectedCount > 0
            ? `Generate PO (${selectedCount})`
            : 'Generate PO';
    }

    handleSelectAll(checked) {
        const visibleRows = document.querySelectorAll('#inventoryTableBody tr');

        if (checked) {
            visibleRows.forEach(row => {
                const medId = parseInt(row.dataset.medId);
                this.selectedItems.add(medId);
                row.querySelector('input[type=\"checkbox\"]').checked = true;
                row.classList.add('selected');
            });
        } else {
            visibleRows.forEach(row => {
                const medId = parseInt(row.dataset.medId);
                this.selectedItems.delete(medId);
                row.querySelector('input[type=\"checkbox\"]').checked = false;
                row.classList.remove('selected');
            });
        }

        this.updateSelectionState();
    }

    handleFilterChange(filterType, value) {
        this.filters[filterType] = value;
        this.currentPage = 1; // Reset to first page when filtering
        this.loadInventoryData();
    }

    clearAllFilters() {
        this.filters = {
            search: '',
            category: '',
            supplier: '',
            stock_level: ''
        };

        // Clear form inputs
        document.getElementById('searchInput').value = '';
        document.getElementById('categoryFilter').value = '';
        document.getElementById('supplierFilter').value = '';
        document.getElementById('stockLevelFilter').value = '';

        this.currentPage = 1;
        this.loadInventoryData();
    }

    goToPage(page) {
        if (page >= 1 && page <= this.totalPages && page !== this.currentPage) {
            this.currentPage = page;
            this.loadInventoryData();
        }
    }

    changePageSize(newSize) {
        this.pageSize = newSize;
        this.currentPage = 1;
        this.loadInventoryData();
    }

    handleGeneratePO() {
        if (this.selectedItems.size === 0) {
            this.showToast('Please select items to generate a Purchase Order', 'warning');
            return;
        }

        // Placeholder functionality - just show a toast
        this.showToast(
            `Generated PO for ${this.selectedItems.size} selected items (placeholder functionality)`,
            'success'
        );

        // Clear selections
        this.selectedItems.clear();
        this.updateSelectionState();

        // Update table rows
        document.querySelectorAll('#inventoryTableBody tr').forEach(row => {
            row.classList.remove('selected');
            row.querySelector('input[type=\"checkbox\"]').checked = false;
        });
    }

    showLoading(show) {
        const loadingIndicator = document.getElementById('loadingIndicator');
        const tableContainer = document.getElementById('tableContainer');

        if (show) {
            loadingIndicator.style.display = 'flex';
            tableContainer.style.display = 'none';
        } else {
            loadingIndicator.style.display = 'none';
            tableContainer.style.display = 'block';
        }
    }

    showToast(message, type = 'info') {
        const toastContainer = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <span>${this.escapeHtml(message)}</span>
        `;

        toastContainer.appendChild(toast);

        // Remove toast after 5 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 5000);
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>\"']/g, function (m) { return map[m]; });
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new InventoryApp();
});