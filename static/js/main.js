// Main JavaScript for AUTO TRADE VIP Landing Page
document.addEventListener('DOMContentLoaded', function() {
    
    // Navbar scroll effect
    const navbar = document.querySelector('.navbar');
    
    window.addEventListener('scroll', function() {
        if (window.scrollY > 50) {
            navbar.style.background = 'rgba(13, 20, 33, 0.98)';
            navbar.style.backdropFilter = 'blur(15px)';
        } else {
            navbar.style.background = 'rgba(13, 20, 33, 0.95)';
            navbar.style.backdropFilter = 'blur(10px)';
        }
    });
    
    // Smooth scrolling for anchor links
    const anchorLinks = document.querySelectorAll('a[href^="#"]');
    
    anchorLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            const targetSection = document.querySelector(targetId);
            
            if (targetSection) {
                const offsetTop = targetSection.offsetTop - 80; // Account for fixed navbar
                
                window.scrollTo({
                    top: offsetTop,
                    behavior: 'smooth'
                });
            }
        });
    });
    
    // Fade in animation on scroll
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, observerOptions);
    
    // Add fade-in class to elements
    const fadeElements = document.querySelectorAll('.package-card, .feature-box, .section-title, .section-subtitle');
    fadeElements.forEach(el => {
        el.classList.add('fade-in');
        observer.observe(el);
    });
    
    // Package card hover effects
    const packageCards = document.querySelectorAll('.package-card');
    
    packageCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            // Add glow effect
            this.style.boxShadow = '0 20px 50px rgba(0, 230, 118, 0.3)';
        });
        
        card.addEventListener('mouseleave', function() {
            // Remove glow effect
            this.style.boxShadow = '0 10px 30px rgba(0, 230, 118, 0.1)';
        });
    });
    
    // Button click animations
    const buttons = document.querySelectorAll('.btn');
    
    buttons.forEach(button => {
        button.addEventListener('click', function(e) {
            // Create ripple effect
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;
            
            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';
            ripple.classList.add('ripple');
            
            this.appendChild(ripple);
            
            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
    });
    
    // Broker carousel pause on hover
    const brokerTrack = document.querySelector('.broker-track');
    
    if (brokerTrack) {
        brokerTrack.addEventListener('mouseenter', function() {
            this.style.animationPlayState = 'paused';
        });
        
        brokerTrack.addEventListener('mouseleave', function() {
            this.style.animationPlayState = 'running';
        });
    }
    
    // Package subscription button handlers
    const subscribeButtons = document.querySelectorAll('.package-footer .btn');
    
    subscribeButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            const packageCard = this.closest('.package-card');
            const packageTitle = packageCard.querySelector('.package-title').textContent;
            const packagePrice = packageCard.querySelector('.price-amount').textContent;
            
            // Show loading state
            const originalText = this.innerHTML;
            this.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Memproses...';
            this.disabled = true;
            
            // Simulate processing (replace with actual subscription logic)
            setTimeout(() => {
                // Show success message
                this.innerHTML = '<i class="fas fa-check me-2"></i>Berhasil!';
                this.classList.remove('btn-primary');
                this.classList.add('btn-success');
                
                // Reset after 3 seconds
                setTimeout(() => {
                    this.innerHTML = originalText;
                    this.classList.remove('btn-success');
                    this.classList.add('btn-primary');
                    this.disabled = false;
                }, 3000);
                
                // Show alert or redirect to payment
                showSubscriptionModal(packageTitle, packagePrice);
            }, 2000);
        });
    });
    
    // Contact button handlers
    const contactButtons = document.querySelectorAll('.contact-buttons .btn, .social-link');
    
    contactButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            const buttonType = this.textContent.toLowerCase();
            let message = '';
            
            if (buttonType.includes('telegram')) {
                message = 'Mengarahkan ke Telegram Support...';
                // Replace with actual Telegram link
                // window.open('https://t.me/your_support_bot', '_blank');
            } else if (buttonType.includes('whatsapp')) {
                message = 'Mengarahkan ke WhatsApp Support...';
                // Replace with actual WhatsApp link
                // window.open('https://wa.me/your_number', '_blank');
            }
            
            if (message) {
                showNotification(message);
            }
        });
    });
    
    // Utility function to show notifications
    function showNotification(message) {
        const notification = document.createElement('div');
        notification.className = 'notification';
        notification.innerHTML = `
            <i class="fas fa-info-circle me-2"></i>
            ${message}
        `;
        
        // Style the notification
        Object.assign(notification.style, {
            position: 'fixed',
            top: '100px',
            right: '20px',
            background: 'var(--gradient-accent)',
            color: 'white',
            padding: '1rem 1.5rem',
            borderRadius: '10px',
            boxShadow: '0 10px 30px rgba(0, 230, 118, 0.3)',
            zIndex: '9999',
            transform: 'translateX(300px)',
            transition: 'transform 0.3s ease'
        });
        
        document.body.appendChild(notification);
        
        // Show notification
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
        }, 100);
        
        // Hide notification after 3 seconds
        setTimeout(() => {
            notification.style.transform = 'translateX(300px)';
            setTimeout(() => {
                notification.remove();
            }, 300);
        }, 3000);
    }
    
    // Utility function to show subscription modal
    function showSubscriptionModal(packageTitle, packagePrice) {
        const modal = document.createElement('div');
        modal.innerHTML = `
            <div class="modal fade show" style="display: block; background: rgba(0,0,0,0.5);">
                <div class="modal-dialog">
                    <div class="modal-content" style="background: var(--background-card); color: var(--text-light);">
                        <div class="modal-header" style="border-bottom: 1px solid rgba(0, 230, 118, 0.1);">
                            <h5 class="modal-title">
                                <i class="fas fa-shopping-cart me-2 text-accent"></i>
                                Konfirmasi Berlangganan
                            </h5>
                        </div>
                        <div class="modal-body">
                            <p><strong>Paket:</strong> ${packageTitle}</p>
                            <p><strong>Harga:</strong> ${packagePrice} / bulan</p>
                            <p class="mt-3">Untuk melanjutkan proses berlangganan, silakan hubungi tim support kami melalui Telegram atau WhatsApp.</p>
                        </div>
                        <div class="modal-footer" style="border-top: 1px solid rgba(0, 230, 118, 0.1);">
                            <button class="btn btn-accent me-2">
                                <i class="fab fa-telegram me-2"></i>
                                Hubungi via Telegram
                            </button>
                            <button class="btn btn-outline-light" onclick="this.closest('.modal').remove()">
                                Tutup
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Remove modal when clicking outside
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                modal.remove();
            }
        });
    }
    
    // Add ripple effect styles
    const rippleStyles = `
        .ripple {
            position: absolute;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.3);
            transform: scale(0);
            animation: ripple-animation 0.6s linear;
            pointer-events: none;
        }
        
        @keyframes ripple-animation {
            to {
                transform: scale(4);
                opacity: 0;
            }
        }
    `;
    
    const styleSheet = document.createElement('style');
    styleSheet.textContent = rippleStyles;
    document.head.appendChild(styleSheet);
    
    // Initialize animations
    setTimeout(() => {
        document.querySelectorAll('.fade-in').forEach((el, index) => {
            setTimeout(() => {
                el.style.opacity = '0';
                el.style.transform = 'translateY(30px)';
            }, index * 100);
        });
    }, 100);
    
    console.log('AUTO TRADE VIP Landing Page initialized successfully!');
});

// Performance optimization: Lazy load broker images
if ('IntersectionObserver' in window) {
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.classList.remove('lazy');
                imageObserver.unobserve(img);
            }
        });
    });
    
    document.querySelectorAll('img[data-src]').forEach(img => {
        imageObserver.observe(img);
    });
}

// Add loading animation for images
document.querySelectorAll('img').forEach(img => {
    img.addEventListener('load', function() {
        this.style.opacity = '1';
    });
    
    img.addEventListener('error', function() {
        this.style.opacity = '0.5';
        this.alt = 'Image failed to load';
    });
    
    // Set initial opacity
    img.style.opacity = '0';
    img.style.transition = 'opacity 0.3s ease';
});
