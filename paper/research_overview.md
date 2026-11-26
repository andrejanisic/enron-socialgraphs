# Do bridges between communities see more?

**Testing the diversity–bandwidth trade-off with the network and the text of Enron email**

02805 Social Graphs and Interactions, final project. Research design.

---

## Summary

- **Groups know different things.** Organisations are made of groups that work on different problems.
- **The claim.** Network theory says that people who sit *between* groups receive more diverse information. This is the
  "vision advantage" of brokerage (Burt 1992, 2004).
- **The counter-claim.** The *diversity–bandwidth trade-off* (Aral & Van Alstyne 2011) says that links between groups are
  thin, so the advantage may be smaller than a person's position suggests.
- **What is usually missing.** Both claims are about the *content* of what flows through a network, but most network
  studies only see who talks to whom. Enron email shows both who talks to whom and what they say, on open data.
- **What we do.**
  - Find email communities from the traffic alone.
  - For each employee, measure from the network how many communities their incoming email comes from (**P**).
  - From the text alone, measure how varied the topics of that same incoming email are (**D**).
- **What we test.**
  - Does a higher P go with a higher D?
  - Do bridges receive less diversity than their mix of communities predicts?

---

## 1. Motivation

### 1.1 The claim: bridges see more

Inside a company, groups specialise. Traders, lawyers and pipeline engineers work on different problems, so they write
about different things. A person whose contacts sit in several groups is exposed to several of these streams.

- **Burt (1992, 2004)** calls this the broker's *vision advantage*: access to diverse, non-redundant information. He
  links it to good ideas, performance and promotion.
- **Granovetter (1973)** makes a related argument: links between groups carry information that a person's own group
  does not have.

### 1.2 The counter-claim: the diversity–bandwidth trade-off

Aral & Van Alstyne (2011) point out a cost.

- Links into other groups are usually **thin**: few messages flow over them.
- A thin link may carry only a narrow, routine slice of what the other group knows ("please sign the attached").
- A person between groups then hears *from* many groups but receives little *of* each. The advantage can be smaller than
  their position suggests, or disappear.

Aral & Dhillon (2023) confirm the first half of this: as brokers' networks become more diverse, their channel
bandwidth contracts.

### 1.3 What is missing

1. **The content is rarely observed.** The vision advantage is a claim about *what* flows. Most network studies,
   including most work on Enron (e.g. Diesner, Frantz & Carley 2005), see only *who* communicates with whom.
2. **The direct tests cannot be repeated.** They used private company email (an executive-recruiting firm; a media
   firm), and they measured position with Burt's constraint, which looks only at a person's own contacts.
3. **The mechanism has not been separated from the cost.** If groups write about different things, then hearing from
   several groups gives variety almost automatically. The real question is whether bridges get **that full amount**, or
   less because their links into other groups are thin. Answering it needs two things:
   - groups (communities);
   - a baseline for how much diversity a person's mix of groups *should* give.

   Constraint provides neither.

### 1.4 What this project adds

1. **An open, reproducible test** of the vision advantage and the trade-off. Enron is the only large public
   corporate email corpus.
2. **Network and information are measured independently, on the same inbox.** P uses only *who sent* a person's emails;
   D uses only *what those emails say*. If the two agree, it is not by construction.
3. **A baseline that separates "mixing" from "bandwidth".** We reassign texts among emails from the same community
   (a content shuffle). This gives the diversity each person's mix of communities predicts, and real inboxes can then be
   compared with it.

---

## 2. Research question

> **Do Enron employees whose incoming email comes from several communities receive more topically diverse email than
> employees whose email comes from one community? And do they receive less diversity than their mix of communities
> predicts, as the diversity–bandwidth trade-off implies?**

- **Part 1** asks whether bridges see more (the vision advantage).
- **Part 2** asks whether they pay for it with narrower content (the trade-off).

*Scope:* "incoming email" means email received from the other people in the dataset, not a person's whole inbox.

---

## 3. Key concepts

| Concept | Meaning | Measure |
|---|---|---|
| **Community** | A group of people who email each other much more than they email others | Louvain on the email network, from traffic only |
| **Bridge** (our position measure) | A person whose incoming email comes from several communities | Participation coefficient **P** |
| **Broker** (Burt) | A person whose contacts are not connected to each other (a "structural hole") | Burt's **constraint** (low = broker); used as a check |
| **Information diversity** | How varied the topics of a person's incoming emails are | **D**, from the email text |
| **Expected diversity** | The diversity a person's mix of communities alone would give | **E[D]**, from the content shuffle |
| **Shortfall** | Diversity below (or above) what the mix predicts | **R = D − E[D]** |
| **Bandwidth** | How much flows over a link | Emails per link |

