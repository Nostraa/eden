# -*- coding: utf-8 -*-

""" Sahana Eden Messaging Model

    @copyright: 2009-2012 (c) Sahana Software Foundation
    @license: MIT

    Permission is hereby granted, free of charge, to any person
    obtaining a copy of this software and associated documentation
    files (the "Software"), to deal in the Software without
    restriction, including without limitation the rights to use,
    copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the
    Software is furnished to do so, subject to the following
    conditions:

    The above copyright notice and this permission notice shall be
    included in all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
    EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
    OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
    NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
    HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
    WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
    OTHER DEALINGS IN THE SOFTWARE.
"""

__all__ = ["S3MessagingModel",
           "S3InboundEmailModel",
           "S3SMSModel",
           "S3SubscriptionModel",
           "S3TropoModel",
           "S3TwitterModel",
           "S3XFormsModel",
           "S3ParsingModel",
           ]

from gluon import *
from gluon.storage import Storage
from ..s3 import *

# =============================================================================
class S3MessagingModel(S3Model):
    """
        Messaging Framework
        - core models defined here
    """

    names = ["msg_log",
             "msg_limit",
             #"msg_tag",
             "msg_outbox",
             #"msg_channel",
             "msg_message_id",
             ]

    def model(self):

        T = current.T
        db = current.db

        UNKNOWN_OPT = current.messages.UNKNOWN_OPT

        configure = self.configure
        define_table = self.define_table
        super_link = self.super_link

        # Message priority
        msg_priority_opts = {
            3:T("High"),
            2:T("Medium"),
            1:T("Low")
        }

        mtable = self.msg_inbound_email_settings
        source_opts = []
        append = source_opts.append
        records = db(mtable.id > 0).select(mtable.username)
        for record in records:
            append(record.username)

        # ---------------------------------------------------------------------
        # Message Log - all Inbound & Outbound Messages
        # ---------------------------------------------------------------------
        tablename = "msg_log"
        table = define_table(tablename,
                             super_link("pe_id", "pr_pentity"),
                             Field("sender"),        # The name to go out incase of the email, if set used
                             Field("fromaddress"),   # From address if set changes sender to this
                             Field("recipient"),
                             Field("subject", length=78),
                             Field("message", "text"),
                             #Field("attachment", "upload", autodelete = True), #TODO
                             Field("verified", "boolean", default = False),
                             Field("verified_comments", "text"),
                             Field("actionable", "boolean", default = True),
                             Field("actioned", "boolean", default = False),
                             Field("actioned_comments", "text"),
                             Field("priority", "integer", default = 1,
                                   requires = IS_NULL_OR(IS_IN_SET(msg_priority_opts)),
                                   label = T("Priority")),
                             Field("inbound", "boolean", default = False,
                                   represent = lambda direction: \
                                       (direction and ["In"] or ["Out"])[0],
                                   label = T("Direction")),
                             Field("is_parsed", "boolean", default = False,
                                   represent = lambda status: \
                                       (status and ["Parsed"] or ["Not Parsed"])[0],
                                   label = T("Parsing Status")),
                             Field("reply", "text" ,
                                   label = T("Reply")),
                             Field("source_task_id",
                                   requires = IS_IN_SET(source_opts,
                                                        zero = None)),
                             *s3_meta_fields())

        configure(tablename,
                  list_fields=["id",
                               "inbound",
                               "pe_id",
                               "fromaddress",
                               "recipient",
                               "subject",
                               "message",
                               "verified",
                               #"verified_comments",
                               "actionable",
                               "actioned",
                               #"actioned_comments",
                               #"priority",
                               "is_parsed",
                               "reply",
                               "source_task_id"
                               ])

        # Components
        self.add_component("msg_outbox", msg_log="message_id")

        # Reusable Message ID
        message_id = S3ReusableField("message_id", table,
                                     requires = IS_NULL_OR(
                                                    IS_ONE_OF_EMPTY(db, "msg_log.id")),
                                     represent = self.message_represent,
                                     ondelete = "RESTRICT")

        # ---------------------------------------------------------------------
        # Message Limit
        #  Used to limit the number of emails sent from the system
        #  - works by simply recording an entry for the timestamp to be checked against
        # @ToDo: have separate limits for Email & SMS
        tablename = "msg_limit"
        table = define_table(tablename,
                             *s3_timestamp())

        # ---------------------------------------------------------------------
        # Message Tag - Used to tag a message to a resource
        # tablename = "msg_tag"
        # table = define_table(tablename,
                                  # message_id(),
                                  # Field("resource"),
                                  # Field("record_uuid", # null in this field implies subscription to the entire resource
                                        # type=s3uuid,
                                        # length=128),
                                  # *s3_meta_fields())

        # configure(tablename,
                       # list_fields=[ "id",
                                     # "message_id",
                                     # "record_uuid",
                                     # "resource",
                                    # ])

        # ---------------------------------------------------------------------
        # Outbound Messages
        # ---------------------------------------------------------------------
        # Show only the supported messaging methods
        msg_contact_method_opts = current.msg.MSG_CONTACT_OPTS

        # Valid message outbox statuses
        msg_status_type_opts = {
            1:T("Unsent"),
            2:T("Sent"),
            3:T("Draft"),
            4:T("Invalid")
            }

        opt_msg_status = S3ReusableField("status", "integer",
                                         notnull=True,
                                         requires = IS_IN_SET(msg_status_type_opts,
                                                              zero=None),
                                         default = 1,
                                         label = T("Status"),
                                         represent = lambda opt: \
                                            msg_status_type_opts.get(opt, UNKNOWN_OPT))

        # Outbox - needs to be separate to Log since a single message sent needs different outbox entries for each recipient
        tablename = "msg_outbox"
        table = define_table(tablename,
                             message_id(),
                             super_link("pe_id", "pr_pentity"), # Person/Group to send the message out to
                             Field("address"),   # If set used instead of picking up from pe_id
                             Field("pr_message_method", length=32,
                                   requires = IS_IN_SET(msg_contact_method_opts,
                                                        zero=None),
                                   default = "EMAIL",
                                   label = T("Contact Method"),
                                   represent = lambda opt: \
                                        msg_contact_method_opts.get(opt, UNKNOWN_OPT)),
                             opt_msg_status(),
                             Field("system_generated", "boolean", default = False),
                             Field("log"),
                             *s3_meta_fields())

        configure(tablename,
                  list_fields=["id",
                               "message_id",
                               "pe_id",
                               "status",
                               "log",
                               ])

        # ---------------------------------------------------------------------
        # Inbound Messages
        # ---------------------------------------------------------------------
        # Channel - For inbound messages this tells which channel the message came in from.
        tablename = "msg_channel"
        table = define_table(tablename,
                             message_id(),
                             Field("pr_message_method",
                                   length=32,
                                   requires = IS_IN_SET(msg_contact_method_opts,
                                                        zero=None),
                                   default = "EMAIL"),
                             Field("log"),
                             *s3_meta_fields())

        # ---------------------------------------------------------------------
        # Pass variables back to global scope (s3db.*)
        return Storage(
                msg_message_id=message_id,
            )

    # -------------------------------------------------------------------------
    @staticmethod
    def message_represent(id):
        """ Represent a Message in the Log """

        if not id:
            return current.messages.NONE

        db = current.db
        table = db.msg_log
        record = db(table.id == id).select(table.subject,
                                           table.message,
                                           limitby=(0, 1)).first()
        try:
            if record.subject:
                # EMail will use Subject
                return record.subject
        except:
            return current.messages.UNKNOWN_OPT

        # SMS/Tweet will use 1st 80 characters from body
        text = record.message
        if len(text) < 80:
            return text
        else:
            return "%s..." % text[:76]

