// Sidebar functionality
class SidebarManager {
    constructor() {
        this.sidebar = null;
        this.sidebarToggle = null;
        this.mainContent = null;
        this.isCollapsed = false;

        this.init();
    }

    init() {
        this.sidebar = document.getElementById('sidebar');
        this.sidebarToggle = document.getElementById('sidebarToggle');
        this.mainContent = document.querySelector('.main-content');

        // Load saved state from localStorage
        this.loadSidebarState();

        this.setupEventListeners();
        this.setupMediaQuery();
    }

    setupEventListeners() {
        if (this.sidebarToggle) {
            this.sidebarToggle.addEventListener('click', () => {
                this.toggleSidebar();
            });
        }

        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', (e) => {
            if (window.innerWidth <= 768 &&
                !this.sidebar.contains(e.target) &&
                !this.sidebarToggle.contains(e.target) &&
                !this.isCollapsed) {
                this.collapseSidebar();
            }
        });

        // Handle navigation clicks
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                this.handleNavigation(e);
            });
        });
    }

    setupMediaQuery() {
        // Handle responsive behavior
        const mediaQuery = window.matchMedia('(max-width: 768px)');
        this.handleMediaQuery(mediaQuery);
        mediaQuery.addListener(this.handleMediaQuery.bind(this));
    }

    handleMediaQuery(mediaQuery) {
        if (mediaQuery.matches) {
            // Mobile: Sidebar should be collapsed by default
            this.collapseSidebar();
        } else {
            // Desktop: Restore previous state
            this.loadSidebarState();
        }
    }

    toggleSidebar() {
        if (this.isCollapsed) {
            this.expandSidebar();
        } else {
            this.collapseSidebar();
        }
    }

    expandSidebar() {
        this.isCollapsed = false;
        this.updateSidebarState();
        this.saveSidebarState();
    }

    collapseSidebar() {
        this.isCollapsed = true;
        this.updateSidebarState();
        this.saveSidebarState();
    }

    updateSidebarState() {
        if (this.isCollapsed) {
            this.sidebar.classList.add('collapsed');
            this.mainContent.classList.add('sidebar-collapsed');
            this.sidebarToggle.classList.add('active');
        } else {
            this.sidebar.classList.remove('collapsed');
            this.mainContent.classList.remove('sidebar-collapsed');
            this.sidebarToggle.classList.remove('active');
        }

        // Dispatch resize event to help other components adjust
        window.dispatchEvent(new Event('resize'));
    }

    saveSidebarState() {
        // Don't save state on mobile - always collapsed
        if (window.innerWidth <= 768) return;

        localStorage.setItem('sidebarCollapsed', this.isCollapsed.toString());
    }

    loadSidebarState() {
        // Don't load state on mobile - always collapsed
        if (window.innerWidth <= 768) {
            this.isCollapsed = true;
            this.updateSidebarState();
            return;
        }

        const saved = localStorage.getItem('sidebarCollapsed');
        if (saved !== null) {
            this.isCollapsed = saved === 'true';
            this.updateSidebarState();
        }
    }

    handleNavigation(e) {
        // Remove active class from all nav items
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });

        // Add active class to clicked item
        const navItem = e.target.closest('.nav-item');
        if (navItem) {
            navItem.classList.add('active');
        }

        // Handle different navigation items
        const linkText = e.target.textContent.trim();

        if (linkText.includes('Current Stock')) {
            e.preventDefault();
            // Check if we're not already on the inventory page (home page)
            if (window.location.pathname !== '/') {
                window.location.href = '/';
            }
            // If already on home page, do nothing (inventory is already shown)
        } else if (linkText.includes('Analytics')) {
            e.preventDefault();
            this.showComingSoon('Analytics Dashboard');
        } else if (linkText.includes('Purchase Orders')) {
            e.preventDefault();
            window.location.href = '/purchase-orders';
        } else if (linkText.includes('Suppliers')) {
            e.preventDefault();
            this.showComingSoon('Supplier Management');
        } else if (linkText.includes('Storage Locations')) {
            e.preventDefault();
            this.showComingSoon('Storage Location Management');
        } else if (linkText.includes('Settings')) {
            e.preventDefault();
            this.showComingSoon('Settings Panel');
        }

        // Close sidebar on mobile after navigation
        if (window.innerWidth <= 768) {
            this.collapseSidebar();
        }
    }

    showComingSoon(featureName) {
        // Show a toast notification for features not yet implemented
        if (window.app && typeof window.app.showToast === 'function') {
            window.app.showToast(`${featureName} - Coming Soon!`, 'info');
        } else {
            alert(`${featureName} - Coming Soon!`);
        }
    }

    // Highlight active section based on current page/view
    setActiveSection(sectionName) {
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });

        const targetItem = document.querySelector(`[data-section=\"${sectionName}\"]`) ||
            document.querySelector(`.nav-item:has(.nav-link:contains(\"${sectionName}\"))`);

        if (targetItem) {
            targetItem.classList.add('active');
        }
    }

    // Add notification badges to nav items
    addNotificationBadge(sectionName, count) {
        const navLink = document.querySelector(`[data-section=\"${sectionName}\"] .nav-link`);
        if (navLink) {
            // Remove existing badge
            const existingBadge = navLink.querySelector('.notification-badge');
            if (existingBadge) {
                existingBadge.remove();
            }

            // Add new badge if count > 0
            if (count > 0) {
                const badge = document.createElement('span');
                badge.className = 'notification-badge';
                badge.textContent = count > 99 ? '99+' : count.toString();
                navLink.appendChild(badge);
            }
        }
    }

    // Update sidebar based on user permissions or data
    updateSidebarVisibility(userPermissions = {}) {
        const navItems = {
            'analytics': document.querySelector('.nav-item:has(.nav-link:contains(\"Analytics\"))'),
            'purchaseOrders': document.querySelector('.nav-item:has(.nav-link:contains(\"Purchase Orders\"))'),
            'suppliers': document.querySelector('.nav-item:has(.nav-link:contains(\"Suppliers\"))'),
            'storageLocations': document.querySelector('.nav-item:has(.nav-link:contains(\"Storage Locations\"))'),
            'settings': document.querySelector('.nav-item:has(.nav-link:contains(\"Settings\"))')
        };

        Object.entries(navItems).forEach(([key, element]) => {
            if (element) {
                if (userPermissions[key] === false) {
                    element.style.display = 'none';
                } else {
                    element.style.display = '';
                }
            }
        });
    }

    // Add custom CSS for sidebar states
    addCustomStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .notification-badge {
                background-color: var(--danger);
                color: white;
                border-radius: 50%;
                padding: 2px 6px;
                font-size: 0.7rem;
                margin-left: auto;
                min-width: 18px;
                text-align: center;
                font-weight: 600;
            }
            
            .nav-link {
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
        `;
        document.head.appendChild(style);
    }
}

// Initialize sidebar manager
document.addEventListener('DOMContentLoaded', () => {
    window.sidebarManager = new SidebarManager();
    window.sidebarManager.addCustomStyles();
});