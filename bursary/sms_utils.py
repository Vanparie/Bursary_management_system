from django.conf import settings
import africastalking

africastalking.initialize(settings.AT_USERNAME, settings.AT_API_KEY)
sms = africastalking.SMS


def send_sms(phone_number, message):
    """
    Send SMS using Africa's Talking.
    Works in sandbox mode with registered numbers.
    """
    try:
        response = sms.send(message, [phone_number])
        print(f"✅ SMS sent: {response}")
    except Exception as e:
        print(f"❌ SMS failed: {str(e)}")
