#  **EPS Account Intelligence Agent** 

# *Product Requirements Document — November, 2025*

### **Executive Summary**

Guild’s decade-long partnerships with leading employers have created a rich history of account intelligence that lives distributed across systems and, most importantly, in the minds of our Account Managers. That institutional knowledge is difficult to access and scale, leading to three key challenges:

1. **Ramp-up inefficiency —** New or transitioning Account Managers spend significant time piecing together insights across fragmented systems.

2. **Limited visibility —** Regional Leads lack a systematic, scalable way to access real-time account insights, relying instead on 1:1 updates from direct reports.

3. **Gap in EP strategic priority tracking —** No consistent way to monitor how Employer Partner priorities evolve across talent strategies and budget decisions.

**Our Solution:** An AI-powered account intelligence agent on top of Glean that enables the EPS team to query account insights in natural language across Slack, Google Drive, Salesforce, Gong, and Gmail. Instead of returning simple search results, the agent synthesizes and contextualizes information to deliver actionable insights aligned with key account lifecycle activities such as renewals or expansions. 

**What is custom:** While Glean provides enterprise-grade search across our systems, Guild is building a custom orchestration layer that:

* Understands account-specific query intent and context (e.g. “what were the key agenda items covered during the last QBR with JPMC?)

* Prioritizes the most relevant data sources for accuracy (e.g. retrieves renewal date from SFDC only)

* Synthesizes findings into coherent, citation-backed summaries

* Applies Guild-specific fine-tuning to align with commercial language and workflows

**Agent Roadmap: MVP vs. V2 and beyond capabilities** 

| Capability  | MVP | V2 and beyond  |
| :---- | :---- | :---- |
| *Agent querying*  | Natural language queries about individual accounts | Multi-account queries analyzing patterns across accounts |
| *Knowledge Retrieval*  | Multi-source retrieval across Slack, Drive, Salesforce, Gong, Gmail with intelligent prioritization | Batch orchestration across portfolios with weighting by account tier, size, or region |
| *Actions*  | None  | Ability to take actions such as update pre-approved Salesforce fields from the agent interface |

### **User Flows by Persona** 

| Phase  | Persona | User Flows  |
| :---- | :---- | :---- |
| *MVP*  | Account Manager  | Onboard to new accounts by querying **historical context** across systems **Prepare for meetings** by surfacing key details from recent interactions with partners **Draft emails and materials** in the appropriate voice/tone based on past interactions |
| *V2 and beyond*  | Regional Lead  | **Monitor portfolio health** with snapshots highlighting at-risk accounts and expansion opportunities Identify **cross-account patterns to inform cross-sell strategy** (e.g., which product combinations succeed or stall) Coach Account Managers using concrete **data on account engagement and sentiment** |
|  | EPS Leader (SVP+) | **Track install base trends and sentiment patterns** to inform strategic planning **Spot expansion opportunities** by analyzing signals across high-performing accounts **Surface recurring product feedback themes** to prioritize roadmap investments |
|  | EPS Strategy and Ops  | **Analyze customer behavior patterns** to inform GTM strategy **Assess resource and enablement needs** across territories  **Generate insights on retention, expansion, and cross-selling** opportunities  |

### **Technical Approach**

Architecture Decision: Glean MCP vs. Glean API

| Approach | Pros | Cons | Best For |
| ----- | ----- | ----- | ----- |
| *Glean MCP* | \- Built-in permission enforcement \- Faster to implement \- Leverages Glean's ranking/personalization | \- Per-query limitation (no batch) \- Less control over search logic | MVP single-account queries |
| *Glean API* | \- Custom search orchestration \- Batch processing capability \- More control over ranking | \- More dev lift | Future portfolio queries |

### **Key Requirements and Data Sources (MVP)** 

| Requirement | What Good Looks Like | Priority |
| ----- | ----- | ----- |
| *Single Query, Multi-Source Search* | Agent parses account name variations (JP Morgan vs. JPMC), extracts intent and time constraints, refined for commercial org language | Must-have |
| *Parallel Multi-Source Orchestration* | Searches Drive, Slack, SFDC, Gmail, Gong concurrently with intelligent prioritization; displays real-time progress | Must-have |
| *Permission-Aware Results* | Only surfaces documents user has access to; clear error messaging for blocked content | Must-have |
| *Unified Context Synthesis* | Synthesizes findings across all sources into coherent response; supports conversational follow-ups | Must-have |
| *Source Transparency & Deep Links* | Source citations with system labels, clickable links, metadata (last modified, author) | Must-have |
| *Search History & Context* | Maintains conversation history within session | Nice-to-have |

