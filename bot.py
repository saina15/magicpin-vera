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
    payload = trigger.get("payload", {}) or {}

    merchant_identity = merchant.get("identity", {}) or {}

    merchant_name = merchant_identity.get(
        "name",
        "your business"
    )

    owner_name = merchant_identity.get(
        "owner_first_name",
        ""
    )

    category_name = category.get(
        "display_name",
        merchant.get("category_slug", "business")
    )

    greeting = f"{owner_name}, " if owner_name else ""

    # ---------------------------------------------------------
    # CUSTOMER-FACING MESSAGES
    # ---------------------------------------------------------

    if customer:

        customer_identity = customer.get("identity", {}) or {}

        customer_name = customer_identity.get(
            "name",
            "there"
        )

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
            f"Hi {customer_name}, {merchant_name} has an update "
            f"relevant to you. Would you like to know more?"
        )

    # ---------------------------------------------------------
    # RESEARCH
    # ---------------------------------------------------------

    if trigger_kind == "research_digest":

        topic = (
            payload.get("topic")
            or payload.get("title")
            or payload.get("subject")
            or "a new market update"
        )

        takeaway = (
            payload.get("takeaway")
            or payload.get("summary")
            or payload.get("key_takeaway")
        )

        if takeaway:
            return (
                f"{greeting}there's a new {category_name} update on "
                f"{topic}. The key takeaway is: {takeaway}. "
                f"Want me to break down what it could mean for {merchant_name}?"
            )

        return (
            f"{greeting}there's a new {category_name} update on "
            f"{topic}. Want me to share the key takeaway?"
        )

    # ---------------------------------------------------------
    # REGULATION
    # ---------------------------------------------------------

    if trigger_kind == "regulation_change":

        deadline = payload.get("deadline_iso")
        regulation = (
            payload.get("regulation")
            or payload.get("title")
            or payload.get("change")
            or "a regulatory requirement"
        )

        message = (
            f"{greeting}there's a relevant regulatory update for your "
            f"{category_name} business: {regulation}"
        )

        if deadline:
            message += f" The current deadline is {deadline}."

        message += " Want me to summarise the action items?"

        return message

    # ---------------------------------------------------------
    # PERFORMANCE DIP
    # ---------------------------------------------------------

    if trigger_kind == "perf_dip":

        metric = payload.get(
            "metric",
            "performance"
        )

        delta = payload.get("delta_pct")

        current_value = (
            payload.get("current_value")
            or payload.get("current")
        )

        previous_value = (
            payload.get("previous_value")
            or payload.get("previous")
        )

        peer_value = (
            payload.get("peer_median")
            or payload.get("peer_average")
            or payload.get("benchmark")
        )

        message = f"{greeting}your {metric}"

        if delta is not None:
            try:
                percent = abs(float(delta) * 100)
                message += f" is down about {percent:.0f}%"
            except (TypeError, ValueError):
                message += " has declined"
        else:
            message += " has declined"

        if current_value is not None and previous_value is not None:
            message += (
                f" from {previous_value} to {current_value}"
            )

        if peer_value is not None:
            message += (
                f", compared with a peer benchmark of {peer_value}"
            )

        message += " in the latest window."

        return (
            message
            + " Want me to look at the likely drivers and suggest "
              "a couple of actions?"
        )

    # ---------------------------------------------------------
    # RENEWAL
    # ---------------------------------------------------------

    if trigger_kind == "renewal_due":

        plan = payload.get(
            "plan",
            "subscription"
        )

        days = payload.get("days_remaining")

        price = (
            payload.get("price")
            or payload.get("amount")
        )

        message = (
            f"{greeting}your {plan} subscription is coming up for renewal"
        )

        if days is not None:
            message += f" in {days} days"

        if price is not None:
            message += f" at {price}"

        message += "."

        return (
            message
            + " Want me to walk you through the renewal details?"
        )

    # ---------------------------------------------------------
    # FESTIVAL
    # ---------------------------------------------------------

    if trigger_kind == "festival_upcoming":

        festival = payload.get(
            "festival",
            "the upcoming festival"
        )

        return (
            f"{greeting}{festival} is coming up. "
            f"For your {category_name} business, this could be a useful "
            f"moment to plan a targeted campaign. "
            f"Want me to suggest a simple campaign idea?"
        )

    # ---------------------------------------------------------
    # SPIKE / POSITIVE PERFORMANCE
    # ---------------------------------------------------------

    if trigger_kind == "perf_spike":

        metric = payload.get(
            "metric",
            "performance"
        )

        delta = payload.get("delta_pct")

        if delta is not None:
            try:
                percent = abs(float(delta) * 100)
                return (
                    f"{greeting}your {metric} is up about "
                    f"{percent:.0f}% in the latest window. "
                    f"Want me to look at what may be driving the increase "
                    f"and how you could build on it?"
                )
            except (TypeError, ValueError):
                pass

        return (
            f"{greeting}your {metric} has improved in the latest window. "
            f"Want me to look at the likely drivers?"
        )

    # ---------------------------------------------------------
    # GENERIC FALLBACK
    # ---------------------------------------------------------

    return (
        f"{greeting}there's a new update relevant to your "
        f"{category_name} business. "
        f"Want me to look at the specific details and next steps?"
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