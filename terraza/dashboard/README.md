# Dashboard API Endpoints

## Overview Statistics

### Get Dashboard Overview

**Endpoint:** `GET /api/dashboard/dashboard/overview/`

**Description:** Get dashboard overview statistics with month-over-month comparisons.

**Permissions:** Admin users only

**Response:**
```json
{
    "current_month": {
        "bookings": 25,
        "revenue": "5000.00",
        "customers": 20,
        "accepted_bookings": 15
    },
    "last_month": {
        "bookings": 22,
        "revenue": "4500.00",
        "customers": 18,
        "accepted_bookings": 12
    },
    "percentage_changes": {
        "bookings": 13.6,
        "revenue": 11.1,
        "customers": 11.1,
        "accepted_bookings": 25.0
    },
    "total_bookings": 150,
    "active_users": 45
}
```

## Daily Cards

### Get Daily Booking Cards

**Endpoint:** `GET /api/dashboard/dashboard/daily_cards/`

**Description:** Get daily booking cards for a specific week. If no date parameter is provided, defaults to the current week.

**Permissions:** Admin users only

**Query Parameters:**
- `date` (optional): Date in YYYY-MM-DD format. The endpoint will return the week containing this date.

**Response:**
```json
{
    "week_start": "2024-01-15",
    "week_end": "2024-01-21",
    "target_date": "2024-01-15",
    "daily_cards": [
        {
            "day_name": "Lunes",
            "day_number": 15,
            "date": "2024-01-15",
            "bookings": [
                {
                    "booking_id": "uuid",
                    "package_name": "Test Package",
                    "people_count": 30,
                    "client_first_name": "John",
                    "client_last_name": "Doe",
                    "client_phone": "+1234567890",
                    "status": "aceptacion",
                    "amount_due": 100.00
                }
            ]
        }
    ]
}
```

**Notes:**
- Always returns 7 days (Monday to Sunday)
- Week always starts on Monday regardless of the target date
- If no date parameter is provided, uses current date
- Invalid date format returns 400 error

## Pending Cash/Transfer Payments

### List Pending Cash/Transfer Payments

**Endpoint:** `GET /api/dashboard/dashboard/pending_cash_transfer_payments/`

**Description:** Get all pending cash or transfer payments for future bookings with specific statuses.

**Permissions:** Admin users only

**Response:**
```json
{
    "total_pending": 2,
    "payments": [
        {
            "payment_id": "uuid",
            "booking_id": "uuid",
            "booking_date": "2024-01-15T14:00:00Z",
            "booking_status": "aceptacion",
            "payment_status": "pending",
            "amount": "100.00",
            "payment_photo_base64": "base64_encoded_photo_data",
            "created_at": "2024-01-10T10:00:00Z",
            "user_name": "John Doe",
            "amount_due": "100.00"
        }
    ]
}
```

**Filters Applied:**
- Only payments with method 'cash' or 'transfer'
- Only payments with status 'pending'
- Only bookings with start date from now forward
- Only bookings with status: 'aceptacion', 'apartado', or 'entregado'

### Approve/Reject Cash/Transfer Payment

**Endpoint:** `POST /api/dashboard/dashboard/approve_cash_transfer_payment/`

**Description:** Approve or reject a pending cash/transfer payment after reviewing the photo.

**Permissions:** Admin users only

**Request Body:**
```json
{
    "payment_id": "uuid",
    "action": "approve|reject",
    "reason": "Optional reason for rejection"
}
```

**Response (Approve):**
```json
{
    "message": "Payment approved successfully",
    "payment_id": "uuid",
    "amount": 100.00,
    "method": "cash",
    "booking_id": "uuid"
}
```

**Response (Reject):**
```json
{
    "message": "Payment rejected successfully",
    "payment_id": "uuid",
    "amount": 100.00,
    "method": "transfer",
    "booking_id": "uuid",
    "rejection_reason": "Invalid payment proof"
}
```

## Usage Examples

### Frontend Integration

```javascript
// Get dashboard overview
const getOverview = async () => {
    const response = await fetch('/api/dashboard/dashboard/overview/', {
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    });
    return await response.json();
};

// Get daily cards for current week
const getCurrentWeekCards = async () => {
    const response = await fetch('/api/dashboard/dashboard/daily_cards/', {
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    });
    return await response.json();
};

// Get daily cards for specific week
const getWeekCards = async (date) => {
    const response = await fetch(`/api/dashboard/dashboard/daily_cards/?date=${date}`, {
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    });
    return await response.json();
};

// Get pending payments
const getPendingPayments = async () => {
    const response = await fetch('/api/dashboard/dashboard/pending_cash_transfer_payments/', {
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    });
    const data = await response.json();
    return data.payments;
};

// Approve a payment
const approvePayment = async (paymentId) => {
    const response = await fetch('/api/dashboard/dashboard/approve_cash_transfer_payment/', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            payment_id: paymentId,
            action: 'approve'
        })
    });
    return await response.json();
};

// Reject a payment
const rejectPayment = async (paymentId, reason) => {
    const response = await fetch('/api/dashboard/dashboard/approve_cash_transfer_payment/', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            payment_id: paymentId,
            action: 'reject',
            reason: reason
        })
    });
    return await response.json();
};
```

### Admin Action Logging

All payment approvals and rejections are automatically logged in the `AdminAction` model for audit purposes:

- **Action types:** `cash_transfer_payment_approved`, `cash_transfer_payment_rejected`
- **Target ID:** Payment ID
- **Description:** Detailed description including amount, booking ID, and rejection reason (if applicable)

## Notes

- The daily cards endpoint always returns a full week (Monday to Sunday)
- Week boundaries are calculated automatically based on the target date
- All endpoints require admin privileges
- Payment photos are returned as base64 encoded strings for easy display
- The `amount_due` field shows the remaining amount to be paid for the booking