**Primary Data Sources (MVP)**

| Source | Data Type | Integration Method | Priority | Notes |
| ----- | ----- | ----- | ----- | ----- |
| *Google Drive* | Unstructured | Glean MCP/API | Must-have | QBRs, account plans, stakeholder maps, transition docs |
| *Salesforce* | Semi-structured | Glean connector  | Must-have | Account records, opportunity data, EP contact info |
| *Gmail* | Unstructured | Glean connector with Salesforce  | Must-have | Account-related emails |
| *Gong* | Unstructured | Glean MCP/API | Must-have | Call transcripts, sentiment analysis, activity and engagement metrics  |
| *Slack* | Unstructured | Glean MCP/API | Nice-to-have | Account-specific channels |
| *Looker* | Structured  | Snowflake  | Must-have  | Automated App Cap ([Looker](https://guildedu.looker.com/dashboards/guild_education_basic::internal_auto_app_caps?Employer+Name=&Art+Cohort+Month=&Academic+Partner+Name=&Program+Type=&Is+In+Employer+Catalog=Yes)) Operational Funnel Tracking ([Looker](https://guildedu.looker.com/dashboards/guild_education_analytics::forecasting_operational_funnel_tracking?Employer+Status=Active&Employer+Partner=Target&Guild+Fiscal+Year=&EP+Fiscal+Year=Current&Academic+Partner=&Program+Type=)) Program performance (By EP); will need to prioritize the ones selected for the MVP  Escalations Analysis ([Looker](https://guildedu.looker.com/dashboards/4129?Employer+Name=&Date+Range=12+month)) Data issues and employer analytics request tracking ([Looker](https://guildedu.looker.com/dashboards/guild_education_basic::reporting_analytics_data_quality_metrics?Date+Granularity=month&Date=6+month+ago+for+6+month&Analytics+Report=&Employer+Partner+Name=)) Pipeline, NPS, operational health scorecard, etc \- Partnerships Exec Dashboard ([Looker](https://guildedu.looker.com/dashboards/guild_education_basic::partnerships_executive_employers?Industry=&Service+Tier=&Region=&Employer+Name=&EPS+Account+Owner=&EPS+Senior+Leader=)) Operational Health ([Looker](https://guildedu.looker.com/dashboards/guild_education_basic::op_health_summary?Employer+Partner+Status=Active&Employer+Partner+Sub-Status+%28Active%29=Ongoing&Employer+Name=&Employer+Service+Tier=&Employer+Industry=&Employer+Launch+Date=&Employer+Renewal+Date=)) Core Metrics Dashboard ([Looker](https://guildedu.looker.com/dashboards/external_employers_core_metrics::client_external_start_here))   Catalog Resource Hub ([Looker](https://guildedu.looker.com/dashboards/4480?Program+Group=&Parent+Program+Discipline=&Program+Category=&Learning+Marketplace+Outcomes+Performance=&Child+Program+Discipline=&Program+Name=&Can+I+Sell=&Guild+Applied+Learning=&Learning+Marketplace+Partner+Type=Employer-Sponsored+Partner%2CGuild+Certified+Partner&Learning+Partner=&Program+Type=&Program+Offering+ID=&Catalog+Status+%28Guild-Wide%29+-+LM+programs+ONLY=Available%2CIn+Progress&SKILL+Category+Name=&SKILL+Subcategory+Name=&Program+Skill+Validation+Complete=&SKILL+Name=&Employer+Name=&Employer+Partner+Status=Active%2CPre-Launch%2CMaintenance%2CGuild&Tuition+Funding+Type=&Coverage+Package+Name=&Employer+Specific+Visibility+Flag+%28Yes+%2F+No%29=Yes&Coverage+Package+Is+Active+%28Yes+%2F+No%29=Yes&Marketplace+Added+Date=)) |

### **Use Cases with Example Questions & Expected Answers**

| Topic Area | Example Question | Example Answer (Based on Document Patterns) | Prioritized Sources   |
| ----- | ----- | ----- | ----- |
| **Relationship Dynamics & Stakeholder Management** | *Who are the key decision-makers at \[EP\] and what are their priorities?* | **Key Decision-Makers at AdventHealth:**  • **Evelyn Rosenthal** (AVP): Focuses on workforce readiness, clinical pipeline credibility, and ensuring learners are placement-ready. Recently escalated DPP implementation urgency. • **Hannah Simaku** (Learning Specialist): Day-to-day program operations, catalog management, field of study cleanup. Communication preference: detailed, organized documentation. • **Michael Page** (Exec Director, HRIS): Owns data integrity and turnover analysis. Values statistically rigorous methodologies and clear ROI narratives. **Recent Priorities:** • Implementing Gallup assessment gating to ensure program readiness • Simplifying catalog through SIP code consolidation • Launching lifetime caps by November 2025 | EP contacts and roles are in Salesforce; priorities might need to be extracted from emails/call transcripts  |
| **Relationship Dynamics & Stakeholder Management** | *Has \[EP\] expressed any concerns or dissatisfaction recently? What were the themes?* | **Recent Concerns at Wellstar:**  **Themes:** 1\. **Data accuracy delays** \- Ann Miller flagged inconsistent reporting between DPP and Marketplace partners 2\. **Gating mechanism complexity** \- Team concerned about technical feasibility of program-level gates 3\. **Textbook cost barriers** \- $750 out-of-pocket expenses for KSU MOA program causing learner dropoff **Status:** All being actively addressed through working sessions. Relationship remains strong with collaborative problem-solving approach. | Operational health inputs in Salesforce or the EPS summary; not consistent |
| **Program Performance & Utilization** | *Which programs are seeing the highest and lowest enrollment at \[EP\]?* | **AdventHealth Program Performance (Q3 2025):**  **Highest Enrollment:** • BSN programs (RN to BSN) \- consistent demand • Medical Office Assistant (MedCerts) \- 70% profile completion, 35% enrollment rate **Lowest/Zero Enrollment:** • 24 programs flagged for removal in recent QLR • KSU Digital Marketing Certificate \- no enrollments in 18 months • Medical Front Office Specialist (both KSU and MedCerts) \- currently paused **Recommendation:** Sunset zero-enrollment programs; prioritize BSN and Allied Health pathways aligned to clinical workforce needs. | Looker |
| **Strategic Priorities & Workforce Needs** | *What are \[EP\]'s top workforce development goals right now?* | **Wellstar's Top Priorities (Fall 2025):**  1\. **Hospital opening in Aiken** \- Urgent need to staff clinical roles; prioritizing 3 DPP schools (Georgia State, USC Aiken, Aiken Tech) 2\. **Career pathway readiness** \- Implementing Gallup assessment gating for fully-funded programs to ensure placement success 3\. **Applied Learning placement** \- Focus on Surgical Tech, Sterile Processing, Medical Office roles 4\. **Equity in access** \- Maintaining foundational learning access while gating clinical programs **Timeline:** November 1, 2025 target for Gallup launch | Account plan will live in Salesforce sometime in December; mostly open text. Otherwise, these are in Google docs |
| **Operational Health & Issues** | *Are there any outstanding escalations or open issues with \[EP\]?* | **Current AdventHealth Escalations:**  **Active:** • Yeney Figueredo \- $7,475 balance from AHU TA→DPP transition; awaiting deadline exception decision • Robyne Williams \- SLR makeup payments for May-Aug 2025 due to servicer change; pending EP approval **Monitoring:** • Core Metrics Dashboard migration \- test file expected this week • Lifetime caps implementation \- awaiting comms team approval, targeting Sept/Oct launch **Resolved:** • Field of Study list reduced by 200+ items through SIP code consolidation | Looker |
| **Meeting Prep & Communication Strategy** | *What were the key takeaways from our last EBR or working session with \[EP\]?* | **AdventHealth Biweekly (Sept 4, 2025\) \- Key Takeaways:**  **Decisions Made:** • Direct mail pilot approved for regions below 8% engagement threshold • Lifetime caps moving forward pending final comms approval • Dashboard update: replace "Job Category" view with race demographics **Action Items:** • **Guild:** Deliver test file for dashboard by EOW; draft mailer concepts; prepare lifetime cap documentation • **AdventHealth:** Secure comms approval; update attestation language; share Career Care page link by Sept 26 **Tone:** Collaborative, forward momentum on all fronts | Google Drive \- QBR deck (not consistent), meeting notes, call transcripts  |
| **Data Requests & Reporting** | *What data has \[EP\] requested recently, and what did we provide?* | **Recent AdventHealth Data Requests:**  **Sept 2025:** • Demographic data view by race for Core Metrics Dashboard \- approved to replace job category view • NPS benchmarks for Michael Page meeting \- compiled external benchmarks (SurveyMonkey) \+ internal HRSS comparisons **Aug 2025:** • Turnover analysis alignment \- provided methodology documentation to match HRIS approach (12-month windows, clinical vs non-clinical splits) • Enrollment by region \- used for direct mail pilot targeting **Format Preference:** Self-service dashboards \> one-time pulls; Ann prefers filtering by fiscal year with rolling date ranges | Looker  |
| **Contract & Financial Context** | *What is \[EP\]'s annual funding cap and how much have they spent YTD?* | **AdventHealth Funding Structure:**  **Annual Cap:** $5,250 per team member per benefit year **Lifetime Cap:** $21,000 (effective cap $23,000 due to final disbursement spillover) \- launching Sept/Oct 2025 **YTD Spend (through Q3 2025):** • Participation rate: 9.8% (above budgeted 8%) • Estimated 1,050 learners projected to exceed lifetime cap in Year 1 • Projected savings from lifetime caps: $5-6M annually **AHU Fully-Funded Agreement:** Once learner exceeds $5,250 in a given year, AHU covers remaining tuition for that year | Budget tab in SFDC \+ Looker / FFA / EA reporting |
| **Future Planning & Roadmap** | *What initiatives or pilots are we planning with \[EP\] in the next 6 months?* | **Wellstar Roadmap (Q4 2025 \- Q1 2026):**  **In Flight:** • Gallup assessment gating mechanism (launch Nov 1, 2025\) • Career Care website redesign (launch Oct 1, 2025\) • 3 new DPP schools for Aiken hospital opening (Georgia State priority, others Nov start) **Planned:** • Certification exam prepayment structure \- awaiting Evelyn's final decision on which exams • Manager approval workflow exploration \- long-term catalog simplification strategy • Workday migration preparation \- coordinate with phenom implementation **Under Discussion:** • Coding program expansion \- 7 programs proposed, pending Evelyn review | Expansion/attainment notes in SFDC or EPS summary, account plans, and AM notes in Google drive  |
| **Risk & Mitigation** | *Are there any risks to the \[EP\] partnership?* | **AdventHealth Risk Assessment (Sept 2025):**  **Low Risk Overall** \- Strong collaborative relationship **Areas to Monitor:** • Michael Page's ROI methodology shows $0.21 ROI vs Guild's higher estimates \- need to align on retention impact calculation approach without appearing defensive • Mary Beth Thornton's "just present the facts" stance suggests some resistance to value storytelling \- may need to build case for narrative framing • Lifetime caps implementation could create team member friction if not communicated well **Mitigation:** Continue collaborative problem-solving approach; position Guild as thought partner on methodology; support comms rollout actively | Salesforce risk indicator at the opportunity level (but not at the account level); discussed with AMs during EPSLT |

### **UAT Overview**

This UAT validates the Account Intelligence Agent's ability to retrieve and synthesize account information across Salesforce, Google Drive, Gong, Gmail, and Slack. Testing progresses from basic data retrieval to complex synthesis, ensuring the agent delivers accurate, actionable insights for Account Managers.

#### Participant Selection Criteria

Select **3-5 Account Managers** representing diversity across:

| Dimension | Target Mix |
| ----- | ----- |
| **Regional Coverage** | Minimum 2 regions (e.g., West, Central, East) |
| **Industry Diversity** | 3+ industries (retail, healthcare, hospitality, financial services, manufacturing) |
| **Tenure** | Mix of tenured AMs (2+ years) and newer AMs (\<1 year at Guild) |
| **AI Fluency** | Range from minimal prompting experience to regular AI tool users |

#### Pre-UAT Setup Requirements

Account Manager Preparation (Due 5 business days before UAT)

**Salesforce Data Hygiene:**

* Verify key account details in Salesforce (e.g. renewal date, EP contacts, etc)  
* Update recent account activities, meeting notes, and escalations from past 90 days  
* Review operational health indicators and risk flags

**Google Drive Docs:** 

* Last 2 QBR decks  
* Account Plan  
* Account Notes   
* EAP  
* Any Account Transition plan  
* Running Working Session Deck  
* Stakeholder Relationship Mapping or other knowledge docs  
* [EPS Ongoing Account Management](https://docs.google.com/document/d/1GTg1aQuWNybnDAJPD3HBXzFwGj81Pm-iRwf2WQZnWj8/edit?usp=drive_web&ouid=104609829598562206348)  
* Executive communication docs ([example](https://docs.google.com/document/d/1fVKlBKKHDvc5EJ50VurQU1E2uSszckGL43Jw_vgZowE/edit?tab=t.0))  
* Applied Learning docs (if applicable)

#### Testing Levels & Success Criteria

| Testing Level | Objective | Sample Test Queries | Expected Agent Behavior | Success Criteria | Why this step matters |
| ----- | ----- | ----- | ----- | ----- | ----- |
| **Level 0: Role-based permissions and system access**  | Confirm permissions/access enforcement, integration with data sources, and output quality  | *\- What is the renewal date for Wellstar?   \- Test common EP name variations (e.g. JPMC) \- Query accounts with missing data fields*  | \- Retrieves basic SFDC data regardless of which EP name variation is used \- Blocks access to accounts outside user's assigned territory \- Returns clear error messages when data fields are null or missing \- Successfully connects to all integrated systems (SFDC, Looker, Drive, Gong, Gmail) | **Permission Enforcement:** 100% success blocking unauthorized access  **Name Variation Handling:** Correctly identifies accounts regardless of abbreviation or formatting  **System Connectivity:** Successfully retrieves data from all 5 sources without errors  **Error Messaging:** Clear, actionable error messages when data is unavailable | Establishes baseline system functionality before testing query accuracy. |
| **Level 1: Basic Account Data Retrieval** | Validate agent accurately surfaces foundational SFDC data with proper source attribution | *\- When is \[EP name\]'s renewal date? \- Who are the main contacts at \[EP name\] and what are their roles? \- What industry does my EP belong to?*  | \- Retrieves account details exclusively from Salesforce \- Returns precise answers with field-level citations \- Handles EP name variations (e.g., "JP Morgan" vs "JPMC") \- Graceful error messaging if data is missing | **Accuracy**: 95%+ on factual data points  **Response Time:** \<5 seconds per query  **Source Attribution:** Clear SFDC field references in every response  **Error Handling:** Clear messaging when data is missing | Allows us to confirm the agent’s ability to consistently prioritize key sources based on design.   |
| **Level 2: Recent Quantitative interpretation** | Quantitative data interpretation from Looker or SFDC  | *\- What data has \[EP\] requested recently, and what did we provide? \- What is \[EP\]'s annual funding cap and how much have they spent YTD? \- Are there any outstanding escalations or open issues with \[EP\]?* | \- Pulls quantitative data from SFDC or Looker  \- Flags when data is stale or missing  \- Deliver point-in-time comparisons, simple comparative statements (above or below average), and outliers  | **Accuracy:** 85%+ on synthesized insights **Recency Indicators:** Includes timestamps or date ranges **Source Attribution:** Clear SFDC or Looker field references in every response **Error Handling:** Clear messaging when data is missing | Allows us to confirm the agent's ability to understand account-specific contextual information, and retrieve quantitative insights from sources that contain structured operational and financial data.  |
| **Level 3: Strategic Intelligence & Document Synthesis** | Strategic synthesis across qualitative sources (SFDC notes, Google Docs, Gong, Gmail, Slack) | *\- What workforce development goals did \[EP name\] identify in their last QBR? \- What were the key takeaways from our most recent EBR with \[EP name\]? \- How do \[EP name\]'s talent priorities align with their program enrollment trends?* | \- Retrieves content from Google Drive documents, Gong transcripts, Gmail  \- Synthesizes across structured (SFDC, Looker) and unstructured (Docs, Gong) sources \- Provides document-level citations with deep links \- Distinguishes between historical context and current priorities \- Flags conflicting information across sources | **Accuracy:** 85%+ on document-based insights **Cross-Source Synthesis:** Connects SFDC data to Drive documents and Gong transcripts  **Document Traceability:** Clickable links with metadata (last modified, author)  | Validates the agent's ability to understand intent, synthesize large amounts of unstructured data, and extract strategic context.  |

