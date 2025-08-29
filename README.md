# Leave Management System

This project implements a **Leave Management System** with the following main components:
- Employee Dashboard
- Leave Application
- Email Notifications
- Admin Dashboard
- Holiday Management

## Dashboard

Welcome

## Home Login

You need to access the system? Login.

## Employee Dashboard

The Employee Dashboard allows users to apply for leave, view leave history, and track leave status.

![Employee Dashboard](https://github.com/damiancodes/leave_management_system-full-project/blob/master/leavemanagement/static/images/empdashboard.png)


## Leave Application

Employees can request leave directly from their dashboards, specifying the type and duration.

![Leave Application](https://github.com/damiancodes/leave_management_system-full-project/blob/master/leavemanagement/static/images/leave_request.png)


## Email Notifications

![Emial Notification](https://github.com/damiancodes/leave_management_system-full-project/blob/master/leavemanagement/static/images/emailnotify.png)

The system sends automatic email notifications for:
- Leave requests
- Approvals/rejections
- Holiday announcements

## Admin Dashboard

The Admin Dashboard provides tools for managing employees, reviewing leave applications, and setting holidays.

![Admin Dashboard](https://github.com/damiancodes/leave_management_system-full-project/blob/master/leavemanagement/static/images/admindash.png)

## Holiday Management

Admins can define and manage holidays that impact leave calculations.

![Holiday Management](https://github.com/damiancodes/leave_management_system-full-project/blob/master/leavemanagement/static/images/manage_holidays.png)

---

## Getting Started

To set up the system, follow these steps:

### Prerequisites  
- Ensure you have **Python** installed on your system.

### Setup  
1. Clone the repository:  
   ```bash
   git clone https://github.com/damiancodes/leave-management.git
   cd leave-management
   ```  
2. Create and activate a virtual environment:  
   - For Linux and macOS:  
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```  
   - For Windows:  
     ```bash
     python -m venv venv
     venv\Scripts\activate
     ```  
3. Install Django and dependencies:  
   ```bash
   pip install django
   pip install requests
   pip install django-crispy-forms
   ```  
4. Set up environment variables (email settings, database configurations, etc.).  
5. Run database migrations:  
   ```bash
   python manage.py migrate
   ```  
6. Start the server:  
   ```bash
   python manage.py runserver
   ```  

## Usage  
1. Apply database migrations:  
   ```bash
   python3 manage.py migrate
   ```  
2. Start the development server:  
   ```bash
   python3 manage.py runserver
   ```  
3. Open your browser and navigate to:  
   `http://127.0.0.1:8000/`  
4. Register/Login as an employee or admin.  
5. Apply for leave and receive email notifications.  
6. Admins can review and approve/reject leave requests.

## License

MIT License.