# =============================================================================
class S3InboundEmailModel(S3Model):
    """
        Inbound Email

        Outbound Email is handled via deployment_settings
    """

    names = ["msg_inbound_email_settings",
             "msg_inbound_email_status",
             "msg_email_inbox",
             ]

    def model(self):

        T = current.T

        define_table = self.define_table

        # ---------------------------------------------------------------------
        tablename = "msg_inbound_email_settings"
        table = define_table(tablename,
                             Field("server"),
                             Field("protocol",
                                   requires = IS_IN_SET(["imap", "pop3"],
                                                        zero=None)),
                             Field("use_ssl", "boolean"),
                             Field("port", "integer"),
                             Field("username"),
                             Field("password"),
                             # Set true to delete messages from the remote
                             # inbox after fetching them.
                             Field("delete_from_server", "boolean"),
                             *s3_meta_fields())

        # ---------------------------------------------------------------------
        # Incoming Email
        tablename = "msg_email_inbox"
        table = define_table(tablename,
                             Field("sender", notnull=True,
                                   label = T("Sender"),
                                   requires = IS_EMAIL()),
                             Field("subject", length=78,    # RFC 2822
                                   label = T("Subject")),
                             Field("body", "text",
                                   label = T("Body")),
                             *s3_meta_fields())

        #table.sender.comment = SPAN("*", _class="req")
        VIEW_EMAIL_INBOX = T("View Email InBox")
        current.response.s3.crud_strings[tablename] = Storage(
            #title_create = T("Add Incoming Email"),
            title_display = T("Email Details"),
            title_list = VIEW_EMAIL_INBOX,
            #title_update = T("Edit Email"),
            title_search = T("Search Email InBox"),
            label_list_button = VIEW_EMAIL_INBOX,
            #label_create_button = T("Add Incoming Email"),
            #msg_record_created = T("Email added"),
            #msg_record_modified = T("Email updated"),
            msg_record_deleted = T("Email deleted"),
            msg_list_empty = T("No Emails currently in InBox"))

        # ---------------------------------------------------------------------
        # Status
        tablename = "msg_inbound_email_status"
        table = define_table(tablename,
                             Field("status"))

        # ---------------------------------------------------------------------
        return Storage()

