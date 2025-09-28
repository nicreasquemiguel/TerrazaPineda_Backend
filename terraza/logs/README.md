# Terraza Logs App

A comprehensive logging system for tracking all activities, changes, and events across the Terraza platform.

## Features

- **Comprehensive Logging**: Track all system activities, user actions, and data changes
- **Automatic Logging**: Uses Django signals to automatically log important events
- **Admin Interface**: Full admin interface for viewing and managing logs
- **API Access**: RESTful API endpoints for programmatic access to logs
- **Audit Trail**: Complete audit trail for compliance and debugging
- **Performance Optimized**: Efficient database queries with proper indexing

## Models

### 1. ActivityLog
Main activity log for tracking all system activities with categories and log levels.

**Fields:**
- `timestamp`: When the activity occurred
- `user`: User who performed the action (optional)
- `category`: Activity category (booking, payment, user, admin, system, etc.)
- `action`: Specific action performed
- `description`: Detailed description of the activity
- `log_level`: Info, warning, error, or critical
- `ip_address`: Client IP address
- `user_agent`: Client user agent
- `metadata`: Additional JSON data
- `content_object`: Generic foreign key to related objects

### 2. BookingLog
Specific logging for booking-related activities.

**Fields:**
- `booking_id`: ID of the affected booking
- `action`: Created, updated, status_changed, cancelled, etc.
- `old_status`/`new_status`: Status before and after changes
- `description`: Detailed description
- `metadata`: Additional context

### 3. PaymentLog
Specific logging for payment-related activities.

**Fields:**
- `payment_id`/`order_id`: IDs of affected payment and order
- `action`: Initiated, attempted, confirmed, failed, etc.
- `amount`: Payment amount
- `method`/`gateway`: Payment method and gateway used
- `old_status`/`new_status`: Status changes
- `error_message`: Error details if payment failed

### 4. UserActivityLog
Specific logging for user-related activities.

**Fields:**
- `action`: Login, logout, profile_updated, etc.
- `description`: Activity description
- `ip_address`/`user_agent`: Client information

### 5. SystemLog
System-level logging for errors, warnings, and important events.

**Fields:**
- `level`: Debug, info, warning, error, critical
- `component`: System component where the event occurred
- `message`: Log message
- `stack_trace`: Full stack trace for errors

### 6. AuditLog
Audit trail for sensitive operations and data changes.

**Fields:**
- `audit_type`: Data change, permission change, security event, etc.
- `table_name`/`record_id`: Affected database record
- `field_name`: Specific field that changed
- `old_value`/`new_value`: Values before and after change

## API Endpoints

### Base URL: `/api/logs/`

#### Activity Logs
- `GET /api/logs/activity/` - List all activity logs
- `GET /api/logs/activity/summary/` - Get activity summary statistics
- `GET /api/logs/activity/recent_activity/` - Get recent activities for dashboard

**Query Parameters:**
- `category`: Filter by activity category
- `action`: Filter by specific action
- `log_level`: Filter by log level
- `user`: Filter by user ID
- `days`: Number of days for summary (default: 30)
- `limit`: Limit for recent activity (default: 50)

#### Booking Logs
- `GET /api/logs/booking/` - List all booking logs
- `GET /api/logs/booking/by_booking/?booking_id=<id>` - Get logs for specific booking

**Query Parameters:**
- `action`: Filter by action type
- `old_status`/`new_status`: Filter by status changes
- `user`: Filter by user ID

#### Payment Logs
- `GET /api/logs/payment/` - List all payment logs
- `GET /api/logs/payment/by_payment/?payment_id=<id>` - Get logs for specific payment
- `GET /api/logs/payment/payment_summary/` - Get payment activity summary

**Query Parameters:**
- `action`: Filter by action type
- `method`/`gateway`: Filter by payment method/gateway
- `old_status`/`new_status`: Filter by status changes
- `days`: Number of days for summary (default: 30)

#### User Activity Logs
- `GET /api/logs/user/` - List all user activity logs
- `GET /api/logs/user/by_user/?user_id=<id>` - Get logs for specific user

**Query Parameters:**
- `action`: Filter by action type
- `user`: Filter by user ID

#### System Logs
- `GET /api/logs/system/` - List all system logs
- `GET /api/logs/system/errors/` - Get only error and critical logs
- `GET /api/logs/system/by_component/?component=<name>` - Get logs for specific component

**Query Parameters:**
- `level`: Filter by log level
- `component`: Filter by system component

#### Audit Logs
- `GET /api/logs/audit/` - List all audit logs
- `GET /api/logs/audit/data_changes/` - Get only data change logs
- `GET /api/logs/audit/security_events/` - Get only security event logs

