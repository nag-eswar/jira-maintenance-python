from jira import JIRA
from datetime import datetime, timedelta
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
    def __init__(self, jira_url: str, email: str, api_token: str):
        """
        Initialize Jira connection
        
        Args:
            jira_url: Your Jira instance URL
            email: Your Jira email
            api_token: Your Jira API token
        """
        self.jira = JIRA(
            server=jira_url,
            basic_auth=(email, api_token)
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
        Find and deactivate users who haven't logged in for the specified number of days.
        
        Args:
            days_threshold: Number of days of inactivity before deactivation
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_threshold)
        active_users = self.get_all_active_users()
        
        deactivated_count = 0
        for user in active_users:
            last_login = self.get_user_last_login(user.name)
            
            if last_login is None:
                logger.warning(f"Could not determine last login for user: {user.name}")
                continue
                
            if last_login < cutoff_date:
                logger.info(f"User {user.name} last logged in on {last_login}, deactivating...")
                if self.deactivate_user(user.name):
                    deactivated_count += 1
                    
        logger.info(f"Deactivation complete. {deactivated_count} users were deactivated.")

def main():
    # Get Jira credentials from environment variables
    jira_url = os.getenv('JIRA_URL')
    jira_email = os.getenv('JIRA_EMAIL')
    jira_api_token = os.getenv('JIRA_API_TOKEN')
    
    if not all([jira_url, jira_email, jira_api_token]):
        logger.error("Missing required environment variables. Please set JIRA_URL, JIRA_EMAIL, and JIRA_API_TOKEN")
        return
    
    try:
        # Initialize the Jira user manager
        jira_manager = JiraUserManager(jira_url, jira_email, jira_api_token)
        
        # Run the cleanup process
        jira_manager.cleanup_inactive_users()
        
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main() 