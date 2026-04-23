# Master System Prompt: Bespoke 1-on-1 Personal Training Platform

Build a robust, professional Django-based web application for an elite Personal Trainer. The platform must move away from a "gym membership" model and strictly follow a **Bespoke Request -> Coach Approval -> Payment -> Active Coaching** lifecycle.

## Core Architectural Requirements

### 1. Conflict-Free Scheduling Engine (The "Coach First" Logic)
- **Constraint:** When a coach assigns a specific time to a trainee, the system MUST verify that the slot is not already booked by another active trainee.
- **Implementation:** Implement model-level validation (`clean()` method) to prevent overlapping sessions for the same coach on the same day and time, considering a set session duration.
- **Workflow:** The coach assigns the time during the approval phase; the system blocks the save if a conflict exists.

### 2. The "Request & Approve" Lifecycle
- **Status Machine:** Implement the following statuses: `requested`, `approved_pending_payment`, `active`, `postponed`, `canceled`, `expired`.
- **Transparency:** All status changes must be immediately visible to the client on their "Training Hub" dashboard.
- **UI:** Trainees submit a request with their goals and preferred times. They CANNOT pay until the coach assigns a time and approves the request.

### 3. Client Transparency & The "Training Hub"
- **Visibility:** Once active, the client must see their full schedule (Day, Time, Duration), their coach's name, and their plan progress.
- **Interactivity:** The client needs a "Negotiate Schedule" option to propose time changes, and buttons to request "Postponement" or "Cancellation."

### 4. Automated Success Workflow (Post-Payment)
- **Email Trigger:** Integrate a system (e.g., Django signals) that fires when a payment is marked as successful.
- **Content:** The email must contain:
    - Confirmation of payment.
    - Full details of the plan contents.
    - The specific assigned coaching schedule (Day/Time/Duration).
    - A personalized welcome message.

### 5. Interactive "Coach's Notebook" (Two-Way Communication)
- **Mechanism:** Within the active plan view, provide a dedicated "Notes/Comments" section.
- **Roles:** 
    - **Coach:** Can post "Priority Reminders" or "Training Notes" that are pinned or highlighted for the trainee.
    - **Trainee:** Can post progress updates, questions, or comments.
- **Persistence:** All notes must be saved chronologically to create a training history.

### 6. Design & Branding Philosophy
- **Persona:** Professional, elite, results-oriented 1-on-1 coach.
- **Aesthetic:** Clean, modern, high-contrast (prefer Glassmorphism or dark/light sleek themes). 
- **Copywriting:** Strip all references to "gym," "locker rooms," or "classes." Use terms like "Bespoke Coaching," "Form Correction," "Nutrition Protocols," and "1-on-1 Transformation."

## Technical Stack Preferences
- **Backend:** Django (Python) with a focus on clean model-view-controller separation.
- **Database:** SQLite for prototyping, ready for PostgreSQL.
- **Frontend:** Django Templates + Bootstrap 5 + Custom CSS (avoid Tailwind unless specified).
- **Payment:** Stripe integration foundation for the "Pay Now" flow.
