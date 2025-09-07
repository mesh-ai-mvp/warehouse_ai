// Table-specific functionality
class TableManager {
    constructor() {
        this.sortColumn = null;
        this.sortDirection = 'asc';
        this.init();
    }
    
    init() {
        this.setupTableEvents();
    }
    
    setupTableEvents() {
        // Make table headers sortable
        document.addEventListener('DOMContentLoaded', () => {
            this.makeSortable();
        });
    }
    
    makeSortable() {
        const headers = document.querySelectorAll('.inventory-table th');
        const sortableColumns = [
            { index: 1, key: 'name', type: 'string' },
            { index: 2, key: 'category', type: 'string' },
            { index: 3, key: 'current_stock', type: 'number' },
            { index: 4, key: 'stock_category', type: 'string' },
            { index: 5, key: 'supplier_name', type: 'string' },
            { index: 6, key: 'pack_size', type: 'number' },
            { index: 7, key: 'avg_daily_pick', type: 'number' }
        ];
        
        sortableColumns.forEach(col => {
            const header = headers[col.index];
            if (header) {
                header.classList.add('sortable');
                header.addEventListener('click', () => this.handleSort(col.key, col.type));
            }
        });
    }
    
    handleSort(column, type) {
        // Toggle sort direction if clicking the same column
        if (this.sortColumn === column) {
            this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            this.sortColumn = column;
            this.sortDirection = 'asc';
        }
        
        // Update header styles
        this.updateSortHeaders();
        
        // Sort the table
        this.sortTable(column, type, this.sortDirection);
    }
    
    updateSortHeaders() {
        document.querySelectorAll('.inventory-table th.sortable').forEach(th => {
            th.classList.remove('asc', 'desc');
        });
        
        // Find and highlight the active sort column
        const headers = document.querySelectorAll('.inventory-table th');
        const columnMapping = {
            'name': 1,
            'category': 2,
            'current_stock': 3,
            'stock_category': 4,
            'supplier_name': 5,
            'pack_size': 6,
            'avg_daily_pick': 7
        };
        
        if (this.sortColumn && columnMapping[this.sortColumn] !== undefined) {
            const headerIndex = columnMapping[this.sortColumn];
            headers[headerIndex]?.classList.add(this.sortDirection);
        }
    }
    
