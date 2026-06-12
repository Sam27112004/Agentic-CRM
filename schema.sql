
CREATE TABLE audit_log (
	id SERIAL NOT NULL, 
	entity_type VARCHAR(100), 
	entity_id INTEGER, 
	action VARCHAR(255), 
	performed_by VARCHAR(255), 
	timestamp TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	diff JSONB, 
	PRIMARY KEY (id)
)

;


CREATE TABLE contacts (
	id SERIAL NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	name VARCHAR(255), 
	company VARCHAR(255), 
	status VARCHAR(50) DEFAULT 'Active' NOT NULL, 
	account_value NUMERIC(12, 2), 
	churn_risk_score NUMERIC(3, 2), 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	last_contact_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id)
)

;


CREATE TABLE knowledge_chunks (
	id SERIAL NOT NULL, 
	source_doc VARCHAR(255), 
	chunk_text TEXT, 
	embedding JSONB, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id)
)

;


CREATE TABLE web_intelligence_cache (
	id SERIAL NOT NULL, 
	source_url TEXT, 
	target_entity VARCHAR(255), 
	scraped_data JSONB, 
	scraped_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	expires_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id)
)

;


CREATE TABLE threads (
	id SERIAL NOT NULL, 
	thread_id VARCHAR(255) NOT NULL, 
	subject TEXT, 
	sender_email VARCHAR(255) NOT NULL, 
	first_seen_at TIMESTAMP WITH TIME ZONE, 
	last_updated_at TIMESTAMP WITH TIME ZONE, 
	status VARCHAR(50) DEFAULT 'Open' NOT NULL, 
	assigned_to VARCHAR(255), 
	PRIMARY KEY (id), 
	UNIQUE (thread_id), 
	FOREIGN KEY(sender_email) REFERENCES contacts (email)
)

;


CREATE TABLE emails (
	id SERIAL NOT NULL, 
	thread_id INTEGER NOT NULL, 
	message_id VARCHAR(255) NOT NULL, 
	sender VARCHAR(255), 
	subject TEXT, 
	body TEXT, 
	timestamp TIMESTAMP WITH TIME ZONE, 
	sentiment_score NUMERIC(4, 2), 
	category VARCHAR(100), 
	urgency VARCHAR(50), 
	requires_human BOOLEAN, 
	confidence NUMERIC(4, 2), 
	raw_entities JSONB, 
	status VARCHAR(50) DEFAULT 'Received' NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(thread_id) REFERENCES threads (id), 
	UNIQUE (message_id)
)

;


CREATE TABLE actions (
	id SERIAL NOT NULL, 
	email_id INTEGER NOT NULL, 
	agent_reasoning_log JSONB, 
	action_type VARCHAR(100), 
	proposed_content TEXT, 
	is_approved BOOLEAN DEFAULT false, 
	approved_by VARCHAR(255), 
	executed_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(email_id) REFERENCES emails (id)
)

;


CREATE TABLE drafts (
	id SERIAL NOT NULL, 
	email_id INTEGER NOT NULL, 
	content TEXT NOT NULL, 
	status VARCHAR(50) DEFAULT 'Pending' NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	approved_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(email_id) REFERENCES emails (id)
)

;


CREATE TABLE processing_jobs (
	id SERIAL NOT NULL, 
	email_id INTEGER NOT NULL, 
	status VARCHAR(50) NOT NULL, 
	error_message TEXT, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	completed_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(email_id) REFERENCES emails (id)
)

;