# =============================================================================
class S3SMSModel(S3Model):
    """
        SMS: Short Message Service

        These can be sent through a number of different gateways
        - modem
        - api
        - smtp
        - tropo
    """

    names = ["msg_setting",
             "msg_modem_settings",
             "msg_api_settings",
             "msg_smtp_to_sms_settings",
            ]

    def model(self):

        #T = current.T

        define_table = self.define_table

        # ---------------------------------------------------------------------
        # Settings
        tablename = "msg_setting"
        table = define_table(tablename,
                             Field("outgoing_sms_handler",
                                   length=32,
                                   requires = IS_IN_SET(current.msg.GATEWAY_OPTS,
                                                        zero=None)),
                             # Moved to deployment_settings
                             #Field("default_country_code", "integer",
                             #      default=44),
                             *s3_meta_fields())

        # ---------------------------------------------------------------------
        tablename = "msg_modem_settings"
        table = define_table(tablename,
                             # Nametag to remember account - To be used later
                             #Field("account_name"),
                             Field("modem_port"),
                             Field("modem_baud", "integer", default = 115200),
                             Field("enabled", "boolean", default = True),
                             # To be used later
                             #Field("preference", "integer", default = 5),
                             *s3_meta_fields())

        # ---------------------------------------------------------------------
        tablename = "msg_api_settings"
        table = define_table(tablename,
                             Field("url",
                                   default = "https://api.clickatell.com/http/sendmsg"),
                             Field("parameters",
                                   default="user=yourusername&password=yourpassword&api_id=yourapiid"),
                             Field("message_variable", "string",
                                   default = "text"),
                             Field("to_variable", "string",
                                   default = "to"),
                             Field("enabled", "boolean",
                                   default = True),
                             # To be used later
                             #Field("preference", "integer", default = 5),
                             *s3_meta_fields())

        # ---------------------------------------------------------------------
        tablename = "msg_smtp_to_sms_settings"
        table = define_table(tablename,
                             # Nametag to remember account - To be used later
                             #Field("account_name"),
                             Field("address", length=64,
                                   requires=IS_NOT_EMPTY()),
                             Field("subject", length=64),
                             Field("enabled", "boolean",
                                   default = True),
                             # To be used later
                             #Field("preference", "integer", default = 5),
                             *s3_meta_fields())

        # ---------------------------------------------------------------------
        return Storage()

