# AUTO TRADE VIP

## Overview

AUTO TRADE VIP is a Flask-based web application serving as a landing page for a trading robot platform. The application markets automated trading solutions for various binary options brokers including Binomo, Olymptrade, IQ Option, Quotex, and Pocket Option. It's designed as a promotional website to showcase trading packages and facilitate customer contact.

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes

- **January 7, 2025**: Successfully migrated project from Replit Agent to standard Replit environment
- **January 7, 2025**: Fixed MetaTrader4 and TradingView icon sizing inconsistencies (reduced from 48px to 36px)
- **January 7, 2025**: Implemented consistent hover effects and color treatment for all feature icons
- **January 7, 2025**: Enhanced feature icon styling with proper white color filtering and scaling animations
- **January 7, 2025**: Fixed hover effect for MetaTrader4 and TradingView icons to turn black on click/hover like Automated Trade icon
- **January 7, 2025**: Added dynamic transparent navbar effect - becomes more transparent when scrolling with enhanced blur effects
- **January 7, 2025**: Implemented scroll progress bar (reading progress indicator) at the top of the page with gradient colors
- **January 7, 2025**: Added integrated login system with modal interface - users can login/register without leaving landing page
- **January 7, 2025**: Implemented Flask-Login authentication with PostgreSQL database for user management
- **January 7, 2025**: Added user dropdown menu in navbar for logged-in users with profile and logout options
- **January 7, 2025**: Professional navbar redesign with gradient background, animated logo, and hover effects
- **January 7, 2025**: Enhanced login system - simple email/password login, comprehensive registration with name, gender, country fields
- **January 7, 2025**: Updated User model to include name, gender, country, and created_at timestamp fields
- **January 7, 2025**: Added official AUTO TRADE VIP logo to navbar from autotradevip.com
- **January 7, 2025**: Enhanced navbar mobile responsiveness with collapsible menu and improved spacing
- **August 7, 2025**: Successfully completed project migration from Replit Agent to standard Replit environment
- **August 7, 2025**: Fixed ATV logo display issue with inline styling and proper path configuration
- **August 7, 2025**: Implemented single active menu state management to prevent duplicate navbar effects
- **August 7, 2025**: Enhanced navbar active state with scroll-based detection and click handling
- **August 7, 2025**: Resolved logo ATV duplicate display bug and stabilized logo rendering
- **August 7, 2025**: Redesigned login button with modern gradient styling and hover animations
- **August 7, 2025**: Fixed JavaScript querySelector errors in navbar active state management
- **August 7, 2025**: Optimized button sizing for professional appearance with proper proportions
- **August 7, 2025**: Redesigned login modal with ultra-professional styling and consistent ATV theme colors
- **August 7, 2025**: Created dedicated login-modal.css with modern gradient effects and smooth animations
- **August 7, 2025**: Implemented sophisticated form styling with backdrop blur and color consistency
- **August 7, 2025**: Enhanced form toggle functionality with improved JavaScript error handling
- **August 7, 2025**: Added Forgot Password functionality with professional styling and backend integration
- **August 7, 2025**: Implemented three-form system (Login, Register, Forgot Password) with smooth transitions
- **August 7, 2025**: Created forgot-password API endpoint with email validation and user verification
- **August 8, 2025**: Redesigned navigation sidebar with modern professional structure
- **August 8, 2025**: Implemented organized navigation sections (Main, Trading, Account) with enhanced visual design
- **August 8, 2025**: Added navigation icons with containers, titles, descriptions, and smooth animations
- **August 8, 2025**: Enhanced sidebar branding with integrated logo and user profile section
- **August 8, 2025**: Updated sidebar from basic list to modern card-style navigation with gradient effects
- **August 8, 2025**: Complete dashboard redesign with professional clean white theme instead of dark theme
- **August 8, 2025**: Redesigned navigation from complex sidebar to simple clean menu structure
- **August 8, 2025**: Implemented new header design with toggle button and notification system
- **August 8, 2025**: Changed color scheme from dark green gradients to clean professional white/gray design
- **August 8, 2025**: Simplified navigation JavaScript and removed complex mobile menu system
- **August 8, 2025**: Updated dashboard layout to be more traditional and user-friendly
- **August 8, 2025**: Successfully completed project migration from Replit Agent to standard Replit environment
- **August 8, 2025**: Configured PostgreSQL database with proper environment variables
- **August 8, 2025**: Removed "High Volume Trading Times" section from bot settings page per user request
- **August 8, 2025**: Updated Trading Session Information to display 4 complete forex sessions (Sydney, Tokyo, London, New York) with accurate UTC times and major pairs
- **August 8, 2025**: Fixed time format to use AM/PM instead of 24-hour format for better readability in trading sessions
- **August 8, 2025**: Simplified Trading Session Information to single box layout and removed Major Pairs information per user request
- **August 8, 2025**: Changed trading sessions to show only the currently active session instead of displaying all 4 sessions at once
- **August 8, 2025**: Updated trading session times to display in client's local timezone instead of UTC per user request
- **August 8, 2025**: Successfully completed project migration from Replit Agent to Replit environment with PostgreSQL database configuration
- **August 8, 2025**: Moved Trading Session Information from sidebar to main header area for better visibility and accessibility
- **August 8, 2025**: Fixed trading session priority logic to properly display New York Session when overlapping with London Session (13-22 UTC prioritized over 8-17 UTC)
- **August 8, 2025**: Updated Signal Type example format from "CALL OR PUT" to "CALL,1" format per user request
- **August 8, 2025**: Added professional drag & drop file upload functionality for signal input feature
- **August 8, 2025**: Implemented signal content textarea with monospace font and CSV/TXT/JSON file support
- **August 8, 2025**: Added clear signals functionality and automatic file content processing with notifications

