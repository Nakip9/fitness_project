# Coaching Management System Design

## 1. Enhanced Database Schema (ERD)

### Core Entities and Relationships

```mermaid
erDiagram
    User ||--o{ Membership : "has"
    User ||--o{ CoachingSession : "attends"
    User ||--o{ Payment : "makes"
    User ||--o{ MembershipNote : "writes"
    User ||--o{ SessionFeedback : "provides"
    
    MembershipPlan ||--o{ Membership : "defines"
    MembershipPlan ||--o{ Payment : "for"
    
    Membership ||--o{ CoachingSession : "includes"
    Membership ||--o{ MembershipNote : "has"
    Membership ||--o{ Payment : "requires"
    
    CoachingSession ||--o{ SessionFeedback : "receives"
    CoachingSession ||--o{ SessionAttendance : "tracks"
    
    Coach ||--o{ CoachingSession : "conducts"
    Coach ||--o{ CoachAvailability : "has"
    
    User {
        int id PK
        string username
        string email
        string first_name
        string last_name
        boolean is_staff
        boolean is_coach
        datetime date_joined
    }
    
    Coach {
        int id PK
        int user_id FK
        string specialization
        text bio
        decimal hourly_rate
        boolean is_active
        datetime created_at
    }
    
    MembershipPlan {
        int id PK
        string name
        string slug
        text description
        decimal price
        int duration_days
        string billing_cycle
        boolean is_active
        boolean featured
        int max_sessions_per_week
        int session_duration_minutes
    }
    
    Membership {
        int id PK
        int user_id FK
        int plan_id FK
        int coach_id FK
        datetime start_date
        datetime end_date
        string status
        boolean auto_renew
        text coach_notes
        int postponed_remaining_days
        datetime created_at
        datetime updated_at
    }
    
    CoachingSession {
        int id PK
        int membership_id FK
        int coach_id FK
        datetime scheduled_start
        datetime scheduled_end
        datetime actual_start
        datetime actual_end
        string status
        text session_notes
        text coach_feedback
        int rating
        datetime created_at
        datetime updated_at
    }
    
    CoachAvailability {
        int id PK
        int coach_id FK
        string day_of_week
        time start_time
        time end_time
        boolean is_active
        datetime created_at
    }
    
    SessionFeedback {
        int id PK
        int session_id FK
        int author_id FK
        text content
        int rating
        boolean is_coach_feedback
        datetime created_at
    }
    
    SessionAttendance {
        int id PK
        int session_id FK
        string status
        datetime check_in_time
        datetime check_out_time
        text notes
    }
    
    MembershipNote {
        int id PK
        int membership_id FK
        int author_id FK
        text content
        boolean is_pinned
        int parent_note_id FK
        datetime created_at
    }
    
    Payment {
        int id PK
        int user_id FK
        int plan_id FK
        int membership_id FK
        decimal amount
        string currency
        string stripe_payment_intent
        string status
        datetime created_at
        datetime updated_at
    }
```

## 2. API Endpoint Structure

### Authentication & Authorization
- All endpoints require authentication
- Coach-specific endpoints require `is_staff=True` or `is_coach=True`
- Users can only access their own data unless they're coaches/staff

### Core API Endpoints

#### Membership Management
```
GET    /api/memberships/                    # List user's memberships
GET    /api/memberships/{id}/               # Get membership details
POST   /api/memberships/                    # Create new membership
PUT    /api/memberships/{id}/               # Update membership
DELETE /api/memberships/{id}/               # Cancel membership
POST   /api/memberships/{id}/postpone/      # Postpone membership
POST   /api/memberships/{id}/resume/        # Resume postponed membership
```

#### Session Management
```
GET    /api/sessions/                       # List sessions (filtered by user/coach)
GET    /api/sessions/{id}/                  # Get session details
POST   /api/sessions/                       # Schedule new session
PUT    /api/sessions/{id}/                  # Update session
DELETE /api/sessions/{id}/                  # Cancel session
POST   /api/sessions/{id}/reschedule/       # Reschedule session
POST   /api/sessions/{id}/checkin/          # Check-in to session
POST   /api/sessions/{id}/checkout/         # Check-out from session
```

#### Coach Management
```
GET    /api/coaches/                        # List available coaches
GET    /api/coaches/{id}/                   # Get coach details
GET    /api/coaches/{id}/availability/      # Get coach availability
POST   /api/coaches/{id}/availability/      # Set coach availability
PUT    /api/coaches/{id}/availability/{av_id}/ # Update availability slot
DELETE /api/coaches/{id}/availability/{av_id}/ # Remove availability slot
GET    /api/coaches/{id}/schedule/          # Get coach's schedule
```

