# Theme Discovery Approach

We used a hybrid method because it balances interpretability and discovery:

1. **Rule-based theme assignment**
   - Clear keyword patterns map meetings to known themes such as support escalation, renewal/expansion, onboarding, compliance, internal planning, and demos/POCs.
   - This makes the output easy to explain and easy to audit.

2. **Unsupervised topic discovery (TF-IDF + NMF)**
   - NMF groups meetings by shared language patterns without needing labels.
   - This helps surface latent themes that may not have been obvious from the seed rules alone.

3. **Representative examples**
   - For each theme, we keep a few example meetings and the matched keywords so the result is explainable, not just a black-box assignment.

### Output counts
- Meetings processed: 100
- Rule-based themes found: 7
- Latent topics discovered: 8
