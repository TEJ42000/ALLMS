# Firestore Indexes for GDPR Compliance

This document describes the required Firestore indexes for GDPR features.

## Overview

Firestore requires composite indexes for queries that filter or sort on multiple fields. This document lists all required indexes for GDPR compliance features.

## Required Indexes

### 1. Consent Records

**Collection:** `consent_records`

**Index 1: User consent history (sorted by timestamp)**
```
Fields:
- user_id (Ascending)
- timestamp (Descending)

Purpose: Retrieve user's consent history sorted by most recent
Query: db.collection('consent_records').where('user_id', '==', userId).orderBy('timestamp', 'desc')
```

**Index 2: Consent type filtering with timestamp**
```
Fields:
- user_id (Ascending)
- consent_type (Ascending)
- timestamp (Descending)

Purpose: Filter user's consent by type and sort by date
Query: db.collection('consent_records').where('user_id', '==', userId).where('consent_type', '==', type).orderBy('timestamp', 'desc')
```

**Index 3: Consent status filtering**
```
Fields:
- user_id (Ascending)
- status (Ascending)
- timestamp (Descending)

Purpose: Filter user's consent by status (granted/revoked)
Query: db.collection('consent_records').where('user_id', '==', userId).where('status', '==', 'granted').orderBy('timestamp', 'desc')
```

### 2. Audit Logs

**Collection:** `audit_logs`

**Index 1: User audit history**
```
Fields:
- user_id (Ascending)
- timestamp (Descending)

Purpose: Retrieve user's audit history
Query: db.collection('audit_logs').where('user_id', '==', userId).orderBy('timestamp', 'desc')
```

**Index 2: Action type filtering**
```
Fields:
- user_id (Ascending)
- action (Ascending)
- timestamp (Descending)

Purpose: Filter audit logs by action type
Query: db.collection('audit_logs').where('user_id', '==', userId).where('action', '==', 'data_export').orderBy('timestamp', 'desc')
```

**Index 3: Admin audit logs**
```
Fields:
- action (Ascending)
- timestamp (Descending)

Purpose: Admin dashboard - view all actions by type
Query: db.collection('audit_logs').where('action', '==', 'account_deleted').orderBy('timestamp', 'desc')
```

### 3. Data Subject Requests

**Collection:** `data_subject_requests`

**Index 1: User requests**
```
Fields:
- user_id (Ascending)
- created_at (Descending)

Purpose: Retrieve user's GDPR requests
Query: db.collection('data_subject_requests').where('user_id', '==', userId).orderBy('created_at', 'desc')
```

**Index 2: Request status filtering**
```
Fields:
- user_id (Ascending)
- status (Ascending)
- created_at (Descending)

Purpose: Filter requests by status
Query: db.collection('data_subject_requests').where('user_id', '==', userId).where('status', '==', 'pending').orderBy('created_at', 'desc')
```

**Index 3: Request type filtering**
```
Fields:
- request_type (Ascending)
- status (Ascending)
- created_at (Descending)

Purpose: Admin dashboard - filter by type and status
Query: db.collection('data_subject_requests').where('request_type', '==', 'deletion').where('status', '==', 'pending').orderBy('created_at', 'desc')
```

**Index 4: Overdue requests**
```
Fields:
- status (Ascending)
- due_date (Ascending)

Purpose: Admin dashboard - find overdue requests
Query: db.collection('data_subject_requests').where('status', '==', 'pending').where('due_date', '<', now).orderBy('due_date', 'asc')
```

### 4. Privacy Settings

**Collection:** `privacy_settings`

**Single-field indexes only (no composite indexes needed)**

User privacy settings are typically queried by user_id only, which doesn't require a composite index.

## Creating Indexes

### Method 1: Firebase Console (Recommended for Initial Setup)

