# What the emails are about

NMF topic model (10 topics) on TF-IDF of the sender's own words, 6209 emails with at least 20 own words. Each email goes to its strongest topic; below weight 0.02 it counts as 'no clear topic'. The model gives no names: the names were written by hand from the top words and examples (`data/topic_names_emails.csv`).

| topic | name | emails | share (%) | top words |
|---|---|---|---|---|
| 1 | California regulation (FERC, PUC) | 940 | 15.1 | don, market, ferc, customers, california, edison, contracts, puc, issue, does, rate, business |
| 2 | Pipeline deliveries | 156 | 2.5 | mmbtu, deliveries, capacity, juan, pkgs, san, average, large, california, waha, perm, averaged |
| 3 | Master agreements (ISDA) | 351 | 5.7 | master, agreement, effective, counterparty, corp, transactions, date, executed, isda, received, ena, entity |
| 4 | Meetings | 609 | 9.8 | meeting, discuss, attend, plan, morning, lynn, meet, room, scheduled, afternoon, stan, set |
| 5 | Drafts for review | 599 | 9.6 | review, draft, comments, changes, letter, agreement, version, revised, language, kim, copy, gerald |
| 6 | Credit and legal paperwork | 621 | 10.0 | sara, credit, susan, mark, isda, email, legal, form, list, confirm, guaranty, group |
| 7 | Power deals and positions | 554 | 8.9 | deal, deals, mws, sale, price, book, peak, enpower, short, sell, buy, did |
| 8 | Confidentiality agreements | 235 | 3.8 | executed, received, llc, dated, copy, agreement, samuels, dave, confidentiality, works, copies, enrononline |
| 9 | Out of office | 599 | 9.6 | office, friday, monday, phone, cell, wednesday, vacation, thursday, tuesday, reached, mail, home |
| 10 | Gas trading desks and EnronOnline | 876 | 14.1 | gas, trading, file, daily, eol, list, west, physical, power, desk, book, set |
| no clear topic |  | 669 | 10.8 |  |

## Strongest emails per topic

**Topic 1: California regulation (FERC, PUC)** (don, market, ferc, customers, california, edison)
- Received the following additional information late yesterday from Speaker Hertzberg's chief of staff regarding Direct Access in the legislation working its way through the Assembly. He relayed the inf
- THE LEGISLATURE No material change from the last update. The Legislature is in recess and the two bills that passed the Senate--SB 78 and SB 18--continue to sit in the Assembly, waiting for the Assemb
- On the various matters currently before the California PUC: The Commission order stating that the utilities should absorb any difference between DWR's cost of power and the retail rate freeze is still

**Topic 2: Pipeline deliveries** (mmbtu, deliveries, capacity, juan, pkgs, san)
- Transwestern's average deliveries to California were 856 MMBtu/d (78%), with San Juan lateral throughput at 783 MMBtu/d and Rio Puerco at 17 MMBtu/d. Total East deliveries averaged 564 MMBtu/d. El Pas
- Transwestern's average deliveries to California were 949 MMBtu/d (87%), with San Juan lateral throughput at 853 MMBtu/d and Rio Puerco at 30 MMBtu/d. Total East deliveries averaged 483 MMBtu/d. El Pas
- Transwestern's average deliveries to California were 1118 MMBtu/d (103%), with San Juan lateral throughput at 873 MMBtu/d and Rio Puerco at 11 MMBtu/d. Total East deliveries averaged 436 MMBtu/d. El P

**Topic 3: Master agreements (ISDA)** (master, agreement, effective, counterparty, corp, transactions)
- We have received an executed financial master agreement: Type of Agreement: ISDA Master Agreement (Multicurrency-Cross Border) Effective Date: June 4, 2001 Enron Entity: Enron Canada Corp. Counterpart
- We have received the following executed Master Agreement: Type of Contract: ISDA Master Agreement ( Multicurrency-Cross Border) Effective Date: March 31, 2000 Enron Entity: Enron North America Corp. C
- We have received the following executed financial master agreement: Type of Contract: ISDA Master Agreement (Multicurrency-Cross Border) Effective Date: September 11, 2001 Enron Entity: Enron North Am

**Topic 4: Meetings** (meeting, discuss, attend, plan, morning, lynn)
- I hope we are not planning on meeting for several hours. I have another meeting scheduled starting at 10:30. Also, where are we meeting?
- We will meet after the morning meeting tomorrow to discuss these imbalances with Market Services. If you are available, please plan to attend.
- We will try again for this meeting. If we do not have the new LTD by this time we will look at having the meeting on Wed. 9/12.