## System Architecture

### Frontend Architecture
The application uses a traditional server-side rendered architecture with Flask serving HTML templates. The frontend is built with:

- **Template Engine**: Jinja2 templates for dynamic content rendering
- **UI Framework**: Bootstrap 5.3.0 for responsive design and component styling
- **Styling**: Custom CSS with CSS variables for consistent theming and dark mode design
- **Icons**: Font Awesome 6.4.0 for iconography
- **Typography**: Google Fonts (Poppins) for consistent font styling
- **JavaScript**: Vanilla JavaScript for interactive features like smooth scrolling and scroll effects

The design follows a single-page application pattern with sections for hero, packages, and contact information.

### Backend Architecture
The backend is built using Flask with authentication capabilities:

- **Web Framework**: Flask for HTTP request handling and template rendering
- **Database**: PostgreSQL with SQLAlchemy ORM for data persistence
- **Authentication**: Flask-Login for session management and user authentication
- **Session Management**: Flask sessions with environment-configurable secret key
- **Data Structure**: Static data structures for broker and package information stored in Python dictionaries
- **API Endpoints**: REST endpoints for login, register, and logout functionality
- **Security**: Password hashing using Werkzeug security utilities

### Design Patterns
- **Static Data**: Broker and package information is hardcoded in the main route handler, indicating this is a promotional site with fixed content
- **Environment Configuration**: Uses environment variables for sensitive configuration like session secrets
- **Responsive Design**: Mobile-first approach with Bootstrap grid system

### Hosting Configuration
The application is configured for deployment with:
- Host binding to 0.0.0.0 for container compatibility
- Port 5000 for web traffic
- Debug mode enabled for development

## External Dependencies

### Frontend Libraries
- **Bootstrap 5.3.0**: UI framework via CDN for responsive design
- **Font Awesome 6.4.0**: Icon library via CDN
- **Google Fonts**: Poppins font family for typography

### Python Dependencies
- **Flask**: Web application framework
- **Flask-SQLAlchemy**: Database ORM for PostgreSQL integration
- **Flask-Login**: User session management and authentication
- **Werkzeug**: Security utilities for password hashing
- **Standard Library**: os module for environment variable access

### Third-party Assets
- **Broker Logos**: External image URLs from various sources (Google Images, Play Store) for broker branding
- **CDN Dependencies**: All frontend libraries loaded from public CDNs

The application currently has no database dependencies, authentication systems, or external API integrations, making it a lightweight promotional website focused on lead generation for trading services.