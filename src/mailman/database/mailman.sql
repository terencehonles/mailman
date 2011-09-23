CREATE TABLE _request (
    id INTEGER NOT NULL,
    "key" TEXT,
    request_type INTEGER,
    data_hash TEXT,
    mailing_list_id INTEGER,
    PRIMARY KEY (id),
    CONSTRAINT _request_mailing_list_id_fk
        FOREIGN KEY (mailing_list_id) REFERENCES mailinglist (id)
    );

CREATE TABLE acceptablealias (
    id INTEGER NOT NULL,
    "alias" TEXT NOT NULL,
    mailing_list_id INTEGER NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT acceptablealias_mailing_list_id_fk
        FOREIGN KEY (mailing_list_id) REFERENCES mailinglist (id)
    );
CREATE INDEX ix_acceptablealias_mailing_list_id
    ON acceptablealias (mailing_list_id);
CREATE INDEX ix_acceptablealias_alias ON acceptablealias ("alias");

CREATE TABLE address (
    id INTEGER NOT NULL,
    email TEXT,
    _original TEXT,
    real_name TEXT,
    verified_on TIMESTAMP,
    registered_on TIMESTAMP,
    user_id INTEGER,
    preferences_id INTEGER,
    PRIMARY KEY (id),
    CONSTRAINT address_user_id_fk
        FOREIGN KEY (user_id) REFERENCES user (id),
    CONSTRAINT address_preferences_id_fk
        FOREIGN KEY (preferences_id) REFERENCES preferences (id)
    );

CREATE TABLE autoresponserecord (
    id INTEGER NOT NULL,
    address_id INTEGER,
    mailing_list_id INTEGER,
    response_type INTEGER,
    date_sent TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT autoresponserecord_address_id_fk
        FOREIGN KEY (address_id) REFERENCES address (id),
    CONSTRAINT autoresponserecord_mailing_list_id
        FOREIGN KEY (mailing_list_id) REFERENCES mailinglist (id)
    );
CREATE INDEX ix_autoresponserecord_address_id
    ON autoresponserecord (address_id);
CREATE INDEX ix_autoresponserecord_mailing_list_id
    ON autoresponserecord (mailing_list_id);

CREATE TABLE bounceevent (
    id INTEGER NOT NULL,
    list_name TEXT,
    email TEXT,
    'timestamp' TIMESTAMP,
    message_id TEXT,
    context INTEGER,
    processed BOOLEAN,
    PRIMARY KEY (id)
    );

CREATE TABLE contentfilter (
    id INTEGER NOT NULL,
    mailing_list_id INTEGER,
    filter_pattern TEXT,
    filter_type INTEGER,
    PRIMARY KEY (id),
    CONSTRAINT contentfilter_mailing_list_id
        FOREIGN KEY (mailing_list_id) REFERENCES mailinglist (id)
    );
CREATE INDEX ix_contentfilter_mailing_list_id
    ON contentfilter (mailing_list_id);

CREATE TABLE domain (
    id INTEGER NOT NULL,
    mail_host TEXT,
    base_url TEXT,
    description TEXT,
    contact_address TEXT,
    PRIMARY KEY (id)
    );

CREATE TABLE language (
    id INTEGER NOT NULL,
    code TEXT,
    PRIMARY KEY (id)
    );

CREATE TABLE mailinglist (
    id INTEGER NOT NULL,
    -- List identity
    list_name TEXT,
    mail_host TEXT,
    list_id TEXT,
    include_list_post_header BOOLEAN,
    include_rfc2369_headers BOOLEAN,
    -- Attributes not directly modifiable via the web u/i
    created_at TIMESTAMP,
    admin_member_chunksize INTEGER,
    next_request_id INTEGER,
    next_digest_number INTEGER,
    digest_last_sent_at TIMESTAMP,
    volume INTEGER,
    last_post_at TIMESTAMP,
    accept_these_nonmembers BLOB,
    acceptable_aliases_id INTEGER,
    admin_immed_notify BOOLEAN,
    admin_notify_mchanges BOOLEAN,
    administrivia BOOLEAN,
    advertised BOOLEAN,
    anonymous_list BOOLEAN,
    archive BOOLEAN,
    archive_private BOOLEAN,
    archive_volume_frequency INTEGER,
    -- Automatic responses.
    autorespond_owner INTEGER,
    autoresponse_owner_text TEXT,
    autorespond_postings INTEGER,
    autoresponse_postings_text TEXT,
    autorespond_requests INTEGER,
    autoresponse_request_text TEXT,
    autoresponse_grace_period TEXT,
    -- Bounces.
    forward_unrecognized_bounces_to INTEGER,
    process_bounces BOOLEAN,
    bounce_info_stale_after TEXT,
    bounce_matching_headers TEXT,
    bounce_notify_owner_on_disable BOOLEAN,
    bounce_notify_owner_on_removal BOOLEAN,
    bounce_score_threshold INTEGER,
    bounce_you_are_disabled_warnings INTEGER,
    bounce_you_are_disabled_warnings_interval TEXT,
    -- Content filtering.
    filter_content BOOLEAN,
    collapse_alternatives BOOLEAN,
    convert_html_to_plaintext BOOLEAN,
    default_member_action INTEGER,
    default_nonmember_action INTEGER,
    description TEXT,
    digest_footer TEXT,
    digest_header TEXT,
    digest_is_default BOOLEAN,
    digest_send_periodic BOOLEAN,
    digest_size_threshold INTEGER,
    digest_volume_frequency INTEGER,
    digestable BOOLEAN,
    discard_these_nonmembers BLOB,
    emergency BOOLEAN,
    encode_ascii_prefixes BOOLEAN,
    first_strip_reply_to BOOLEAN,
    forward_auto_discards BOOLEAN,
    gateway_to_mail BOOLEAN,
    gateway_to_news BOOLEAN,
    generic_nonmember_action INTEGER,
    goodbye_msg TEXT,
    header_matches BLOB,
    hold_these_nonmembers BLOB,
    info TEXT,
    linked_newsgroup TEXT,
    max_days_to_hold INTEGER,
    max_message_size INTEGER,
    max_num_recipients INTEGER,
    member_moderation_notice TEXT,
    mime_is_default_digest BOOLEAN,
    moderator_password TEXT,
    msg_footer TEXT,
    msg_header TEXT,
    new_member_options INTEGER,
    news_moderation INTEGER,
    news_prefix_subject_too BOOLEAN,
    nntp_host TEXT,
    nondigestable BOOLEAN,
    nonmember_rejection_notice TEXT,
    obscure_addresses BOOLEAN,
    personalize INTEGER,
    pipeline TEXT,
    post_id INTEGER,
    preferred_language TEXT,
    private_roster BOOLEAN,
    real_name TEXT,
    reject_these_nonmembers BLOB,
    reply_goes_to_list INTEGER,
    reply_to_address TEXT,
    require_explicit_destination BOOLEAN,
    respond_to_post_requests BOOLEAN,
    scrub_nondigest BOOLEAN,
    send_goodbye_msg BOOLEAN,
    send_reminders BOOLEAN,
    send_welcome_msg BOOLEAN,
    start_chain TEXT,
    subject_prefix TEXT,
    subscribe_auto_approval BLOB,
    subscribe_policy INTEGER,
    topics BLOB,
    topics_bodylines_limit INTEGER,
    topics_enabled BOOLEAN,
    unsubscribe_policy INTEGER,
    welcome_msg TEXT,
    PRIMARY KEY (id)
    );

