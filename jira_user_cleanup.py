from jira import JIRA
from datetime import datetime, timedelta, timezone
import logging
import os
from typing import List

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class JiraUserManager:
    def __init__(self, jira_url: str, access_token: str):
        """
        Initialize Jira connection using Personal Access Token
        
        Args:
            jira_url: Your Jira instance URL
            access_token: Your Jira Personal Access Token
        """
        self.jira = JIRA(
            server=jira_url,
            token_auth=access_token  # Using PAT authentication
        )
        
    def get_all_active_users(self) -> List[dict]:
        """Get all active users from Jira."""
        try:
            # Get all users with 'active' status
            users = self.jira.search_users(query='', maxResults=False)
            active_users = [user for user in users if user.active]
            logger.info(f"Found {len(active_users)} active users")
            return active_users
        except Exception as e:
            logger.error(f"Error getting active users: {str(e)}")
            raise

    def get_user_last_login(self, username: str) -> datetime:
        """Get the last login date for a user."""
        try:
            # Note: This requires the appropriate Jira permissions
            user = self.jira.user(username)
            last_login = user.raw.get('lastLoginTime')
            if last_login:
                return datetime.strptime(last_login, "%Y-%m-%dT%H:%M:%S.%f%z")
            return None
        except Exception as e:
            logger.error(f"Error getting last login for user {username}: {str(e)}")
            return None

    def deactivate_user(self, username: str) -> bool:
        """Deactivate a Jira user."""
        try:
            # Note: This requires admin permissions
            self.jira.deactivate_user(username)
            logger.info(f"Successfully deactivated user: {username}")
            return True
        except Exception as e:
            logger.error(f"Error deactivating user {username}: {str(e)}")
            return False

    def cleanup_inactive_users(self, days_threshold: int = 60):
        """
        Find users who haven't logged in for the specified number of days.
        Currently only lists users without deactivating them.
        
        Args:
            days_threshold: Number of days of inactivity before listing
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_threshold)
        active_users = self.get_all_active_users()
        
        inactive_users = []
        for user in active_users:
            last_login = self.get_user_last_login(user.name)
            
            if last_login is None:
                logger.warning(f"Could not determine last login for user: {user.name}")
                continue
                
            if last_login < cutoff_date:
                logger.info(f"Inactive user found - Username: {user.name}, Last login: {last_login}")
                inactive_users.append({
                    'username': user.name,
                    'last_login': last_login,
                    'days_inactive': (datetime.now(timezone.utc) - last_login).days
                })
        
        # Print summary
        logger.info(f"\nInactive Users Summary:")
        logger.info(f"Total active users checked: {len(active_users)}")
        logger.info(f"Total inactive users found: {len(inactive_users)}")
        
        if inactive_users:
            logger.info("\nDetailed list of inactive users:")
            for user in sorted(inactive_users, key=lambda x: x['days_inactive'], reverse=True):
                logger.info(f"Username: {user['username']:<30} Last login: {user['last_login']} ({user['days_inactive']} days ago)")

def main():
    # Get Jira credentials from environment variables
    jira_url = os.getenv('JIRA_URL')
    jira_pat = os.getenv('JIRA_PAT')  # Personal Access Token
    
    if not all([jira_url, jira_pat]):
        logger.error("Missing required environment variables. Please set JIRA_URL and JIRA_PAT")
        return
    
    try:
        # Initialize the Jira user manager with PAT
        jira_manager = JiraUserManager(jira_url, jira_pat)
        
        # Run the cleanup process
        jira_manager.cleanup_inactive_users()
        
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main() 