    sortTable(column, type, direction) {
        const tbody = document.getElementById('inventoryTableBody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        
        const columnIndex = this.getColumnIndex(column);
        if (columnIndex === -1) return;
        
        rows.sort((a, b) => {
            let aValue = this.getCellValue(a, columnIndex, type);
            let bValue = this.getCellValue(b, columnIndex, type);
            
            if (type === 'number') {
                aValue = parseFloat(aValue) || 0;
                bValue = parseFloat(bValue) || 0;
                return direction === 'asc' ? aValue - bValue : bValue - aValue;
            } else {
                aValue = aValue.toLowerCase();
                bValue = bValue.toLowerCase();
                if (direction === 'asc') {
                    return aValue < bValue ? -1 : aValue > bValue ? 1 : 0;
                } else {
                    return aValue > bValue ? -1 : aValue < bValue ? 1 : 0;
                }
            }
        });
        
        // Reappend sorted rows
        rows.forEach(row => tbody.appendChild(row));
    }
    
    getColumnIndex(column) {
        const mapping = {
            'name': 1,
            'category': 2,
            'current_stock': 3,
            'stock_category': 4,
            'supplier_name': 5,
            'pack_size': 6,
            'avg_daily_pick': 7
        };
        return mapping[column] || -1;
    }
    
    getCellValue(row, columnIndex, type) {
        const cell = row.cells[columnIndex];
        if (!cell) return '';
        
        if (type === 'number') {
            // Extract number from text content
            const text = cell.textContent || cell.innerText || '';
            const match = text.match(/[\\d,]+\\.?\\d*/);
            return match ? match[0].replace(/,/g, '') : '0';
        } else {
            // For string sorting, get clean text content
            let text = cell.textContent || cell.innerText || '';
            // Remove extra whitespace and special characters for sorting
            return text.trim();
        }
    }
    
    // Highlight search terms in table
    highlightSearchTerms(searchTerm) {
        const tbody = document.getElementById('inventoryTableBody');
        const rows = tbody.querySelectorAll('tr');
        
        rows.forEach(row => {
            const cells = row.querySelectorAll('td');
            cells.forEach(cell => {
                // Remove existing highlights
                this.removeHighlights(cell);
                
                if (searchTerm && searchTerm.length > 0) {
                    this.highlightText(cell, searchTerm);
                }
            });
        });
    }
    
    highlightText(element, searchTerm) {
        const walker = document.createTreeWalker(
            element,
            NodeFilter.SHOW_TEXT,
            null,
            false
        );
        
        const textNodes = [];
        let node;
        while (node = walker.nextNode()) {
            textNodes.push(node);
        }
        
        textNodes.forEach(textNode => {
            const text = textNode.textContent;
            const regex = new RegExp(`(${this.escapeRegex(searchTerm)})`, 'gi');
            
            if (regex.test(text)) {
                const highlightedText = text.replace(regex, '<mark>$1</mark>');
                const wrapper = document.createElement('span');
                wrapper.innerHTML = highlightedText;
                textNode.parentNode.replaceChild(wrapper, textNode);
            }
        });
    }
    
    removeHighlights(element) {
        const highlights = element.querySelectorAll('mark');
        highlights.forEach(mark => {
            const parent = mark.parentNode;
            parent.replaceChild(document.createTextNode(mark.textContent), mark);
            parent.normalize();
        });
    }
    
    escapeRegex(string) {
        return string.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&');
    }
    
    // Export table data to CSV
    exportToCSV() {
        const table = document.getElementById('inventoryTable');
        const rows = table.querySelectorAll('tr');
        let csvContent = '';
        
        rows.forEach(row => {
            const cols = row.querySelectorAll('td, th');
            const rowData = Array.from(cols).map(col => {
                // Skip checkbox column and actions column
                if (col.classList.contains('checkbox-column') || 
                    col.textContent.includes('Actions')) {
                    return null;
                }
                return '\"' + (col.textContent || '').replace(/\"/g, '\"\"') + '\"';
            }).filter(Boolean);
            
            if (rowData.length > 0) {
                csvContent += rowData.join(',') + '\\n';
            }
        });
        
        // Download CSV
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        if (link.download !== undefined) {
            const url = URL.createObjectURL(blob);
            link.setAttribute('href', url);
            link.setAttribute('download', 'inventory_export.csv');
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    }
    
    // Print table
    printTable() {
        const printWindow = window.open('', '_blank');
        const table = document.getElementById('inventoryTable').cloneNode(true);
        
        // Remove checkbox column and actions column
        const headerCells = table.querySelectorAll('th');
        const dataCells = table.querySelectorAll('td');
        
        headerCells.forEach((cell, index) => {
            if (index === 0 || cell.textContent.includes('Actions')) {
                cell.remove();
            }
        });
        
        const rows = table.querySelectorAll('tr');
        rows.forEach(row => {
            const cells = row.querySelectorAll('td');
            cells.forEach((cell, index) => {
                if (index === 0 || cell.textContent.includes('👁️')) {
                    cell.remove();
                }
            });
        });
        
        printWindow.document.write(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>Inventory Report</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    table { width: 100%; border-collapse: collapse; }
                    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                    th { background-color: #f5f5f5; font-weight: bold; }
                    tr:nth-child(even) { background-color: #f9f9f9; }
                    .header { text-align: center; margin-bottom: 20px; }
                    .timestamp { text-align: right; color: #666; font-size: 0.9em; }
                </style>
            </head>
            <body>
                <div class=\"header\">
                    <h1>Inventory Management Report</h1>
                    <div class=\"timestamp\">Generated on: ${new Date().toLocaleString()}</div>
                </div>
                ${table.outerHTML}
            </body>
            </html>
        `);
        
        printWindow.document.close();
        printWindow.focus();
        setTimeout(() => {
            printWindow.print();
            printWindow.close();
        }, 250);
    }
}

// Initialize table manager
document.addEventListener('DOMContentLoaded', () => {
    window.tableManager = new TableManager();
});