# Drift label review — 25 cases (seed 7)

For each case, replace `VERDICT: ?` with one of:

- `drift` — the doc said something untrue about the code, and this commit corrected it
- `new` — the doc was documenting something that did not exist yet (feature + its docs)
- `cosmetic` — wording, formatting or a link -- nothing factual changed
- `unrelated` — the doc change and the code change are not about the same thing
- `unclear` — cannot tell from these diffs alone

The question is always: **at the parent commit, was this documentation false about the code?** Not whether the commit improved the docs — whether what it replaced was wrong.

---

## Case 1 — `e9d07899c5931ed7`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Use American English for "behavior" in docs.
- **commit** https://github.com/pallets/flask/commit/a3cb2a33829ee517530d30cd920e5d652b358086
- **doc** `docs/quickstart.rst`
- **code** `flask/app.py`
- **shared identifiers** `behaviour`, `behavior`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/quickstart.rst b/docs/quickstart.rst
index daaecb23..46290d0b 100644
--- a/docs/quickstart.rst
+++ b/docs/quickstart.rst
@@ -166,7 +166,7 @@ The following converters exist:
 `path`      like the default but also accepts slashes
 =========== ===========================================
 
-.. admonition:: Unique URLs / Redirection Behaviour
+.. admonition:: Unique URLs / Redirection Behavior
 
    Flask's URL rules are based on Werkzeug's routing module.  The idea
    behind that module is to ensure beautiful and unique URLs based on

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/flask/app.py b/flask/app.py
index 8460f476..4c00c36b 100644
--- a/flask/app.py
+++ b/flask/app.py
@@ -1360,7 +1360,7 @@ class Flask(_PackageBoundObject):
     def make_default_options_response(self):
         """This method is called to create the default `OPTIONS` response.
         This can be changed through subclassing to change the default
-        behaviour of `OPTIONS` responses.
+        behavior of `OPTIONS` responses.
 
         .. versionadded:: 0.7
         """

```

</details>

---

## Case 2 — `5b8313d781660a32`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** add json provider interface
- **commit** https://github.com/pallets/flask/commit/69f9845ef2da3051d74d4dade3e88ccf5b2ee3de
- **doc** `docs/api.rst`
- **code** `src/flask/ctx.py`
- **shared identifiers** `json`

**VERDICT: `new`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/api.rst b/docs/api.rst
index 67772a77..5359b370 100644
--- a/docs/api.rst
+++ b/docs/api.rst
@@ -236,21 +236,15 @@ JSON Support
 
 .. module:: flask.json
 
-Flask uses the built-in :mod:`json` module for handling JSON. It will
-use the current blueprint's or application's JSON encoder and decoder
-for easier customization. By default it handles some extra data types:
-
--   :class:`datetime.datetime` and :class:`datetime.date` are serialized
-    to :rfc:`822` strings. This is the same as the HTTP date format.
--   :class:`uuid.UUID` is serialized to a string.
--   :class:`dataclasses.dataclass` is passed to
-    :func:`dataclasses.asdict`.
--   :class:`~markupsafe.Markup` (or any object with a ``__html__``
-    method) will call the ``__html__`` method to get a string.
-
-Jinja's ``|tojson`` filter is configured to use Flask's :func:`dumps`
-function. The filter marks the output with ``|safe`` automatically. Use
-the filter to render data inside ``<script>`` tags.
+Flask uses Python's built-in :mod:`json` module for handling JSON by
+default. The JSON implementation can be changed by assigning a different
+provider to :attr:`flask.Flask.json_provider_class` or
+:attr:`flask.Flask.json`. The functions provided by ``flask.json`` will
+use methods on ``app.json`` if an app context is active.
+
+Jinja's ``|tojson`` filter is configured to use the app's JSON provider.
+The filter marks the output with ``|safe``. Use it to render data inside
+HTML ``<script>`` tags.
 
 .. sourcecode:: html+jinja
 
@@ -269,6 +263,14 @@ the filter to render data inside ``<script>`` tags.
 
 .. autofunction:: load
 
+.. autoclass:: flask.json.provider.JSONProvider
+    :members:
+    :member-order: bysource
+
+.. autoclass:: flask.json.provider.DefaultJSONProvider
+    :members:
+    :member-order: bysource
+
 .. autoclass:: JSONEncoder
    :members:
 

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/src/flask/ctx.py b/src/flask/ctx.py
index d0e7e1e4..84d739ec 100644
--- a/src/flask/ctx.py
+++ b/src/flask/ctx.py
@@ -307,6 +307,7 @@ class RequestContext:
         self.app = app
         if request is None:
             request = app.request_class(environ)
+            request.json_module = app.json  # type: ignore[misc]
         self.request: Request = request
         self.url_adapter = None
         try:

```

</details>

---

## Case 3 — `48faf82e4d283c54`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Added appcontext_pushed and appcontext_popped signals
- **commit** https://github.com/pallets/flask/commit/0676bb8ab54a575616cd65d3c2ef1cc31fb82a84
- **doc** `docs/signals.rst`
- **code** `flask/ctx.py`
- **shared identifiers** `appcontext_popped`, `appcontext_pushed`, `appcontext`, `popped`, `pushed`

**VERDICT: `new`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/signals.rst b/docs/signals.rst
index 4d96cc14..799b5a91 100644
--- a/docs/signals.rst
+++ b/docs/signals.rst
@@ -291,6 +291,45 @@ The following signals exist in Flask:
    This will also be passed an `exc` keyword argument that has a reference
    to the exception that caused the teardown if there was one.
 
+.. data:: flask.appcontext_pushed
+   :noindex:
+
+   This signal is sent when an application context is pushed.  The sender
+   is the application.  This is usually useful for unittests in order to
+   temporarily hook in information.  For instance it can be used to
+   set a resource early onto the `g` object.
+
+   Example usage::
+
+        from contextlib import contextmanager
+        from flask import appcontext_pushed
+
+        @contextmanager
+        def user_set(app, user):
+            def handler(sender, **kwargs):
+                g.user = user
+            with appcontext_pushed.connected_to(handler, app):
+                yield
+
+   And in the testcode::
+
+        def test_user_me(self):
+            with user_set(app, 'john'):
+                c = app.test_client()
+                resp = c.get('/users/me')
+                assert resp.data == 'username=john'
+
+   .. versionadded:: 0.10
+
+.. data:: appcontext_popped
+
+   This signal is sent when an application context is popped.  The sender
+   is the application.  This usually falls in line with the
+   :data:`appcontext_tearing_down` signal.
+
+   .. versionadded:: 0.10
+
+
 .. data:: flask.message_flashed
    :noindex:
 

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/flask/ctx.py b/flask/ctx.py
index 6ea3158f..19f42047 100644
--- a/flask/ctx.py
+++ b/flask/ctx.py
@@ -18,6 +18,7 @@ from werkzeug.exceptions import HTTPException
 
 from .globals import _request_ctx_stack, _app_ctx_stack
 from .module import blueprint_is_module
+from .signals import appcontext_pushed, appcontext_popped
 
 
 class _AppCtxGlobals(object):
@@ -166,6 +167,7 @@ class AppContext(object):
         """Binds the app context to the current context."""
         self._refcnt += 1
         _app_ctx_stack.push(self)
+        appcontext_pushed.send(self.app)
 
     def pop(self, exc=None):
         """Pops the app context."""
@@ -177,6 +179,7 @@ class AppContext(object):
         rv = _app_ctx_stack.pop()
         assert rv is self, 'Popped wrong app context.  (%r instead of %r)' \
             % (rv, self)
+        appcontext_popped.send(self.app)
 
     def __enter__(self):
         self.push()

