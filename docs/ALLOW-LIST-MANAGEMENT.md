# Allow List Management Guide

## Overview

The **allow list** enables external users (non-`@mgms.eu` domain) to access the LLS Study Portal. This guide covers how to add, manage, and remove external users using both the admin UI and API.

## Purpose

- Grant temporary or permanent access to guest users
- Support external collaborators (e.g., guest lecturers, partner institutions)
- Maintain audit trail of external access
- Enforce expiration policies

## Access Requirements

**Admin access required**: Only users with `@mgms.eu` email addresses can manage the allow list.

## Adding External Users

### Via Admin UI

1. **Navigate to User Management**:
   ```
   https://your-app.com/admin/users
   ```

2. **Click "Add User"**

3. **Fill in the form**:
   - **Email**: User's email address (required)
   - **Name**: Full name (required)
   - **Reason**: Why access is being granted (required)
   - **Expiration Date**: When access expires (optional)
   - **Notes**: Additional context (optional)

4. **Click "Save"**

5. **Grant IAP Access** (required):
   ```bash
   gcloud iap web add-iam-policy-binding \
       --resource-type=backend-services \
       --service=lls-portal-backend \
       --member="user:guest@university.edu" \
       --role="roles/iap.httpsResourceAccessor"
   ```

### Via API

**Endpoint**: `POST /api/admin/users/allowed`

**Request**:
```bash
curl -X POST https://your-app.com/api/admin/users/allowed \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -d '{
    "email": "guest@university.edu",
    "name": "Dr. Jane Smith",
    "reason": "Guest lecturer for Contract Law module",
    "expires_at": "2026-06-30T23:59:59Z",
    "notes": "Teaching 3 sessions in Spring 2026"
  }'
```

**Response**:
```json
{
  "success": true,
  "entry": {
    "email": "guest@university.edu",
    "name": "Dr. Jane Smith",
    "reason": "Guest lecturer for Contract Law module",
    "is_active": true,
    "expires_at": "2026-06-30T23:59:59Z",
    "created_at": "2026-01-06T10:00:00Z",
    "created_by": "admin@mgms.eu",
    "notes": "Teaching 3 sessions in Spring 2026"
  }
}
```

## Viewing Allow List

### Via Admin UI

1. Navigate to: `https://your-app.com/admin/users`
2. View table with all allowed users
3. Filter by:
   - Active/Inactive status
   - Expired/Non-expired
   - Search by email or name

### Via API

**Endpoint**: `GET /api/admin/users/allowed`

**List all active users**:
```bash
curl https://your-app.com/api/admin/users/allowed \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)"
```

**Include expired entries**:
```bash
curl "https://your-app.com/api/admin/users/allowed?include_expired=true" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)"
```

**Include inactive entries**:
```bash
curl "https://your-app.com/api/admin/users/allowed?include_inactive=true" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)"
```

**Response**:
```json
{
  "entries": [
    {
      "email": "guest@university.edu",
      "name": "Dr. Jane Smith",
      "is_active": true,
      "expires_at": "2026-06-30T23:59:59Z",
      "is_expired": false,
      "is_effective": true
    }
  ],
  "total": 1
}
```

## Updating Users

### Via Admin UI

1. Navigate to user management page
2. Click "Edit" next to user
3. Update fields
4. Click "Save"

### Via API

**Endpoint**: `PATCH /api/admin/users/allowed/{email}`

**Update expiration date**:
```bash
curl -X PATCH https://your-app.com/api/admin/users/allowed/guest%40university.edu \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -d '{
    "expires_at": "2026-12-31T23:59:59Z"
  }'
```

**Deactivate user**:
```bash
curl -X PATCH https://your-app.com/api/admin/users/allowed/guest%40university.edu \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -d '{
    "is_active": false,
    "notes": "Access revoked - project completed"
  }'
```

## Removing Users

### Via Admin UI

1. Navigate to user management page
2. Click "Delete" next to user
3. Confirm deletion
4. **Revoke IAP access** (required):
   ```bash
   gcloud iap web remove-iam-policy-binding \
       --resource-type=backend-services \
       --service=lls-portal-backend \
       --member="user:guest@university.edu" \
       --role="roles/iap.httpsResourceAccessor"
   ```

### Via API

**Endpoint**: `DELETE /api/admin/users/allowed/{email}`

```bash
curl -X DELETE https://your-app.com/api/admin/users/allowed/guest%40university.edu \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)"
```

**Response**:
```json
{
  "success": true,
  "message": "User guest@university.edu removed from allow list"
}
```

## Expiration Policies

### How Expiration Works

- **`expires_at`**: Optional ISO 8601 datetime
- **Automatic check**: System checks expiration on every request
- **Expired users**: Cannot access the application even if on allow list
- **No automatic removal**: Expired entries remain in database for audit trail

### Setting Expiration Dates

