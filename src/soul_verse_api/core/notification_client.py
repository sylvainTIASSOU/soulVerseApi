import logging
from enum import Enum
from typing import Dict, List, Optional

import firebase_admin
from firebase_admin import credentials, messaging

# Set up logging
logger = logging.getLogger(__name__)


class NotificationPushType(Enum):
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    URGENT = "urgent"
    DAILY_VERSE = "daily_verse"
    MORNING_PRAYER = "morning_prayer"
    EVENING_PRAYER = "evening_prayer"
    SPIRITUAL_REMINDER = "spiritual_reminder"


class Priority(Enum):
    HIGH = "high"
    NORMAL = "normal"


class NotificationError(Exception):
    """Custom exception for notification errors"""
    pass


def initialize_firebase():
    """
    Initialize Firebase Admin SDK with service account credentials.
    """
    if not firebase_admin._apps:
        cred = credentials.Certificate(
            "src/soul_verse_api/core/soulverse-app-c69392a6c184.json")
        firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized successfully.")


class NotificationClient:
    """
    Firebase Cloud Messaging client for sending notifications to SoulVerse users.
    """

    def __init__(self):
        initialize_firebase()

    def _create_notification(self, title: str, body: str, token: str = None, topic: str = None,
                             tokens: List[str] = None, image_url: str = None,
                             notification_type: NotificationPushType = NotificationPushType.INFO,
                             priority: Priority = Priority.NORMAL,
                             data: Dict[str, str] = None) -> messaging.Message:
        """
        Create a Firebase message.

        Args:
            title (str): Notification title
            body (str): Notification body
            token (str, optional): FCM token for single device
            topic (str, optional): Topic name for topic messaging
            tokens (List[str], optional): List of FCM tokens for multiple devices
            image_url (str, optional): URL of image to display
            notification_type (NotificationPushType): Type of notification
            priority (Priority): Message priority
            data (Dict[str, str], optional): Additional data to send

        Returns:
            messaging.Message: Firebase message object
        """
        # Prepare notification payload
        notification_payload = messaging.Notification(
            title=title,
            body=body,
            image=image_url
        )

        # Prepare data payload
        data_payload = data or {}
        data_payload.update({
            "type": notification_type.value,
            "priority": priority.value
        })

        # Android specific configuration
        android_config = messaging.AndroidConfig(
            priority=priority.value,
            notification=messaging.AndroidNotification(
                title=title,
                body=body,
                icon="ic_stat_soulverse",
                color="#4A90E2",
                sound="default",
                channel_id=f"soulverse_{notification_type.value}"
            )
        )

        # iOS specific configuration
        apns_config = messaging.APNSConfig(
            payload=messaging.APNSPayload(
                aps=messaging.Aps(
                    alert=messaging.ApsAlert(
                        title=title,
                        body=body
                    ),
                    sound="default",
                    badge=1
                )
            )
        )

        # Create message based on target type
        if token:
            return messaging.Message(
                notification=notification_payload,
                data=data_payload,
                token=token,
                android=android_config,
                apns=apns_config
            )
        elif topic:
            return messaging.Message(
                notification=notification_payload,
                data=data_payload,
                topic=topic,
                android=android_config,
                apns=apns_config
            )
        else:
            raise NotificationError("Either token or topic must be provided")

    def send_to_token(self, title: str, body: str, token: str,
                      image_url: str = None,
                      notification_type: NotificationPushType = NotificationPushType.INFO,
                      priority: Priority = Priority.NORMAL,
                      data: Dict[str, str] = None) -> bool:
        """
        Send notification to a specific device token.

        Args:
            title (str): Notification title
            body (str): Notification body
            token (str): FCM token
            image_url (str, optional): URL of image to display
            notification_type (NotificationPushType): Type of notification
            priority (Priority): Message priority
            data (Dict[str, str], optional): Additional data

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            message = self._create_notification(
                title=title,
                body=body,
                token=token,
                image_url=image_url,
                notification_type=notification_type,
                priority=priority,
                data=data
            )

            response = messaging.send(message)
            logger.info(f"Successfully sent message to token: {response}")
            return True

        except Exception as e:
            logger.error(f"Error sending message to token {token}: {str(e)}")
            return False

    def send_to_topic(self, title: str, body: str, topic: str,
                      image_url: str = None,
                      notification_type: NotificationPushType = NotificationPushType.INFO,
                      priority: Priority = Priority.NORMAL,
                      data: Dict[str, str] = None) -> bool:
        """
        Send notification to a topic.

        Args:
            title (str): Notification title
            body (str): Notification body
            topic (str): Topic name
            image_url (str, optional): URL of image to display
            notification_type (NotificationPushType): Type of notification
            priority (Priority): Message priority
            data (Dict[str, str], optional): Additional data

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            message = self._create_notification(
                title=title,
                body=body,
                topic=topic,
                image_url=image_url,
                notification_type=notification_type,
                priority=priority,
                data=data
            )

            response = messaging.send(message)
            logger.info(
                f"Successfully sent message to topic {topic}: {response}")
            return True

        except Exception as e:
            logger.error(f"Error sending message to topic {topic}: {str(e)}")
            return False

    def send_to_multiple(self, title: str, body: str, tokens: List[str],
                         image_url: str = None,
                         notification_type: NotificationPushType = NotificationPushType.INFO,
                         priority: Priority = Priority.NORMAL,
                         data: Dict[str, str] = None) -> Dict[str, int]:
        """
        Send notification to multiple device tokens.

        Args:
            title (str): Notification title
            body (str): Notification body
            tokens (List[str]): List of FCM tokens
            image_url (str, optional): URL of image to display
            notification_type (NotificationPushType): Type of notification
            priority (Priority): Message priority
            data (Dict[str, str], optional): Additional data

        Returns:
            Dict[str, int]: Result summary with success_count and failure_count
        """
        try:
            # Prepare notification payload
            notification_payload = messaging.Notification(
                title=title,
                body=body,
                image=image_url
            )

            # Prepare data payload
            data_payload = data or {}
            data_payload.update({
                "type": notification_type.value,
                "priority": priority.value
            })

            # Android specific configuration
            android_config = messaging.AndroidConfig(
                priority=priority.value,
                notification=messaging.AndroidNotification(
                    title=title,
                    body=body,
                    icon="ic_stat_soulverse",
                    color="#4A90E2",
                    sound="default",
                    channel_id=f"soulverse_{notification_type.value}"
                )
            )

            # iOS specific configuration
            apns_config = messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        alert=messaging.ApsAlert(
                            title=title,
                            body=body
                        ),
                        sound="default",
                        badge=1
                    )
                )
            )

            # Send to each token individually
            # Note: send_multicast is not available, using individual sends
            success_count = 0
            failure_count = 0
            failed_tokens = []

            for token in tokens:
                try:
                    message = messaging.Message(
                        notification=notification_payload,
                        data=data_payload,
                        token=token,
                        android=android_config,
                        apns=apns_config
                    )

                    messaging.send(message)
                    success_count += 1

                except messaging.UnregisteredError:
                    failure_count += 1
                    failed_tokens.append({
                        "token": token[:20] + "...",
                        "error": "Unregistered token"
                    })
                    logger.warning(f"Token is unregistered: {token[:20]}...")

                except messaging.InvalidArgumentError as e:
                    failure_count += 1
                    failed_tokens.append({
                        "token": token[:20] + "...",
                        "error": f"Invalid argument: {str(e)}"
                    })
                    logger.error(
                        f"Invalid argument for token {token[:20]}...: {e}")

                except Exception as e:
                    failure_count += 1
                    failed_tokens.append({
                        "token": token[:20] + "...",
                        "error": str(e)
                    })
                    logger.error(
                        f"Error sending to token {token[:20]}...: {e}")

            logger.info(f"Successfully sent {success_count} messages")
            if failure_count > 0:
                logger.warning(f"Failed to send {failure_count} messages")

            return {
                "success_count": success_count,
                "failure_count": failure_count,
                "failed_tokens": failed_tokens
            }

        except Exception as e:
            logger.error(f"Error sending multicast message: {str(e)}")
            return {"success_count": 0, "failure_count": len(tokens)}

    def subscribe_to_topic(self, tokens: List[str], topic: str) -> bool:
        """
        Subscribe device tokens to a topic.

        Args:
            tokens (List[str]): List of FCM tokens
            topic (str): Topic name

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            response = messaging.subscribe_to_topic(tokens, topic)
            logger.info(
                f"Successfully subscribed {len(tokens)} tokens to topic {topic}")
            return True
        except Exception as e:
            logger.error(f"Error subscribing to topic {topic}: {str(e)}")
            return False

    def unsubscribe_from_topic(self, tokens: List[str], topic: str) -> bool:
        """
        Unsubscribe device tokens from a topic.

        Args:
            tokens (List[str]): List of FCM tokens
            topic (str): Topic name

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            response = messaging.unsubscribe_from_topic(tokens, topic)
            logger.info(
                f"Successfully unsubscribed {len(tokens)} tokens from topic {topic}")
            return True
        except Exception as e:
            logger.error(f"Error unsubscribing from topic {topic}: {str(e)}")
            return False

    # SoulVerse-specific notification methods

    def send_daily_verse(self, verse_content: str, verse_reference: str,
                         reflection: str = None, image_url: str = None,
                         tokens: List[str] = None, topic: str = "daily_verses") -> bool:
        """
        Send daily verse notification.

        Args:
            verse_content (str): Bible verse text
            verse_reference (str): Verse reference (e.g., "John 3:16")
            reflection (str, optional): AI-generated reflection
            image_url (str, optional): Generated verse image URL
            tokens (List[str], optional): Specific device tokens
            topic (str): Topic name for daily verses

        Returns:
            bool: True if successful, False otherwise
        """
        title = f"Daily Verse - {verse_reference}"
        body = verse_content[:100] + \
            "..." if len(verse_content) > 100 else verse_content

        data = {
            "verse_reference": verse_reference,
            "verse_content": verse_content,
        }

        if reflection:
            data["reflection"] = reflection

        if image_url:
            data["image_url"] = image_url

        if tokens:
            return self.send_to_multiple(
                title=title,
                body=body,
                tokens=tokens,
                image_url=image_url,
                notification_type=NotificationPushType.DAILY_VERSE,
                priority=Priority.NORMAL,
                data=data
            )["success_count"] > 0
        else:
            return self.send_to_topic(
                title=title,
                body=body,
                topic=topic,
                image_url=image_url,
                notification_type=NotificationPushType.DAILY_VERSE,
                priority=Priority.NORMAL,
                data=data
            )

    def send_morning_prayer(self, prayer_text: str = None,
                            tokens: List[str] = None,
                            topic: str = "morning_prayers") -> bool:
        """
        Send morning prayer notification.

        Args:
            prayer_text (str, optional): Custom prayer text
            tokens (List[str], optional): Specific device tokens
            topic (str): Topic name for morning prayers

        Returns:
            bool: True if successful, False otherwise
        """
        title = "Good Morning! 🌅"
        body = prayer_text or "Start your day with prayer and reflection. May God bless your day!"

        data = {
            "prayer_type": "morning",
            "prayer_text": body
        }

        if tokens:
            return self.send_to_multiple(
                title=title,
                body=body,
                tokens=tokens,
                notification_type=NotificationPushType.MORNING_PRAYER,
                priority=Priority.NORMAL,
                data=data
            )["success_count"] > 0
        else:
            return self.send_to_topic(
                title=title,
                body=body,
                topic=topic,
                notification_type=NotificationPushType.MORNING_PRAYER,
                priority=Priority.NORMAL,
                data=data
            )

    def send_evening_prayer(self, prayer_text: str = None,
                            tokens: List[str] = None,
                            topic: str = "evening_prayers") -> bool:
        """
        Send evening prayer notification.

        Args:
            prayer_text (str, optional): Custom prayer text
            tokens (List[str], optional): Specific device tokens
            topic (str): Topic name for evening prayers

        Returns:
            bool: True if successful, False otherwise
        """
        title = "Good Evening! 🌙"
        body = prayer_text or "End your day with gratitude and prayer. Rest in God's peace."

        data = {
            "prayer_type": "evening",
            "prayer_text": body
        }

        if tokens:
            return self.send_to_multiple(
                title=title,
                body=body,
                tokens=tokens,
                notification_type=NotificationPushType.EVENING_PRAYER,
                priority=Priority.NORMAL,
                data=data
            )["success_count"] > 0
        else:
            return self.send_to_topic(
                title=title,
                body=body,
                topic=topic,
                notification_type=NotificationPushType.EVENING_PRAYER,
                priority=Priority.NORMAL,
                data=data
            )

    def send_spiritual_reminder(self, title: str, message: str,
                                tokens: List[str] = None,
                                topic: str = "spiritual_reminders") -> bool:
        """
        Send spiritual reminder notification.

        Args:
            title (str): Reminder title
            message (str): Reminder message
            tokens (List[str], optional): Specific device tokens
            topic (str): Topic name for spiritual reminders

        Returns:
            bool: True if successful, False otherwise
        """
        data = {
            "reminder_type": "spiritual",
            "message": message
        }

        if tokens:
            return self.send_to_multiple(
                title=title,
                body=message,
                tokens=tokens,
                notification_type=NotificationPushType.SPIRITUAL_REMINDER,
                priority=Priority.NORMAL,
                data=data
            )["success_count"] > 0
        else:
            return self.send_to_topic(
                title=title,
                body=message,
                topic=topic,
                notification_type=NotificationPushType.SPIRITUAL_REMINDER,
                priority=Priority.NORMAL,
                data=data
            )