#### Communication & Feedback
```
GET    /api/memberships/{id}/notes/         # Get membership notes/comments
POST   /api/memberships/{id}/notes/         # Add note/comment
PUT    /api/notes/{id}/                     # Update note
DELETE /api/notes/{id}/                     # Delete note
POST   /api/notes/{id}/pin/                 # Pin/unpin note

GET    /api/sessions/{id}/feedback/         # Get session feedback
POST   /api/sessions/{id}/feedback/         # Add session feedback
PUT    /api/feedback/{id}/                  # Update feedback
```

#### Payment & Notifications
```
POST   /api/payments/                       # Create payment intent
POST   /api/payments/{id}/confirm/          # Confirm payment
GET    /api/payments/                       # List user payments
POST   /api/notifications/send/             # Send notification (coach only)
```

## 3. Logic Flowcharts

### A. Session Scheduling Logic (Conflict Prevention)

```mermaid
flowchart TD
    A[Coach attempts to schedule session] --> B[Extract proposed start/end times]
    B --> C[Query existing ACTIVE sessions for coach]
    C --> D{Any existing sessions?}
    
    D -->|No| H[Save session]
    D -->|Yes| E[Check each existing session for overlap]
    
    E --> F{Overlap detected?<br/>proposed_start < existing_end AND<br/>proposed_end > existing_start}
    
    F -->|Yes| G[Reject with conflict error<br/>Show conflicting session details]
    F -->|No| I{More sessions to check?}
    
    I -->|Yes| E
    I -->|No| H
    
    H --> J[Send confirmation to trainee]
    J --> K[Update trainee dashboard]
    
    G --> L[Suggest alternative time slots]
```

### B. Payment Processing & Automation Flow

```mermaid
flowchart TD
    A[User initiates payment] --> B[Create Stripe Payment Intent]
    B --> C[User completes payment]
    C --> D{Payment successful?}
    
    D -->|No| E[Update payment status to 'failed']
    D -->|Yes| F[Update payment status to 'succeeded']
    
    F --> G[Activate membership]
    G --> H[Set membership status to 'active']
    H --> I[Calculate end_date based on plan duration]
    I --> J[Generate confirmation email]
    
    J --> K[Email includes:<br/>- Plan details<br/>- Schedule info<br/>- Payment confirmation<br/>- Next steps]
    
    K --> L[Send email to user]
    L --> M[Log notification in system]
    M --> N[Update user dashboard]
    
    E --> O[Send payment failure notification]
    O --> P[Retry payment flow]
```

### C. Membership Lifecycle Management

```mermaid
flowchart TD
    A[Membership Created] --> B[Status: 'pending']
    B --> C{Payment received?}
    
    C -->|No| D[Remain pending]
    C -->|Yes| E[Status: 'active']
    
    E --> F[Coach schedules sessions]
    F --> G[Trainee sees dashboard updates]
    
    G --> H{Lifecycle action?}
    
    H -->|Postpone| I[Status: 'postponed'<br/>Freeze remaining days<br/>Clear scheduled times]
    H -->|Cancel| J[Status: 'canceled'<br/>Stop countdown]
    H -->|Resume| K[Status: 'active'<br/>Restore remaining days<br/>Allow rescheduling]
    H -->|Expire| L[Status: 'expired'<br/>Auto-renewal check]
    
    I --> M[Coach notification:<br/>Trainee postponed]
    J --> N[Refund processing<br/>if applicable]
    K --> O[Coach notification:<br/>Trainee resumed]
    L --> P{Auto-renew enabled?}
    
    P -->|Yes| Q[Process renewal payment]
    P -->|No| R[Send expiration notice]
    
    Q --> S{Renewal successful?}
    S -->|Yes| E
    S -->|No| R
```

## 4. Enhanced Models Implementation

The enhanced models will include:

1. **Coach Model**: Extends User with coaching-specific fields
2. **CoachingSession Model**: Manages individual training sessions
3. **CoachAvailability Model**: Defines when coaches are available
4. **SessionFeedback Model**: Bi-directional feedback system
5. **Enhanced MembershipNote Model**: Threaded comments with pinning
6. **SessionAttendance Model**: Check-in/check-out tracking

## 5. Key Features Implementation

### Automated Conflict Prevention
- Server-side validation in `CoachingSession.clean()`
- Real-time availability checking via API
- Conflict resolution suggestions

### Trainee Transparency Dashboard
- Real-time session updates
- Payment status tracking
- Progress visualization
- Communication history

### Dynamic Lifecycle Management
- State machine for membership status
- Automated notifications for state changes
- Flexible rescheduling with conflict prevention

### Transactional Automation
- Webhook integration with Stripe
- Automated email generation
- Payment confirmation workflows

### Interactive Feedback Loop
- Threaded comment system
- Pinned coach directives
- Real-time messaging interface
- Context-aware notifications

## 6. Security & Performance Considerations

- Row-level security for data access
- Optimized queries with select_related/prefetch_related
- Caching for frequently accessed data
- Rate limiting on API endpoints
- Input validation and sanitization
- CSRF protection for state-changing operations