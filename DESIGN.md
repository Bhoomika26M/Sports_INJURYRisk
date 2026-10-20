# Sports Injury Risk Detection - UI Design Document

## Overview
This document details all pages, components, and UI requirements for the Sports Injury Risk Detection application frontend revamp.

---

## Page Structure & Components

### 1. Landing Page (Not Implemented)
**Purpose**: Public-facing landing page for marketing
**Current Status**: Not implemented
**Planned Components**:
- Hero section with CTA
- Feature highlights
- Role-based feature preview
- Sign up / Login buttons

---

### 2. Login Page (`/login`)
**Purpose**: User authentication
**Current Components**:
- Email input field
- Password input field
- Submit button
- Link to registration
- Link to forgot password
- Error message display

**Current Issues**:
- Basic styling with Tailwind
- No password visibility toggle
- No "Remember me" checkbox
- No social login options
- Minimal branding

**Design Requirements**:
- **Hero/Branding Section**:
  - App logo/icon
  - App name "Sports Injury Risk Detection"
  - Tagline: "AI-Powered Movement Analysis for Athletes"
  - Sports-themed background or gradient

- **Form Container**:
  - Centered card with shadow
  - Rounded corners (8-12px)
  - Clean white background
  - Max width: 400-450px

- **Form Fields**:
  - Email input with email icon
  - Password input with eye icon (toggle visibility)
  - Floating labels or clear placeholder text
  - Focus states with brand color accent
  - Error state styling (red border, error message below field)

- **Additional Features**:
  - "Remember me" checkbox
  - "Forgot password?" link
  - Social login buttons (Google, etc.)
  - Demo account quick-login button (for development)

- **Footer**:
  - Link to Register
  - Privacy policy link
  - Terms of service link

---

### 3. Register Page (`/register`)
**Purpose**: New user registration
**Current Components**:
- Full name input
- Email input
- Password input
- Role dropdown (athlete, coach, physiotherapist, sports_scientist, administrator)
- Athlete-specific fields (conditional):
  - Sport type dropdown (8 sports supported)
  - Position dropdown (dynamic based on sport)
  - Age number input
  - Height (cm) number input
  - Weight (kg) number input
- Submit button
- Link to login
- Error message display

**Current Issues**:
- Long form (8+ fields) can be overwhelming
- No form validation indicators
- No password strength meter
- No role information/help tooltips
- Athlete fields appear suddenly when athlete role selected

**Design Requirements**:
- **Hero/Branding Section**:
  - App logo/icon
  - "Create your account" heading
  - Role selection guidance

- **Form Layout**:
  - Multi-step form or organized sections:
    - Section 1: Account Info (name, email, password)
    - Section 2: Role Selection
    - Section 3: Athlete Details (conditional)
  - Progress indicator for multi-step

- **Enhanced Form Fields**:
  - Full name with icon
  - Email with icon
  - Password with eye icon + strength meter
  - Role dropdown with descriptions:
    - Athlete: "View your own data and injury history"
    - Coach: "Manage athletes and training programs"
    - Physiotherapist: "Access injury-related information"
    - Sports Scientist: "View analysis-ready data"
    - Administrator: "Full system access"
  - Athlete fields with icons

- **Validation & Feedback**:
  - Real-time password strength indicator
  - Email format validation indicator
  - Field-level error messages
  - Success animations

- **Footer**:
  - Link to Login
  - Terms & Conditions checkbox
  - Privacy Policy checkbox

---

### 4. Forgot Password Page (`/forgot-password`)
**Purpose**: Password reset via OTP
**Current Components**:
- Email input (Step 1)
- OTP input (Step 2)
- New password input (Step 2)
- Confirm password input (Step 2)
- Resend code button with countdown
- Back to login link
- Error/success messages

**Current Issues**:
- Minimal styling
- No visual code input boxes
- No security education
- No branding

**Design Requirements**:
- **Header**:
  - Lock icon
  - "Reset your password" heading
  - Step indicator (Step 1 of 2)

- **Step 1 - Email**:
  - Email input with envelope icon
  - "Send verification code" button
  - Security note: "For security, we'll send a 6-digit code to your email"
  - Back to login link