```

</details>

---

## Case 4 — `046a3fd9496aa640`

- **repo** `psf/requests` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Add support for Python 3.14 and drop support for Python 3.8 (#6993)
- **commit** https://github.com/psf/requests/commit/2edca11103c1c27dd8b572dab544b7f48cf3b446
- **doc** `docs/index.rst`
- **code** `setup.py`
- **shared identifiers** `ver:3.8`, `ver:3.9`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/index.rst b/docs/index.rst
index 289250c2..aef47a89 100644
--- a/docs/index.rst
+++ b/docs/index.rst
@@ -72,7 +72,7 @@ Requests is ready for today's web.
 - Chunked Requests
 - ``.netrc`` Support
 
-Requests officially supports Python 3.8+, and runs great on PyPy.
+Requests officially supports Python 3.9+, and runs great on PyPy.
 
 
 The User Guide

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/setup.py b/setup.py
index 7d9b52bc..ff65d391 100755
--- a/setup.py
+++ b/setup.py
@@ -6,7 +6,7 @@ from codecs import open
 from setuptools import setup
 
 CURRENT_PYTHON = sys.version_info[:2]
-REQUIRED_PYTHON = (3, 8)
+REQUIRED_PYTHON = (3, 9)
 
 if CURRENT_PYTHON < REQUIRED_PYTHON:
     sys.stderr.write(
@@ -69,7 +69,7 @@ setup(
     package_data={"": ["LICENSE", "NOTICE"]},
     package_dir={"": "src"},
     include_package_data=True,
-    python_requires=">=3.8",
+    python_requires=">=3.9",
     install_requires=requires,
     license=about["__license__"],
     zip_safe=False,
@@ -82,12 +82,12 @@ setup(
         "Operating System :: OS Independent",
         "Programming Language :: Python",
         "Programming Language :: Python :: 3",
-        "Programming Language :: Python :: 3.8",
         "Programming Language :: Python :: 3.9",
         "Programming Language :: Python :: 3.10",
         "Programming Language :: Python :: 3.11",
         "Programming Language :: Python :: 3.12",
         "Programming Language :: Python :: 3.13",
+        "Programming Language :: Python :: 3.14",
         "Programming Language :: Python :: 3 :: Only",
         "Programming Language :: Python :: Implementation :: CPython",
         "Programming Language :: Python :: Implementation :: PyPy",

```

</details>

---

## Case 5 — `f7a4b954ca3a941a`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Use American English for "behavior" in docs.
- **commit** https://github.com/pallets/flask/commit/a3cb2a33829ee517530d30cd920e5d652b358086
- **doc** `docs/templating.rst`
- **code** `flask/app.py`
- **shared identifiers** `behaviour`, `behavior`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/templating.rst b/docs/templating.rst
index d4878cdb..8ecf5332 100644
--- a/docs/templating.rst
+++ b/docs/templating.rst
@@ -63,7 +63,7 @@ by default:
 
    The :func:`flask.get_flashed_messages` function.
 
-.. admonition:: The Jinja Context Behaviour
+.. admonition:: The Jinja Context Behavior
 
    These variables are added to the context of variables, they are not
    global variables.  The difference is that by default these will not

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/flask/app.py b/flask/app.py
index 8460f476..4c00c36b 100644
--- a/flask/app.py
+++ b/flask/app.py
@@ -1360,7 +1360,7 @@ class Flask(_PackageBoundObject):
     def make_default_options_response(self):
         """This method is called to create the default `OPTIONS` response.
         This can be changed through subclassing to change the default
-        behaviour of `OPTIONS` responses.
+        behavior of `OPTIONS` responses.
 
         .. versionadded:: 0.7
         """

```

</details>

---

## Case 6 — `eb457aed8ccb07e6`

- **repo** `psf/requests` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Document Timeout behaviour
- **commit** https://github.com/psf/requests/commit/dfa41afd43a15222eb7a2db35feadd36dba4b445
- **doc** `docs/api.rst`
- **code** `requests/exceptions.py`
- **shared identifiers** `connecttimeout`, `readtimeout`, `exceptions`, `connect`, `timeout`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/api.rst b/docs/api.rst
index 69f138a2..f1242ccb 100644
--- a/docs/api.rst
+++ b/docs/api.rst
@@ -60,6 +60,8 @@ Exceptions
 .. autoexception:: requests.exceptions.HTTPError
 .. autoexception:: requests.exceptions.URLRequired
 .. autoexception:: requests.exceptions.TooManyRedirects
+.. autoexception:: requests.exceptions.ConnectTimeout
+.. autoexception:: requests.exceptions.ReadTimeout
 .. autoexception:: requests.exceptions.Timeout
 
 
@@ -255,21 +257,3 @@ Behavioral Changes
   keys are not native strings (unicode on Python2 or bytestrings on Python 3)
   they will be converted to the native string type assuming UTF-8 encoding.
 
-* Timeouts behave slightly differently. On streaming requests, the timeout
-  only applies to the connection attempt. On regular requests, the timeout
-  is applied to the connection process and on to all attempts to read data from
-  the underlying socket. It does *not* apply to the total download time for the
-  request.
-
-  ::
-
-      tarball_url = 'https://github.com/kennethreitz/requests/tarball/master'
-
-      # One second timeout for the connection attempt
-      # Unlimited time to download the tarball
-      r = requests.get(tarball_url, stream=True, timeout=1)
-
-      # One second timeout for the connection attempt
-      # Another full second timeout to download the tarball
-      r = requests.get(tarball_url, timeout=1)
-

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/requests/exceptions.py b/requests/exceptions.py
index 6dbd98a9..d8f05f08 100644
--- a/requests/exceptions.py
+++ b/requests/exceptions.py
@@ -46,15 +46,16 @@ class SSLError(ConnectionError):
 class Timeout(RequestException):
     """The request timed out.
 
-    Catching this error will catch both :exc:`ConnectTimeout` and
-    :exc:`ReadTimeout` errors.
+    Catching this error will catch both
+    :exc:`~requests.exceptions.ConnectTimeout` and
+    :exc:`~requests.exceptions.ReadTimeout` errors.
     """
 
 
 class ConnectTimeout(ConnectionError, Timeout):
-    """The request timed out while trying to connect to the server.
+    """The request timed out while trying to connect to the remote server.
 
-    Requests that produce this error are safe to retry
+    Requests that produced this error are safe to retry.
     """
 
 

```

</details>

---

## Case 7 — `d882bce695b08b52`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** added a new behaviour for responses that enable the tuple to be in the form of (response, headers) and continiue to support the (response, status, headers) format.
- **commit** https://github.com/pallets/flask/commit/70f8b39c52527573e65e7066024a187867564c01
- **doc** `docs/quickstart.rst`
- **code** `flask/testsuite/basic.py`
- **shared identifiers** `headers`, `status`

**VERDICT: `new`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/quickstart.rst b/docs/quickstart.rst
index 3cb9b2f7..c8a1140b 100644
--- a/docs/quickstart.rst
+++ b/docs/quickstart.rst
@@ -676,9 +676,9 @@ converting return values into response objects is as follows:
     default parameters.
 3.  If a tuple is returned the items in the tuple can provide extra
     information.  Such tuples have to be in the form ``(response, status,
-    headers)`` where at least one item has to be in the tuple.  The
-    `status` value will override the status code and `headers` can be a
-    list or dictionary of additional header values.
+    headers)`` or ``(response, headers)`` where at least one item has
+    to be in the tuple.  The `status` value will override the status code
+    and `headers` can be a list or dictionary of additional header values.
 4.  If none of that works, Flask will assume the return value is a
     valid WSGI application and convert that into a response object.
 

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/flask/testsuite/basic.py b/flask/testsuite/basic.py
index 71a1f832..be11fa6b 100644
--- a/flask/testsuite/basic.py
+++ b/flask/testsuite/basic.py
@@ -735,7 +735,17 @@ class BasicFunctionalityTestCase(FlaskTestCase):
             return 'Meh', 400, {
                 'X-Foo': 'Testing',
                 'Content-Type': 'text/plain; charset=utf-8'
+            } 
+        @app.route("/two_args")
+        def from_two_args_tuple():
+            return "Hello", {
+                'X-Foo': 'Test',
+                'Content-Type': 'text/plain; charset=utf-8'
             }
+        @app.route("/args_status")
+        def from_status_tuple():
+            return "Hi, status!", 400
+
         c = app.test_client()
         self.assert_equal(c.get('/unicode').data, u'Hällo Wörld'.encode('utf-8'))
         self.assert_equal(c.get('/string').data, u'Hällo Wörld'.encode('utf-8'))
@@ -745,6 +755,18 @@ class BasicFunctionalityTestCase(FlaskTestCase):
         self.assert_equal(rv.status_code, 400)
         self.assert_equal(rv.mimetype, 'text/plain')
 
