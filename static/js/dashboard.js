// Dashboard JavaScript - ATV Theme Consistent
document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard loaded successfully!');
    
    // ===== SIDEBAR NAVIGATION ===== 
    const sidebarLinks = document.querySelectorAll('.sidebar-nav .nav-link');
    const contentSections = document.querySelectorAll('.content-section');
    
    // Handle sidebar navigation
    sidebarLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetSection = this.getAttribute('data-section');
            
            // Remove active class from all links
            sidebarLinks.forEach(l => l.classList.remove('active'));
            
            // Add active class to clicked link
            this.classList.add('active');
            
            // Hide all content sections
            contentSections.forEach(section => {
                section.classList.remove('active');
            });
            
            // Show target section
            const targetElement = document.getElementById(targetSection);
            if (targetElement) {
                targetElement.classList.add('active');
            }
            
            // Update page title
            updatePageTitle(targetSection);
        });
    });
    
    // Update page title based on active section
    function updatePageTitle(section) {
        const titles = {
            'overview': 'Dashboard Overview',
            'trading': 'Trading Robot',
            'packages': 'My Packages',
            'analytics': 'Analytics',
            'settings': 'Settings',
            'support': 'Support'
        };
        
        const title = titles[section] || 'Dashboard';
        document.title = `${title} - AUTO TRADE VIP`;
    }
    
    // ===== STATS CARDS ANIMATION =====
    const statsCards = document.querySelectorAll('.stats-card');
    
    // Add hover effects and click animations
    statsCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-8px) scale(1.02)';
            this.style.boxShadow = '0 15px 40px rgba(0, 230, 118, 0.25)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
            this.style.boxShadow = '0 10px 30px rgba(0, 230, 118, 0.1)';
        });
        
        card.addEventListener('click', function() {
            // Add click ripple effect
            const ripple = document.createElement('div');
            ripple.className = 'click-ripple';
            ripple.style.cssText = `
                position: absolute;
                border-radius: 50%;
                background: rgba(0, 230, 118, 0.3);
                width: 100px;
                height: 100px;
                left: 50%;
                top: 50%;
                transform: translate(-50%, -50%) scale(0);
                animation: ripple 0.6s ease-out;
                pointer-events: none;
            `;
            
            this.style.position = 'relative';
            this.appendChild(ripple);
            
            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
    });
    
    // Add ripple animation
    const style = document.createElement('style');
    style.textContent = `
        @keyframes ripple {
            to {
                transform: translate(-50%, -50%) scale(4);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
    
    // ===== ROBOT CONTROL BUTTONS =====
    const robotControls = document.querySelectorAll('.robot-controls .btn');
    
    robotControls.forEach(button => {
        button.addEventListener('click', function() {
            const action = this.textContent.toLowerCase();
            
            if (action.includes('stop')) {
                handleRobotStop();
            } else if (action.includes('settings')) {
                handleRobotSettings();
            }
        });
    });
    
    function handleRobotStop() {
        const robotStatus = document.querySelector('.robot-status');
        const statusText = robotStatus.querySelector('h3');
        const statusDesc = robotStatus.querySelector('p');
        
        // Show loading state
        statusText.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>STOPPING...';
        statusDesc.textContent = 'Stopping trading robot safely...';
        
        // Simulate stopping process
        setTimeout(() => {
            robotStatus.classList.remove('active');
            robotStatus.style.background = 'rgba(220, 53, 69, 0.1)';
            robotStatus.style.borderColor = 'rgba(220, 53, 69, 0.3)';
            
            statusText.innerHTML = 'STOPPED';
            statusText.style.color = '#ff6b6b';
            statusDesc.textContent = 'Trading robot has been stopped';
            
            // Update button
            const stopButton = document.querySelector('.robot-controls .btn-danger');
            stopButton.innerHTML = '<i class="fas fa-play"></i> Start Robot';
            stopButton.classList.remove('btn-danger');
            stopButton.classList.add('btn-success');
            
            showNotification('Trading robot stopped successfully', 'success');
        }, 2000);
    }
    
    function handleRobotSettings() {
        showNotification('Opening robot settings...', 'info');
        // Here you would typically open a settings modal
    }
    
    // ===== ACTIVITY ITEMS INTERACTION =====
    const activityItems = document.querySelectorAll('.activity-item');
    
    activityItems.forEach(item => {
        item.addEventListener('click', function() {
            // Add selection effect
            activityItems.forEach(i => i.classList.remove('selected'));
            this.classList.add('selected');
            
            // Show activity details (you can expand this)
            const activityTitle = this.querySelector('h5').textContent;
            showNotification(`Viewing details for: ${activityTitle}`, 'info');
        });
    });
    
    // ===== NOTIFICATION SYSTEM =====
    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        
        const icons = {
            'success': 'fas fa-check-circle',
            'error': 'fas fa-exclamation-circle',
            'info': 'fas fa-info-circle',
            'warning': 'fas fa-exclamation-triangle'
        };
        
        notification.innerHTML = `
            <i class="${icons[type]} me-2"></i>
            <span>${message}</span>
            <button class="notification-close" onclick="this.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        // Style the notification
        Object.assign(notification.style, {
            position: 'fixed',
            top: '90px',
            right: '20px',
            background: getNotificationColor(type),
            color: 'white',
            padding: '1rem 1.5rem',
            borderRadius: '10px',
            boxShadow: '0 10px 30px rgba(0, 0, 0, 0.3)',
            zIndex: '9999',
            transform: 'translateX(300px)',
            transition: 'transform 0.3s ease',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            minWidth: '300px',
            maxWidth: '400px'
        });
        
        // Style close button
        const closeBtn = notification.querySelector('.notification-close');
        Object.assign(closeBtn.style, {
            background: 'none',
            border: 'none',
            color: 'white',
            cursor: 'pointer',
            opacity: '0.7',
            marginLeft: 'auto'
        });
        
        closeBtn.addEventListener('mouseenter', () => closeBtn.style.opacity = '1');
        closeBtn.addEventListener('mouseleave', () => closeBtn.style.opacity = '0.7');
        
        document.body.appendChild(notification);
        
        // Show notification
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
        }, 100);
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            notification.style.transform = 'translateX(300px)';
            setTimeout(() => {
                if (notification.parentElement) {
                    notification.remove();
                }
            }, 300);
        }, 5000);
    }
    
    function getNotificationColor(type) {
        const colors = {
            'success': 'linear-gradient(135deg, #00e676, #00c965)',
            'error': 'linear-gradient(135deg, #dc3545, #c82333)',
            'info': 'linear-gradient(135deg, #0dcaf0, #0bb5d9)',
            'warning': 'linear-gradient(135deg, #ffc107, #e0a800)'
        };
        return colors[type] || colors.info;
    }
    
    // ===== REAL-TIME UPDATES SIMULATION =====
    function simulateRealTimeUpdates() {
        // Simulate updating stats
        const statsValues = document.querySelectorAll('.stats-content h3');
        
        setInterval(() => {
            statsValues.forEach(stat => {
                if (stat.textContent.includes('$')) {
                    const currentValue = parseInt(stat.textContent.replace(/[^0-9]/g, ''));
                    const newValue = currentValue + Math.floor(Math.random() * 50);
                    stat.textContent = `$${newValue}`;
                } else if (stat.textContent.includes('%')) {
                    const currentValue = parseFloat(stat.textContent.replace('%', ''));
                    const change = (Math.random() - 0.5) * 2; // Random change between -1 and 1
                    const newValue = Math.max(0, currentValue + change).toFixed(1);
                    stat.textContent = `${newValue}%`;
                }
            });
        }, 30000); // Update every 30 seconds
    }
    
    // Start real-time updates simulation
    simulateRealTimeUpdates();
    
    // ===== MOBILE RESPONSIVE SIDEBAR =====
    function initMobileMenu() {
        // Create mobile menu toggle button if not exists
        let mobileToggle = document.querySelector('.mobile-toggle');
        
        if (window.innerWidth <= 991) {
            if (!mobileToggle) {
                mobileToggle = document.createElement('button');
                mobileToggle.className = 'mobile-toggle';
                mobileToggle.innerHTML = '<i class="fas fa-bars"></i>';
                mobileToggle.setAttribute('aria-label', 'Toggle Sidebar');
                document.body.appendChild(mobileToggle);
            }
            
            // Remove any existing event listeners
            const newToggle = mobileToggle.cloneNode(true);
            mobileToggle.parentNode.replaceChild(newToggle, mobileToggle);
            mobileToggle = newToggle;
            
            mobileToggle.addEventListener('click', function() {
                const sidebar = document.querySelector('.sidebar');
                let overlay = document.querySelector('.sidebar-overlay');
                
                // Toggle sidebar
                sidebar.classList.toggle('mobile-open');
                this.classList.toggle('active');
                
                // Update button icon
                const icon = this.querySelector('i');
                if (sidebar.classList.contains('mobile-open')) {
                    icon.className = 'fas fa-times';
                    
                    // Create overlay if doesn't exist
                    if (!overlay) {
                        overlay = document.createElement('div');
                        overlay.className = 'sidebar-overlay';
                        document.body.appendChild(overlay);
                    }
                    
                    overlay.classList.add('show');
                    
                    // Close sidebar when clicking overlay
                    overlay.addEventListener('click', closeSidebar);
                } else {
                    icon.className = 'fas fa-bars';
                    if (overlay) {
                        overlay.classList.remove('show');
                        setTimeout(() => {
                            if (overlay && overlay.parentNode) {
                                overlay.remove();
                            }
                        }, 300);
                    }
                }
            });
            
            function closeSidebar() {
                const sidebar = document.querySelector('.sidebar');
                const overlay = document.querySelector('.sidebar-overlay');
                const toggle = document.querySelector('.mobile-toggle');
                
                sidebar.classList.remove('mobile-open');
                toggle.classList.remove('active');
                toggle.querySelector('i').className = 'fas fa-bars';
                
                if (overlay) {
                    overlay.classList.remove('show');
                    setTimeout(() => {
                        if (overlay && overlay.parentNode) {
                            overlay.remove();
                        }
                    }, 300);
                }
            }
            
            // Close sidebar when clicking sidebar links on mobile
            const sidebarLinks = document.querySelectorAll('.sidebar-nav .nav-link');
            sidebarLinks.forEach(link => {
                link.addEventListener('click', function() {
                    if (window.innerWidth <= 991) {
                        setTimeout(closeSidebar, 100);
                    }
                });
            });
            
        } else {
            // Remove mobile toggle on desktop
            if (mobileToggle) {
                mobileToggle.remove();
            }
            
            // Remove overlay on desktop
            const overlay = document.querySelector('.sidebar-overlay');
            if (overlay) {
                overlay.remove();
            }
            
            // Ensure sidebar is visible on desktop
            const sidebar = document.querySelector('.sidebar');
            sidebar.classList.remove('mobile-open');
        }
    }
    
    // Initialize mobile menu on load and resize
    initMobileMenu();
    window.addEventListener('resize', debounce(initMobileMenu, 250));
    
    // Debounce function for resize events
    function debounce(func, wait) {
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
    
    // ===== TOUCH GESTURES FOR MOBILE =====
    function initTouchGestures() {
        if (window.innerWidth <= 991) {
            let startX = 0;
            let startY = 0;
            let isScrolling = false;
            
            document.addEventListener('touchstart', function(e) {
                startX = e.touches[0].clientX;
                startY = e.touches[0].clientY;
                isScrolling = false;
            }, { passive: true });
            
            document.addEventListener('touchmove', function(e) {
                if (!startX || !startY) return;
                
                const diffX = Math.abs(e.touches[0].clientX - startX);
                const diffY = Math.abs(e.touches[0].clientY - startY);
                
                if (diffY > diffX) {
                    isScrolling = true;
                }
            }, { passive: true });
            
            document.addEventListener('touchend', function(e) {
                if (isScrolling) return;
                
                const diffX = e.changedTouches[0].clientX - startX;
                const sidebar = document.querySelector('.sidebar');
                
                // Swipe right from left edge to open sidebar
                if (startX < 50 && diffX > 100 && !sidebar.classList.contains('mobile-open')) {
                    document.querySelector('.mobile-toggle').click();
                }
                
                // Swipe left on sidebar to close
                if (startX > 50 && diffX < -100 && sidebar.classList.contains('mobile-open')) {
                    document.querySelector('.mobile-toggle').click();
                }
                
                startX = 0;
                startY = 0;
            }, { passive: true });
        }
    }
    
    initTouchGestures();
    
    // ===== LOADING STATES =====
    function addLoadingStates() {
        const buttons = document.querySelectorAll('.btn');
        
        buttons.forEach(button => {
            button.addEventListener('click', function(e) {
                // Skip if it's a navigation button or close button
                if (this.closest('.sidebar-nav') || this.classList.contains('notification-close')) {
                    return;
                }
                
                const originalText = this.innerHTML;
                this.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
                this.disabled = true;
                
                // Simulate processing
                setTimeout(() => {
                    this.innerHTML = originalText;
                    this.disabled = false;
                }, 1500);
            });
        });
    }
    
    addLoadingStates();
    
    // ===== WELCOME MESSAGE =====
    setTimeout(() => {
        showNotification('Welcome to your AUTO TRADE VIP dashboard!', 'success');
    }, 1000);
    
    console.log('Dashboard initialization complete!');
});

// ===== UTILITY FUNCTIONS =====

// Format currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

// Format percentage
function formatPercentage(value) {
    return `${value.toFixed(2)}%`;
}

// Format date/time
function formatDateTime(date) {
    return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    }).format(date);
}

// Add CSS for activity item selection
const additionalStyles = document.createElement('style');
additionalStyles.textContent = `
    .activity-item.selected {
        background: rgba(0, 230, 118, 0.05);
        border-radius: 8px;
        transform: translateX(5px);
    }
    
    .activity-item {
        cursor: pointer;
        transition: all 0.3s ease;
        border-radius: 8px;
        margin: 0 -0.5rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    
    .activity-item:hover {
        background: rgba(255, 255, 255, 0.02);
    }
`;
document.head.appendChild(additionalStyles);