**Query Parameters:**
- `audit_type`: Filter by audit type
- `table_name`: Filter by database table
- `user`: Filter by user ID

## Usage Examples

### Frontend Integration

```javascript
// Get recent activity for dashboard
const getRecentActivity = async () => {
    const response = await fetch('/api/logs/activity/recent_activity/?limit=20', {
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    });
    return await response.json();
};

// Get payment summary for last 7 days
const getPaymentSummary = async () => {
    const response = await fetch('/api/logs/payment/payment_summary/?days=7', {
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    });
    return await response.json();
};

// Get logs for specific booking
const getBookingLogs = async (bookingId) => {
    const response = await fetch(`/api/logs/booking/by_booking/?booking_id=${bookingId}`, {
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    });
    return await response.json();
};

// Get system errors
const getSystemErrors = async () => {
    const response = await fetch('/api/logs/system/errors/', {
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    });
    return await response.json();
};
```

### Backend Integration

```python
from logs.utils import (
    log_activity, log_booking_activity, log_payment_activity,
    log_user_activity, log_system_event, log_audit_event
)

# Log a general activity
log_activity(
    user=request.user,
    category='admin',
    action='venue_updated',
    description=f'Venue {venue.name} was updated',
    request=request
)

# Log a booking status change
log_booking_activity(
    user=request.user,
    booking_id=booking.id,
    action='status_changed',
    old_status='solicitud',
    new_status='aceptacion',
    description='Booking approved by admin'
)

# Log a payment confirmation
log_payment_activity(
    user=request.user,
    payment_id=payment.id,
    order_id=payment.order.id,
    action='confirmed',
    amount=payment.amount,
    method=payment.method,
    gateway=payment.gateway,
    old_status='pending',
    new_status='paid',
    description='Payment confirmed via webhook'
)

# Log a system error
log_system_event(
    level='error',
    component='PaymentGateway',
    message='Stripe API connection failed',
    stack_trace=traceback.format_exc()
)

# Log a data change for audit
log_audit_event(
    user=request.user,
    audit_type='data_change',
    table_name='users_useraccount',
    record_id=user.id,
    field_name='is_active',
    old_value='True',
    new_value='False',
    description='User account deactivated',
    request=request
)
```

## Automatic Logging

The app automatically logs the following events using Django signals:

### User Activities
- User login/logout
- Account creation
- Profile updates
- Permission changes

### Booking Activities
- Booking creation
- Status changes
- Updates and modifications

### Payment Activities
- Payment attempts
- Status changes
- Confirmations and failures

### System Events
- System startup
- Error logging
- Component-specific events

## Admin Interface

All log models have comprehensive admin interfaces with:

- **List Views**: Sortable and filterable lists
- **Search**: Full-text search across relevant fields
- **Filters**: Date ranges, categories, actions, users, etc.
- **Export**: Data export capabilities
- **Read-only**: Logs are read-only to prevent tampering

## Performance Considerations

- **Database Indexing**: Proper indexes on timestamp, category, action, and user fields
- **Efficient Queries**: Optimized querysets with select_related for foreign keys
- **Pagination**: API endpoints support pagination for large datasets
- **Filtering**: Server-side filtering to reduce data transfer

## Security Features

- **Admin Only Access**: All log endpoints require admin privileges
- **Audit Trail**: Complete audit trail for sensitive operations
- **IP Tracking**: Client IP addresses are logged for security
- **User Agent Logging**: Browser/client information is captured
- **Metadata Storage**: Additional context stored as JSON

## Monitoring and Alerts

The logs can be used to:

- **Monitor System Health**: Track errors and system events
- **User Activity Analysis**: Understand user behavior patterns
- **Payment Monitoring**: Track payment success/failure rates
- **Security Monitoring**: Detect suspicious activities
- **Compliance**: Maintain audit trails for regulatory requirements

## Best Practices

1. **Use Appropriate Log Levels**: Use info, warning, error, and critical appropriately
2. **Include Context**: Always provide meaningful descriptions and metadata
3. **Regular Review**: Regularly review logs for patterns and issues
4. **Retention Policy**: Implement log retention policies based on business needs
5. **Performance Monitoring**: Monitor log table sizes and query performance

## Troubleshooting

### Common Issues

1. **Logs Not Appearing**: Check if signals are properly connected
2. **Performance Issues**: Review database indexes and query optimization
3. **Permission Errors**: Ensure user has admin privileges
4. **Missing Data**: Verify that models are properly imported in signals

### Debug Mode

Enable debug logging by adding to settings:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'logs': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```
