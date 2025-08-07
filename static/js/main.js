// Main JavaScript for AUTO TRADE VIP Landing Page
document.addEventListener('DOMContentLoaded', function() {
    
    // Create scroll progress bar
    const progressBar = document.createElement('div');
    progressBar.className = 'scroll-progress';
    document.body.appendChild(progressBar);
    
    // Navbar scroll effect with transparent background + progress bar
    const navbar = document.querySelector('.navbar');
    let lastScrollTop = 0;
    
    window.addEventListener('scroll', function() {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        const scrollDirection = scrollTop > lastScrollTop ? 'down' : 'up';
        
        // Calculate scroll progress
        const docHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
        const scrollPercent = (scrollTop / docHeight) * 100;
        progressBar.style.width = scrollPercent + '%';
        
        // Navbar transparency effects
        if (scrollTop > 100) {
            // Scrolling down - make navbar more transparent
            navbar.style.background = 'rgba(26, 31, 46, 0.3)';
            navbar.style.backdropFilter = 'blur(20px)';
            navbar.classList.add('navbar-transparent');
        } else if (scrollTop > 50) {
            // Mid-scroll - semi-transparent
            navbar.style.background = 'rgba(26, 31, 46, 0.7)';
            navbar.style.backdropFilter = 'blur(15px)';
            navbar.classList.remove('navbar-transparent');
        } else {
            // At top - normal background
            navbar.style.background = 'rgba(26, 31, 46, 0.95)';
            navbar.style.backdropFilter = 'blur(10px)';
            navbar.classList.remove('navbar-transparent');
        }
        
        lastScrollTop = scrollTop <= 0 ? 0 : scrollTop; // For Mobile or negative scrolling
    });

    // Active Menu Management - Ensure only ONE active menu
    function setActiveMenu() {
        // Get all navigation links
        const navLinks = document.querySelectorAll('.navbar-nav .nav-link:not(.btn-login-nav)');
        const sections = ['hero', 'features', 'packages', 'contact'];
        
        // Remove all active states first
        navLinks.forEach(link => {
            link.classList.remove('active');
        });
        
        // Determine current section based on scroll position
        let currentSection = 'hero'; // default
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        
        sections.forEach(sectionId => {
            const section = document.getElementById(sectionId);
            if (section) {
                const sectionTop = section.offsetTop - 100; // offset for navbar
                if (scrollTop >= sectionTop) {
                    currentSection = sectionId;
                }
            }
        });
        
        // Set active state to current section link
        if (currentSection) {
            const activeLink = document.querySelector(`a[href="#${currentSection}"]`);
            if (activeLink && activeLink.classList.contains('nav-link')) {
                activeLink.classList.add('active');
            }
        }
    }
    
    // Set initial active state
    setActiveMenu();
    
    // Update active state on scroll
    window.addEventListener('scroll', setActiveMenu);
    
    // Handle nav link clicks
    document.querySelectorAll('.navbar-nav .nav-link:not(.btn-login-nav)').forEach(link => {
        link.addEventListener('click', function(e) {
            // Remove active from all links
            document.querySelectorAll('.navbar-nav .nav-link').forEach(l => l.classList.remove('active'));
            // Add active to clicked link
            this.classList.add('active');
        });
    });

    // Login Modal Functionality
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const toggleFormBtn = document.getElementById('toggleForm');
    const loginAlert = document.getElementById('loginAlert');
    let isRegisterMode = false;

    // Toggle between login and register forms
    toggleFormBtn.addEventListener('click', function() {
        isRegisterMode = !isRegisterMode;
        if (isRegisterMode) {
            loginForm.style.display = 'none';
            registerForm.style.display = 'block';
            toggleFormBtn.textContent = 'Already have an account? Login here';
            document.querySelector('.modal-title').innerHTML = 
                '<i class="fas fa-user-plus me-2 text-accent"></i>Register to AUTO TRADE VIP';
        } else {
            loginForm.style.display = 'block';
            registerForm.style.display = 'none';
            toggleFormBtn.textContent = 'Create new account';
            document.querySelector('.modal-title').innerHTML = 
                '<i class="fas fa-sign-in-alt me-2 text-accent"></i>Login to AUTO TRADE VIP';
        }
        hideAlert();
    });

    // Handle login form submission
    loginForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const email = document.getElementById('loginEmail').value;
        const password = document.getElementById('loginPassword').value;

        try {
            const response = await fetch('/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email, password })
            });

            const data = await response.json();
            
            if (data.success) {
                showAlert('success', data.message);
                setTimeout(() => {
                    location.reload(); // Refresh to show logged in state
                }, 1500);
            } else {
                showAlert('danger', data.message);
            }
        } catch (error) {
            showAlert('danger', 'An error occurred. Please try again.');
        }
    });

    // Handle register form submission
    registerForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const name = document.getElementById('registerName').value;
        const email = document.getElementById('registerEmail').value;
        const gender = document.getElementById('registerGender').value;
        const country = document.getElementById('registerCountry').value;
        const password = document.getElementById('registerPassword').value;
        const confirm_password = document.getElementById('registerConfirmPassword').value;
        const agree_terms = document.getElementById('agreeTerms').checked;

        try {
            const response = await fetch('/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    name, 
                    email, 
                    gender, 
                    country, 
                    password, 
                    confirm_password, 
                    agree_terms 
                })
            });

            const data = await response.json();
            
            if (data.success) {
                showAlert('success', data.message);
                setTimeout(() => {
                    location.reload(); // Refresh to show logged in state
                }, 1500);
            } else {
                showAlert('danger', data.message);
            }
        } catch (error) {
            showAlert('danger', 'An error occurred. Please try again.');
        }
    });

    // Show alert message
    function showAlert(type, message) {
        loginAlert.className = `alert alert-${type}`;
        loginAlert.textContent = message;
        loginAlert.classList.remove('d-none');
    }

    // Hide alert message
    function hideAlert() {
        loginAlert.classList.add('d-none');
    }
    
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
    
    // Enhanced broker carousel interactions
    const brokerSlider = document.querySelector('.broker-slider');
    const brokerCarousel = document.querySelector('.broker-carousel');
    
    if (brokerSlider) {
        // Pause on hover
        brokerCarousel.addEventListener('mouseenter', function() {
            brokerSlider.style.animationPlayState = 'paused';
        });
        
        brokerCarousel.addEventListener('mouseleave', function() {
            brokerSlider.style.animationPlayState = 'running';
        });
        
        // Add click functionality to broker items
        document.querySelectorAll('.broker-item').forEach(item => {
            item.addEventListener('click', function() {
                const brokerName = this.querySelector('.broker-label').textContent;
                showBrokerInfo(brokerName);
            });
        });
    }
    
    // Show broker info modal
    function showBrokerInfo(brokerName) {
        const brokerInfo = {
            'Binomo': {
                description: 'Platform trading binary options dengan interface yang user-friendly dan berbagai instrumen trading.',
                features: ['Minimal deposit rendah', 'Trading turnamen', 'Bonus deposit', 'Mobile app']
            },
            'Olymptrade': {
                description: 'Broker internasional dengan lisensi resmi dan berbagai instrumen keuangan.',
                features: ['Regulasi international', 'Fixed time trades', 'Forex trading', 'Crypto trading']
            },
            'Stockity': {
                description: 'Platform trading modern dengan fokus pada pengalaman user yang optimal.',
                features: ['Interface modern', 'Fast execution', 'Multiple assets', 'Educational resources']
            },
            'IQ Option': {
                description: 'Salah satu broker terpopuler dengan jutaan trader di seluruh dunia.',
                features: ['Chart analysis tools', 'Copy trading', 'Tournaments', 'Demo account']
            },
            'Quotex': {
                description: 'Platform trading inovatif dengan teknologi terdepan dan spread kompetitif.',
                features: ['Advanced charts', 'Social trading', 'Risk management', 'Fast withdrawals']
            },
            'Pocket Option': {
                description: 'Broker yang menawarkan trading experience yang simpel namun powerful.',
                features: ['One-click trading', 'Social features', 'Achievement system', 'Multiple languages']
            }
        };
        
        const info = brokerInfo[brokerName] || {
            description: 'Platform trading terpercaya dengan berbagai fitur unggulan.',
            features: ['Trading tools', 'Customer support', 'Secure platform', 'Educational content']
        };
        
        const modal = document.createElement('div');
        modal.innerHTML = `
            <div class="modal fade show" style="display: block; background: rgba(0,0,0,0.8);">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content" style="background: var(--secondary-dark); border: 2px solid var(--border-color); border-radius: 20px;">
                        <div class="modal-header" style="border-bottom: 1px solid var(--border-color);">
                            <h5 class="modal-title" style="color: var(--accent-green);">
                                <i class="fas fa-chart-line me-2"></i>
                                ${brokerName}
                            </h5>
                            <button type="button" class="btn-close" onclick="this.closest('.modal').remove()" style="filter: invert(1);"></button>
                        </div>
                        <div class="modal-body" style="color: var(--text-gray);">
                            <p class="mb-3">${info.description}</p>
                            <h6 style="color: var(--text-white); margin-bottom: 1rem;">Fitur Utama:</h6>
                            <ul class="list-unstyled">
                                ${info.features.map(feature => `
                                    <li class="mb-2">
                                        <i class="fas fa-check text-success me-2"></i>
                                        ${feature}
                                    </li>
                                `).join('')}
                            </ul>
                        </div>
                        <div class="modal-footer" style="border-top: 1px solid var(--border-color);">
                            <button class="btn" style="background: var(--accent-green); color: white;" onclick="this.closest('.modal').remove()">
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
    
    // Initialize products carousel
    initProductsCarousel();
});

// Products Carousel Navigation
function initProductsCarousel() {
    const carousel = document.getElementById('productsCarousel');
    const navLeft = document.getElementById('navLeft');
    const navRight = document.getElementById('navRight');
    
    if (!carousel || !navLeft || !navRight) return;
    
    const checkScrollButtons = () => {
        const scrollLeft = carousel.scrollLeft;
        const maxScroll = carousel.scrollWidth - carousel.clientWidth;
        
        // Hide/show left button
        if (scrollLeft <= 0) {
            navLeft.classList.add('hidden');
        } else {
            navLeft.classList.remove('hidden');
        }
        
        // Hide/show right button  
        if (scrollLeft >= maxScroll - 1) {
            navRight.classList.add('hidden');
        } else {
            navRight.classList.remove('hidden');
        }
    };
    
    // Initial check
    checkScrollButtons();
    
    // Scroll left
    navLeft.addEventListener('click', () => {
        const isMobile = window.innerWidth <= 480;
        const isTablet = window.innerWidth <= 768;
        let scrollDistance = 420; // Desktop
        
        if (isMobile) {
            scrollDistance = 220; // Mobile with improved layout
        } else if (isTablet) {
            scrollDistance = 290; // Tablet
        }
        
        carousel.scrollBy({
            left: -scrollDistance,
            behavior: 'smooth'
        });
    });
    
    // Scroll right
    navRight.addEventListener('click', () => {
        const isMobile = window.innerWidth <= 480;
        const isTablet = window.innerWidth <= 768;
        let scrollDistance = 420; // Desktop
        
        if (isMobile) {
            scrollDistance = 220; // Mobile with improved layout
        } else if (isTablet) {
            scrollDistance = 290; // Tablet
        }
        
        carousel.scrollBy({
            left: scrollDistance,
            behavior: 'smooth'
        });
    });
    
    // Check buttons on scroll
    carousel.addEventListener('scroll', checkScrollButtons);
    
    // Check buttons on resize
    window.addEventListener('resize', checkScrollButtons);
}

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

// Broker image error handling with fallback SVGs
function createBrokerFallbackSVG(brokerName) {
    const brokerConfigs = {
        'Binomo': { color: '#00e676', letter: 'B' },
        'Olymptrade': { color: '#1a237e', letter: 'OT' },
        'Stockity': { color: '#ffd700', letter: 'S' },
        'IQ Option': { color: '#00e676', letter: 'IQ' },
        'Quotex': { color: '#1a237e', letter: 'Q' },
        'Pocket Option': { color: '#ffd700', letter: 'PO' }
    };
    
    const config = brokerConfigs[brokerName] || { color: '#00e676', letter: 'X' };
    const textColor = config.color === '#ffd700' ? '#1a237e' : 'white';
    
    return `
        <svg width="60" height="60" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
            <rect width="120" height="120" rx="25" fill="${config.color}"/>
            <text x="60" y="70" text-anchor="middle" font-size="26" font-weight="bold" fill="${textColor}" font-family="Poppins, sans-serif">${config.letter}</text>
        </svg>
    `;
}

// Handle broker image loading
document.querySelectorAll('.broker-logo img').forEach(img => {
    img.addEventListener('load', function() {
        this.style.opacity = '1';
    });
    
    img.addEventListener('error', function() {
        const brokerName = this.alt;
        const fallbackSVG = createBrokerFallbackSVG(brokerName);
        this.parentNode.innerHTML = fallbackSVG;
    });
    
    // Set initial styles
    img.style.opacity = '0';
    img.style.transition = 'opacity 0.3s ease';
});

// Add loading animation for other images
document.querySelectorAll('img:not(.broker-logo img)').forEach(img => {
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
