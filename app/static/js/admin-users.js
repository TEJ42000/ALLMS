/**
 * Admin Users Management JavaScript
 * Handles allow list CRUD operations
 */

const API_BASE = '/api/admin/users';

// State
let showExpired = false;
let showInactive = false;

// Helper function to get headers with CSRF token
// Note: getCSRFToken() is provided by utils.js
function getHeaders(includeContentType = true) {
    const headers = {
        'X-CSRF-Token': getCSRFToken()
    };
    if (includeContentType) {
        headers['Content-Type'] = 'application/json';
    }
    return headers;
}

// DOM Elements
const usersTbody = document.getElementById('users-tbody');
const addUserBtn = document.getElementById('add-user-btn');
const addUserModal = document.getElementById('add-user-modal');
const addUserForm = document.getElementById('add-user-form');
const showExpiredCheckbox = document.getElementById('show-expired');
const showInactiveCheckbox = document.getElementById('show-inactive');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadUsers();

    addUserBtn.addEventListener('click', () => openModal());
    addUserForm.addEventListener('submit', handleAddUser);
    showExpiredCheckbox.addEventListener('change', (e) => {
        showExpired = e.target.checked;
        loadUsers();
    });
    showInactiveCheckbox.addEventListener('change', (e) => {
        showInactive = e.target.checked;
        loadUsers();
    });

    // Event delegation for action buttons (avoids inline onclick for CSP compliance)
    usersTbody.addEventListener('click', (e) => {
        const button = e.target.closest('button[data-action]');
        if (!button) return;

        const action = button.dataset.action;
        const email = button.dataset.email;

        if (action === 'toggle') {
            toggleActive(email, button.dataset.active === 'true');
        } else if (action === 'remove') {
            removeUser(email);
        }
    });

    // Modal close buttons
    const modalClose = document.querySelector('.modal-close');
    if (modalClose) {
        modalClose.addEventListener('click', closeModal);
    }
    const cancelBtn = document.getElementById('cancel-btn');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', closeModal);
    }
});

async function loadUsers() {
    try {
        usersTbody.innerHTML = '<tr><td colspan="6" class="loading">Loading...</td></tr>';
        
        const params = new URLSearchParams();
        if (showExpired) params.append('include_expired', 'true');
        if (showInactive) params.append('include_inactive', 'true');
        
        const response = await fetch(`${API_BASE}/allowed?${params}`);
        if (!response.ok) throw new Error('Failed to load users');
        
        const data = await response.json();
        
        // Update stats
        document.getElementById('active-count').textContent = data.active_count;
        document.getElementById('expired-count').textContent = data.expired_count;
        document.getElementById('inactive-count').textContent = data.inactive_count;
        
        renderUsers(data.entries);
    } catch (error) {
        console.error('Error loading users:', error);
        usersTbody.innerHTML = '<tr><td colspan="6" class="error">Failed to load users</td></tr>';
    }
}

function renderUsers(users) {
    if (users.length === 0) {
        usersTbody.innerHTML = '<tr><td colspan="6" class="empty">No users on allow list</td></tr>';
        return;
    }
    
    usersTbody.innerHTML = users.map(user => `
        <tr data-email="${escapeHtml(user.email)}">
            <td>${escapeHtml(user.email)}</td>
            <td>${getStatusBadge(user)}</td>
            <td>${escapeHtml(user.reason)}</td>
            <td>${escapeHtml(user.added_by)}</td>
            <td>${user.expires_at ? formatDate(user.expires_at) : 'Never'}</td>
            <td>
                <button class="btn btn-sm btn-secondary" data-action="toggle" data-email="${escapeHtml(user.email)}" data-active="${!user.active}">
                    ${user.active ? 'Deactivate' : 'Activate'}
                </button>
                <button class="btn btn-sm btn-danger" data-action="remove" data-email="${escapeHtml(user.email)}">
                    Remove
                </button>
            </td>
        </tr>
    `).join('');
}

function getStatusBadge(user) {
    if (!user.active) return '<span class="badge badge-inactive">Inactive</span>';
    if (user.is_expired) return '<span class="badge badge-expired">Expired</span>';
    return '<span class="badge badge-active">Active</span>';
}

function openModal() {
    addUserModal.style.display = 'flex';
    document.getElementById('email').focus();
}

function closeModal() {
    addUserModal.style.display = 'none';
    addUserForm.reset();
}

async function handleAddUser(e) {
    e.preventDefault();

    const email = document.getElementById('email').value;
    const reason = document.getElementById('reason').value;
    const expiresAt = document.getElementById('expires_at').value;
    const notes = document.getElementById('notes').value;

    const body = { email, reason };
    if (expiresAt) body.expires_at = new Date(expiresAt).toISOString();
    if (notes) body.notes = notes;

    try {
        const response = await fetch(`${API_BASE}/allowed`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify(body)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to add user');
        }

        closeModal();
        loadUsers();
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

async function toggleActive(email, active) {
    try {
        const response = await fetch(`${API_BASE}/allowed/${encodeURIComponent(email)}`, {
            method: 'PATCH',
            headers: getHeaders(),
            body: JSON.stringify({ active })
        });

        if (!response.ok) throw new Error('Failed to update user');
        loadUsers();
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

async function removeUser(email) {
    if (!confirm(`Remove ${email} from the allow list?`)) return;

    try {
        const response = await fetch(`${API_BASE}/allowed/${encodeURIComponent(email)}`, {
            method: 'DELETE',
            headers: getHeaders(false)  // DELETE doesn't need Content-Type
        });

        if (!response.ok) throw new Error('Failed to remove user');
        loadUsers();
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

function formatDate(isoString) {
    return new Date(isoString).toLocaleDateString('en-US', {
        year: 'numeric', month: 'short', day: 'numeric'
    });
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