- **Step 2 - Reset**:
  - 6-digit OTP input with visual boxes (6 separate inputs)
  - Auto-focus next box
  - Paste support
  - New password with strength meter
  - Confirm password with match indicator
  - "Reset password" button
  - "Resend code" with countdown timer
  - Success message after reset

- **Security Features**:
  - Code expires in 5 minutes notification
  - One-time use only
  - No account enumeration (generic response)

---

### 5. Dashboard (`/dashboard`)
**Purpose**: Main dashboard with stats and feature access
**Current Components**:
- Welcome message with user name and role
- Stats cards (4 cards):
  - Total Athletes
  - Total Videos
  - Processed Videos
  - Current Milestone
- Feature grid (7 features):
  - Athlete Management (available)
  - Video Upload (available)
  - Movement Analysis (Milestone 2 - disabled)
  - Biomechanical Assessment (Milestone 2 - disabled)
  - Injury Risk Prediction (Milestone 3 - disabled)
  - Dataset Integration (available)
  - Recommendation Engine (Milestone 3 - disabled)

**Current Issues**:
- Emoji icons are inconsistent
- Feature cards look plain
- No charts or visualizations
- No recent activity feed
- Milestone 2 features disabled but not visually distinct

**Design Requirements**:
- **Header Section**:
  - User avatar or profile icon
  - Welcome message: "Welcome back, [Name]"
  - Role badge (colored by role)
  - Last login time
  - Quick actions dropdown

- **Stats Cards** (improved):
  - Total Athletes: Icon + number + trend indicator (↑ 12% this month)
  - Total Videos: Icon + number + trend indicator
  - Processed Videos: Icon + number + completion rate
  - Processing Queue: Icon + number (new feature)
  - Use consistent icon library (Lucide React, Heroicons, or custom SVG icons)

- **Quick Actions**:
  - Upload Video button (prominent CTA)
  - Add Athlete button
  - View Reports button

- **Recent Activity Feed**:
  - Timeline of recent actions:
    - "You uploaded video for ATH001"
    - "Analysis completed for ATH002"
    - "Coach added new athlete ATH003"
  - Filter by: All, Uploads, Analyses, Athletes

- **Feature Grid** (improved):
  - 3-column grid layout
  - Each feature card:
    - Icon (color-coded by category)
    - Title
    - Description
    - Status badge (Available, Coming Soon, In Progress)
    - Access button or Coming Soon badge
  - Hover effects and animations

- **Charts Section**:
  - Weekly activity chart (videos uploaded/processed)
  - Athlete distribution by sport type
  - Processing success rate

- **Milestone Progress**:
  - Visual progress bar for current milestone
  - "Milestone 2: Video Analysis - 75% complete"

---

### 6. Athlete List Page (`/athletes`)
**Purpose**: List and manage athlete profiles
**Current Components**:
- Page header with title and "Add Athlete" button (coaches/therapists/admins only)
- Add Athlete form (toggled):
  - Athlete ID input
  - Sport type input
  - Position input
  - Age input
  - Height (cm) input
  - Weight (kg) input
  - Injury history textarea
  - Training load input
- Athlete list (cards or list items):
  - Athlete ID (link to profile)
  - Sport type
  - Position
  - Age
  - View button
  - Delete button (admins only)
- Empty state message

**Current Issues**:
- No search/filter functionality
- No sorting options
- Basic list view, no cards
- No athlete avatars
- No quick actions (bulk actions)
- No pagination
- Text inputs instead of dropdowns for sport/position

**Design Requirements**:
- **Header Section**:
  - Page title "Athletes"
  - Search bar with filters
  - Filter dropdowns:
    - Sport Type
    - Position
    - Status (Active/Inactive)
  - Sort dropdown
  - "Add Athlete" button (for authorized roles)
  - "Export" button

- **Athlete Cards** (instead of list):
  - Card layout with:
    - Avatar (initials or default silhouette)
    - Name / Athlete ID
    - Sport & Position badges
    - Age, Height, Weight stats
    - Status indicator (Active/Inactive)
    - Quick actions menu (⋮)
      - View Profile
      - Upload Video
      - Edit
      - Delete (if admin)
  - Hover lift effect
  - Grid layout (2-3 columns)

