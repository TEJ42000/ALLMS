/**
 * Activity Tracker
 * 
 * Tracks user activity and time-on-site for gamification system.
 * Uses Page Visibility API to track only active time.
 */

class ActivityTracker {
    constructor() {
        this.sessionId = null;
        this.isActive = true;
        this.lastActivityTime = Date.now();
        this.activeSeconds = 0;
        this.currentPage = this.getCurrentPage();
        
        // Constants
        this.IDLE_THRESHOLD = 120000; // 2 minutes in milliseconds
        this.HEARTBEAT_INTERVAL = 30000; // 30 seconds
        this.CHECK_IDLE_INTERVAL = 30000; // Check idle every 30 seconds
        
        // Timers
        this.heartbeatTimer = null;
        this.idleCheckTimer = null;
        this.activeTimer = null;
        
        this.init();
    }
    
    /**
     * Initialize the activity tracker
     */
    async init() {
        console.log('[ActivityTracker] Initializing...');
        
        // Start session
        await this.startSession();
        
        // Setup event listeners
        this.setupVisibilityListener();
        this.setupActivityListeners();
        
        // Start timers
        this.startActiveTimer();
        this.startHeartbeat();
        this.startIdleCheck();
        
        // Handle page unload
        window.addEventListener('beforeunload', () => this.endSession());
        
        console.log('[ActivityTracker] Initialized');
    }
    
    /**
     * Get current page name
     */
    getCurrentPage() {
        const path = window.location.pathname;
        if (path === '/' || path === '/index') return 'dashboard';
        if (path.includes('/quiz')) return 'quiz';
        if (path.includes('/assessment')) return 'assessment';
        if (path.includes('/ai-tutor')) return 'ai-tutor';
        if (path.includes('/study-guide')) return 'study-guide';
        return 'other';
    }
    