### Bridge or broker? We study bridges

- A **bridge** is a person whose incoming email comes from several *communities*.
- A **broker**, in Burt's sense, is a person whose contacts do not know each other.
- **They are related but not the same.** Most structural holes are gaps between groups, so brokers are often bridges. But
  a broker's unconnected contacts may all sit inside one community.

The theory is written in terms of brokers, and earlier tests used constraint. We use **P as the main measure**, for two
reasons:

1. **The theory's mechanism is about groups.** Different *groups* know different things, and P measures access to
   different groups directly.
2. **Only with groups can the mechanism be tested.**
   - We can check that groups really write about different things (H0).
   - We can compute how much diversity a person's mix of groups should give (H2b).

Constraint needs no communities, so it is used as a **check**: if the result also holds for constraint, it is not an
artefact of the community detection.

*Wording:* in the literature, "bridge" can also mean a *link* between groups (Granovetter). We use "bridge" for a
person and "link between groups" for the tie.

### Precise definitions

- **Participation coefficient** (Guimerà & Amaral 2005), from incoming email:

  P_i = 1 − Σ_s (k_is / k_i)²

  - k_is = number of emails person *i* received from senders in community *s* (including their own community);
  - k_i = all emails *i* received.

  P is the chance that two randomly picked incoming emails come from different communities. 0 = all from one community.
  Louvain gives slightly different communities in different runs, so P is computed in each of 50 runs and averaged.
- **Information diversity** (the same idea as in Aral & Van Alstyne 2011: the average cosine distance of incoming emails
  from the mean of the inbox):
  - each email is a topic vector of length 1 (LSA, §6);
  - draw 20 of a person's incoming emails; D = 1 − (length of their average vector);
  - this equals the average cosine distance of the 20 emails from their common direction. 0 = all on the same topic;
    higher = more spread;
  - repeat the draw 200 times and average. Using a fixed number of emails means that people who simply receive more
    email do not look more diverse.
  - With LDA topic mixes θ, the second method is D = [H(mean θ) − mean H(θ)] / log K, where H is entropy and K is the
    number of topics.
- **Expected diversity E[D].**
  - Keep the network exactly as it is: who emails whom, how often, from which community.
  - Give every email the text of a random other email **from the same sender community**.
  - Recompute D on the same draws. E[D] is the average over 200 such shuffles.
  - E[D] is the diversity a person would get if every email from a community were a typical email of that community.
- **Constraint** (Burt 1992): c_i = Σ_j (p_ij + Σ_q p_iq p_qj)², where p_ij is the share of *i*'s email traffic that goes
  to or from *j*.
- **Bandwidth:** the number of emails on a link. Aral & Van Alstyne (2011) use the same idea per person: emails received ÷
  number of contacts.

---

## 4. Hypotheses

```
H0   Precondition: do communities write about different things?        no → bridging cannot bring variety; stop
 │
H1   Part 1, the vision advantage: does higher P go with higher D?      ← primary test, fixed in advance
 │
H2   Part 2, the trade-off
      H2a  premise:     do links between groups carry fewer emails than links within groups?
      H2b  consequence: do bridges fall further below their expected diversity (D < E[D])?
```

| | Claim | Test | Refuted if |
|---|---|---|---|
| **H0** | Email content is community-specific | A text classifier predicts the *sender's* community. It is trained and tested on **different senders**. Null: community labels shuffled between senders. | Accuracy falls inside the null |
| **H1** | Higher P → higher D | **Primary test:** Spearman ρ(P, D) across people. p-value from 5,000 shuffles of D **within seniority groups**; two-sided. | ρ falls inside the null |
| **H2a** | Links between groups carry fewer emails | Mean emails per link, within vs between **departments**. Null: email counts shuffled across links, keeping who is linked to whom. | Between ≥ within |
| **H2b** | Bridges get less than their mix predicts | Spearman ρ(P, R) with R = D − E[D]. Shuffles within seniority groups. | ρ(P, R) ≥ 0 |

**Why H0 comes first.** If all communities write about the same things, receiving from several communities cannot bring
variety, and H1 has no basis.