**Temporary access (3 months)**:
```json
{
  "expires_at": "2026-04-06T23:59:59Z"
}
```

**Semester access (6 months)**:
```json
{
  "expires_at": "2026-07-31T23:59:59Z"
}
```

**Permanent access**:
```json
{
  "expires_at": null
}
```

### Extending Access

Update the expiration date before it expires:

```bash
curl -X PATCH https://your-app.com/api/admin/users/allowed/guest%40university.edu \
  -H "Content-Type: application/json" \
  -d '{
    "expires_at": "2027-01-06T23:59:59Z"
  }'
```

## Best Practices

### ✅ Do

- **Set expiration dates** for temporary access
- **Document the reason** for granting access
- **Add notes** for context and tracking
- **Review regularly** - audit allow list quarterly
- **Revoke IAP access** when removing users
- **Use descriptive names** - include role/affiliation

### ❌ Don't

- Grant permanent access without justification
- Skip the `reason` field
- Forget to revoke IAP access when removing users
- Share credentials - each user should have their own email
- Add internal `@mgms.eu` users (they have access by default)

## Audit Trail

### Tracking Changes

All allow list entries include:
- `created_at`: When user was added
- `created_by`: Who added the user
- `updated_at`: Last modification time
- `updated_by`: Who made the last change

### Viewing History

**Via API**:
```bash
curl https://your-app.com/api/admin/users/allowed/guest%40university.edu \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)"
```

**Response includes audit fields**:
```json
{
  "email": "guest@university.edu",
  "created_at": "2026-01-06T10:00:00Z",
  "created_by": "admin@mgms.eu",
  "updated_at": "2026-01-06T15:30:00Z",
  "updated_by": "admin@mgms.eu"
}
```

## Common Scenarios

### Guest Lecturer

```json
{
  "email": "lecturer@university.edu",
  "name": "Prof. John Doe",
  "reason": "Guest lecturer for Constitutional Law",
  "expires_at": "2026-05-31T23:59:59Z",
  "notes": "Teaching 6 sessions in Spring semester"
}
```

### Research Collaborator

```json
{
  "email": "researcher@partner-uni.edu",
  "name": "Dr. Sarah Johnson",
  "reason": "Research collaboration on EU law project",
  "expires_at": "2027-12-31T23:59:59Z",
  "notes": "Joint research project 2026-2027"
}
```

### External Examiner

```json
{
  "email": "examiner@law-school.edu",
  "name": "Prof. Michael Brown",
  "reason": "External examiner for final assessments",
  "expires_at": "2026-07-15T23:59:59Z",
  "notes": "Access needed for June-July exam period"
}
```

## Troubleshooting

### User added to allow list but cannot access

**Possible causes**:
1. IAP access not granted
2. User expired
3. User inactive

**Solutions**:
```bash
# 1. Grant IAP access
gcloud iap web add-iam-policy-binding \
    --resource-type=backend-services \
    --service=lls-portal-backend \
    --member="user:guest@university.edu" \
    --role="roles/iap.httpsResourceAccessor"

# 2. Check expiration
curl https://your-app.com/api/admin/users/allowed/guest%40university.edu

# 3. Activate user
curl -X PATCH https://your-app.com/api/admin/users/allowed/guest%40university.edu \
  -d '{"is_active": true}'
```

### User removed but still has access

**Cause**: IAP access not revoked  
**Solution**:
```bash
gcloud iap web remove-iam-policy-binding \
    --resource-type=backend-services \
    --service=lls-portal-backend \
    --member="user:guest@university.edu" \
    --role="roles/iap.httpsResourceAccessor"
```

## API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/admin/users/allowed` | List all allowed users |
| `GET` | `/api/admin/users/allowed/{email}` | Get specific user |
| `POST` | `/api/admin/users/allowed` | Add new user |
| `PATCH` | `/api/admin/users/allowed/{email}` | Update user |
| `DELETE` | `/api/admin/users/allowed/{email}` | Remove user |

### Data Model

```typescript
{
  email: string;              // Required, unique
  name: string;               // Required
  reason: string;             // Required
  is_active: boolean;         // Default: true
  expires_at: string | null;  // ISO 8601 datetime
  notes: string | null;       // Optional
  created_at: string;         // Auto-generated
  created_by: string;         // Auto-generated
  updated_at: string;         // Auto-updated
  updated_by: string;         // Auto-updated
}
```

## Related Documentation

- [Authentication System](AUTHENTICATION.md) - Architecture overview
- [IAP Setup Guide](IAP-SETUP.md) - Configure Google Cloud IAP
- [Local Development](LOCAL-DEVELOPMENT.md) - Testing allow list locally

## References

- [Firestore Security Rules](https://firebase.google.com/docs/firestore/security/get-started)
- [IAP Access Control](https://cloud.google.com/iap/docs/managing-access)