# =============================================================================
class S3SubscriptionModel(S3Model):
    """
        Handle Subscription
        - currently this is just for Saved Searches
    """

    names = ["msg_subscription"]

    def model(self):

        T = current.T
        auth = current.auth

        # @ToDo: Use msg.CONTACT_OPTS
        msg_subscription_mode_opts = {
                                        1:T("Email"),
                                        #2:T("SMS"),
                                        #3:T("Email and SMS")
                                    }
        # @ToDo: Move this to being a component of the Saved Search
        #        (so that each search can have it's own subscription options)
        # @ToDo: Make Conditional
        # @ToDo: CRUD Strings
        tablename = "msg_subscription"
        table = self.define_table(tablename,
                                  Field("user_id", "integer",
                                        default = auth.user_id,
                                        requires = IS_NOT_IN_DB(current.db,
                                                                "msg_subscription.user_id"),
                                        readable = False,
                                        writable = False
                                        ),
                                  Field("subscribe_mode", "integer",
                                        default = 1,
                                        represent = lambda opt: \
                                            msg_subscription_mode_opts.get(opt, None),
                                        readable = False,
                                        requires = IS_IN_SET(msg_subscription_mode_opts,
                                                             zero=None)
                                        ),
                                  Field("subscription_frequency",
                                        requires = IS_IN_SET(["daily",
                                                              "weekly",
                                                              "monthly"]),
                                        default = "daily",
                                        ),
                                  self.pr_person_id(label = T("Person"),
                                                    default = auth.s3_logged_in_person()),
                                  *s3_meta_fields())

        self.configure("msg_subscription",
                       list_fields=["subscribe_mode",
                                    "subscription_frequency"])

        # ---------------------------------------------------------------------
        return Storage()

# =============================================================================
class S3TropoModel(S3Model):
    """
        Tropo can be used to send & receive SMS, Twitter & XMPP

        https://www.tropo.com
    """

    names = ["msg_tropo_settings",
             "msg_tropo_scratch",
            ]

    def model(self):

        #T = current.T

        define_table = self.define_table

        # ---------------------------------------------------------------------
        tablename = "msg_tropo_settings"
        table = define_table(tablename,
                             Field("token_messaging"),
                             #Field("token_voice"),
                             *s3_meta_fields())

        # ---------------------------------------------------------------------
        # Tropo Scratch pad for outbound messaging
        tablename = "msg_tropo_scratch"
        table = define_table(tablename,
                             Field("row_id","integer"),
                             Field("message_id","integer"),
                             Field("recipient"),
                             Field("message"),
                             Field("network")
                             )

        # ---------------------------------------------------------------------
        return Storage()