- **Add Athlete Modal** (instead of inline form):
  - Same fields as register athlete section
  - Sport type dropdown (8 sports)
  - Position dropdown (dynamic)
  - Validation indicators
  - Cancel/Save buttons

- **Pagination**:
  - 10-20 athletes per page
  - Page numbers
  - "Previous" / "Next" buttons
  - Show X-Y of Z athletes

- **Empty State**:
  - Illustration of empty list
  - "No athletes found" message
  - "Add your first athlete" CTA (if authorized)

---

### 7. Athlete Profile Page (`/athletes/:id`)
**Purpose**: View and edit athlete details
**Current Components**- Profile header:
  - Back to Athletes link
  - Athlete ID
  - "Athlete Profile" label
  - Edit Profile button (if authorized)
- Error message display
- Edit Profile form (when editing):
  - Sport type input
  - Position input
  - Age input
  - Height (cm) input
  - Weight (kg) input
  - Training Load input
  - Injury History textarea
  - Cancel/Save buttons
- Profile view (when not editing):
  - Athlete ID
  - Sport Type
  - Position
  - Age
  - Height
  - Weight
  - Training Load
  - Injury History
- Analysis Status section:
  - Movement Analysis (Coming in Milestone 2)
  - Biomechanical Assessment (Coming in Milestone 2)
  - Injury Risk Prediction (Coming in Milestone 3)

**Current Issues**:
- No profile photo/avatar
- No athlete demographics visualization
- No video history
- No recent analyses
- No injury timeline
- Status badges are static, not dynamic
- No action buttons (upload video, etc.)

**Design Requirements**:
- **Profile Header**:
  - Large avatar / profile photo upload
  - Athlete name / ID
  - Role badge (Athlete)
  - Status indicator (Active/Inactive)
  - Last updated timestamp
  - Action buttons:
    - Upload Video
    - View Analyses
    - Export Report
    - Edit Profile (if authorized)
    - Delete (if admin)

- **Profile Information Card**:
  - 2-column grid layout
  - Icon for each field
  - Edit button in card header
  - Fields:
    - Athlete ID
    - Sport Type (with icon)
    - Position (with icon)
    - Age (with calendar icon)
    - Height (with ruler icon)
    - Weight (with scale icon)
    - Training Load (with graph icon)
    - Injury History (with medical cross icon)

- **Video History Section**:
  - List of uploaded videos
  - Each video card:
    - Thumbnail
    - Filename
    - Upload date
    - Activity type
    - Processing status (badge)
    - Action button: "View Analysis"

- **Recent Analyses Section**:
  - Timeline of recent analyses
  - Each analysis:
    - Date
    - Activity type
    - Movement quality score
    - Risk level badge (Low/Medium/High)
    - Action button: "View Details"

- **Injury Timeline**:
  - Visual timeline of injury history
  - Date, type, severity
  - Recovery status

- **Quick Stats Cards**:
  - Total Videos
  - Analyses Completed
  - Average Quality Score
  - Risk Level

- **Analysis Status Section** (improved):
  - Movement Analysis (with progress bar)
  - Biomechanical Assessment (with progress bar)
  - Injury Risk Prediction (with progress bar)
  - Each with:
    - Description
    - Status (Not Started, In Progress, Available)
    - "Learn More" tooltip

---

### 8. Video Upload Page (`/videos/upload`)
**Purpose**: Upload athlete videos for analysis
**Current Components**:
- Athlete dropdown (populated based on user role)
- Activity Type dropdown (squat, jump, running, walking, lunges, deadlift, other)
- Video file input (with file type validation)
- File size limit notice (500 MB)
- Supported formats notice (MP4, AVI, MOV, WebM)
- Selected file preview (name, size)
- Upload button
- Error message display

**Current Issues**:
- No drag and drop area
- No video preview before upload
- No upload progress bar
- No batch upload
- No activity type descriptions
- No file validation feedback during selection

**Design Requirements**:
- **Header Section**:
  - Page title "Upload Video"
  - Breadcrumb navigation

