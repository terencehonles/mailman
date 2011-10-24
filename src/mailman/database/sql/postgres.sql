CREATE TABLE mailinglist (
    id SERIAL NOT NULL,
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
    accept_these_nonmembers BYTEA,
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
    digest_size_threshold REAL,
    digest_volume_frequency INTEGER,
    digestable BOOLEAN,
    discard_these_nonmembers BYTEA,
    emergency BOOLEAN,
    encode_ascii_prefixes BOOLEAN,
    first_strip_reply_to BOOLEAN,
    forward_auto_discards BOOLEAN,
    gateway_to_mail BOOLEAN,
    gateway_to_news BOOLEAN,
    generic_nonmember_action INTEGER,
    goodbye_msg TEXT,
    header_matches BYTEA,
    hold_these_nonmembers BYTEA,
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
    reject_these_nonmembers BYTEA,
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
    subscribe_auto_approval BYTEA,
    subscribe_policy INTEGER,
    topics BYTEA,
    topics_bodylines_limit INTEGER,
    topics_enabled BOOLEAN,
    unsubscribe_policy INTEGER,
    welcome_msg TEXT,
    moderation_callback TEXT,
    PRIMARY KEY (id)
    );

CREATE TABLE _request (
    id SERIAL NOT NULL,
    "key" TEXT,
    request_type INTEGER,
    data_hash BYTEA,
    mailing_list_id INTEGER,
    PRIMARY KEY (id)
    -- XXX: config.db_reset() triggers IntegrityError
    -- ,
    -- CONSTRAINT _request_mailing_list_id_fk
    --    FOREIGN KEY (mailing_list_id) REFERENCES mailinglist (id)
    );

CREATE TABLE acceptablealias (
    id SERIAL NOT NULL,
    "alias" TEXT NOT NULL,
    mailing_list_id INTEGER NOT NULL,
    PRIMARY KEY (id)
    -- XXX: config.db_reset() triggers IntegrityError
    -- ,
    -- CONSTRAINT acceptablealias_mailing_list_id_fk
    --    FOREIGN KEY (mailing_list_id) REFERENCES mailinglist (id)
    );
CREATE INDEX ix_acceptablealias_mailing_list_id
    ON acceptablealias (mailing_list_id);
CREATE INDEX ix_acceptablealias_alias ON acceptablealias ("alias");

CREATE TABLE preferences (
    id SERIAL NOT NULL,
    acknowledge_posts BOOLEAN,
    hide_address BOOLEAN,
    preferred_language TEXT,
    receive_list_copy BOOLEAN,
    receive_own_postings BOOLEAN,
    delivery_mode INTEGER,
    delivery_status INTEGER,
    PRIMARY KEY (id)
    );

CREATE TABLE address (
    id SERIAL NOT NULL,
    email TEXT,
    _original TEXT,
    real_name TEXT,
    verified_on TIMESTAMP,
    registered_on TIMESTAMP,
    user_id INTEGER,
    preferences_id INTEGER,
    PRIMARY KEY (id)
    -- XXX: config.db_reset() triggers IntegrityError
    -- ,
    -- CONSTRAINT address_preferences_id_fk
    --    FOREIGN KEY (preferences_id) REFERENCES preferences (id)
    );

CREATE TABLE "user" (
    id SERIAL NOT NULL,
    real_name TEXT,
    password BYTEA,
    _user_id UUID,
    _created_on TIMESTAMP,
    _preferred_address_id INTEGER,
    preferences_id INTEGER,
    PRIMARY KEY (id)
    -- XXX: config.db_reset() triggers IntegrityError
    -- ,
    -- CONSTRAINT user_preferences_id_fk
    --    FOREIGN KEY (preferences_id) REFERENCES preferences (id),
    -- XXX: config.db_reset() triggers IntegrityError
    -- CONSTRAINT _preferred_address_id_fk
    --    FOREIGN KEY (_preferred_address_id) REFERENCES address (id)
    );
CREATE INDEX ix_user_user_id ON "user" (_user_id);

-- since user and address have circular foreign key refs, the
-- constraint on the address table has to be added after
-- the user table is created
--
-- XXX: users.rst triggers an IntegrityError
-- ALTER TABLE address ADD
--     CONSTRAINT address_user_id_fk
--       FOREIGN KEY (user_id) REFERENCES "user" (id);

