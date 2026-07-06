# Manual Labelling Guidelines

This guide explains how to manually label a smaller trusted set of cleaned reviews.

The project has two label tables:

- `review_labels_weak` contains automatic rule-based guesses.
- `review_labels_manual` contains trusted human-checked labels.

Manual labels are not needed for every review. They are used as a smaller
gold-standard answer key for evaluation, error analysis, and future retraining checks.

The final system will still classify reviews automatically. Manual labels are used to perform evaluation and error analysis on the
automatic system

## 1. What Manual Labelling Is For

Manual labelling means a person reads a review and chooses the correct labels.

The manual labels help answer questions like:

- Is the automatic classifier choosing the right issue?
- Are weak labels making common mistakes?
- Which issue types are hardest to classify?
- Did a future model improve or get worse?

## 2. What Each Label Column Means

`review_id`

The review being labelled. This should match one row in `clean_reviews`.

`scope_label`

Whether the review is about the digital wallet part of the app.

`primary_issue_label`

The main issue in the review. The allowed issue labels come from
`config/issue_taxonomy.yaml`.

`priority_label`

How urgent or important the review seems.

`labelled_by`

The name, initials, or identifier of the person who labelled the review.

`labelled_at`

When the manual label was created.

`label_notes`

Optional notes explaining a difficult or uncertain label.

`created_at`

When the row was created in the database.

`updated_at`

When the row was last updated in the database.

## 3. How To Choose `scope_label`

Use `scope_label` to say whether the review is mainly about the wallet or
payment-related part of the app.

Allowed values:

- `wallet_related`
- `non_wallet_related`
- `unclear`

Choose `wallet_related` when the review is about payments, wallet balance, top-ups, transfers, QR payments, refunds, account access, KYC, fraud, rewards, fees, or customer support for wallet issues.

Choose `non_wallet_related` when the review is mainly about another part of a superapp, such as food delivery, shopping, ride hailing, games, or other non-wallet services.

Choose `unclear` when there is not enough information to decide.

## 4. How To Choose `primary_issue_label`

Use `primary_issue_label` for the main issue in the review.

The allowed labels come from `config/issue_taxonomy.yaml`:

- `login_otp_authentication`
- `top_up_failure`
- `wallet_balance_issue`
- `failed_transfer`
- `qr_payment_failure`
- `money_deducted_transaction_failed`
- `refund_dispute`
- `merchant_payment_issue`
- `kyc_verification`
- `account_locked_restricted`
- `fraud_scam_concern`
- `cashback_rewards_promo`
- `fees_charges`
- `customer_service_support`
- `app_crash_bug_performance`
- `app_update_issue`
- `general_positive_feedback`
- `other_unclear`

If the review contains more than one issue, choose the issue that seems most central or most urgent.

For example, if a review says the payment failed and money was deducted, choose `money_deducted_transaction_failed` because the money loss is the most important part.

If the review is positive and does not describe a problem, choose
`general_positive_feedback`.

If the review is too vague to classify, choose `other_unclear`.

## 5. How To Choose `priority_label`

Use `priority_label` to describe how serious the review seems.

Allowed values:

- `high`
- `medium`
- `low`
- `unclear`

Choose `high` for serious or urgent issues, such as:

- money loss
- failed transaction
- account locked
- fraud or scam concern
- refund dispute
- KYC blocking access
- urgent support issue

Choose `medium` for a clear complaint that is not immediately severe.

Choose `low` for general feedback, a mild issue, a positive review, or an
unclear low-impact issue.

Choose `unclear` when there is not enough information to decide.

## 6. How To Use `label_notes`

`label_notes` is optional.

Use it when the label is difficult, uncertain, or needs extra explanation. Notes
are useful later during error analysis because they explain why a human chose a
label.

Examples of useful notes:

- "Mentions both login and refund, but refund seems more urgent."
- "Review is vague, but appears to be about wallet payment."
- "Could be non-wallet support, not enough detail."

Leave `label_notes` empty when the label is obvious.

## 7. Example Labelled Reviews

### Example 1: Money deducted after failed transaction

**Review text:**  
"My money was deducted but the transfer failed."

**Labels:**
- `scope_label`: `wallet_related`
- `primary_issue_label`: `money_deducted_transaction_failed`
- `priority_label`: `high`

**Label notes:**  
Money loss is the most urgent issue.

---

### Example 2: OTP login problem

**Review text:**  
"I cannot log in because the OTP never arrives."

**Labels:**
- `scope_label`: `wallet_related`
- `primary_issue_label`: `login_otp_authentication`
- `priority_label`: `medium`

**Label notes:**  
Account access issue, but no money loss mentioned.

---

### Example 3: Top-up failure

**Review text:**  
"Top up failed and my balance did not update."

**Labels:**
- `scope_label`: `wallet_related`
- `primary_issue_label`: `top_up_failure`
- `priority_label`: `high`

**Label notes:**  
Top-up failure affects wallet balance.

---

### Example 4: App crash after update

**Review text:**  
"The app keeps crashing after the latest update."

**Labels:**
- `scope_label`: `wallet_related`
- `primary_issue_label`: `app_update_issue`
- `priority_label`: `medium`

**Label notes:**  
The review suggests the update caused the problem.

---

### Example 5: Cashback issue

**Review text:**  
"Cashback voucher did not appear after payment."

**Labels:**
- `scope_label`: `wallet_related`
- `primary_issue_label`: `cashback_rewards_promo`
- `priority_label`: `low`

**Label notes:**  
Rewards issue, but not urgent.

---

### Example 6: Non-wallet superapp review

**Review text:**  
"Food delivery was late again."

**Labels:**
- `scope_label`: `non_wallet_related`
- `primary_issue_label`: `other_unclear`
- `priority_label`: `low`

**Label notes:**  
This is about food delivery, not wallet or payment features.

---

### Example 7: Vague review

**Review text:**  
"Bad app, useless."

**Labels:**
- `scope_label`: `unclear`
- `primary_issue_label`: `other_unclear`
- `priority_label`: `unclear`

**Label notes:**  
Too vague to classify confidently.

---

### Example 8: Positive wallet feedback

**Review text:**  
"Great app, payment is smooth."

**Labels:**
- `scope_label`: `wallet_related`
- `primary_issue_label`: `general_positive_feedback`
- `priority_label`: `low`

**Label notes:**  
Positive wallet-related feedback.