    /**
     * Setup Page Visibility API listener
     */
    setupVisibilityListener() {
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                console.log('[ActivityTracker] Page hidden, pausing timer');
                this.pauseTimer();
            } else {
                console.log('[ActivityTracker] Page visible, resuming timer');
                this.resumeTimer();
            }
        });
    }
    
    /**
     * Setup activity listeners (mouse, keyboard)
     */
    setupActivityListeners() {
        const updateActivity = () => {
            this.lastActivityTime = Date.now();
            if (!this.isActive) {
                console.log('[ActivityTracker] User active again');
                this.isActive = true;
                this.resumeTimer();
            }
        };
        
        document.addEventListener('mousemove', updateActivity);
        document.addEventListener('keydown', updateActivity);
        document.addEventListener('click', updateActivity);
        document.addEventListener('scroll', updateActivity);
    }
    
    /**
     * Start active time timer
     */
    startActiveTimer() {
        if (this.activeTimer) return;
        
        this.activeTimer = setInterval(() => {
            if (this.isActive && !document.hidden) {
                this.activeSeconds++;
            }
        }, 1000);
    }
    
    /**
     * Pause timer
     */
    pauseTimer() {
        this.isActive = false;
    }
    
    /**
     * Resume timer
     */
    resumeTimer() {
        this.isActive = true;
        this.lastActivityTime = Date.now();
    }
    
    /**
     * Start heartbeat to server
     */
    startHeartbeat() {
        this.heartbeatTimer = setInterval(async () => {
            await this.sendHeartbeat();
        }, this.HEARTBEAT_INTERVAL);
    }
    
    /**
     * Start idle check
     */
    startIdleCheck() {
        this.idleCheckTimer = setInterval(() => {
            const timeSinceActivity = Date.now() - this.lastActivityTime;
            if (timeSinceActivity > this.IDLE_THRESHOLD && this.isActive) {
                console.log('[ActivityTracker] User idle, pausing timer');
                this.pauseTimer();
            }
        }, this.CHECK_IDLE_INTERVAL);
    }

    /**
     * Start a new session
     */
    async startSession() {
        try {
            const response = await fetch('/api/gamification/session/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.sessionId = data.session_id;
                console.log('[ActivityTracker] Session started:', this.sessionId);
            } else {
                console.error('[ActivityTracker] Failed to start session:', response.status);
            }
        } catch (error) {
            console.error('[ActivityTracker] Error starting session:', error);
        }
    }

    /**
     * Send heartbeat to server
     */
    async sendHeartbeat() {
        if (!this.sessionId || this.activeSeconds === 0) return;

        const secondsToSend = this.activeSeconds;

        try {
            const response = await fetch('/api/gamification/session/heartbeat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    active_seconds: secondsToSend,
                    current_page: this.currentPage
                })
            });

            if (response.ok) {
                console.log(`[ActivityTracker] Heartbeat sent: ${secondsToSend}s active`);
                // Only subtract what was successfully sent
                this.activeSeconds -= secondsToSend;
            } else {
                console.error('[ActivityTracker] Failed to send heartbeat, will retry:', response.status);
                // Keep accumulating for next attempt
            }
        } catch (error) {
            console.error('[ActivityTracker] Error sending heartbeat, will retry:', error);
            // Keep accumulating for next attempt
        }
    }

    /**
     * End session
     */
    async endSession() {
        if (!this.sessionId) return;

        // Send final heartbeat
        await this.sendHeartbeat();

        // Clear timers
        if (this.heartbeatTimer) clearInterval(this.heartbeatTimer);
        if (this.idleCheckTimer) clearInterval(this.idleCheckTimer);
        if (this.activeTimer) clearInterval(this.activeTimer);

        try {
            // Use sendBeacon for reliable delivery on page unload
            // Send as query parameter since sendBeacon doesn't support JSON body well
            const url = `/api/gamification/session/end?session_id=${encodeURIComponent(this.sessionId)}`;
            const success = navigator.sendBeacon(url, new Blob());
            if (success) {
                console.log('[ActivityTracker] Session ended:', this.sessionId);
            } else {
                console.warn('[ActivityTracker] sendBeacon failed, session may not have ended');
            }
        } catch (error) {
            console.error('[ActivityTracker] Error ending session:', error);
        }
    }

    /**
     * Cleanup method to remove event listeners and timers
     */
    destroy() {
        console.log('[ActivityTracker] Destroying tracker');

        // End session
        this.endSession();

        // Clear all timers
        if (this.heartbeatTimer) clearInterval(this.heartbeatTimer);
        if (this.idleCheckTimer) clearInterval(this.idleCheckTimer);
        if (this.activeTimer) clearInterval(this.activeTimer);

        // Note: Event listeners are on document, so they'll be cleaned up when page unloads
        // If we need to recreate the tracker, we should store listener references
    }

    /**
     * Log an activity
     */
    async logActivity(activityType, activityData = {}, courseId = null) {
        try {
            const response = await fetch('/api/gamification/activity', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    activity_type: activityType,
                    activity_data: activityData,
                    course_id: courseId
                })
            });

            if (response.ok) {
                const data = await response.json();
                console.log('[ActivityTracker] Activity logged:', activityType, data);

                // Show XP notification if XP was awarded
                if (data.xp_awarded > 0) {
                    this.showXPNotification(data);
                }

                // Show level up notification if leveled up
                if (data.level_up) {
                    this.showLevelUpNotification(data);
                }

                return data;
            } else {
                console.error('[ActivityTracker] Failed to log activity:', response.status);
                return null;
            }
        } catch (error) {
            console.error('[ActivityTracker] Error logging activity:', error);
            return null;
        }
    }

    /**
     * Show XP notification
     */
    showXPNotification(data) {
        console.log(`[ActivityTracker] +${data.xp_awarded} XP! Total: ${data.new_total_xp}`);

        // Dispatch custom event for UI to handle
        const event = new CustomEvent('xp-awarded', {
            detail: data
        });
        document.dispatchEvent(event);
    }

    /**
     * Show level up notification
     */
    showLevelUpNotification(data) {
        console.log(`[ActivityTracker] Level Up! Now level ${data.new_level}: ${data.new_level_title}`);

        // Dispatch custom event for UI to handle
        const event = new CustomEvent('level-up', {
            detail: data
        });
        document.dispatchEvent(event);
    }
}

// Initialize tracker when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.activityTracker = new ActivityTracker();
    });
} else {
    window.activityTracker = new ActivityTracker();
}

// Export for use in other scripts
window.ActivityTracker = ActivityTracker;