+        rv2 = c.get("/two_args")
+        self.assert_equal(rv2.data, b'Hello')
+        self.assert_equal(rv2.headers['X-Foo'], 'Test')
+        self.assert_equal(rv2.status_code, 200)
+        self.assert_equal(rv2.mimetype, 'text/plain')
+
+        rv3 = c.get("/args_status")
+        self.assert_equal(rv3.data, b'Hi, status!')
+        self.assert_equal(rv3.status_code, 400)
+        self.assert_equal(rv3.mimetype, 'text/html')
+
+
     def test_make_response(self):
         app = flask.Flask(__name__)
         with app.test_request_context():

```

</details>

---

## Case 8 — `7bc3f6f0445e1851`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** docs: :mimetype:`application/json`
- **commit** https://github.com/pallets/flask/commit/d4b9b9854c7afb32c4c2ee27c4d98def1c8e22ca
- **doc** `docs/patterns/apierrors.rst`
- **code** `flask/json.py`
- **shared identifiers** `mimetype`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/patterns/apierrors.rst b/docs/patterns/apierrors.rst
index b06966e6..ce5c8446 100644
--- a/docs/patterns/apierrors.rst
+++ b/docs/patterns/apierrors.rst
@@ -4,7 +4,7 @@ Implementing API Exceptions
 It's very common to implement RESTful APIs on top of Flask.  One of the
 first thing that developers run into is the realization that the builtin
 exceptions are not expressive enough for APIs and that the content type of
-``text/html`` they are emitting is not very useful for API consumers.
+:mimetype:`text/html` they are emitting is not very useful for API consumers.
 
 The better solution than using ``abort`` to signal errors for invalid API
 usage is to implement your own exception type and install an error handler

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/flask/json.py b/flask/json.py
index 318fe28b..c895a446 100644
--- a/flask/json.py
+++ b/flask/json.py
@@ -200,7 +200,7 @@ def htmlsafe_dump(obj, fp, **kwargs):
 
 def jsonify(*args, **kwargs):
     """Creates a :class:`~flask.Response` with the JSON representation of
-    the given arguments with an `application/json` mimetype.  The arguments
+    the given arguments with an :mimetype:`application/json` mimetype.  The arguments
     to this function are the same as to the :class:`dict` constructor.
 
     Example usage::

```

</details>

---

## Case 9 — `82f1f152d6ae7705`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Added template tests and made config a true global
- **commit** https://github.com/pallets/flask/commit/f34c0281252bf1838e2ec24fe8b064b232a098ef
- **doc** `docs/templating.rst`
- **code** `flask/testsuite/templating.py`
- **shared identifiers** `context`, `flask`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/templating.rst b/docs/templating.rst
index 8ecf5332..166f26aa 100644
--- a/docs/templating.rst
+++ b/docs/templating.rst
@@ -38,20 +38,29 @@ by default:
 
    .. versionadded:: 0.6
 
+   .. versionchanged:: 0.10
+      This is now always available, even in imported templates.
+
 .. data:: request
    :noindex:
 
-   The current request object (:class:`flask.request`)
+   The current request object (:class:`flask.request`).  This variable is
+   unavailable if the template was rendered without an active request
+   context.
 
 .. data:: session
    :noindex:
 
-   The current session object (:class:`flask.session`)
+   The current session object (:class:`flask.session`).  This variable
+   is unavailable if the template was rendered without an active request
+   context.
 
 .. data:: g
    :noindex:
 
-   The request-bound object for global variables (:data:`flask.g`)
+   The request-bound object for global variables (:data:`flask.g`).  This
+   variable is unavailable if the template was rendered without an active
+   request context.
 
 .. function:: url_for
    :noindex:

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/flask/testsuite/templating.py b/flask/testsuite/templating.py
index 1df4292d..6345b710 100644
--- a/flask/testsuite/templating.py
+++ b/flask/testsuite/templating.py
@@ -37,6 +37,18 @@ class TemplatingTestCase(FlaskTestCase):
         rv = app.test_client().get('/')
         self.assert_equal(rv.data, '42')
 
+    def test_request_less_rendering(self):
+        app = flask.Flask(__name__)
+        app.config['WORLD_NAME'] = 'Special World'
+        @app.context_processor
+        def context_processor():
+            return dict(foo=42)
+
+        with app.app_context():
+            rv = flask.render_template_string('Hello {{ config.WORLD_NAME }} '
+                                              '{{ foo }}')
+            self.assert_equal(rv, 'Hello Special World 42')
+
     def test_standard_context(self):
         app = flask.Flask(__name__)
         app.secret_key = 'development key'

```

</details>

---

## Case 10 — `2d886fc23ef46f71`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** move send_file and send_from_directory to Werkzeug
- **commit** https://github.com/pallets/flask/commit/dc11cdb4a4627b9f8c79e47e39aa7e1357151896
- **doc** `docs/config.rst`
- **code** `src/flask/app.py`
- **shared identifiers** `timedelta`, `seconds`, `hours`, `send`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/config.rst b/docs/config.rst
index 70800c94..768cf60d 100644
--- a/docs/config.rst
+++ b/docs/config.rst
@@ -265,11 +265,16 @@ The following configuration values are used internally by Flask:
 .. py:data:: SEND_FILE_MAX_AGE_DEFAULT
 
     When serving files, set the cache control max age to this number of
-    seconds.  Can either be a :class:`datetime.timedelta` or an ``int``.
+    seconds. Can be a :class:`datetime.timedelta` or an ``int``.
     Override this value on a per-file basis using
-    :meth:`~flask.Flask.get_send_file_max_age` on the application or blueprint.
+    :meth:`~flask.Flask.get_send_file_max_age` on the application or
+    blueprint.
 
-    Default: ``timedelta(hours=12)`` (``43200`` seconds)
+    If ``None``, ``send_file`` tells the browser to use conditional
+    requests will be used instead of a timed cache, which is usually
+    preferable.
+
+    Default: ``None``
 
 .. py:data:: SERVER_NAME
 

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/src/flask/app.py b/src/flask/app.py
index eaeb613e..34ca3700 100644
--- a/src/flask/app.py
+++ b/src/flask/app.py
@@ -55,9 +55,10 @@ from .wrappers import Response
 
 
 def _make_timedelta(value):
-    if not isinstance(value, timedelta):
-        return timedelta(seconds=value)
-    return value
+    if value is None or isinstance(value, timedelta):
+        return value
+
+    return timedelta(seconds=value)
 
 
 class Flask(Scaffold):
@@ -234,13 +235,16 @@ class Flask(Scaffold):
         "PERMANENT_SESSION_LIFETIME", get_converter=_make_timedelta
     )
 
-    #: A :class:`~datetime.timedelta` which is used as default cache_timeout
-    #: for the :func:`send_file` functions. The default is 12 hours.
+    #: A :class:`~datetime.timedelta` or number of seconds which is used
+    #: as the default ``max_age`` for :func:`send_file`. The default is
+    #: ``None``, which tells the browser to use conditional requests
+    #: instead of a timed cache.
     #:
-    #: This attribute can also be configured from the config with the
-    #: ``SEND_FILE_MAX_AGE_DEFAULT`` configuration key. This configuration
-    #: variable can also be set with an integer value used as seconds.
-    #: Defaults to ``timedelta(hours=12)``
+    #: Configured with the :data:`SEND_FILE_MAX_AGE_DEFAULT`
+    #: configuration key.
+    #:
+    #: .. versionchanged:: 2.0
+    #:     Defaults to ``None`` instead of 12 hours.
     send_file_max_age_default = ConfigAttribute(
         "SEND_FILE_MAX_AGE_DEFAULT", get_converter=_make_timedelta
     )
@@ -297,7 +301,7 @@ class Flask(Scaffold):
             "SESSION_COOKIE_SAMESITE": None,
             "SESSION_REFRESH_EACH_REQUEST": True,
             "MAX_CONTENT_LENGTH": None,
-            "SEND_FILE_MAX_AGE_DEFAULT": timedelta(hours=12),
+            "SEND_FILE_MAX_AGE_DEFAULT": None,
             "TRAP_BAD_REQUEST_ERRORS": None,
             "TRAP_HTTP_EXCEPTIONS": False,
             "EXPLAIN_TEMPLATE_LOADING": False,

```

</details>

---