# =============================================================================
class S3TwitterModel(S3Model):

    names = ["msg_twitter_settings",
             "msg_twitter_search",
             "msg_twitter_search_results"
            ]

    def model(self):

        #T = current.T
        db = current.db

        configure = self.configure
        define_table = self.define_table

        # ---------------------------------------------------------------------
        tablename = "msg_twitter_settings"
        table = define_table(tablename,
                             Field("pin"),
                             Field("oauth_key",
                                   readable = False, writable = False),
                             Field("oauth_secret",
                                   readable = False, writable = False),
                             Field("twitter_account", writable = False),
                             *s3_meta_fields())

        configure(tablename,
                  onvalidation=self.twitter_settings_onvalidation)

        # ---------------------------------------------------------------------
        # Twitter Search Queries
        tablename = "msg_twitter_search"
        table = define_table(tablename,
                             Field("search_query", length = 140),
                             *s3_meta_fields())

        # ---------------------------------------------------------------------
        tablename = "msg_twitter_search_results"
        table = define_table(tablename,
                             Field("tweet", length=140),
                             Field("posted_by"),
                             Field("posted_at"),
                             Field("twitter_search", db.msg_twitter_search),
                             *s3_meta_fields())

        #table.twitter_search.requires = IS_ONE_OF(db, "twitter_search.search_query")
        #table.twitter_search.represent = lambda id: db(db.msg_twitter_search.id == id).select(db.msg_twitter_search.search_query,
                                                                                              #limitby = (0, 1)).first().search_query

        #self.add_component(table, msg_twitter_search="twitter_search")

        configure(tablename,
                  list_fields=["id",
                               "tweet",
                               "posted_by",
                               "posted_at",
                               "twitter_search",
                               ])

        # ---------------------------------------------------------------------
        return Storage()

    # -------------------------------------------------------------------------
    @staticmethod
    def twitter_settings_onvalidation(form):
        """
            Complete oauth: take tokens from session + pin from form, and do the 2nd API call to Twitter
        """

        T = current.T
        session = current.session
        settings = current.deployment_settings
        s3 = session.s3
        vars = form.vars

        if vars.pin and s3.twitter_request_key and s3.twitter_request_secret:
            try:
                import tweepy
            except:
                raise HTTP(501, body=T("Can't import tweepy"))

            oauth = tweepy.OAuthHandler(settings.twitter.oauth_consumer_key,
                                        settings.twitter.oauth_consumer_secret)
            oauth.set_request_token(s3.twitter_request_key,
                                    s3.twitter_request_secret)
            try:
                oauth.get_access_token(vars.pin)
                vars.oauth_key = oauth.access_token.key
                vars.oauth_secret = oauth.access_token.secret
                twitter = tweepy.API(oauth)
                vars.twitter_account = twitter.me().screen_name
                vars.pin = "" # we won't need it anymore
                return
            except tweepy.TweepError:
                session.error = T("Settings were reset because authenticating with Twitter failed")
        # Either user asked to reset, or error - clear everything
        for k in ["oauth_key", "oauth_secret", "twitter_account"]:
            vars[k] = None
        for k in ["twitter_request_key", "twitter_request_secret"]:
            s3[k] = ""

# =============================================================================
class S3XFormsModel(S3Model):
    """
        XForms are used by the ODK Collect mobile client

        http://eden.sahanafoundation.org/wiki/BluePrint/Mobile#Android
    """

    names = ["msg_xforms_store"]

    def model(self):

        #T = current.T

        # ---------------------------------------------------------------------
        # SMS store for persistence and scratch pad for combining incoming xform chunks
        tablename = "msg_xforms_store"
        table = self.define_table(tablename,
                                  Field("sender", "string", length=20),
                                  Field("fileno", "integer"),
                                  Field("totalno", "integer"),
                                  Field("partno", "integer"),
                                  Field("message", "string", length=160)
                                )

        # ---------------------------------------------------------------------
        return Storage()

# =============================================================================
class S3ParsingModel(S3Model):
    """
        Message Parsing Model
    """

    names = ["msg_workflow"]

    def model(self):

        from s3 import s3parser
        import inspect

        T = current.T
        mtable = self.msg_inbound_email_settings
        # source_opts contain the available message sources.
        source_opts = []
        records = current.db(mtable.deleted == False).select(mtable.username)
        for record in records:
            source_opts += [record.username]

        # Dynamic lookup of the parsing functions in S3Parsing class.
        parsers = inspect.getmembers(s3parser.S3Parsing, predicate=inspect.isfunction)
        parse_opts = []
        for parser in parsers:
            parse_opts += [parser[0]]

        tablename = "msg_workflow"
        table = self.define_table(tablename,
                                  Field("source_task_id",
                                        label = T("Inbound Message Source"),
                                        requires = IS_IN_SET(source_opts,
                                                             zero = None)),
                                  Field("workflow_task_id",
                                        label = T("Workflow"),
                                        requires = IS_IN_SET(parse_opts,
                                                             zero=None)),
                                  *s3_meta_fields())

        return Storage()

# END =========================================================================