- **Upload Area**:
  - Large drag-and-drop zone
  - Dashed border
  - Upload icon in center
  - "Drag and drop video here or click to browse"
  - Supported formats: MP4, AVI, MOV, WebM
  - File size limit: 500 MB

- **Form Fields**:
  - Athlete dropdown with:
    - Search/filter
    - Show athlete ID, sport, position
    - Current video count indicator
  - Activity Type dropdown with:
    - Icon for each activity
    - Description:
      - Squat: "Analyze squat form and depth"
      - Jump: "Analyze jump and landing mechanics"
      - Running: "Analyze running gait and stride"
      - Walking: "Analyze walking pattern"
      - Lunges: "Analyze lunge form"
      - Deadlift: "Analyze deadlift form"
      - Other: "General movement analysis"

- **File Preview**:
  - Video thumbnail after selection
  - Filename
  - File size
  - Duration (if available)
  - Resolution (if available)
  - "Remove" button

- **Upload Progress**:
  - Progress bar
  - Percentage
  - Status text:
    - "Uploading..."
    - "Processing queue..."
    - "Analyzing..."

- **Upload Button**:
  - Primary CTA button
  - Disabled during upload
  - Loading spinner

- **Tips Section**:
  - Best practices for video recording
  - Recommended camera angles
  - Lighting requirements
  - Background suggestions

---

### 9. Video Analysis Page (`/videos/:id`)
**Purpose**: View video analysis results
**Current Components**:
- Video Information section:
  - Filename
  - Activity
  - Status
  - Duration
  - Resolution
  - FPS
- Processing Controls:
  - "Start Analysis" button (when status = uploaded)
  - Processing status message
- Analysis Results (when completed):
  - Video Player (with annotated video)
  - Skeleton View Info
  - Pose Quality metrics
  - Movement Windows table
  - Biomechanics section
  - Time-Series Charts (knee/hip trajectory)
  - Movement Quality scores
  - Movement-Change Analysis (Early vs Late)
- Disclaimer
- Back to Dashboard button

**Current Issues**:
- No video thumbnail before processing
- No original video player (only annotated)
- No video playback controls enhancements
- Charts are basic
- No comparison with previous analyses
- No export/download options
- No sharing functionality
- No annotations/markup tools
- No frame-by-frame navigation
- No playback speed controls

**Design Requirements**:
- **Header Section**:
  - Breadcrumb navigation
  - Video title / filename
  - Activity type badge
  - Status badge (Uploaded, Processing, Completed, Failed)
  - Action buttons:
    - Share
    - Export Report
    - Delete
    - Re-process

- **Video Player Section**:
  - Large video player
  - Playback controls:
    - Play/Pause
    - Progress bar with time display
    - Volume
    - Fullscreen
    - Playback speed (0.5x, 1x, 1.5x, 2x)
  - Toggle between:
    - Original video
    - Annotated video (with skeleton, bounding boxes, metrics)
  - Frame-by-frame navigation
  - Thumbnail scrubbing

- **Analysis Overview**:
  - Summary cards:
    - Movement Quality Score (large, color-coded)
    - Risk Level (Low/Medium/High)
    - Total Frames Analyzed
    - Processing Time
  - Activity type badge
    - Date of analysis

- **Video Information**:
  - Compact, collapsible section
  - Filename, Duration, Resolution, FPS

- **Visualization Sections** (tabs or accordion):
  - **Tab 1: Skeleton Visualization**
    - Video player with overlay
    - Toggle skeleton visibility
    - Toggle bounding boxes
    - Toggle tracker IDs
    - Toggle joint labels
    - Color-coded confidence scores

  - **Tab 2: Movement Windows**
    - Timeline view of repetitions
    - Click to jump to that frame
    - Quality score per rep
    - Duration per rep
    - Export frames

  - **Tab 3: Biomechanics**
    - Joint angles chart
    - Range of Motion gauges
    - Symmetry visualization
    - Trunk lean indicator
    - Velocity chart
    - Acceleration chart

  - **Tab 4: Time-Series Charts**
    - Knee/hip Y-position over time
    - Quality metrics over time
    - Comparison with baseline (if available)

  - **Tab 5: Movement Quality**
    - Overall score with gauge
    - Component scores:
      - Confidence
      - Symmetry
      - Alignment
      - Stability
      - ROM
      - Smoothness
    - Raw measurements table

  - **Tab 6: Movement-Change Analysis**
    - Early vs Late comparison
    - Changes in:
      - ROM
      - Symmetry
      - Trunk Lean
    - Visual indicators of degradation