## Case 11 — `df12f69b6ee1bb91`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Remove python 2.6 and 3.3 everywhere. (#2583)
- **commit** https://github.com/pallets/flask/commit/60eecb547d8af9916c55163c7356999ca2d5ffb9
- **doc** `CONTRIBUTING.rst`
- **code** `setup.py`
- **shared identifiers** `ver:2.6`, `ver:3.3`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/CONTRIBUTING.rst b/CONTRIBUTING.rst
index f6ff7015..ef02b732 100644
--- a/CONTRIBUTING.rst
+++ b/CONTRIBUTING.rst
@@ -109,8 +109,8 @@ depends on which part of Flask you're working on. Travis-CI will run the full
 suite when you submit your pull request.
 
 The full test suite takes a long time to run because it tests multiple
-combinations of Python and dependencies. You need to have Python 2.6, 2.7, 3.3,
-3.4, 3.5 3.6, and PyPy 2.7 installed to run all of the environments. Then run::
+combinations of Python and dependencies. You need to have Python 2.7, 3.4,
+3.5 3.6, and PyPy 2.7 installed to run all of the environments. Then run::
 
     tox
 

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/setup.py b/setup.py
index bb2aab41..bf2d0bc6 100644
--- a/setup.py
+++ b/setup.py
@@ -95,10 +95,8 @@ setup(
         'Operating System :: OS Independent',
         'Programming Language :: Python',
         'Programming Language :: Python :: 2',
-        'Programming Language :: Python :: 2.6',
         'Programming Language :: Python :: 2.7',
         'Programming Language :: Python :: 3',
-        'Programming Language :: Python :: 3.3',
         'Programming Language :: Python :: 3.4',
         'Programming Language :: Python :: 3.5',
         'Programming Language :: Python :: 3.6',

```

</details>

---

## Case 12 — `d84f6373eb5e7d0b`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Implemented experimental JSON based sessions
- **commit** https://github.com/pallets/flask/commit/4df3bf2058954624f9376fd16774a769299dc40a
- **doc** `docs/api.rst`
- **code** `flask/testsuite/basic.py`
- **shared identifiers** `session`

**VERDICT: `new`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/api.rst b/docs/api.rst
index 8a7b5ce0..e808e771 100644
--- a/docs/api.rst
+++ b/docs/api.rst
@@ -215,6 +215,13 @@ implementation that Flask is using.
 .. autoclass:: SecureCookieSessionInterface
    :members:
 
+.. autoclass:: UpgradeSecureCookieSessionInterface
+
+.. autoclass:: SecureCookieSession
+   :members:
+
+.. autoclass:: UpgradeSecureCookieSession
+
 .. autoclass:: NullSession
    :members:
 

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/flask/testsuite/basic.py b/flask/testsuite/basic.py
index 388b5a8e..3d758b3a 100644
--- a/flask/testsuite/basic.py
+++ b/flask/testsuite/basic.py
@@ -13,6 +13,7 @@ from __future__ import with_statement
 
 import re
 import flask
+import pickle
 import unittest
 from datetime import datetime
 from threading import Thread
@@ -297,6 +298,31 @@ class BasicFunctionalityTestCase(FlaskTestCase):
         self.assert_equal(c.get('/').data, 'None')
         self.assert_equal(c.get('/').data, '42')
 
+    def test_session_special_types(self):
+        app = flask.Flask(__name__)
+        app.secret_key = 'development-key'
+        app.testing = True
+        now = datetime.utcnow().replace(microsecond=0)
+
+        @app.after_request
+        def modify_session(response):
+            flask.session['m'] = flask.Markup('Hello!')
+            flask.session['dt'] = now
+            flask.session['t'] = (1, 2, 3)
+            return response
+
+        @app.route('/')
+        def dump_session_contents():
+            return pickle.dumps(dict(flask.session))
+
+        c = app.test_client()
+        c.get('/')
+        rv = pickle.loads(c.get('/').data)
+        self.assert_equal(rv['m'], flask.Markup('Hello!'))
+        self.assert_equal(type(rv['m']), flask.Markup)
+        self.assert_equal(rv['dt'], now)
+        self.assert_equal(rv['t'], (1, 2, 3))
+
     def test_flashes(self):
         app = flask.Flask(__name__)
         app.secret_key = 'testkey'

```

</details>

---

## Case 13 — `e738c0254959063b`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Greatly refactored click integration and documented it a bit more.
- **commit** https://github.com/pallets/flask/commit/3569fc24415f8bac7b269ec041bd1f6bc23038ce
- **doc** `docs/api.rst`
- **code** `setup.py`
- **shared identifiers** `click`

**VERDICT: `new`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/api.rst b/docs/api.rst
index 6c9f7414..945082bc 100644
--- a/docs/api.rst
+++ b/docs/api.rst
@@ -753,3 +753,30 @@ Full example::
 
 .. versionadded:: 0.8
    The `provide_automatic_options` functionality was added.
+
+Command Line Interface
+----------------------
+
+.. currentmodule:: flask.cli
+
+.. autoclass:: FlaskGroup
+   :members:
+
+.. autoclass:: ScriptInfo
+   :members:
+
+.. autofunction:: pass_script_info
+
+.. autofunction:: without_appcontext
+
+.. autofunction:: script_info_option
+
+   A special decorator that informs a click callback to be passed the
+   script info object as first argument.  This is normally not useful
+   unless you implement very special commands like the run command which
+   does not want the application to be loaded yet.  This can be combined
+   with the :func:`without_appcontext` decorator.
+
+.. autodata:: run_command
+
+.. autodata:: shell_command

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/setup.py b/setup.py
index 196eca4c..1df413b2 100644
--- a/setup.py
+++ b/setup.py
@@ -96,7 +96,7 @@ setup(
         'Werkzeug>=0.7',
         'Jinja2>=2.4',
         'itsdangerous>=0.21',
-        'click',
+        'click>=0.6',
     ],
     classifiers=[
         'Development Status :: 4 - Beta',

```

</details>

---

## Case 14 — `4f45dc221b53f080`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** clean up FLASK_ENV docs [ci skip]
- **commit** https://github.com/pallets/flask/commit/87c2e121e0bf32f5234eabbf4773a82f9d5523d2
- **doc** `docs/config.rst`
- **code** `flask/helpers.py`
- **shared identifiers** `development`, `environment`, `flask_debug`, `production`, `flask_env`, `otherwise`, `variable`, `envvar`, `flask`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/config.rst b/docs/config.rst
index e8da82d1..777a1d28 100644
--- a/docs/config.rst
+++ b/docs/config.rst
@@ -20,6 +20,7 @@ object.  This is the place where Flask itself puts certain configuration
 values and also where extensions can put their configuration values.  But
 this is also where you can have your own configuration.
 
+
 Configuration Basics
 --------------------
 
@@ -42,52 +43,77 @@ method::
         SECRET_KEY=b'_5#y2L"F4Q8z\n\xec]/'
     )
 
+
 Environment and Debug Features
 ------------------------------
 
-Some values are special in that they can show unexpected behavior when
-changed late.  In particular that applies to the Flask environment and
-debug mode.
+The :data:`ENV` and :data:`DEBUG` config values are special because they
+may behave inconsistently if changed after the app has begun setting up.
+In order to set the environment and debug mode reliably, Flask uses
+environment variables.
 
-If you use the :command:`flask` script to start a local development server
-for instance you should tell Flask that you want to work in the
-development environment.  For safety reasons we default the flask
-environment to production mode instead of development.  This is done
-because development mode can turn on potentially unsafe features such as
-the debugger by default.
+The environment is used to indicate to Flask, extensions, and other
+programs, like Sentry, what context Flask is running in. It is
+controlled with the :envvar:`FLASK_ENV` environment variable and
+defaults to ``production``.
 
-To control the environment and such fundamental features Flask provides
-the two environment variables :envvar:`FLASK_ENV` and :envvar:`FLASK_DEBUG`.
-In versions of Flask older than 1.0 the :envvar:`FLASK_ENV` environment
-variable did not exist.
+Setting :envvar:`FLASK_ENV` to ``development`` will enable debug mode.
+``flask run`` will use the interactive debugger and reloader by default
+in debug mode. To control this separately from the environment, use the
+:envvar:`FLASK_DEBUG` flag.
+
+.. versionchanged:: 1.0
+    Added :envvar:`FLASK_ENV` to control the environment separately
+    from debug mode. The development environment enables debug mode.
 
-The most common way to switch Flask to development mode is to tell it to
-work on the ``development`` environment::
+To switch Flask to the development environment and enable debug mode,
+set :envvar:`FLASK_ENV`::
 
-$ export FLASK_ENV=development
-$ flask run
+    $ export FLASK_ENV=development
+    $ flask run
 
-(On Windows you need to use ``set`` instead of ``export``).
+(On Windows, use ``set`` instead of ``export``.)
+
+Using the environment variables as described above is recommended. While
+it is possible to set :data:`ENV` and :data:`DEBUG` in your config or
+code, this is strongly discouraged. They can't be read early by the
+``flask`` command, and some systems or extensions may have already
+configured themselves based on a previous value.
 
-While you can attempt to flip the environment and debug flag separately in
-the Flask config from the config file this is strongly discouraged as
-those flags are often loaded early and changing them late might not apply
-to all systems and extensions.
 
 Builtin Configuration Values
 ----------------------------
 
 The following configuration values are used internally by Flask:
 
+.. py:data:: ENV
+
+    What environment the app is running in. Flask and extensions may
+    enable behaviors based on the environment, such as enabling debug
+    mode. The :attr:`~flask.Flask.env` attribute maps to this config
+    key. This is set by the :envvar:`FLASK_ENV` environment variable and
+    may not behave as expected if set in code.
+
+    **Do not enable development when deploying in production.**
+
+    Default: ``'production'``
+
+    .. versionadded:: 1.0
+
 .. py:data:: DEBUG
 
-    Enable debug mode. When using the development server with ``flask run`` or
-    ``app.run``, an interactive debugger will
```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/flask/helpers.py b/flask/helpers.py
index 705ea3e1..922509cf 100644
--- a/flask/helpers.py
+++ b/flask/helpers.py
@@ -47,19 +47,24 @@ _os_alt_seps = list(sep for sep in [os.path.sep, os.path.altsep]
 
 
 def get_env():
-    val = os.environ.get('FLASK_ENV')
-    if not val:
-        val = 'production'
-    return val
+    """Get the environment the app is running in, indicated by the
+    :envvar:`FLASK_ENV` environment variable. The default is
+    ``'production'``.
+    """
+    return os.environ.get('FLASK_ENV') or 'production'
 
 
 def get_debug_flag():
+    """Get whether debug mode should be enabled for the app, indicated
+    by the :envvar:`FLASK_DEBUG` environment variable. The default is
+    ``True`` if :func:`.get_env` returns ``'development'``, or ``False``
+    otherwise.
+    """
     val = os.environ.get('FLASK_DEBUG')
+
     if not val:
-        env = get_env()
-        if env == 'development':
-            return True
-        return False
+        return get_env() == 'development'
+
     return val.lower() not in ('0', 'false', 'no')
 
 

```

</details>

---

## Case 15 — `88fabe4287e1317b`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** add json provider interface
- **commit** https://github.com/pallets/flask/commit/69f9845ef2da3051d74d4dade3e88ccf5b2ee3de
- **doc** `docs/config.rst`
- **code** `src/flask/blueprints.py`
- **shared identifiers** `json`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/config.rst b/docs/config.rst
index ebe29d05..6111931e 100644
--- a/docs/config.rst
+++ b/docs/config.rst
@@ -301,6 +301,10 @@ The following configuration values are used internally by Flask:
 
     Default: ``True``
 
+    .. deprecated:: 2.2
+        Will be removed in Flask 2.3. Set ``app.json.ensure_ascii``
+        instead.
+
 .. py:data:: JSON_SORT_KEYS
 
     Sort the keys of JSON objects alphabetically. This is useful for caching
@@ -310,19 +314,30 @@ The following configuration values are used internally by Flask:
 
     Default: ``True``
 
+    .. deprecated:: 2.2
+        Will be removed in Flask 2.3. Set ``app.json.sort_keys``
+        instead.
+
 .. py:data:: JSONIFY_PRETTYPRINT_REGULAR
 
-    ``jsonify`` responses will be output with newlines, spaces, and indentation
-    for easier reading by humans. Always enabled in debug mode.
+    :func:`~flask.jsonify` responses will be output with newlines,
+    spaces, and indentation for easier reading by humans. Always enabled
+    in debug mode.
 
     Default: ``False``
 
+    .. deprecated:: 2.2
+        Will be removed in Flask 2.3. Set ``app.json.compact`` instead.
+
 .. py:data:: JSONIFY_MIMETYPE
 
     The mimetype of ``jsonify`` responses.
 
     Default: ``'application/json'``
 
+    .. deprecated:: 2.2
+        Will be removed in Flask 2.3. Set ``app.json.mimetype`` instead.
+
 .. py:data:: TEMPLATES_AUTO_RELOAD
 
     Reload templates when they are changed. If not set, it will be enabled in
@@ -387,6 +402,12 @@ The following configuration values are used internally by Flask:
 .. versionchanged:: 2.2
     Removed ``PRESERVE_CONTEXT_ON_EXCEPTION``.
 
+.. versionchanged:: 2.2
+    ``JSON_AS_ASCII``, ``JSON_SORT_KEYS``,
+    ``JSONIFY_MIMETYPE``, and ``JSONIFY_PRETTYPRINT_REGULAR`` will be
+    removed in Flask 2.3. The default ``app.json`` provider has
+    equivalent attributes instead.
+
 
 Configuring from Python Files
 -----------------------------

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/src/flask/blueprints.py b/src/flask/blueprints.py
index 6deda47e..17885136 100644
--- a/src/flask/blueprints.py
+++ b/src/flask/blueprints.py
@@ -174,10 +174,16 @@ class Blueprint(Scaffold):
 
     #: Blueprint local JSON encoder class to use. Set to ``None`` to use
     #: the app's :class:`~flask.Flask.json_encoder`.
-    json_encoder = None
+    #:
+    #: .. deprecated:: 2.2
+    #:      Will be removed in Flask 2.3.
+    json_encoder: None = None
     #: Blueprint local JSON decoder class to use. Set to ``None`` to use
     #: the app's :class:`~flask.Flask.json_decoder`.
-    json_decoder = None
+    #:
+    #: .. deprecated:: 2.2
+    #:      Will be removed in Flask 2.3.
+    json_decoder: None = None
 
     def __init__(
         self,

```

</details>

---

## Case 16 — `b7170d6cc2b063e8`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** flask.g is now on the app context and not the request context
- **commit** https://github.com/pallets/flask/commit/1949c4a9abc174bf29620f6dd8ceab9ed3ace2eb
- **doc** `docs/upgrading.rst`
- **code** `flask/app.py`
- **shared identifiers** `app_ctx_globals_class`, `request_globals_class`, `attribute`, `context`, `globals`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/upgrading.rst b/docs/upgrading.rst
index 1f67df05..1d9239f5 100644
--- a/docs/upgrading.rst
+++ b/docs/upgrading.rst
@@ -36,6 +36,13 @@ extensions for tuples and strings with HTML markup.
 In order to not break people's sessions it is possible to continue using
 the old session system by using the `Flask-OldSessions_` extension.
 
+Flask also started storing the :data:`flask.g` object on the application
+context instead of the request context.  This change should be transparent
+for you but it means that you now can store things on the ``g`` object
+when there is no request context yet but an application context.  The old
+``flask.Flask.request_globals_class`` attribute was renamed to
+:attr:`flask.Flask.app_ctx_globals_class`.
+
 .. _Flask-OldSessions: http://packages.python.org/Flask-OldSessions/
 
 Version 0.9

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/flask/app.py b/flask/app.py
index 9d291b3a..902c2ba8 100644
--- a/flask/app.py
+++ b/flask/app.py
@@ -28,7 +28,7 @@ from .helpers import _PackageBoundObject, url_for, get_flashed_messages, \
 from . import json
 from .wrappers import Request, Response
 from .config import ConfigAttribute, Config
-from .ctx import RequestContext, AppContext, _RequestGlobals
+from .ctx import RequestContext, AppContext, _AppCtxGlobals
 from .globals import _request_ctx_stack, request
 from .sessions import SecureCookieSessionInterface
 from .module import blueprint_is_module
@@ -157,8 +157,24 @@ class Flask(_PackageBoundObject):
     #: 3. Return None instead of AttributeError on expected attributes.
     #: 4. Raise exception if an unexpected attr is set, a "controlled" flask.g.
     #:
-    #: .. versionadded:: 0.9
-    request_globals_class = _RequestGlobals
+    #: In Flask 0.9 this property was called `request_globals_class` but it
+    #: was changed in 0.10 to :attr:`app_ctx_globals_class` because the
+    #: flask.g object is not application context scoped.
+    #:
+    #: .. versionadded:: 0.10
+    app_ctx_globals_class = _AppCtxGlobals
+
+    # Backwards compatibility support
+    def _get_request_globals_class(self):
+        return self.app_ctx_globals_class
+    def _set_request_globals_class(self, value):
+        from warnings import warn
+        warn(DeprecationWarning('request_globals_class attribute is now '
+                                'called app_ctx_globals_class'))
+        self.app_ctx_globals_class = value
+    request_globals_class = property(_get_request_globals_class,
+                                     _set_request_globals_class)
+    del _get_request_globals_class, _set_request_globals_class
 
     #: The debug flag.  Set this to `True` to enable debugging of the
     #: application.  In debug mode the debugger will kick in when an unhandled

```

</details>

---

## Case 17 — `b59ac3fdadd7d0eb`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Use American English for "behavior" in docs.
- **commit** https://github.com/pallets/flask/commit/a3cb2a33829ee517530d30cd920e5d652b358086
- **doc** `docs/templating.rst`
- **code** `flask/helpers.py`
- **shared identifiers** `behaviour`, `behavior`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/templating.rst b/docs/templating.rst
index d4878cdb..8ecf5332 100644
--- a/docs/templating.rst
+++ b/docs/templating.rst
@@ -63,7 +63,7 @@ by default:
 
    The :func:`flask.get_flashed_messages` function.
 
-.. admonition:: The Jinja Context Behaviour
+.. admonition:: The Jinja Context Behavior
 
    These variables are added to the context of variables, they are not
    global variables.  The difference is that by default these will not

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/flask/helpers.py b/flask/helpers.py
index 1be2daf7..238d7df7 100644
--- a/flask/helpers.py
+++ b/flask/helpers.py
@@ -60,7 +60,7 @@ def _assert_have_json():
         raise RuntimeError('simplejson not installed')
 
 
-# figure out if simplejson escapes slashes.  This behaviour was changed
+# figure out if simplejson escapes slashes.  This behavior was changed
 # from one version to another without reason.
 if not json_available or '\\/' not in json.dumps('/'):
 
@@ -121,7 +121,7 @@ def jsonify(*args, **kwargs):
 
     .. versionadded:: 0.9
         If the ``padded`` argument is true, the JSON object will be padded
-        for JSONP calls and the response mimetype will be changed to 
+        for JSONP calls and the response mimetype will be changed to
         ``application/javascript``. By default, the request arguments ``callback``
         and ``jsonp`` will be used as the name for the callback function.
         This will work with jQuery and most other JavaScript libraries
@@ -387,7 +387,7 @@ def send_file(filename_or_fp, mimetype=None, as_attachment=False,
 
     .. versionadded:: 0.5
        The `add_etags`, `cache_timeout` and `conditional` parameters were
-       added.  The default behaviour is now to attach etags.
+       added.  The default behavior is now to attach etags.
 
     .. versionchanged:: 0.7
        mimetype guessing and etag support for file objects was
@@ -422,7 +422,7 @@ def send_file(filename_or_fp, mimetype=None, as_attachment=False,
         file = filename_or_fp
         filename = getattr(file, 'name', None)
 
-        # XXX: this behaviour is now deprecated because it was unreliable.
+        # XXX: this behavior is now deprecated because it was unreliable.
         # removed in Flask 1.0
         if not attachment_filename and not mimetype \
            and isinstance(filename, basestring):
@@ -433,7 +433,7 @@ def send_file(filename_or_fp, mimetype=None, as_attachment=False,
         if add_etags:
             warn(DeprecationWarning('In future flask releases etags will no '
                 'longer be generated for file objects passed to the send_file '
-                'function because this behaviour was unreliable.  Pass '
+                'function because this behavior was unreliable.  Pass '
                 'filenames instead if possible, otherwise attach an etag '
                 'yourself based on another value'), stacklevel=2)
 

```

</details>

---

## Case 18 — `185e5d908da6574c`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** docs: ``True``, ``False`` and ``None``
- **commit** https://github.com/pallets/flask/commit/8284217593d5ea3d4bdeaed1e146fa94578b7999
- **doc** `docs/patterns/distribute.rst`
- **code** `flask/helpers.py`
- **shared identifiers** `parameter`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/patterns/distribute.rst b/docs/patterns/distribute.rst
index aa53e685..466032dc 100644
--- a/docs/patterns/distribute.rst
+++ b/docs/patterns/distribute.rst
@@ -109,7 +109,7 @@ your tarball::
 
 Don't forget that even if you enlist them in your `MANIFEST.in` file, they
 won't be installed for you unless you set the `include_package_data`
-parameter of the `setup` function to `True`!
+parameter of the `setup` function to ``True``!
 
 
 Declaring Dependencies

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/flask/helpers.py b/flask/helpers.py
index aaed81c4..828e8f67 100644
--- a/flask/helpers.py
+++ b/flask/helpers.py
@@ -188,7 +188,7 @@ def url_for(endpoint, **values):
 
     Variable arguments that are unknown to the target endpoint are appended
     to the generated URL as query arguments.  If the value of a query argument
-    is `None`, the whole pair is skipped.  In case blueprints are active
+    is ``None``, the whole pair is skipped.  In case blueprints are active
     you can shortcut references to the same blueprint by prefixing the
     local endpoint with a dot (``.``).
 
@@ -203,7 +203,7 @@ def url_for(endpoint, **values):
     function results in a :exc:`~werkzeug.routing.BuildError` when the current
     app does not have a URL for the given endpoint and values.  When it does, the
     :data:`~flask.current_app` calls its :attr:`~Flask.url_build_error_handlers` if
-    it is not `None`, which can return a string to use as the result of
+    it is not ``None``, which can return a string to use as the result of
     `url_for` (instead of `url_for`'s default to raise the
     :exc:`~werkzeug.routing.BuildError` exception) or re-raise the exception.
     An example::
@@ -244,11 +244,11 @@ def url_for(endpoint, **values):
 
     :param endpoint: the endpoint of the URL (name of the function)
     :param values: the variable arguments of the URL rule
-    :param _external: if set to `True`, an absolute URL is generated. Server
+    :param _external: if set to ``True``, an absolute URL is generated. Server
       address can be changed via `SERVER_NAME` configuration variable which
       defaults to `localhost`.
     :param _scheme: a string specifying the desired URL scheme. The `_external`
-      parameter must be set to `True` or a `ValueError` is raised. The default
+      parameter must be set to ``True`` or a `ValueError` is raised. The default
       behavior uses the same scheme as the current request, or
       ``PREFERRED_URL_SCHEME`` from the :ref:`app configuration <config>` if no
       request context is available. As of Werkzeug 0.10, this also can be set
@@ -376,7 +376,7 @@ def get_flashed_messages(with_categories=False, category_filter=[]):
     """Pulls all flashed messages from the session and returns them.
     Further calls in the same request to the function will return
     the same messages.  By default just the messages are returned,
-    but when `with_categories` is set to `True`, the return value will
+    but when `with_categories` is set to ``True``, the return value will
     be a list of tuples in the form ``(category, message)`` instead.
 
     Filter the flashed messages to one or more categories by providing those
@@ -385,7 +385,7 @@ def get_flashed_messages(with_categories=False, category_filter=[]):
     arguments are distinct:
 
     * `with_categories` controls whether categories are returned with message
-      text (`True` gives a tuple, where `False` gives just the message text).
+      text (``True`` gives a tuple, where ``False`` gives just the message text).
     * `category_filter` filters the messages down to only those matching the
       provided categories.
 
@@ -397,7 +397,7 @@ def get_flashed_messages(with_categories=False, category_filter=[]):
     .. versionchanged:: 0.9
         `category_filter` parameter added.
 
-    :param with_categories: set to `True` to also receive categories.
+    :param with_categories: set to ``True`` to also receive categories.
     :param category_filter: whitelist of categories to limit return values
     """
     flashes = _request_ctx_stack.top.flashes
@@ -459,14 +459,14 @@ def send_file(filename_or_fp, mimetype=None, as_attachment=False,
                            of data to send before calling :func:`send_file`.
     :param mimetype: the mimetype of the file if provided, otherwise
                      auto detection happens.
-    :param as_attachment: set to `True` if you want to send this file with
+    :param as_a
```

</details>

---

## Case 19 — `b6ef6021e4dff8ee`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Add Support for FLASK_ENV (#2570)
- **commit** https://github.com/pallets/flask/commit/2433522d2967b8a5e46f16de587a8fac5088a47c
- **doc** `docs/server.rst`
- **code** `flask/helpers.py`
- **shared identifiers** `development`, `flask_env`, `flask`

**VERDICT: `new`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/server.rst b/docs/server.rst
index f8332ebf..7e03d8df 100644
--- a/docs/server.rst
+++ b/docs/server.rst
@@ -12,12 +12,13 @@ but you can also continue using the :meth:`Flask.run` method.
 Command Line
 ------------
 
-The :command:`flask` command line script (:ref:`cli`) is strongly recommended for
-development because it provides a superior reload experience due to how it
-loads the application.  The basic usage is like this::
+The :command:`flask` command line script (:ref:`cli`) is strongly
+recommended for development because it provides a superior reload
+experience due to how it loads the application.  The basic usage is like
+this::
 
     $ export FLASK_APP=my_application
-    $ export FLASK_DEBUG=1
+    $ export FLASK_ENV=development
     $ flask run
 
 This will enable the debugger, the reloader and then start the server on
@@ -29,6 +30,13 @@ disabled::
 
     $ flask run --no-reload
 
+.. note::
+
+    On older Flask version (before 1.0) the :envvar:`FLASK_ENV`
+    environment variable is not supported and you need to enable the
+    debug mode separately by setting the :envvar:`FLASK_DEBUG` environment
+    variable to ``1``.
+
 In Code
 -------
 

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/flask/helpers.py b/flask/helpers.py
index 412d9caf..705ea3e1 100644
--- a/flask/helpers.py
+++ b/flask/helpers.py
@@ -46,10 +46,20 @@ _os_alt_seps = list(sep for sep in [os.path.sep, os.path.altsep]
                     if sep not in (None, '/'))
 
 
-def get_debug_flag(default=None):
+def get_env():
+    val = os.environ.get('FLASK_ENV')
+    if not val:
+        val = 'production'
+    return val
+
+
+def get_debug_flag():
     val = os.environ.get('FLASK_DEBUG')
     if not val:
-        return default
+        env = get_env()
+        if env == 'development':
+            return True
+        return False
     return val.lower() not in ('0', 'false', 'no')
 
 

```

</details>

---

## Case 20 — `feee5ce88c1d17c4`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Fixed some smaller things in the docs
- **commit** https://github.com/pallets/flask/commit/d26af4fd6dd71793cf6373c1c18c82349494e0aa
- **doc** `docs/appcontext.rst`
- **code** `flask/__init__.py`
- **shared identifiers** `context`

**VERDICT: `unrelated`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/appcontext.rst b/docs/appcontext.rst
index c331ffa5..e9e1ad8f 100644
--- a/docs/appcontext.rst
+++ b/docs/appcontext.rst
@@ -1,4 +1,4 @@
-.. _app_context:
+.. _app-context:
 
 The Application Context
 =======================

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/flask/__init__.py b/flask/__init__.py
index f35ef328..b91f9395 100644
--- a/flask/__init__.py
+++ b/flask/__init__.py
@@ -25,7 +25,7 @@ from .helpers import url_for, jsonify, json_available, flash, \
     get_template_attribute, make_response, safe_join
 from .globals import current_app, g, request, session, _request_ctx_stack, \
      _app_ctx_stack
-from .ctx import has_request_context
+from .ctx import has_request_context, has_app_context
 from .module import Module
 from .blueprints import Blueprint
 from .templating import render_template, render_template_string

```

</details>

---

## Case 21 — `a216d010252a9c48`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** document python 2.6 minimum requirement, remove all stuff that refers to 2.5
- **commit** https://github.com/pallets/flask/commit/40fad2ece80e8bf6784e137028645fa66a3cd9c2
- **doc** `docs/installation.rst`
- **code** `flask/wrappers.py`
- **shared identifiers** `ver:2.6`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/installation.rst b/docs/installation.rst
index 5e4673dd..16475383 100644
--- a/docs/installation.rst
+++ b/docs/installation.rst
@@ -13,7 +13,7 @@ So how do you get all that on your computer quickly?  There are many ways you
 could do that, but the most kick-ass method is virtualenv, so let's have a look
 at that first.
 
-You will need Python 2.5 or higher to get started, so be sure to have an
+You will need Python 2.6 or higher to get started, so be sure to have an
 up-to-date Python 2.x installation.  Python 3.x is not supported.
 
 .. _virtualenv:

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/flask/wrappers.py b/flask/wrappers.py
index a56fe5d7..d348ee0a 100644
--- a/flask/wrappers.py
+++ b/flask/wrappers.py
@@ -92,8 +92,6 @@ class Request(RequestBase):
     def json(self):
         """If the mimetype is `application/json` this will contain the
         parsed JSON data.  Otherwise this will be `None`.
-
-        This requires Python 2.6 or an installed version of simplejson.
         """
         if self.mimetype == 'application/json':
             request_charset = self.mimetype_params.get('charset')

```

</details>

---

## Case 22 — `d9321319cda0580f`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Add Blueprint level cli command registration
- **commit** https://github.com/pallets/flask/commit/ec1ccd753084c6ff3215b9a64ba46d6af56715bd
- **doc** `docs/cli.rst`
- **code** `flask/app.py`
- **shared identifiers** `group`

**VERDICT: `new`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/cli.rst b/docs/cli.rst
index 5a05be9f..211effb2 100644
--- a/docs/cli.rst
+++ b/docs/cli.rst
@@ -310,10 +310,66 @@ group. This is useful if you want to organize multiple related commands. ::
 
     $ flask user create demo
 
+
 See :ref:`testing-cli` for an overview of how to test your custom
 commands.
 
 
+Registering Commands with Blueprints
+~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
+
+If your application uses blueprints, you can optionally register CLI
+commands directly onto them. When your blueprint is registered onto your
+application, the associated commands will be available to the ``flask``
+command. By default, those commands will be nested in a group matching
+the name of the blueprint.
+
+.. code-block:: python
+
+    from flask import Blueprint
+
+    bp = Blueprint('students', __name__)
+
+    @bp.cli.command('create')
+    @click.argument('name')
+    def create(name):
+        ...
+
+    app.register_blueprint(bp)
+
+.. code-block:: text
+
+    $ flask students create alice
+
+You can alter the group name by specifying the ``cli_group`` parameter
+when creating the :class:`Blueprint` object, or later with
+:meth:`app.register_blueprint(bp, cli_group='...') <Flask.register_blueprint>`.
+The following are equivalent:
+
+.. code-block:: python
+
+    bp = Blueprint('students', __name__, cli_group='other')
+    # or
+    app.register_blueprint(bp, cli_group='other')
+
+.. code-block:: text
+
+    $ flask other create alice
+
+Specifying ``cli_group=None`` will remove the nesting and merge the
+commands directly to the application's level:
+
+.. code-block:: python
+
+    bp = Blueprint('students', __name__, cli_group=None)
+    # or
+    app.register_blueprint(bp, cli_group=None)
+
+.. code-block:: text
+
+    $ flask create alice
+
+
 Application Context
 ~~~~~~~~~~~~~~~~~~~
 

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/flask/app.py b/flask/app.py
index b0b2bc26..7a2c7dc4 100644
--- a/flask/app.py
+++ b/flask/app.py
@@ -600,13 +600,9 @@ class Flask(_PackageBoundObject):
                 view_func=self.send_static_file,
             )
 
-        #: The click command line context for this application.  Commands
-        #: registered here show up in the :command:`flask` command once the
-        #: application has been discovered.  The default commands are
-        #: provided by Flask itself and can be overridden.
-        #:
-        #: This is an instance of a :class:`click.Group` object.
-        self.cli = cli.AppGroup(self.name)
+        # Set the name of the Click group in case someone wants to add
+        # the app's commands to another CLI tool.
+        self.cli.name = self.name
 
     @locked_cached_property
     def name(self):

```

</details>

---

## Case 23 — `7e9da67c9f96d72d`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** s/1.0/0.11/ in versionadded/versionchanged markers
- **commit** https://github.com/pallets/flask/commit/c5900a1adf8e868eca745225f3cf32218cdbbb23
- **doc** `docs/cli.rst`
- **code** `flask/config.py`
- **shared identifiers** `versionadded`, `ver:0.11`, `ver:1.0`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/cli.rst b/docs/cli.rst
index 141176ce..d3269c57 100644
--- a/docs/cli.rst
+++ b/docs/cli.rst
@@ -3,7 +3,7 @@
 Command Line Interface
 ======================
 
-.. versionadded:: 1.0
+.. versionadded:: 0.11
 
 .. currentmodule:: flask
 

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/flask/config.py b/flask/config.py
index 6f643a99..426a23a2 100644
--- a/flask/config.py
+++ b/flask/config.py
@@ -176,7 +176,7 @@ class Config(dict):
         :param silent: set to ``True`` if you want silent failure for missing
                        files.
 
-        .. versionadded:: 1.0
+        .. versionadded:: 0.11
         """
         filename = os.path.join(self.root_path, filename)
 
@@ -194,7 +194,7 @@ class Config(dict):
         """Updates the config like :meth:`update` ignoring items with non-upper
         keys.
 
-        .. versionadded:: 1.0
+        .. versionadded:: 0.11
         """
         mappings = []
         if len(mapping) == 1:
@@ -239,7 +239,7 @@ class Config(dict):
         :param trim_namespace: a flag indicating if the keys of the resulting
                           dictionary should not include the namespace
 
-        .. versionadded:: 1.0
+        .. versionadded:: 0.11
         """
         rv = {}
         for k, v in iteritems(self):

```

</details>

---

## Case 24 — `ff8fa262518d2768`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Added SESSION_REFRESH_EACH_REQUEST config option.
- **commit** https://github.com/pallets/flask/commit/d1d835c02302884b2db1cab099b3ea6a84f41d32
- **doc** `docs/config.rst`
- **code** `flask/sessions.py`
- **shared identifiers** `session_refresh_each_request`, `versionadded`, `permanent`, `modified`, `sessions`, `refresh`, `session`, `ver:1.0`, `cookie`, `header`

**VERDICT: `new`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/config.rst b/docs/config.rst
index ced2ad82..1bc46afa 100644
--- a/docs/config.rst
+++ b/docs/config.rst
@@ -88,6 +88,15 @@ The following configuration values are used internally by Flask:
                                   :class:`datetime.timedelta` object.
                                   Starting with Flask 0.8 this can also be
                                   an integer representing seconds.
+``SESSION_REFRESH_EACH_REQUEST``  this flag controls how permanent
+                                  sessions are refresh.  If set to `True`
+                                  (which is the default) then the cookie
+                                  is refreshed each request which
+                                  automatically bumps the lifetime.  If
+                                  set to `False` a `set-cookie` header is
+                                  only sent if the session is modified.
+                                  Non permanent sessions are not affected
+                                  by this.
 ``USE_X_SENDFILE``                enable/disable x-sendfile
 ``LOGGER_NAME``                   the name of the logger
 ``SERVER_NAME``                   the name and port number of the server.
@@ -210,6 +219,9 @@ The following configuration values are used internally by Flask:
 .. versionadded:: 0.10
    ``JSON_AS_ASCII``, ``JSON_SORT_KEYS``, ``JSONIFY_PRETTYPRINT_REGULAR``
 
+.. versionadded:: 1.0
+   ``SESSION_REFRESH_EACH_REQUEST``
+
 Configuring from Files
 ----------------------
 

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/flask/sessions.py b/flask/sessions.py
index 3246eb83..d6b7e5ae 100644
--- a/flask/sessions.py
+++ b/flask/sessions.py
@@ -252,6 +252,24 @@ class SessionInterface(object):
         if session.permanent:
             return datetime.utcnow() + app.permanent_session_lifetime
 
+    def should_set_cookie(self, app, session):
+        """Indicates weather a cookie should be set now or not.  This is
+        used by session backends to figure out if they should emit a
+        set-cookie header or not.  The default behavior is controlled by
+        the ``SESSION_REFRESH_EACH_REQUEST`` config variable.  If
+        it's set to `False` then a cookie is only set if the session is
+        modified, if set to `True` it's always set if the session is
+        permanent.
+
+        This check is usually skipped if sessions get deleted.
+
+        .. versionadded:: 1.0
+        """
+        if session.modified:
+            return True
+        save_each = app.config['SESSION_REFRESH_EACH_REQUEST']
+        return save_each and session.permanent
+
     def open_session(self, app, request):
         """This method has to be implemented and must either return `None`
         in case the loading failed because of a configuration error or an
@@ -315,11 +333,26 @@ class SecureCookieSessionInterface(SessionInterface):
     def save_session(self, app, session, response):
         domain = self.get_cookie_domain(app)
         path = self.get_cookie_path(app)
+
+        # Delete case.  If there is no session we bail early.
+        # If the session was modified to be empty we remove the
+        # whole cookie.
         if not session:
             if session.modified:
                 response.delete_cookie(app.session_cookie_name,
                                        domain=domain, path=path)
             return
+
+        # Modification case.  There are upsides and downsides to
+        # emitting a set-cookie header each request.  The behavior
+        # is controlled by the :meth:`should_set_cookie` method
+        # which performs a quick check to figure out if the cookie
+        # should be set or not.  This is controlled by the
+        # SESSION_REFRESH_EACH_REQUEST config flag as well as
+        # the permanent flag on the session itself.
+        if not self.should_set_cookie(app, session):
+            return
+
         httponly = self.get_cookie_httponly(app)
         secure = self.get_cookie_secure(app)
         expires = self.get_expiration_time(app, session)

```

</details>

---

## Case 25 — `b3da5f231e4dfb23`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** support timedelta for SEND_FILE_MAX_AGE_DEFAULT config variable
- **commit** https://github.com/pallets/flask/commit/d526932a09557be4aff6d27261cabb7c5c5ebb8d
- **doc** `docs/config.rst`
- **code** `flask/app.py`
- **shared identifiers** `timedelta`, `send`

**VERDICT: `new`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/config.rst b/docs/config.rst
index fb39b4c4..855136ff 100644
--- a/docs/config.rst
+++ b/docs/config.rst
@@ -130,7 +130,8 @@ The following configuration values are used internally by Flask:
 ``SEND_FILE_MAX_AGE_DEFAULT``     Default cache control max age to use with
                                   :meth:`~flask.Flask.send_static_file` (the
                                   default static file handler) and
-                                  :func:`~flask.send_file`, in
+                                  :func:`~flask.send_file`, as
+                                  :class:`datetime.timedelta` or as seconds.
                                   seconds. Override this value on a per-file
                                   basis using the
                                   :meth:`~flask.Flask.get_send_file_max_age`

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/flask/app.py b/flask/app.py
index 2d24d8b2..3d741ae9 100644
--- a/flask/app.py
+++ b/flask/app.py
@@ -246,6 +246,16 @@ class Flask(_PackageBoundObject):
     permanent_session_lifetime = ConfigAttribute('PERMANENT_SESSION_LIFETIME',
         get_converter=_make_timedelta)
 
+    #: A :class:`~datetime.timedelta` which is used as default cache_timeout
+    #: for the :func:`send_file` functions. The default is 12 hours.
+    #:
+    #: This attribute can also be configured from the config with the
+    #: ``SEND_FILE_MAX_AGE_DEFAULT`` configuration key. This configuration
+    #: variable can also be set with an integer value used as seconds.
+    #: Defaults to ``timedelta(hours=12)``
+    send_file_max_age_default = ConfigAttribute('SEND_FILE_MAX_AGE_DEFAULT',
+        get_converter=_make_timedelta)
+
     #: Enable this if you want to use the X-Sendfile feature.  Keep in
     #: mind that the server has to support this.  This only affects files
     #: sent with the :func:`send_file` method.
@@ -297,7 +307,7 @@ class Flask(_PackageBoundObject):
         'SESSION_COOKIE_SECURE':                False,
         'SESSION_REFRESH_EACH_REQUEST':         True,
         'MAX_CONTENT_LENGTH':                   None,
-        'SEND_FILE_MAX_AGE_DEFAULT':            12 * 60 * 60,  # 12 hours
+        'SEND_FILE_MAX_AGE_DEFAULT':            timedelta(hours=12),
         'TRAP_BAD_REQUEST_ERRORS':              False,
         'TRAP_HTTP_EXCEPTIONS':                 False,
         'EXPLAIN_TEMPLATE_LOADING':             False,

```

</details>

---

