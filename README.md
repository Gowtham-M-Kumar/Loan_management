Loan Management System

A robust and secure Django-based platform designed for managing the entire lifecycle of gold loans. This system streamlines customer onboarding, gold item appraisal, interest tracking, and payment processing with a focus on accuracy and financial security.

## 🚀 Key Features

### 1. Customer Management & KYC
- **Onboarding**: Comprehensive customer registration with localized data fields.
- **Identity Verification**: Built-in validation for Aadhaar (12 digits) and Mobile numbers.
- **KYC Documentation**: Upload and manage customer photos and digital copies of ID proofs (PAN, Aadhaar, Voter ID, etc.).
- **Unique IDs**: Automatic generation of unique Customer IDs (e.g., `PG000001`).

### 2. Loan Management Lifecycle
- **Step-by-Step Entry**: A guided 5-step workflow for loan creation:
    1. Customer Selection/Creation
    2. Gold Item Details & Appraisal
    3. Document Upload
    4. Data Verification
    5. Final Approval & Summary
- **Loan States**: Track loans through `Draft`, `Active`, and `Closed` statuses.
- **Extensions & Closures**: Structured workflows for extending loan periods or closing loans with full financial audits.

### 3. Financial Engine
- **Interest Calculation**: Sophisticated interest logic featuring **Yearly Capitalization** (Interest is added to principal annually).
- **Payment Decomposition**: Automatically splits payments into Principal and Interest components.
- **Simulation Tool**: Built-in interest simulator to project future outstanding balances for any given date.
- **Expense Tracking**: Log internal loan-related expenses for better margin analysis.

### 4. Inventory Tracking
- **Gold Appraisal**: Detailed tracking of gold items including Carat (18K, 20K, 22K, 24K), Gross Weight, and Approved Net Weight.
- **Visual Evidence**: Multi-image upload support for gold items to ensure transparency.
- **Lot Management**: Automated Lot number generation for physical storage tracking.

### 5. internal Pledge Management (Admin Only)
- **Secondary Pledging**: Track when the company pledges gold to external banks.
- **Margin Monitoring**: Manage external interest rates, bank addresses, and pledge receipts.
- **Adjustments**: Log adjustments and profit markers within secondary pledges.

### 6. Security & Documentation
- **OTP Verification**: Critical actions (Loan Creation, Extension, and Closure) are secured with OTP verification via **Twilio**.
- **Automated Receipts**: Instant generation of professional receipts for:
    - Loan Approvals
    - Payments (Interest/Principal)
    - Final Loan Closures
- **Audit Logs**: Traceable payment history and documentation for every transaction.

## 🛠️ Technical Stack

- **Backend**: Python 3.12+ / Django 6.0
- **Database**: SQLite (Default)
- **Frontend**: Vanilla HTML5, CSS3, and JavaScript (No heavy frameworks for maximum performance).
- **Communications**: Twilio Verify API for secure SMS OTP delivery.
- **Environment**: Decoupled configuration using `.env`.

## ⚙️ Setup & Installation

1. **Clone the Repository**:
   ```bash
   git clone <repository-url>
   cd PUNNAGAI-GOLD-LOAN
   ```

2. **Set Up Virtual Environment**:
   ```bash
   python -m venv env
   source env/bin/activate  # Mac/Linux
   # or
   .\env\Scripts\activate  # Windows
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**:
   Create a `.env` file in the root directory and add your credentials:
   ```env
   DEBUG=True
   SECRET_KEY=your-django-secret-key
   TWILIO_ACCOUNT_SID=your-sid
   TWILIO_AUTH_TOKEN=your-token
   TWILIO_VERIFY_SERVICE_SID=your-service-sid
   OTP_ADMIN_MOBILE=your-admin-number
   ```

5. **Database Setup**:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

6. **Run the Server**:
   ```bash
   python manage.py runserver
   ```

## 🚀 Deployment

This project is ready to deploy on various platforms directly from GitHub!

### Quick Deploy Options:
- **Heroku**: One-click deployment with Procfile included
- **Railway**: Automatic deployment with railway.json
- **Render**: Free hosting with render.yaml configuration
- **PythonAnywhere**: Step-by-step manual deployment

📖 **[Read the complete deployment guide →](DEPLOYMENT.md)**

The deployment guide covers:
- Environment variable configuration
- Platform-specific setup instructions
- Database configuration (PostgreSQL support)
- Post-deployment steps
- Troubleshooting tips

### GitHub Actions CI/CD
This repository includes automated testing and security checks that run on every push via GitHub Actions.

## 📂 Project Structure

- `gold_loan/`: The core application containing models, views for the 5-step entry, interest logic, and templates.
- `gold_loan_project/`: Project-level settings, URL routing, and WSGI/ASGI configurations.
- `media/`: Storage for customer photos, item images, and documents.
- `static/`: Global CSS/JS assets and organized app-specific styles.

## 📄 License

This project is proprietary. All rights reserved.