- **Download/Export Section**:
  - Download annotated video
  - Download analysis report (PDF)
  - Download raw data (JSON)
  - Export frames (ZIP)

- **Comparison Section** (if multiple analyses exist):
  - Compare with previous analysis
  - Side-by-side video comparison
  - Charts showing differences

- **Actions**:
  - Re-process video
  - Share analysis link
  - Delete video

- **Disclaimer**:
  - Medical disclaimer
  - Not a diagnosis

---

### 10. Profile Page (`/profile`)
**Purpose**: User account settings
**Current Components**:
- Account Information section:
  - Full Name
  - Email
  - Role
  - Account Status (Active/Inactive badge)
  - Member Since date
- Role Permissions section:
  - Role description based on user role

**Current Issues**:
- No profile photo/avatar
- No editable fields
- No password change option
- No notification settings
- No API key management
- No session management (view active sessions)
- No activity log

**Design Requirements**:
- **Profile Header**:
  - Large avatar with upload button
  - Full name
  - Email
  - Role badge (colored)
  - "Edit Profile" button

- **Account Information** (editable):
  - Full Name
  - Email
  - Phone (new field)
  - Bio/About Me (new field)
  - Timezone (new field)
  - Language (new field)

- **Security Section**:
  - Change Password:
    - Current password
    - New password
    - Confirm password
    - Password strength meter
  - Two-Factor Authentication (toggle)
  - Active Sessions:
    - List of active sessions
    - Device/browser info
    - Last active time
    - "Revoke" button for each session
  - Login History:
    - Recent logins with device/browser info

- **Notification Settings**:
  - Email notifications (toggle)
  - Push notifications (toggle)
  - Analysis complete notifications (toggle)
  - Weekly summary (toggle)

- **API Keys** (for developers):
  - Generate API key
  - List of API keys
  - Revoke API key
  - Last used date

- **Activity Log**:
  - Timeline of user actions
  - Login/logout events
  - Profile changes
  - Video uploads
  - Analysis completions

- **Danger Zone**:
  - Delete Account (with confirmation)
  - Download all data

---

### 11. Layout Component (`Layout.jsx`)
**Purpose**: Main navigation layout
**Current Components**:
- Top navigation bar:
  - App name "Sports Injury Risk Detection"
  - Navigation links: Dashboard, Athletes
  - User info (name + role)
  - Profile link
  - Logout button
- Main content area

**Current Issues**:
- Minimal styling
- No mobile responsiveness
- No hamburger menu for mobile
- No notification center
- No help/support link
- No settings menu

**Design Requirements**:
- **Header/Navigation**:
  - App logo on left
  - Navigation links:
    - Dashboard
    - Athletes
    - Videos
    - Reports (new)
    - Settings (new)
  - Right side:
    - Notification bell icon with badge count
    - User avatar dropdown:
      - Profile
      - Settings
      - Help/Support
      - Logout
  - Mobile: Hamburger menu

- **Notification Center**:
  - Dropdown from bell icon
  - Notifications:
    - Analysis complete
    - Athlete added
    - Video uploaded
    - System updates
  - Mark as read / clear all

- **Breadcrumbs**:
  - Breadcrumb navigation for nested pages
  - Example: Dashboard > Athletes > ATH001

- **Sidebar Navigation** (optional):
  - Collapsible sidebar for larger screens
  - Navigation links with icons
  - Role-based menu items

- **Footer**:
  - Copyright
  - Links: Privacy Policy, Terms, Help, Contact

---

## Global Design System