CREATE TABLE autoresponserecord (
    id SERIAL NOT NULL,
    address_id INTEGER,
    mailing_list_id INTEGER,
    response_type INTEGER,
    date_sent TIMESTAMP,
    PRIMARY KEY (id)
    -- XXX: config.db_reset() triggers IntegrityError
    -- ,
    -- CONSTRAINT autoresponserecord_address_id_fk
    --    FOREIGN KEY (address_id) REFERENCES address (id)
    -- XXX: config.db_reset() triggers IntegrityError
    --     ,
    -- CONSTRAINT autoresponserecord_mailing_list_id
    --     FOREIGN KEY (mailing_list_id) REFERENCES mailinglist (id)
    );
CREATE INDEX ix_autoresponserecord_address_id
    ON autoresponserecord (address_id);
CREATE INDEX ix_autoresponserecord_mailing_list_id
    ON autoresponserecord (mailing_list_id);

CREATE TABLE bounceevent (
    id SERIAL NOT NULL,
    list_name TEXT,
    email TEXT,
    "timestamp" TIMESTAMP,
    message_id TEXT,
    context INTEGER,
    processed BOOLEAN,
    PRIMARY KEY (id)
    );

CREATE TABLE contentfilter (
    id SERIAL NOT NULL,
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
    id SERIAL NOT NULL,
    mail_host TEXT,
    base_url TEXT,
    description TEXT,
    contact_address TEXT,
    PRIMARY KEY (id)
    );

CREATE TABLE language (
    id SERIAL NOT NULL,
    code TEXT,
    PRIMARY KEY (id)
    );

CREATE TABLE member (
    id SERIAL NOT NULL,
    _member_id UUID,
    role INTEGER,
    mailing_list TEXT,
    moderation_action INTEGER,
    address_id INTEGER,
    preferences_id INTEGER,
    user_id INTEGER,
    PRIMARY KEY (id)
    -- XXX: config.db_reset() triggers IntegrityError
    -- ,
    -- CONSTRAINT member_address_id_fk
    --     FOREIGN KEY (address_id) REFERENCES address (id),
    -- XXX: config.db_reset() triggers IntegrityError
    -- CONSTRAINT member_preferences_id_fk
    --     FOREIGN KEY (preferences_id) REFERENCES preferences (id),
    -- CONSTRAINT member_user_id_fk
    --    FOREIGN KEY (user_id) REFERENCES "user" (id)
    );
CREATE INDEX ix_member__member_id ON member (_member_id);
CREATE INDEX ix_member_address_id ON member (address_id);
CREATE INDEX ix_member_preferences_id ON member (preferences_id);

CREATE TABLE message (
    id SERIAL NOT NULL,
    message_id_hash BYTEA,
    path BYTEA,
    message_id TEXT,
    PRIMARY KEY (id)
    );

CREATE TABLE onelastdigest (
    id SERIAL NOT NULL,
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
    id SERIAL NOT NULL,
    token BYTEA,
    expiration_date TIMESTAMP,
    PRIMARY KEY (id)
    );

CREATE TABLE pendedkeyvalue (
    id SERIAL NOT NULL,
    "key" TEXT,
    value TEXT,
    pended_id INTEGER,
    PRIMARY KEY (id)
    -- ,
    -- XXX: config.db_reset() triggers IntegrityError
    -- CONSTRAINT pendedkeyvalue_pended_id_fk
    --    FOREIGN KEY (pended_id) REFERENCES pended (id)
    );

CREATE TABLE version (
    id SERIAL NOT NULL,
    component TEXT,
    version INTEGER,
    PRIMARY KEY (id)
    );

CREATE INDEX ix__request_mailing_list_id ON _request (mailing_list_id);
CREATE INDEX ix_address_preferences_id ON address (preferences_id);
CREATE INDEX ix_address_user_id ON address (user_id);
CREATE INDEX ix_pendedkeyvalue_pended_id ON pendedkeyvalue (pended_id);
CREATE INDEX ix_user_preferences_id ON "user" (preferences_id);

CREATE TABLE ban (
    id SERIAL NOT NULL,
    email TEXT,
    mailing_list TEXT,
    PRIMARY KEY (id)
    );

CREATE TABLE uid (
    -- Keep track of all assigned unique ids to prevent re-use.
    id SERIAL NOT NULL,
    uid UUID,
    PRIMARY KEY (id)
    );
CREATE INDEX ix_uid_uid ON uid (uid);
