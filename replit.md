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