### Color Palette
- **Primary**: #BD4006
- **Secondary**: Green (#10B981 for success, F59E0B for warning, EF4444 for error)
- **Neutral**: Gray scale for text (#111827, #6B7280, #9CA3AF, #D1D5DB) whichever makes it more contrast with the background so text is clearly visible
- **Background**: White (#FFFFFF), Light Gray (#F9FAFB) cards or modals with dark thin borders
- **Role-based colors**:
  - Athlete: #1C1613
  - Coach: Green
  - Physiotherapist: Purple
  - Sports Scientist: Orange
  - Administrator: Red

### Typography
- **Font**: Inter or Roboto
- **Headings**: Bold, dark gray
- **Body**: Regular, dark gray
- **Text sizes**:
  - H1: 2xl or 3xl
  - H2: xl or 2xl
  - H3: lg
  - Body: base or sm

### Spacing
- **Padding**: 4 (16px), 6 (24px), 8 (32px)
- **Margin**: 4 (16px), 6 (24px), 8 (32px)
- **Gap**: 4 (16px), 6 (24px), 8 (32px)

### Components
- **Cards**: White background, shadow-sm, rounded-lg (8px)
- **Buttons**: px-4 py-2, rounded-md (6px), hover effects
- **Inputs**: px-3 py-2, border-gray-300, rounded-md, focus rings
- **Badges**: rounded-full, text-xs, font-medium
- **Modals**: Fixed positioning, backdrop blur, max-w-lg

### Icons
- Use consistent icon library (Lucide React, Heroicons, or custom SVGs)
- Icon size: small (sm), medium (md), large (lg)
- Icons should have semantic meaning

### Responsive Design
- Mobile-first approach
- Breakpoints: sm (640px), md (768px), lg (1024px), xl (1280px)
- Collapsible navigation on mobile
- Stacked grids on smaller screens

### Accessibility
- ARIA labels for all inputs
- Keyboard navigation support
- Focus indicators
- Color contrast ratios (WCAG AA compliant)
- Screen reader compatibility

---

## Additional Components Needed

### Common Components
1. **Button**: Primary, Secondary, Tertiary, Danger, Ghost
2. **Input**: Text, Number, Email, Password, Select, Textarea
3. **Card**: Base card, Stats card, Feature card
4. **Badge**: Status badge, Role badge
5. **Modal**: Alert modal, Confirm modal, Form modal
6. **Dropdown**: Navigation dropdown, Filter dropdown, Action dropdown
7. **Table**: Base table, Sortable table, Selectable table
8. **Chart**: Line chart, Bar chart, Gauge chart, Timeline
9. **Timeline**: Activity timeline, Analysis timeline
10. **Toast**: Success, Error, Warning, Info
11. **Skeleton Loader**: For loading states
12. **Empty State**: For lists, pages, data views
13. **Pagination**: Standard pagination with page numbers
14. **Breadcrumbs**: Navigation breadcrumbs
15. **Avatar**: User avatar, Initials avatar
16. **Progress Bar**: Linear, Circular
17. **Toggle Switch**: For boolean settings
18. **Rating**: Star rating, Rating scale
19. **Tabs**: Basic tabs, Vertical tabs
20. **Accordion**: Expandable sections

### Page-Specific Components
1. **Video Player**: Enhanced video player with annotations
2. **Chart**: Time-series, Bar, Gauge, Line
3. **Timeline**: Activity timeline, Analysis timeline
4. **Form Wizard**: Multi-step form with progress
5. **File Upload**: Drag-and-drop with preview
6. **OTP Input**: 6-digit code with auto-focus
7. **Sport Selector**: Sport + Position dropdowns
8. **Role Selector**: Role with descriptions
9. **Filter Bar**: Search + filters + sort
10. **Action Menu**: Dropdown with actions

---

## Priority Implementation Order

### Phase 1: Core Pages (High Priority)
1. Login
2. Register
3. Dashboard
4. Layout

### Phase 2: Main Features (High Priority)
5. Athlete List
6. Athlete Profile
7. Video Upload
8. Video Analysis

### Phase 3: Additional Features (Medium Priority)
9. Profile
10. Forgot Password

### Phase 4: Enhancements (Low Priority)
11. Landing Page
12. Additional features as needed

---

## Notes
- All pages should follow consistent design system
- Role-based permissions should be visually clear
- Loading states should be visually appealing
- Error states should be helpful and actionable
- Success states should provide clear feedback
- All forms should have validation
- All pages should be responsive
- Consider adding dark mode support