**Why H2b is needed.** If H0 holds, H1 is partly *expected*: someone who hears from four communities with different
vocabularies receives varied text almost automatically. H1 alone therefore cannot tell the vision advantage from simple
mixing. E[D] measures how much diversity the mix gives, and H2b asks whether bridges reach it. If links between groups
carry narrow, routine slices, a bridge's real emails from other communities are more alike than typical emails from
those communities. Then the bridge's D falls further below E[D], and R falls with P.

**Why H2a is tested.** It is the premise of the trade-off. If links between groups are *not* thinner, there is no
bandwidth cost to expect.

**One primary test, fixed in advance:** H1 with P (averaged over 50 Louvain runs) and D from LSA, for everyone with at
least 20 usable incoming emails. Every other analysis is labelled as support or robustness. This avoids trying many
versions and reporting the best one (multiple testing).

### What each outcome would mean

| Outcome | Interpretation |
|---|---|
| H0 fails | Communities share one vocabulary, so bridging cannot add information. Report this as a negative result. |
| H1 holds, ρ(P, R) ≈ 0 | Bridges see more, and exactly as much as their mix predicts: there is no content penalty for bridging. |
| H1 holds, ρ(P, R) < 0 | Bridges see more, but less than their mix predicts. This is the diversity–bandwidth trade-off. |
| H1 holds, ρ(P, R) > 0 | Bridges get *more* than their mix predicts: links between groups carry especially varied content. |
| H1 fails | Bridges do not see more: bandwidth wins. |
| H1 holds only without the seniority control | It is seniority, not bridging: executives both hear from many groups and receive broad information. |

---

## 5. Data

- **Source.** The CMU release of the Enron email corpus (made public by the FERC investigation), in our
  `data/enron_main_characters.sqlite`:
  - **people:** 148 "custodians", the employees whose mailboxes were collected;
  - **emails:** about 14,800 emails sent *between* custodians, 1999–2002;
  - **recipients:** one row per sender→recipient pair, so an email to 4 people gives 4 rows.
- **People data.** `data/enron_external.sqlite`: names, two lists of job titles and a department for each custodian.
  Checked before use (§6, Step 5).
- **Unit of analysis.** A person.
  - Included: everyone with at least 20 usable incoming emails, because D is measured on 20 emails. This is expected to
    be about 120 people.
  - Mailboxes whose identity is unclear are left out of the person-level tests.
- **Power.** With about 120 people, a correlation of |ρ| ≈ 0.25 is detected with 80% power. Smaller effects may be
  missed, so we report confidence intervals and not only p-values.

---

## 6. Analysis plan

```
            NETWORK side                                        TEXT side
 Step 2  clean emails  ─────────────────────────────────────────────┐
           │                                                        ▼
 Step 3  network (who emails whom, weight = emails)  Step 6  clean text (the sender's own words, no names)
           │                                                        │
 Step 4  communities (Louvain, 50 runs)              Step 8  topic vectors (TF-IDF → LSA; LDA)
 Step 5  people data (seniority, departments)                       │
           │                                                        │
 Step 7  P: who sent my incoming email               Step 10 D: how varied my incoming email is
           └──────────────────────────┬─────────────────────────────┘
                                      ▼
      Step 9 H0 · Step 11 H1 · Step 12 H2a and H2b · Step 13 hand labels · Step 14 robustness
```

P and D are computed from **exactly the same incoming emails**: P from *who sent* them, D from *what they say*.