**Topic 5: Drafts for review** (review, draft, comments, changes, letter, agreement)
- Attached for your review and comments is a first draft of the letter that Kim requested to the operators that have not yet executed new OBAs.
- Attached for your review and comments is a revised draft of the Citizens Utilities reimbursement agreement, which is red-lined to show changes from the prior draft. The only changes are to address tax
- Attached is a draft of a nonbinding letter for use to submit the indicative bid to Wildhorse. Please review and provide any comments.

**Topic 6: Credit and legal paperwork** (sara, credit, susan, mark, isda, email)
- Kim: Thanks for your call. Legal received credit for Tuscon on 5/1/00 from Ed Sacks. Susan Flynn is preparing the ISDA agreement to send to the counterparty. Let me know if you have any other question
- I don't know if you have spoken with Susan Flynn about her schedule before/after her surgery, but I have some questions that you may have already addressed, such as: Has Susan prepared a matrix reflec
- Per my earlier email and the one below, could you please let us know about the 2000 Defintions? Thanks. Sara

**Topic 7: Power deals and positions** (deal, deals, mws, sale, price, book)
- For tonight, Frontera is long 85mw's hour ending 2300. We need to sell this under the Teco Services book. For tomorrow Frontera needs to sell: hour ending 4 - 30 mw's hour ending 5 -30 mw's Enter a pu
- A reminder, I am 55 mws long for hours 23 & 24 today. This has been scheduled into the North Zone. If you sell make sure that you cut the Enpower deal and make the appropriate entries in the Portal. E
- We have a 2500 dt/day supply from Equitable in Tenn Z4. This deal is matched with a term sale to FirstEnergy (deal 145648 for Jan and deal 157848 for Feb and Mar). This is a John Singer deal. I have n

**Topic 8: Confidentiality agreements** (executed, received, llc, dated, copy, agreement)
- We have received the executed Confidentiality Agreement dated 11/15/00 between the referenced Counterparty and Enron North America Corp., Enron Net Works LLC and EnronOnline, LLC. A copy will be sent 
- We have received the executed Confidentiality Agreement with the referenced Counterparty and Enron Net Works LLC dated 1/12/01. Copies will be sent to Dave Samuels and Nora Dobin.
- We have received the executed Non-Disclosure Agreement between Excambria, Inc. and Enron Net Works LLC and EnronOnline, LLC dated 12/14/00. A copy will be sent to Dave Samuels.

**Topic 9: Out of office** (office, friday, monday, phone, cell, wednesday)
- I will be out of the office this Friday, next Monday and Tuesday. I will be taking some vacation days. I will be checking in and I will be available by cell phone.
- I will be out of the office for 06/29/01. I can be reached on my cell phone at 503-887-3449 if you need anything.
- I will be out of the office next week on vacation. Monday July 30 out Tuesday in Wednesday out Thursday out Friday out I will be packing and beginning to move into our new house if you have any questi

**Topic 10: Gas trading desks and EnronOnline** (gas, trading, file, daily, eol, list)
- Just to be more clear. The file will combine the Gas Daily index and the Physical Index curves. The Gas Daily BOM can remain in a separate file.
- I tried to breakout the curves for Keith and Frank in the file you are working on but we should run that by them for approval. Mike will be setting all gas daily and physical curves. I think we can co
- OK, the fun continues. We need to assign EOL products to traders. Torrey sent a file (Netco\controls\Trader-Book template (US Gas)_EOL new books) with all products and the old book assignments. We nee

## Topic mix of each person group (% of the group's emails)

| group | emails | 1. California regulation (FERC, PUC) | 2. Pipeline deliveries | 3. Master agreements (ISDA) | 4. Meetings | 5. Drafts for review | 6. Credit and legal paperwork | 7. Power deals and positions | 8. Confidentiality agreements | 9. Out of office | 10. Gas trading desks and EnronOnline | no clear topic |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Named by Congress | 262 | 21.4 | 0.0 | 1.5 | 17.9 | 5.7 | 4.6 | 5.0 | 6.5 | 9.9 | 15.6 | 11.8 |
| Central core | 3496 | 14.7 | 2.9 | 8.4 | 6.9 | 9.7 | 14.7 | 8.9 | 4.5 | 8.1 | 11.6 | 9.6 |
| Brokers | 281 | 24.2 | 0.4 | 2.8 | 6.0 | 8.9 | 3.6 | 20.3 | 2.8 | 8.2 | 10.3 | 12.5 |
| Others | 2119 | 13.7 | 2.5 | 2.2 | 14.1 | 10.1 | 3.7 | 8.1 | 2.2 | 12.5 | 18.6 | 12.2 |