1. Go to [Firebase Console](https://console.firebase.google.com)
2. Select your project
3. Navigate to Firestore Database
4. Click on "Indexes" tab
5. Click "Create Index"
6. Enter collection name and fields
7. Click "Create"

### Method 2: gcloud CLI

```bash
# Consent records - user history
gcloud firestore indexes composite create \
  --collection-group=consent_records \
  --field-config field-path=user_id,order=ascending \
  --field-config field-path=timestamp,order=descending

# Consent records - type filtering
gcloud firestore indexes composite create \
  --collection-group=consent_records \
  --field-config field-path=user_id,order=ascending \
  --field-config field-path=consent_type,order=ascending \
  --field-config field-path=timestamp,order=descending

# Consent records - status filtering
gcloud firestore indexes composite create \
  --collection-group=consent_records \
  --field-config field-path=user_id,order=ascending \
  --field-config field-path=status,order=ascending \
  --field-config field-path=timestamp,order=descending

# Audit logs - user history
gcloud firestore indexes composite create \
  --collection-group=audit_logs \
  --field-config field-path=user_id,order=ascending \
  --field-config field-path=timestamp,order=descending

# Audit logs - action filtering
gcloud firestore indexes composite create \
  --collection-group=audit_logs \
  --field-config field-path=user_id,order=ascending \
  --field-config field-path=action,order=ascending \
  --field-config field-path=timestamp,order=descending

# Audit logs - admin view
gcloud firestore indexes composite create \
  --collection-group=audit_logs \
  --field-config field-path=action,order=ascending \
  --field-config field-path=timestamp,order=descending

# Data subject requests - user requests
gcloud firestore indexes composite create \
  --collection-group=data_subject_requests \
  --field-config field-path=user_id,order=ascending \
  --field-config field-path=created_at,order=descending

# Data subject requests - status filtering
gcloud firestore indexes composite create \
  --collection-group=data_subject_requests \
  --field-config field-path=user_id,order=ascending \
  --field-config field-path=status,order=ascending \
  --field-config field-path=created_at,order=descending

# Data subject requests - type filtering (admin)
gcloud firestore indexes composite create \
  --collection-group=data_subject_requests \
  --field-config field-path=request_type,order=ascending \
  --field-config field-path=status,order=ascending \
  --field-config field-path=created_at,order=descending

# Data subject requests - overdue requests
gcloud firestore indexes composite create \
  --collection-group=data_subject_requests \
  --field-config field-path=status,order=ascending \
  --field-config field-path=due_date,order=ascending
```

### Method 3: firestore.indexes.json (Recommended for Production)

Create a `firestore.indexes.json` file:

```json
{
  "indexes": [
    {
      "collectionGroup": "consent_records",
      "queryScope": "COLLECTION",
      "fields": [
        {"fieldPath": "user_id", "order": "ASCENDING"},
        {"fieldPath": "timestamp", "order": "DESCENDING"}
      ]
    },
    {
      "collectionGroup": "consent_records",
      "queryScope": "COLLECTION",
      "fields": [
        {"fieldPath": "user_id", "order": "ASCENDING"},
        {"fieldPath": "consent_type", "order": "ASCENDING"},
        {"fieldPath": "timestamp", "order": "DESCENDING"}
      ]
    },
    {
      "collectionGroup": "consent_records",
      "queryScope": "COLLECTION",
      "fields": [
        {"fieldPath": "user_id", "order": "ASCENDING"},
        {"fieldPath": "status", "order": "ASCENDING"},
        {"fieldPath": "timestamp", "order": "DESCENDING"}
      ]
    },
    {
      "collectionGroup": "audit_logs",
      "queryScope": "COLLECTION",
      "fields": [
        {"fieldPath": "user_id", "order": "ASCENDING"},
        {"fieldPath": "timestamp", "order": "DESCENDING"}
      ]
    },
    {
      "collectionGroup": "audit_logs",
      "queryScope": "COLLECTION",
      "fields": [
        {"fieldPath": "user_id", "order": "ASCENDING"},
        {"fieldPath": "action", "order": "ASCENDING"},
        {"fieldPath": "timestamp", "order": "DESCENDING"}
      ]
    },
    {
      "collectionGroup": "audit_logs",
      "queryScope": "COLLECTION",
      "fields": [
        {"fieldPath": "action", "order": "ASCENDING"},
        {"fieldPath": "timestamp", "order": "DESCENDING"}
      ]
    },
    {
      "collectionGroup": "data_subject_requests",
      "queryScope": "COLLECTION",
      "fields": [
        {"fieldPath": "user_id", "order": "ASCENDING"},
        {"fieldPath": "created_at", "order": "DESCENDING"}
      ]
    },
    {
      "collectionGroup": "data_subject_requests",
      "queryScope": "COLLECTION",
      "fields": [
        {"fieldPath": "user_id", "order": "ASCENDING"},
        {"fieldPath": "status", "order": "ASCENDING"},
        {"fieldPath": "created_at", "order": "DESCENDING"}
      ]
    },
    {
      "collectionGroup": "data_subject_requests",
      "queryScope": "COLLECTION",
      "fields": [
        {"fieldPath": "request_type", "order": "ASCENDING"},
        {"fieldPath": "status", "order": "ASCENDING"},
        {"fieldPath": "created_at", "order": "DESCENDING"}
      ]
    },
    {
      "collectionGroup": "data_subject_requests",
      "queryScope": "COLLECTION",
      "fields": [
        {"fieldPath": "status", "order": "ASCENDING"},
        {"fieldPath": "due_date", "order": "ASCENDING"}
      ]
    }
  ],
  "fieldOverrides": []
}
```

Deploy indexes:
```bash
firebase deploy --only firestore:indexes
```

## Verification

### Check Index Status

```bash
# List all indexes
gcloud firestore indexes composite list

# Check specific index
gcloud firestore indexes composite describe INDEX_ID
```

### Test Queries

After creating indexes, test your queries:

```python
# Test consent records query
consent_records = db.collection('consent_records') \
    .where('user_id', '==', 'test-user') \
    .order_by('timestamp', direction=firestore.Query.DESCENDING) \
    .limit(10) \
    .stream()

# Test audit logs query
audit_logs = db.collection('audit_logs') \
    .where('user_id', '==', 'test-user') \
    .where('action', '==', 'data_export') \
    .order_by('timestamp', direction=firestore.Query.DESCENDING) \
    .stream()
```

## Index Build Time

- Small collections (<1000 documents): Minutes
- Medium collections (1000-100,000 documents): Hours
- Large collections (>100,000 documents): Days

**Note:** Queries will fail until indexes are built. Plan accordingly.

## Monitoring

Monitor index usage in Firebase Console:
1. Go to Firestore Database
2. Click "Usage" tab
3. View index usage statistics

## Troubleshooting

### Error: "The query requires an index"

**Solution:** Create the missing index. The error message includes a link to create it automatically.

### Index Build Stuck

**Solution:**
1. Check Firestore quotas
2. Verify no ongoing operations
3. Contact Firebase support if stuck >24 hours

### Query Still Slow After Index

**Solution:**
1. Check index is READY (not CREATING)
2. Verify query uses indexed fields
3. Consider pagination for large result sets

## Related Documentation

- [GDPR Deployment Guide](GDPR_DEPLOYMENT.md)
- [Firestore Documentation](https://firebase.google.com/docs/firestore)
- [Index Best Practices](https://firebase.google.com/docs/firestore/query-data/indexing)

