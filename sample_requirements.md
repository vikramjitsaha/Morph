# Project Requirements: TaskFlow Pro

## Overview
Build a modern project management and task tracking web application called **TaskFlow Pro**.
It allows teams to create projects, manage tasks with Kanban boards, track time,
and collaborate in real-time with comments and file attachments.

## Target Users
- Small to medium development teams (5-50 people)
- Project managers, developers, designers

## Core Features

### 1. Authentication & Users
- Email/password login and registration
- JWT-based authentication
- User profile with avatar upload
- Role-based access: Admin, Manager, Member

### 2. Projects
- Create / edit / archive projects
- Project cover image and colour theme
- Project members management
- Project-level statistics (completion %, open tasks, overdue)

### 3. Task Management
- Kanban board with drag-and-drop columns (Todo, In Progress, Review, Done)
- Create tasks with: title, description, assignees, due date, priority (Low/Medium/High/Critical), labels/tags
- Sub-tasks (checklist items)
- Task comments with @mentions
- File attachments (images, docs)
- Activity log per task

### 4. Dashboard
- Overview cards: total projects, open tasks, tasks due today, overdue tasks
- Bar chart: tasks completed per week (last 8 weeks)
- Pie chart: tasks by status
- Recent activity feed
- My assigned tasks list

### 5. Notifications
- In-app notification bell
- Notifications for: task assignment, due-date reminder, comment mention, status change

### 6. Time Tracking
- Start/stop timer on tasks
- Manual time entry
- Time log per task
- Weekly time report per user

## Tech Stack
- **Frontend**: React 18 + Vite + TypeScript
- **Styling**: Tailwind CSS + shadcn/ui
- **State**: Zustand
- **Routing**: React Router v6
- **Charts**: Recharts
- **Drag & Drop**: @dnd-kit/core
- **Forms**: React Hook Form + Zod
- **HTTP**: Axios + React Query (TanStack Query)
- **Backend**: Express.js REST API (Node.js) with mock data layer
- **Auth**: JWT + bcrypt
- **Database**: PostgreSQL (schema only, mocked in frontend)
- **Deployment**: Docker + Docker Compose + Nginx

## Non-Functional Requirements
- Fully responsive (mobile-first)
- Dark/light mode toggle
- Page load < 2s
- Accessibility: WCAG 2.1 AA
- Test coverage > 80%

## API Endpoints Required
- `POST /api/auth/login`
- `POST /api/auth/register`
- `GET  /api/auth/me`
- `GET  /api/projects`
- `POST /api/projects`
- `GET  /api/projects/:id`
- `PUT  /api/projects/:id`
- `GET  /api/projects/:id/tasks`
- `POST /api/tasks`
- `PUT  /api/tasks/:id`
- `DELETE /api/tasks/:id`
- `GET  /api/tasks/:id/comments`
- `POST /api/tasks/:id/comments`
- `GET  /api/dashboard/stats`
- `GET  /api/notifications`
- `PUT  /api/notifications/:id/read`
- `POST /api/time-entries`
- `GET  /api/time-entries?userId=&week=`

## Pages / Routes
- `/login` — Login page
- `/register` — Registration page
- `/` — Dashboard (protected)
- `/projects` — Projects list
- `/projects/:id` — Kanban board for project
- `/tasks/:id` — Task detail modal/page
- `/profile` — User profile
- `/notifications` — Notifications
- `/reports` — Time tracking reports

## Design Preferences
- Clean, modern, professional look
- Navy + teal accent colour palette OR dark mode by default
- Sidebar navigation
- Card-based layout
- Smooth animations on transitions