CREATE TABLE member (
    id INTEGER NOT NULL,
    _member_id TEXT,
    role INTEGER,
    mailing_list TEXT,
    moderation_action INTEGER,
    address_id INTEGER,
    preferences_id INTEGER,
    user_id INTEGER,
    PRIMARY KEY (id),
    CONSTRAINT member_address_id_fk
        FOREIGN KEY (address_id) REFERENCES address (id),
    CONSTRAINT member_preferences_id_fk
        FOREIGN KEY (preferences_id) REFERENCES preferences (id)
    CONSTRAINT member_user_id_fk
        FOREIGN KEY (user_id) REFERENCES user (id)
    );
CREATE INDEX ix_member__member_id ON member (_member_id);
CREATE INDEX ix_member_address_id ON member (address_id);
CREATE INDEX ix_member_preferences_id ON member (preferences_id);

CREATE TABLE message (
    id INTEGER NOT NULL,
    message_id_hash TEXT,
    path TEXT,
    message_id TEXT,
    PRIMARY KEY (id)
    );

CREATE TABLE onelastdigest (
    id INTEGER NOT NULL,
    mailing_list_id INTEGER,
    address_id INTEGER,
    delivery_mode INTEGER,
    PRIMARY KEY (id),
    CONSTRAINT onelastdigest_mailing_list_id_fk
        FOREIGN KEY (mailing_list_id) REFERENCES mailinglist(id),
    CONSTRAINT onelastdigest_address_id_fk
        FOREIGN KEY (address_id) REFERENCES address(id)
    );

CREATE TABLE pended (
    id INTEGER NOT NULL,
    token TEXT,
    expiration_date TIMESTAMP,
    PRIMARY KEY (id)
    );

CREATE TABLE pendedkeyvalue (
    id INTEGER NOT NULL,
    "key" TEXT,
    value TEXT,
    pended_id INTEGER,
    PRIMARY KEY (id),
    CONSTRAINT pendedkeyvalue_pended_id_fk
        FOREIGN KEY (pended_id) REFERENCES pended (id)
    );

CREATE TABLE preferences (
    id INTEGER NOT NULL,
    acknowledge_posts BOOLEAN,
    hide_address BOOLEAN,
    preferred_language TEXT,
    receive_list_copy BOOLEAN,
    receive_own_postings BOOLEAN,
    delivery_mode INTEGER,
    delivery_status INTEGER,
    PRIMARY KEY (id)
    );

CREATE TABLE user (
    id INTEGER NOT NULL,
    real_name TEXT,
    password BINARY,
    _user_id TEXT,
    _created_on TIMESTAMP,
    _preferred_address_id INTEGER,
    preferences_id INTEGER,
    PRIMARY KEY (id),
    CONSTRAINT user_preferences_id_fk
        FOREIGN KEY (preferences_id) REFERENCES preferences (id),
    CONSTRAINT _preferred_address_id_fk
        FOREIGN KEY (_preferred_address_id) REFERENCES address (id)
    );
CREATE INDEX ix_user_user_id ON user (_user_id);

CREATE TABLE version (
    id INTEGER NOT NULL,
    component TEXT,
    version INTEGER,
    PRIMARY KEY (id)
    );

CREATE INDEX ix__request_mailing_list_id ON _request (mailing_list_id);
CREATE INDEX ix_address_preferences_id ON address (preferences_id);
CREATE INDEX ix_address_user_id ON address (user_id);
CREATE INDEX ix_pendedkeyvalue_pended_id ON pendedkeyvalue (pended_id);
CREATE INDEX ix_user_preferences_id ON user (preferences_id);

CREATE TABLE ban (
    id INTEGER NOT NULL,
    email TEXT,
    mailing_list TEXT,
    PRIMARY KEY (id)
    );

CREATE TABLE uid (
    -- Keep track of all assigned unique ids to prevent re-use.
    id INTEGER NOT NULL,
    uid TEXT,
    PRIMARY KEY (id)
    );
CREATE INDEX ix_uid_uid ON uid (uid);
