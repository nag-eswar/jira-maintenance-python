import com.atlassian.jira.component.ComponentAccessor
import com.atlassian.jira.user.util.UserManager
import com.atlassian.crowd.embedded.api.User
import java.time.LocalDateTime
import java.time.ZoneId
import groovy.time.TimeCategory

// Get the user manager
def userManager = ComponentAccessor.userManager
def crowdService = ComponentAccessor.crowdService
def lastLoginService = ComponentAccessor.getLastLoginService()

// Get current date and calculate the cutoff date (60 days ago)
def now = LocalDateTime.now()
def cutoffDate = now.minusDays(60)

// Counter for deactivated users
def deactivatedCount = 0
def skippedCount = 0

// Get all active users
def activeUsers = userManager.getAllUsers().findAll { it.isActive() }

log.info "Found ${activeUsers.size()} active users"

activeUsers.each { user ->
    def username = user.getName()
    
    // Skip the current user and admin accounts
    if (username == "admin" || username == ComponentAccessor.jiraAuthenticationContext.loggedInUser.name) {
        log.warn "Skipping admin user: ${username}"
        skippedCount++
        return
    }
    
    // Get last login date
    def lastLoginMillis = lastLoginService.getLastLoginTime(username)
    if (lastLoginMillis == null) {
        log.warn "No login record found for user: ${username}"
        return
    }
    
    def lastLoginDate = LocalDateTime.ofInstant(
        java.time.Instant.ofEpochMilli(lastLoginMillis), 
        ZoneId.systemDefault()
    )
    
    // Check if user hasn't logged in for more than 60 days
    if (lastLoginDate.isBefore(cutoffDate)) {
        log.info "User ${username} last logged in on ${lastLoginDate}"
        
        try {
            // Deactivate the user
            crowdService.deactivateUser(username)
            log.info "Successfully deactivated user: ${username}"
            deactivatedCount++
        } catch (Exception e) {
            log.error "Failed to deactivate user ${username}: ${e.message}"
        }
    }
}

// Print summary
log.info """
Deactivation process completed:
- Total active users processed: ${activeUsers.size()}
- Users deactivated: ${deactivatedCount}
- Users skipped (admin accounts): ${skippedCount}
""" 