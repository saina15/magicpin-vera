from fastapi import FastAPI
from typing import Any

app = FastAPI()

# Store all challenge context here
contexts = {
    "category": {},
    "merchant": {},
    "customer": {},
    "trigger": {}
}


@app.get("/v1/healthz")
def healthz():
    return {
        "status": "ok"
    }


@app.get("/v1/metadata")
def metadata():
    return {
        "team_name": "Saina Sinha",
        "team_members": ["Saina Sinha"],
        "model": "AI",
        "approach": "Context-aware AI assistant",
        "contact_email": "sainasinha803@gmail.com",
        "version": "1.0.0"
    }


@app.post("/v1/context")
def add_context(data: dict[str, Any]):

    scope = data.get("scope")
    context_id = data.get("context_id")
    version = data.get("version")
    payload = data.get("payload")

    # Check that the scope is valid
    if scope not in contexts:
        return {
            "accepted": False,
            "reason": "invalid_scope"
        }

    # Check that required fields exist
    if not context_id or version is None:
        return {
            "accepted": False,
            "reason": "missing_context_id_or_version"
        }

    # Check whether we already have a newer version
    existing = contexts[scope].get(context_id)

    if existing and version <= existing["version"]:
        return {
            "accepted": False,
            "reason": "stale_version",
            "current_version": existing["version"]
        }

    # Store the latest version
    contexts[scope][context_id] = {
        "version": version,
        "payload": payload
    }

    return {
        "accepted": True,
        "scope": scope,
        "context_id": context_id,
        "version": version
    }
def create_message(trigger, merchant, category, customer=None):

    trigger_kind = trigger.get("kind", "")
    payload = trigger.get("payload", {})

    merchant_name = merchant.get("identity", {}).get(
        "name",
        "your business"
    )

    owner_name = merchant.get("identity", {}).get(
        "owner_first_name",
        ""
    )

    category_name = category.get(
        "display_name",
        merchant.get("category_slug", "your category")
    )

    # Customer-facing message
    if customer:

        customer_name = customer.get(
            "identity", {}
        ).get("name", "there")

        if trigger_kind == "recall_due":

            service = payload.get(
                "service_due",
                "your next service"
            )

            return (
                f"Hi {customer_name}, {merchant_name} here. "
                f"You're due for {service}. "
                f"Would you like to book a convenient slot?"
            )

        return (
            f"Hi {customer_name}, "
            f"{merchant_name} has a quick update for you. "
            f"Would you like to know more?"
        )

    # Merchant-facing messages

    greeting = f"{owner_name}, " if owner_name else ""

    if trigger_kind == "research_digest":

        return (
            f"{greeting}a new {category_name} research update is worth a look. "
            f"I found a relevant item for your practice. "
            f"Want me to share the key takeaway?"
        )

    if trigger_kind == "regulation_change":

        deadline = payload.get("deadline_iso", "")

        return (
            f"{greeting}there's a relevant regulatory update for your "
            f"{category_name.lower()} practice. "
            f"The current deadline is {deadline}. "
            f"Want me to summarise what needs checking?"
        )

    if trigger_kind == "perf_dip":

        metric = payload.get("metric", "performance")
        delta = payload.get("delta_pct")

        if delta is not None:
            percent = round(abs(delta) * 100)

            return (
                f"{greeting}your {metric} is down about {percent}% "
                f"in the latest window. "
                f"Want me to suggest a couple of things to investigate?"
            )

        return (
            f"{greeting}there's a recent dip in your {metric}. "
            f"Want me to look at the likely drivers?"
        )

    if trigger_kind == "renewal_due":

        days = payload.get("days_remaining")

        return (
            f"{greeting}your {payload.get('plan', 'plan')} subscription "
            f"is coming up for renewal"
            + (f" in {days} days." if days else ".")
            + " Want me to walk you through the renewal details?"
        )

    if trigger_kind == "festival_upcoming":

        festival = payload.get("festival", "upcoming festival")

        return (
            f"{greeting}{festival} is coming up. "
            f"Want me to suggest a simple campaign idea for "
            f"your {category_name.lower()} business?"
        )

    # Generic fallback
    return (
        f"{greeting}there's a new update relevant to "
        f"your {category_name.lower()} business. "
        f"Want me to take a closer look?"
    )
@app.post("/v1/tick")
def tick(data: dict[str, Any]):

    available_triggers = data.get("available_triggers", [])

    actions = []

    for trigger_id in available_triggers:

        # Get trigger
        trigger_context = contexts["trigger"].get(trigger_id)

        if not trigger_context:
            continue

        trigger = trigger_context["payload"]

        # Get merchant/customer IDs from trigger
        merchant_id = trigger.get("merchant_id")
        customer_id = trigger.get("customer_id")

        # Get merchant context
        merchant_context = None

        if merchant_id:
            merchant_context = contexts["merchant"].get(merchant_id)

        if not merchant_context:
            continue

        merchant = merchant_context["payload"]

        # Get category
        category_slug = merchant.get("category_slug")

        category_context = contexts["category"].get(category_slug)

        if not category_context:
            continue

        category = category_context["payload"]

        # Get customer if this is a customer-facing trigger
        customer = None

        if customer_id:
            customer_context = contexts["customer"].get(customer_id)

            if customer_context:
                customer = customer_context["payload"]

        # Create message
        message = create_message(
            trigger,
            merchant,
            category,
            customer
        )

        # Decide who receives the message
        if customer_id:
            send_as = "merchant_on_behalf"
        else:
            send_as = "vera"

        # Create conversation ID
        conversation_id = f"conv_{trigger_id}"

        actions.append({
            "conversation_id": conversation_id,
            "merchant_id": merchant_id,
            "customer_id": customer_id,
            "send_as": send_as,
            "trigger_id": trigger_id,
            "template_name": "vera_contextual_v1",
            "template_params": [],
            "body": message,
            "cta": "open_ended",
            "suppression_key": trigger.get("suppression_key"),
            "rationale": f"Relevant {trigger.get('kind', 'business')} trigger for this merchant"
        })

    return {
        "actions": actions
    }
@app.post("/v1/reply")
def reply(data: dict[str, Any]):

    message = data.get("message", "").strip()
    message_lower = message.lower()

    # Handle unsubscribe / hostile messages
    if any(word in message_lower for word in [
        "stop messaging",
        "stop",
        "unsubscribe",
        "do not message",
        "don't message",
        "spam"
    ]):
        return {
            "action": "end",
            "body": ""
        }

    # Detect automated replies
    if any(phrase in message_lower for phrase in [
        "thank you for contacting us",
        "our team will respond shortly",
        "we will respond shortly",
        "automated response",
        "auto-reply"
    ]):
        return {
            "action": "end",
            "body": ""
        }

    # Merchant has committed to proceed
    if any(phrase in message_lower for phrase in [
        "ok lets do it",
        "ok let's do it",
        "lets do it",
        "let's do it",
        "whats next",
        "what's next",
        "what next"
    ]):
        return {
            "action": "send",
            "body": "Absolutely. Next, I'll proceed with the relevant details and guide you through the next step."
        }

    # Generic conversational response
    return {
        "action": "send",
        "body": "Thanks for the update. Let me know what you'd like to do next."
    }