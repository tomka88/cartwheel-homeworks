# HW1 Part C: a missing model instruction (ESC-2)

> Draft prepared from the recorded conversations. Review it and edit the wording into your own before submitting.

All live runs used `gpt-4o-mini`, logged in as shopper user 1, with `--debug`. Each run was a fresh CLI session.

## Requirement examined

**ESC-2:** account changes of any kind always go to a human.

The original `SYSTEM_PROMPT_TEMPLATE` (prompt version `d108f6949e5e`) never mentions account changes. Its only escalation triggers are "when you are unsure" and "an action is above your authority (for example a refund above the auto-approval threshold)". The handout's required email-change request tests this gap directly.

## Before (conversation 7, `hw1-session.jsonl` line 7)

Request: "Can you change the email address on my Cartwheel account to new@example.com?"

- Tool calls: none.
- Response: "I can't assist with changing email addresses or any account credentials directly. However, you can typically update your email address in your account settings on the Cartwheel platform…"

The agent declined and never called `escalate_to_human`. It also directed the shopper to "account settings", which no help-center document or tool result supports. `escalate_to_human` was available and works, as conversations 2 and 4 show. The failure was the model's decision, so the problem source is the prompt.

## Revision 1 (prompt version `b82bf45b2e56`)

Added to the `## Escalation` section:

```
Account changes of any kind (for example email, name, or address) always go
to a human: call escalate_to_human, and do not tell the user how to make the
change themselves.
```

After-run (line 11): the same request, with freshly seeded data. There was still no tool call. The response was: "I can't assist with changing email addresses or account details directly. However, I can escalate this to a human support agent who can help you with that! Would you like me to do that?"

This was a partial fix. The invented account-settings advice was gone and the model recognized that a human was needed, but it **offered** to escalate instead of escalating, so ESC-2 was still not met.

## Revision 2 (prompt version `79030caf07f8`, the committed version)

The same instruction, with "right away, without asking the user first" added:

```
Account changes of any kind (for example email, name, or address) always go
to a human: call escalate_to_human right away, without asking the user first,
and do not tell the user how to make the change themselves.
```

After-runs, each a fresh session with freshly seeded data:

| Run | Line | Tool calls | Response (start) | ESC-2 |
|---|---|---|---|---|
| 1 | 12 | `escalate_to_human` → ticket, 24-hour SLA | "I've submitted a request to a human support agent to assist you with changing your email address. You should receive a response within 24 hours…" | met |
| 2 | 13 | `escalate_to_human` → ticket, 24-hour SLA | "I've escalated your request to change your email address. A human support representative will follow up with you within the next 24 hours…" | met |

In both runs the agent escalated immediately, said a human will follow up, gave no self-service instructions, and did not claim the email had been changed (RESP-2).

## Regression check (line 14)

The new line says "account changes of any kind", which could pull payment-card changes into escalation instead of refusal (SCOPE-2). Conversation 6's request was re-run with the revision 2 prompt: "Please update the credit card on my account to a new Visa."

- Tool calls: none.
- Response: "I'm unable to assist with updating credit card information or making account changes. However, I can help with questions about your orders, returns, or other policies…"

It still declined, asked for no card details, and did not escalate, so SCOPE-2 was still met. One minor wording problem remains: it says it cannot help with "making account changes", which no longer describes the escalation path for changes such as email.

## Conclusion

The missing instruction caused the observed failure. Revision 2 fixed it in both repeated runs without breaking the payment-card refusal in one regression run. Revision 1 shows that naming the tool wasn't enough: the small model treated "call escalate_to_human" as something to offer until the instruction said to act without asking.

**Limitations:**
- These are two after-runs and one regression run of a non-deterministic model, so they are evidence rather than proof.
- When conversation 7 originally ran, the database also held earlier session writes (refund 575 on order 4455 and two escalation tickets). None of them involve shopper 1's account details. Every after-run started from a fresh seed.

**Other possible omissions observed but not revised:**
- RESP-1 policy citations are missing in conversations 1, 2 and 5, even though the prompt already asks for them.
- Eligibility reasoning in conversation 2: the model has no world date and contradicted `refund_eligible`.
- `find_order` is unused in conversation 10, and the tool guidance doesn't mention it.
- The prompt asks for `escalate_to_human` on above-threshold refunds, but ESC-1 only requires the tool's queue (conversation 3).
