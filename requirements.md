# Project Requirements: SplitWise Pro (PWA)

## Overview
Build a fast, offline-capable Progressive Web App (PWA) called **SplitWise Pro**.
It simplifies expense tracking and group bill sharing for friends, roommates, and small travel groups.
The focus is on ease of use, instant calculations, and seamless synchronization.

## Target Users
- Friends splitting living expenses
- Travel groups (vacations, road trips)
- Small social clubs or events

## Core Features

### 1. Authentication & Users
- Email/password or OAuth (Google/Apple) login
- User profile with avatar and default currency setting
- Manage contact lists/friends for easy bill splitting

### 2. Groups
- Create/edit groups (e.g., "Trip to Japan", "Apartment Bills")
- Group-level expense history
- Total balance breakdown for the group (who owes whom)
- Leave/Archive group functionality

### 3. Expense Management
- Add expense: amount, description, date, payer, split type (equal, exact amounts, percentages, shares)
- Upload receipt images (OCR support preferred)
- Expense categories (Food, Rent, Travel, Utilities, etc.)
- Comment on expenses for clarification

### 4. Settlement
- Record a payment (settle debt)
- Suggest optimal repayment plans (minimizing number of transactions)
- Payment reminders/notifications for overdue debts

### 5. Dashboard
- Total balance across all groups (I owe / I am owed)
- Recent activity feed
- "Owe/Owed" summary per friend
- Quick-add expense button

### 6. PWA & Offline Functionality
- Offline-first architecture (Service Workers, IndexedDB)
- Background sync once back online
- Installable via browser (Add to Home Screen)
- Push notifications for new expenses/settlements

## Tech Stack
- **Frontend**: React 18 + Vite + TypeScript
- **Styling**: Tailwind CSS + shadcn/ui
- **State**: Zustand (with Persist middleware)
- **Routing**: React Router v6
- **Offline/PWA**: Workbox + Vite PWA plugin
- **Database (Client)**: Dexie.js (IndexedDB)
- **HTTP**: Axios + React Query (TanStack Query)
- **Backend**: Node.js + Express (REST API)
- **Auth**: JWT + bcrypt + Passport.js
- **Database (Server)**: PostgreSQL + Prisma ORM
- **Deployment**: Docker + Nginx + HTTPS (Mandatory for PWA)

## Non-Functional Requirements
- Offline-first capability: App must function without network
- Responsive mobile-first design
- Fast initial load (< 1s)
- Accessibility: WCAG 2.1 AA
- Secure data handling (HTTPS, secure cookies)

## API Endpoints Required
- `POST /api/auth/login`
- `POST /api/auth/register`
- `GET  /api/groups`
- `POST /api/groups`
- `GET  /api/groups/:id/expenses`
- `POST /api/expenses`
- `POST /api/settlements`
- `GET  /api/user/balances`
- `GET  /api/notifications`

## Pages / Routes
- `/login` / `/register` — Authentication
- `/dashboard` — Main balance summary
- `/groups` — List of groups
- `/groups/:id` — Group details and activity
- `/groups/:id/add-expense` — Add expense form
- `/activity` — Global activity log
- `/settings` — Profile and currency preferences

## Design Preferences
- Very clean, minimalist, high-contrast mobile UI
- "Soft" color palette (Green/Teal for "Money/Success", Red/Orange for "Alerts")
- Bottom navigation bar (Mobile pattern)
- Fast, tactile transitions (swipe to settle)


## How to run in windows ##
1) python -m venv .venv
2) .venv\Scripts\Activate.ps1 
3) pip install -r requirements.txt
4) python main.py requirements.md 

## How to run in mac ##
1) python3 -m venv .venv
2) source .venv/bin/activate     
3) pip install -r requirements.txt
4) python3 main.py requirements.md 