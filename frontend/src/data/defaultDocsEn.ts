export const defaultDocsEn: Record<string, any> = {
  "privacy-policy": `# Privacy Policy
*Last updated: June 16, 2026*

The Traditional Medicine Knowledge System **YHCT Diamond** is committed to protecting your privacy and personal information. This policy explains how we collect, use, and share information when you use our application and its related services.

### 1. Information We Collect
We only collect necessary information to provide and improve the traditional medicine Q&A service:
* **Personal Identification Information:** Email address, display name, and avatar provided through Google Account authentication (Google Sign-In).
* **Chat History & Queries:** Content of your Q&A conversations and keywords you enter to retrieve knowledge. This helps improve chatbot accuracy and display your chat history.
* **Transaction Data:** Deposit logs, token balance, and payment status (we do not store credit card or bank account details directly).

### 2. How We Use Information
* Provide secure user authentication and access via Google.
* Display, group, and store your personal chat history.
* Operate and optimize the Knowledge Graph retrieval system (GraphRAG) to accurately answer your queries.
* Manage token balance and reconcile deposit transactions.
* Conduct scientific research to improve entity extraction algorithms and eliminate LLM hallucinations.

### 3. Cookies and Local Storage
We use **LocalStorage** to store your session access token (JWT). We do not use any third-party advertising tracking cookies. LocalStorage helps maintain your login session so you do not need to re-login in each session.

### 4. Sharing Information with Third Parties
> **Important Commitment:** We **DO NOT** sell, share, or rent your personal data or Q&A history to any third party for marketing or commercial purposes.
>
> Your data is processed internally through our secure APIs connecting to trusted cloud services (like Google Vertex AI for response generation) under strict confidentiality agreements. Data sent to LLM models is anonymous and contains no personal identifiers.

### 5. User Rights & Data Deletion
You have full rights over your personal data, including:
* View and read your entire chat history in the app.
* Actively delete specific chat sessions directly in the Sidebar Chat menu.
* **Request Permanent Account Deletion:** You can self-perform account deletion along with all associated data (chat history, transactions, logs) immediately at the [Data Deletion](/data-deletion) page without admin intervention.
* Submit data deletion or support requests via our support email.

***

### Security of Your Information
We apply strict encryption and access management security measures to protect data in the SQLite database and Neo4j Graph. All data transmission between your browser and our servers is encrypted using secure HTTPS/TLS protocols.`,

  "terms-of-service": `# Terms of Service
*Last updated: June 16, 2026*

Welcome to **YHCT Diamond**. By accessing or using our application, you agree to comply with and be bound by these Terms of Service. Please read them carefully before using the service.

> ### Medical Literature & AI Disclaimer
> * **Not a Substitute for Medical Advice:** AI chatbot answers of YHCT Diamond are synthesized from traditional medicine literature (e.g. "Medicinal Plants and Herbs of Vietnam") and GraphRAG technology. This information is **FOR REFERENCE ONLY**.
> * **Do Not Use for Self-Treatment:** Absolutely do not apply any remedies or herbs without direct prescription, diagnosis, and examination from licensed traditional medicine practitioners or doctors.
> * **User Responsibility:** Users assume full responsibility for using or applying information provided by the system. The development team bears no liability for any health issues arising from self-applying chatbot information.

### 1. Conditions of Use & Account Registration
To fully use application features (AI chat, knowledge map), you must log in via authorized Google accounts. You are responsible for keeping your login session secure and are liable for all activities occurring under your account.

### 2. AI Operation Policy (GraphRAG)
Our system applies the **"Imperial Doctor Diamond"** mechanism combining a Knowledge Graph (Neo4j) to minimize hallucinations commonly found in standard LLMs. However:
* Although hallucinations are reduced via graph verification, traditional literature translated from Nôm/Chinese characters or ancient records may contain discrepancies or may not completely align with modern medicine.
* The system always displays graph entity source citations (e.g., book name, chapter, page number) at the end of answers for users to verify.

### 3. Prohibited Conducts
When using YHCT Diamond, you agree not to:
* Use any scraping tools, bots, or scripts to collect knowledge graph data from our system.
* Intentional attacks, hacking, injecting malicious codes (Cypher injection, SQL injection), or disrupting server services.
* Use the chatbot to generate or propagate violent, pornographic, offensive, or illegal content.
* Falsify deposit transactions or attempt to unauthorizedly manipulate token balances.

### 4. Limitation of Liability
The system is provided on an "as-is" and "as-available" basis. The development team makes no warranties, express or implied, regarding the absolute accuracy of LLM answers in clinical situations. We disclaim all liability for any direct or indirect damage to health, finance, or law arising from the misuse of application information.

### 5. Term Changes & Termination of Service
We reserve the right to update or adjust these Terms of Service at any time without prior notice. Your continued use of the application after changes are posted constitutes acceptance of the new terms. We also reserve the right to suspend or permanently ban accounts violating these regulations.`,

  "data-deletion": `# Data Deletion Request
*Policies & Self-Service Account Deletion Tools*

### Process and Commitment for Data Deletion
Under Google and Apple guidelines for user privacy protection, YHCT Diamond allows you to delete your account. When you submit a request:
* **Personal Info:** Name, email, and avatar retrieved from Google OAuth will be permanently deleted from the database.
* **Chat History:** All messages and medical Q&A conversations will be deleted (physically removed from SQLite).
* **Balance & Transactions:** Token wallet, balance change logs, and deposit history will be completely discarded.
* **Processing Time:** Instant deletion if performed via the tool below, or up to 30 days if requested manually via email.`,

  "support": [
    {"question": "What is the YHCT Diamond system?", "answer": "YHCT Diamond is an Artificial Intelligence platform supporting research and lookup of Vietnamese Traditional Medicine. The system combines a digitized Knowledge Graph from classic medical literatures and GraphRAG (Retrieval-Augmented Generation) technology to deliver the most accurate answers."},
    {"question": "How does the system eliminate the 'hallucination' phenomenon?", "answer": "The system uses a Natural Language Understanding (NLU) engine to convert your natural questions into Cypher graph queries. It extracts actual knowledge from the verified Neo4j database (Gold Linked Data) and feeds this real data to the Gemini language model to synthesize responses. The LLM is strictly instructed not to fabricate or speculate beyond the actual literature context."},
    {"question": "Where does the data of YHCT Diamond come from?", "answer": "The core data is automatically extracted using advanced OCR (Google Document AI) from official Vietnamese medical literatures, notably the classic book 'Medicinal Plants and Herbs of Vietnam' by Prof. Do Tat Loi, then structured into entity nodes (Herbs, Active Ingredients, Parts Used, Pharmacology, Formulas) and relationships on Neo4j."},
    {"question": "Can I self-prescribe and take medicine according to the Chatbot's guidance?", "answer": "No! All chatbot answers are for academic research, information search, and literature query purposes only. Absolutely do not self-apply any remedies or herbs without direct prescription and supervision from specialists or licensed traditional medicine doctors."},
    {"question": "What is the Token Wallet for and how do I recharge?", "answer": "Each in-depth RAG chatbot query or knowledge map analysis operation consumes a certain amount of tokens to cover server and API costs. You can recharge tokens via SePay automatic gateway by scanning a dynamic QR code on your Financial management page."}
  ],

  "contact": {
    "description": "The **YHCT Diamond Knowledge Graph** system is developed by an artificial intelligence research group, focusing on applying knowledge graph and natural language processing technologies to preserve and exploit the values of the country's traditional medicine.",
    "email": "support@yhct-diamond.vn",
    "unit": "University of Information Technology - VNU-HCM",
    "office": "Quarter 6, Linh Trung Ward, Thu Duc City, Ho Chi Minh City, Vietnam",
    "github": "https://github.com/huynhcan2004/225731_TIEN_PHONG_TT_VL_2026",
    "copyright": "All medical literature documents used as the knowledge base (Knowledge Graph) belong to the original authors and publishers. The system only indexes entities for non-profit scientific search purposes."
  }
};
