# AUTO TRADE VIP

## Overview
AUTO TRADE VIP is a Flask-based web application designed as a landing page for a trading robot platform. It markets automated trading solutions for various binary options brokers (Binomo, Olymptrade, IQ Option, Quotex, and Pocket Option). The primary purpose is to serve as a promotional website, showcasing trading packages, and facilitating customer contact for lead generation in automated trading services.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
The frontend utilizes a server-side rendered architecture with Flask and Jinja2 templates. It employs Bootstrap 5.3.0 for responsive design, custom CSS with CSS variables for theming (including dark mode), Font Awesome 6.4.0 for iconography, and Google Fonts (Poppins) for typography. Interactive features like smooth scrolling and scroll effects are implemented with vanilla JavaScript. The design follows a single-page application pattern with dedicated sections for hero, packages, and contact information.

### Backend Architecture
The backend is built with Flask, providing HTTP request handling and template rendering. It integrates PostgreSQL via Flask-SQLAlchemy for data persistence and Flask-Login for user authentication and session management. Password hashing is handled using Werkzeug security utilities. Broker and package information are managed as static Python dictionaries. The system includes REST API endpoints for user login, registration, and logout functionalities.

### Design Patterns
Key design patterns include the use of static data for fixed content, environment variables for sensitive configurations, and a mobile-first responsive design approach using the Bootstrap grid system.

### Core Features
- Integrated login and registration system with a modal interface.
- User management with Flask-Login and PostgreSQL, including user profiles (name, gender, country).
- Dynamic transparent navbar with scroll effects, an animated logo, and hover effects.
- Scroll progress bar.
- Professional UI/UX with consistent ATV theme colors, modern gradient styling, and smooth animations across various components (buttons, modals, forms).
- Three-form system for Login, Register, and Forgot Password with seamless transitions.
- Redesigned dashboard with a clean white theme and simplified navigation structure.
- Displays current trading session information (Sydney, Tokyo, London, New York) in the client's local timezone.
- Professional drag & drop file upload for signal input, supporting CSV, TXT, and JSON formats.
- Manual signal input processing with support for multiple formats (e.g., "CALL,1" and "YYYY-MM-DD HH:MM:SS,PAIR,CALL/PUT,TIMEFRAME").
- Simplified trading robot (`iq_trading_robot.py`) focused exclusively on manual signal input, removed complex strategies (martingale, technical analysis, OTC assets).
- Trading bot configuration managed via a `TradingBotConfig` dataclass for consistency between the HTML form and robot execution.
- Enhanced trading order system with asset variants (e.g., EURUSD, EURUSD-OTC) for improved order success rates.
- Signal parsing prioritizes asset from signal content over form fields.
- Execution scheduler for signals with future timestamps.

## External Dependencies

### Frontend Libraries
- **Bootstrap 5.3.0**: UI framework (via CDN)
- **Font Awesome 6.4.0**: Icon library (via CDN)
- **Google Fonts**: Poppins font family (via CDN)

### Python Dependencies
- **Flask**: Web application framework
- **Flask-SQLAlchemy**: ORM for PostgreSQL integration
- **Flask-Login**: User session management and authentication
- **Werkzeug**: Security utilities (for password hashing)

### Third-party Assets
- **Broker Logos**: External image URLs used for branding.