| Step | What | Why |
|---|---|---|
| 1. Explore | Read the tables: what one row means, dates, recipients per email, emails to oneself, duplicates | Know the data before deciding anything |
| 2. Clean emails | Remove broken dates, machine-generated emails (our own subject rules), duplicate copies of the same email stored in two mailboxes, and arrows from a person to themself. Mass emails are kept. | These are not communication between people and would distort link weights. Mass emails are real communication; their effect is a robustness check. |
| 3. Network | Nodes = the custodians (people; the database maps each person's addresses to one ID). Directed weighted network: A→B, weight = number of emails A sent to B (an email to 4 people adds 1 to each of 4 links); used for what a person *receives*. Undirected version: A–B, weight = emails A→B + emails B→A; used for communities. **No email text is used.** | A community is a group that works together, whichever direction the email goes. Week 4 defines modularity for undirected networks (directed modularity needs adapting). Counting *incoming* email needs direction. |
| 4. Communities | Louvain on the undirected weighted network (it maximises modularity), resolution γ = 1, 50 random seeds; all runs are kept. Week 4 checks: (1) every community is connected inside; (2) "compared to what?": Q against 100 rewired networks (each person keeps their number of contacts, each link keeps its email count, the wiring is random) and 100 networks with the real links but the email counts shuffled between them; (3) stability between runs (NMI between runs; how often each person stays with their community); (4) agreement with departments (NMI against shuffled department labels). Communities are named only after these checks. | Louvain's result depends on the random visiting order, so we keep all runs. **The text is never used to find communities**; otherwise H0 would be true by construction. |
| 5. People data | Check that each row describes the right person. Build seniority from job titles with a written rule (VP and above). Check departments against the business-unit addresses in people's own emails. | Seniority is the main confounder of H1. Departments are needed for H2a. |
| 6. Clean text | Keep the subject and the sender's own words; cut forwarded and quoted parts. Remove greetings, closings, signatures, disclaimers, addresses, numbers, and names (all custodian names plus names found by spaCy NER). Usable email = at least 50 characters of content words. | The text must describe *what* an email is about, not *who* wrote it. Otherwise names and signatures would make communities look different. |
| 7. Position measures | P from each person's usable incoming emails, computed in each of the 50 runs and averaged. Burt's constraint on the undirected weighted network. | P is the main measure; constraint checks the result without communities. Averaging is valid because P does not depend on how the communities are numbered. |
| 8. Topic vectors | TF-IDF (Week 6), then LSA with 100 dimensions (essentially PCA on TF-IDF: words that occur together are merged) as the main method. LDA with 20 topics and 5 seeds as the second method. | LSA works well on short texts. LDA is the course's topic model; we check its stability over seeds. |
| 9. **H0** | Classifier (TF-IDF + logistic regression, Week 7), cross-validation **split by sender**, null with labels shuffled between senders. Distinctive words per community (log-odds, Monroe et al. 2008). | Splitting by sender stops the classifier from learning one person's writing style. The words show what each community is about. |
| 10. D | Rarefied diversity per person (20 emails, 200 draws), for LSA and LDA | Fixed sample size removes the effect of email volume |
| 11. **H1** | Primary test (§4). Support: bootstrap confidence interval; regression D ~ P + log(emails received) + senior (+ own community); constraint instead of P; LDA instead of LSA. | Shuffling within seniority groups removes the seniority confounder |
| 12. **H2a, H2b** | H2a: emails per link within vs between departments (§4). H2b: content shuffle within sender communities, giving E[D] and R; test ρ(P, R). Sanity check: shuffle texts among *all* emails, and then ρ(P, D) must be ≈ 0. | H2a uses departments because a weighted Louvain partition puts heavy links inside communities *by construction*. The sanity check shows the pipeline does not build in a correlation. |
| 13. Hand labels | Code 100 emails (stratified by community) into topics. A second coder codes them blind; compute Cohen's κ. Check whether LSA/LDA put same-topic emails closer together (AUC). | Validates that D measures topic diversity the way a human sees it (Week 7) |
| 14. Robustness | A fixed list (§7), reported as support, not as new questions | Shows that the result does not depend on one choice |

---

## 7. Threats to validity and how the design handles them

| Threat | Why it matters | How it is handled |
|---|---|---|
| Circularity | If text helped build communities, H0 and H1 would be true by construction | Communities from email traffic only |
| Names and signatures | Text would identify *people*, not topics | Own words only; names, signatures and addresses removed; vocabulary checked by hand |
| Email volume | A larger inbox looks more varied by chance | D on a fixed sample of 20 emails; log(volume) in the regression |
| Seniority | Executives may hear from every group *and* receive broad information | Permutation within seniority groups; seniority in the regression |
| Unstable communities | P could depend on one Louvain run | P averaged over 50 runs; robustness with the single best run |
| Artefact of community detection | The result could exist only for Louvain communities | The same test with constraint, which uses no communities |
| "Mechanical" H1 | Bridges get diversity automatically if communities differ | Content-shuffle baseline E[D]; H2b |
| Circular H2a | Weighted communities put heavy links inside by construction | Departments (external labels) and an unweighted partition |
| Validity of D | LSA vectors may not match topics as humans see them | Hand labels and κ; LDA as a second method |
| Short emails | Very short emails give noisy vectors that look diverse | Minimum content per email; email length as a robustness control |
| Multiple testing | Many variants could produce a "significant" one by chance | One primary test fixed in advance; everything else labelled as support |

**Robustness list (fixed in advance):**
- P from the single best run;
- without mass emails (fewer than 5 recipients only);
- a strict seniority rule (both title lists must agree);
- 10 or 40 emails per draw instead of 20;
- forwarded content included;
- the period before the crisis only (before 16 Oct 2001);
- control for the length of incoming emails;
- the content shuffle with another partition.

---

## 8. Scope and limitations (known in advance)

**Limitations:**
- **Who is in the data.** FERC chose the custodians, and only email *among* them is available. Results describe
  communication within this group, not the whole company.
- **Observational design.** The study can show association, not causation.
- **Email is only one channel.** Phone calls and meetings are not seen. To, CC and BCC are not distinguished, and
  assistants wrote some executives' emails.
- **Incomplete mailboxes.** Email deleted by both sender and recipient is lost.
- **People labels.** Departments and titles are one label per person, with no dates, although people changed jobs during
  1999–2002.
- **Little text in many emails.** Many emails are short replies or forwards and cannot be used for the text measures.

**Out of scope:**
- performance or promotion;
- how novelty changes over time;
- changes during the crisis;
- betweenness-based brokers.

---

## 9. Planned figures

1. **Figure 1: content follows communities (H0).** The email network coloured by community; the distinctive words of
   each community; the classifier's accuracy against its shuffled-label null.
2. **Figure 2: the vision advantage (H1).** P against D, one dot per person, with the permutation null.
3. **Figure 3: the trade-off (H2).** (a) Emails per link within and between departments (H2a). (b) Real ρ(P, D) against
   the content-shuffle worlds, and R against P (H2b).

---

## 10. Course methods used

| Week | Method | Where |
|---|---|---|
| 2 | Degree-preserving randomisation, permutation p-values, multiple testing | Modularity nulls; all tests; one primary test |
| 3 | Permutation within strata ("compared to what?") | H1 and H2b shuffled within seniority groups |
| 4 | Louvain, modularity against a null, stability over seeds (NMI), NMI with metadata | Step 4 |
| 5–6 | Tokenisation, TF-IDF, cosine, LDA and its stability, two-group word comparison | Steps 6, 8 and 9 |
| 7 | TF-IDF classifier, named-entity recognition, hand-label validation | H0, name removal, Step 13 |
| Beyond the course | Participation coefficient, Burt's constraint, rarefaction, content-shuffle null | Steps 7, 10 and 12 |

---

## References

- Aral, S. & Van Alstyne, M. (2011). The diversity–bandwidth trade-off. *American Journal of Sociology* 117(1), 90–171.
- Aral, S. & Dhillon, P. S. (2023). What (exactly) is novelty in networks? Unpacking the vision advantages of brokers,
  bridges, and weak ties. *Management Science* 69(2), 1092–1115.
- Blei, D. M., Ng, A. Y. & Jordan, M. I. (2003). Latent Dirichlet allocation. *JMLR* 3, 993–1022.
- Blondel, V. D. et al. (2008). Fast unfolding of communities in large networks. *J. Stat. Mech.* P10008.
- Burt, R. S. (1992). *Structural Holes: The Social Structure of Competition.* Harvard University Press.
- Burt, R. S. (2004). Structural holes and good ideas. *American Journal of Sociology* 110(2), 349–399.
- Cohen, J. (1960). A coefficient of agreement for nominal scales. *Educational and Psychological Measurement* 20(1), 37–46.
- Deerwester, S. et al. (1990). Indexing by latent semantic analysis. *JASIS* 41(6), 391–407.
- Diesner, J., Frantz, T. L. & Carley, K. M. (2005). Communication networks from the Enron email corpus.
  *Computational & Mathematical Organization Theory* 11(3), 201–228.
- Granovetter, M. (1973). The strength of weak ties. *American Journal of Sociology* 78(6), 1360–1380.
- Guimerà, R. & Amaral, L. A. N. (2005). Functional cartography of complex metabolic networks. *Nature* 433, 895–900.
- Klimt, B. & Yang, Y. (2004). The Enron corpus: a new dataset for email classification research. *ECML 2004*.
- Monroe, B. L., Colaresi, M. P. & Quinn, K. M. (2008). Fightin' words. *Political Analysis* 16(4), 372–403.
- Newman, M. E. J. (2006). Modularity and community structure in networks. *PNAS* 103(23), 8577–8582.
