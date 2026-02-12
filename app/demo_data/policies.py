"""
Synthetic policy document generator.
Creates fake internal policy documents for RAG demonstration.
"""

from uuid import uuid4

from app.db.models import PolicyDocument


# Mock policy documents (entirely fictional)
POLICY_DOCUMENTS = [
    {
        "title": "Transaction Monitoring and Fraud Detection Policy",
        "category": "fraud_detection",
        "content": """
        This policy outlines the procedures for monitoring customer transactions and detecting potentially fraudulent activity.
        
        SCOPE: All customer accounts across checking, savings, and business account types.
        
        MONITORING CRITERIA:
        - Transactions exceeding $5,000 in a single transaction
        - Multiple transactions totaling over $10,000 within a 24-hour period
        - Transactions occurring between 2 AM and 5 AM local time
        - Transactions from foreign merchants without prior travel notification
        - Transactions that deviate significantly from established spending patterns
        
        RESPONSE PROTOCOL:
        When suspicious activity is detected, the system should:
        1. Flag the transaction for review
        2. Generate an anomaly report with supporting evidence
        3. Retrieve relevant policy documents for context
        4. Draft a preliminary explanation of the anomaly
        5. If confidence is high (>70%), proceed with automated notification
        6. If confidence is low (<70%), escalate to human review team
        
        All actions must be logged in the audit system with timestamps and decision rationale.
        """,
    },
    {
        "title": "Transaction Amount Limits by Account Type",
        "category": "transaction_limits",
        "content": """
        This document defines maximum transaction limits for different account types.
        
        CHECKING ACCOUNTS:
        - Single transaction limit: $10,000
        - Daily transaction limit: $20,000
        - Monthly transaction limit: $100,000
        
        SAVINGS ACCOUNTS:
        - Single transaction limit: $5,000
        - Daily transaction limit: $10,000
        - Monthly transaction limit: $50,000
        - Note: Savings accounts are limited to 6 withdrawal transactions per month per federal regulation
        
        BUSINESS ACCOUNTS:
        - Single transaction limit: $50,000
        - Daily transaction limit: $100,000
        - Monthly transaction limit: $500,000
        - Higher limits available upon approval
        
        EXCEPTIONS:
        Customers may request temporary limit increases for specific purposes such as:
        - Real estate purchases
        - Business equipment procurement
        - International travel
        
        Requests must be submitted 48 hours in advance and require manager approval.
        """,
    },
    {
        "title": "Escalation Procedures for Anomalous Transactions",
        "category": "escalation",
        "content": """
        This policy defines when and how to escalate potentially fraudulent or anomalous transactions.
        
        ESCALATION TRIGGERS:
        - Automated system confidence score below 70%
        - Transaction amount exceeds account limits by more than 20%
        - Multiple anomalies detected for the same customer within 7 days
        - Customer has disputed similar transactions in the past
        - Transaction involves high-risk merchant categories (wire transfers, cryptocurrency, etc.)
        
        ESCALATION LEVELS:
        
        Level 1 (Automated Review):
        - System generates explanation and recommendations
        - Customer receives automated notification
        - Transaction is monitored but not blocked
        
        Level 2 (Analyst Review):
        - Assigned to fraud analyst within 4 hours
        - Analyst reviews full transaction history and supporting documents
        - Analyst may contact customer for verification
        - Decision made within 24 hours
        
        Level 3 (Manager Review):
        - Complex cases requiring policy interpretation
        - Potential account closure decisions
        - Legal or regulatory implications
        - Decision made within 48 hours
        
        All escalations must include:
        - Complete audit trail
        - Policy documents used in assessment
        - System-generated analysis
        - Confidence scores and rationale
        """,
    },
    {
        "title": "Customer Notification Requirements",
        "category": "notifications",
        "content": """
        This policy outlines requirements for notifying customers about account activity.
        
        IMMEDIATE NOTIFICATION REQUIRED:
        - Transactions exceeding $5,000
        - Transactions flagged as potentially fraudulent
        - Account access from unrecognized device or location
        - Password or security setting changes
        
        NOTIFICATION CHANNELS:
        - Email: Primary channel, sent to registered email address
        - SMS: For amounts over $10,000 or high-priority alerts
        - Mobile app push notification: Real-time for critical alerts
        - Phone call: Only for confirmed fraud or account compromise
        
        NOTIFICATION CONTENT:
        All notifications must include:
        - Transaction amount and merchant
        - Date and time of transaction
        - Last 4 digits of account/card used
        - Clear action steps for customer (verify or dispute)
        - Contact information for fraud department
        - Reference number for tracking
        
        TIMING:
        - Automated notifications: Within 5 minutes of detection
        - Escalated cases: Within 4 hours of escalation
        - Final resolution: Within 24 hours of case closure
        
        Do not include:
        - Full account numbers
        - Security questions or PINs
        - Links to external websites (use official app links only)
        """,
    },
    {
        "title": "Anomaly Detection Algorithm Parameters",
        "category": "technical_specifications",
        "content": """
        This document specifies the technical parameters for the anomaly detection system.
        
        STATISTICAL THRESHOLDS:
        - Z-score threshold: 3.0 (transactions 3 standard deviations from mean)
        - Minimum historical data points: 30 transactions
        - Rolling window for pattern analysis: 90 days
        - Pattern refresh frequency: Daily at 2 AM UTC
        
        FEATURE WEIGHTS:
        The system evaluates multiple features with the following weights:
        - Transaction amount deviation: 30%
        - Time-of-day anomaly: 20%
        - Merchant category deviation: 15%
        - Geographic location anomaly: 15%
        - Transaction frequency: 10%
        - Historical dispute rate: 10%
        
        CONFIDENCE SCORING:
        Confidence scores range from 0.0 to 1.0:
        - 0.9-1.0: Very high confidence (automated action)
        - 0.7-0.89: High confidence (automated with enhanced monitoring)
        - 0.5-0.69: Medium confidence (requires analyst review)
        - 0.0-0.49: Low confidence (escalate to senior analyst)
        
        MODEL RETRAINING:
        - Frequency: Monthly
        - Training data: Last 12 months of transactions
        - Validation set: Most recent 30 days
        - Performance metrics: Precision, Recall, F1-score, AUC-ROC
        - Minimum acceptable precision: 85%
        """,
    },
    {
        "title": "Data Retention and Audit Trail Policy",
        "category": "compliance",
        "content": """
        This policy defines data retention requirements for transaction monitoring and audit trails.
        
        RETENTION PERIODS:
        - Transaction records: 7 years from transaction date
        - Audit events: 7 years from event date
        - Customer communications: 5 years from communication date
        - Policy documents: Indefinite (historical versions retained)
        - Workflow execution logs: 3 years from execution date
        
        AUDIT TRAIL REQUIREMENTS:
        Every workflow execution must log:
        - Unique workflow run identifier
        - Input parameters and source system
        - Each node execution with timestamp
        - All tool invocations with input/output data
        - Decision points with confidence scores
        - Escalation triggers and outcomes
        - Final recommendations and actions taken
        - Total execution duration
        
        IMMUTABILITY:
        Audit records must be append-only and immutable. No deletion or modification is permitted.
        Corrections should be made by adding supplemental audit entries.
        
        ACCESS CONTROLS:
        - Read access: Fraud analysts, compliance officers, auditors
        - Write access: System accounts only (automated processes)
        - Admin access: Database administrators for maintenance only
        
        COMPLIANCE:
        This policy ensures compliance with:
        - Financial recordkeeping requirements
        - Data protection regulations
        - Internal audit standards
        - Regulatory examination requirements
        """,
    },
    {
        "title": "Cross-Border Transaction Monitoring",
        "category": "international",
        "content": """
        This policy addresses monitoring of international and cross-border transactions.
        
        ENHANCED MONITORING TRIGGERS:
        - Transactions with foreign merchants
        - Currency conversion transactions
        - Wire transfers to international accounts
        - Transactions in high-risk countries (per OFAC list)
        - Multiple transactions just below reporting thresholds
        
        ADDITIONAL VERIFICATION:
        For international transactions, the system should:
        - Verify customer has active travel notification
        - Check merchant against sanctions lists
        - Assess country risk score
        - Compare against typical customer behavior
        - Evaluate transaction purpose if declared
        
        SPECIAL CONSIDERATIONS:
        - Time zone differences may affect normal business hours detection
        - Currency conversion may result in unusual amounts
        - International merchants may have unfamiliar naming patterns
        - Consider cultural factors (holidays, business practices)
        
        REPORTING REQUIREMENTS:
        - Transactions over $10,000: File CTR (Currency Transaction Report)
        - Suspicious activity: File SAR (Suspicious Activity Report) within 30 days
        - OFAC match: Immediate hold and report within 24 hours
        
        This policy must be reviewed quarterly due to changing regulatory landscape.
        """,
    },
    {
        "title": "Machine Learning Model Governance",
        "category": "ai_governance",
        "content": """
        This policy establishes governance for AI and machine learning models used in transaction monitoring.
        
        MODEL LIFECYCLE:
        1. Development: Document model architecture, features, and training data
        2. Validation: Test against holdout dataset, measure performance metrics
        3. Deployment: Gradual rollout with A/B testing
        4. Monitoring: Continuous performance tracking
        5. Retraining: Regular updates with new data
        6. Retirement: Graceful deprecation when replaced
        
        EXPLAINABILITY REQUIREMENTS:
        All model decisions must be explainable to:
        - Customers (in plain language)
        - Analysts (with technical details)
        - Regulators (with full documentation)
        
        Methods for explainability:
        - Feature importance scores
        - SHAP values for individual predictions
        - Decision path visualization
        - Similar case examples
        
        BIAS MONITORING:
        Models must be monitored for bias across:
        - Account types
        - Customer demographics
        - Transaction categories
        - Geographic regions
        
        Quarterly bias audits required with documented remediation plans.
        
        HUMAN OVERSIGHT:
        - High-impact decisions require human review
        - Model recommendations are advisory, not binding
        - Override mechanisms must be available
        - All overrides must be documented with rationale
        
        MODEL DOCUMENTATION:
        Required documentation includes:
        - Model card with purpose, limitations, and performance
        - Training data specifications
        - Feature engineering decisions
        - Hyperparameter tuning results
        - Validation and testing results
        - Deployment configuration
        - Monitoring dashboard access
        """,
    },
    {
        "title": "Incident Response for False Positives",
        "category": "customer_service",
        "content": """
        This policy defines procedures for handling false positive fraud alerts.
        
        FALSE POSITIVE DEFINITION:
        A false positive occurs when a legitimate transaction is incorrectly flagged as potentially fraudulent.
        
        IMMEDIATE RESPONSE:
        When a customer reports a false positive:
        1. Apologize for the inconvenience
        2. Verify customer identity
        3. Review the transaction and detection rationale
        4. Remove any holds or blocks immediately
        5. Provide incident reference number
        
        ROOT CAUSE ANALYSIS:
        For each false positive, document:
        - Which detection rules triggered
        - Model confidence score
        - Why the transaction appeared anomalous
        - Customer explanation for the transaction
        - Whether this was preventable
        
        SYSTEM IMPROVEMENTS:
        Use false positive data to:
        - Retrain anomaly detection models
        - Adjust detection thresholds
        - Add customer-specific exceptions
        - Improve feature engineering
        - Update policy rules
        
        CUSTOMER COMPENSATION:
        Based on impact severity:
        - Minor inconvenience (notification only): Apology, explanation
        - Transaction declined: Fee waiver, apology
        - Repeated false positives: Account review, enhanced allowlisting
        - Significant disruption: Escalate to customer relations team
        
        PREVENTION:
        To minimize false positives:
        - Encourage travel notifications
        - Allow customers to set spending patterns
        - Learn from historical customer behavior
        - Implement merchant allowlists
        - Provide real-time customer feedback mechanisms
        
        METRICS:
        Track and report monthly:
        - False positive rate (target: <5%)
        - Customer complaint rate
        - Time to resolution
        - Repeat false positive incidents
        """,
    },
    {
        "title": "Integration with External Fraud Databases",
        "category": "technical_integration",
        "content": """
        This policy governs integration with external fraud detection and merchant verification services.
        
        APPROVED EXTERNAL SERVICES:
        - Merchant verification databases
        - Stolen card number databases
        - IP reputation services
        - Device fingerprinting services
        - Geolocation verification services
        
        INTEGRATION REQUIREMENTS:
        All external service integrations must:
        - Use secure, encrypted connections (TLS 1.3+)
        - Implement request/response logging
        - Have documented SLAs and fallback procedures
        - Include rate limiting and timeout handling
        - Comply with data sharing agreements
        
        DATA SHARING LIMITS:
        May share with external services:
        - Transaction amount and merchant
        - Transaction timestamp and location
        - Device and IP information
        - Risk scores and flags
        
        Must NOT share:
        - Customer personally identifiable information
        - Full account numbers
        - Customer contact information
        - Internal policy documents
        
        FALLBACK PROCEDURES:
        If external service is unavailable:
        - Continue processing with internal rules only
        - Log the service outage
        - Add conservative buffer to confidence scores
        - Increase human review rate temporarily
        - Alert operations team if outage exceeds 15 minutes
        
        PERFORMANCE MONITORING:
        Track for each external service:
        - Response time (target: <200ms at p95)
        - Success rate (target: >99.9%)
        - False positive contribution
        - Cost per transaction
        - Data quality metrics
        
        SERVICE EVALUATION:
        Quarterly review of each external service:
        - Value provided vs. cost
        - Performance against SLAs
        - Data quality and accuracy
        - Customer impact
        - Regulatory compliance
        """,
    },
]


def generate_policy_documents() -> list[PolicyDocument]:
    """
    Generate synthetic policy documents for RAG demonstration.
    
    Returns:
        List of PolicyDocument model instances (without embeddings yet)
    """
    policies = []
    
    for policy_data in POLICY_DOCUMENTS:
        policy = PolicyDocument(
            id=uuid4(),
            title=policy_data["title"],
            content=policy_data["content"].strip(),
            category=policy_data["category"],
            embedding=None,  # Will be populated by RAG indexer
        )
        policies.append(policy)
    
    return policies
