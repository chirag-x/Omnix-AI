"""High-confidence messaging workflows for apps where a wrong click has impact."""
from core.task_control import check_cancelled, wait as cancellable_wait
from skills.keyboard import press_key, type_text
from skills.mouse import click_element, click_text, find_window, verify_text
from utils.logger import log


def _require_success(result, step):
    if not isinstance(result, str) or not result.startswith("Success"):
        return f"Error: WhatsApp {step} failed. {result}"
    return None


def open_whatsapp_chat(contact: str) -> str:
    """Search one contact and verify its chat header before returning success."""
    contact = str(contact or "").strip()
    if not contact:
        return "Error: A non-empty WhatsApp contact name is required."

    check_cancelled()
    result = find_window("WhatsApp")
    error = _require_success(result, "window activation")
    if error:
        return error

    # WhatsApp's own search is safer than choosing from recent chats.
    press_key("ctrl+f")
    cancellable_wait(0.2)
    press_key("ctrl+a")
    type_text(contact)
    cancellable_wait(0.9)

    result = click_text(contact, timeout=4.0, region="chat_list", exact=True)
    error = _require_success(result, "contact selection")
    if error:
        return error

    cancellable_wait(0.8)
    result = verify_text(contact, timeout=3.0, region="chat_header", exact=True)
    error = _require_success(result, "recipient-header verification")
    if error:
        return (
            f"Error: Refusing to continue because the open chat header could not be "
            f"verified as '{contact}'. {result}"
        )
    return f"Success: Opened and verified the WhatsApp chat for '{contact}'."


def send_whatsapp_message(contact: str, message: str) -> str:
    """Send only after exact search-result and header verification."""
    contact = str(contact or "").strip()
    message = str(message or "")
    if not contact:
        return "Error: A non-empty WhatsApp contact name is required."
    if not message:
        return "Error: A non-empty WhatsApp message is required."

    result = open_whatsapp_chat(contact)
    if result.startswith("Error"):
        return result

    # Restrict the composer lookup to the lower-right conversation region.
    composer_result = click_element(
        "Type a message", timeout=2.0, region="message_box", exact=False,
    )
    if composer_result.startswith("Error"):
        composer_result = click_element(
            "Message", timeout=2.0, region="message_box", exact=False,
        )
    error = _require_success(composer_result, "message-box targeting")
    if error:
        return error

    # Re-check the recipient after focus moves to the composer and immediately
    # before typing. A changed or covered window stops the send.
    check_cancelled()
    result = verify_text(contact, timeout=2.0, region="chat_header", exact=True)
    error = _require_success(result, "final recipient verification")
    if error:
        return f"Error: Message was not typed or sent. {error}"

    log.info("Recipient verified; submitting a WhatsApp message to '%s'.", contact)
    type_text(message)
    check_cancelled()
    press_key("enter")
    cancellable_wait(0.4)

    # Verify the chat identity once more. This confirms the send was submitted
    # in the intended conversation, without claiming network delivery/read state.
    result = verify_text(contact, timeout=2.0, region="chat_header", exact=True)
    error = _require_success(result, "post-send recipient verification")
    if error:
        return (
            f"Error: The message was submitted, but Omnix could not verify that the "
            f"chat remained '{contact}'. Stop and inspect WhatsApp."
        )
    return (
        f"Success: Submitted the exact message to the verified WhatsApp chat "
        f"'{contact}'. Delivery/read status was not assumed."
    )
