# Drift label review — 25 cases (seed 11)

For each case, replace `VERDICT: ?` with one of:

- `drift` — the doc said something untrue about the code, and this commit corrected it
- `new` — the doc was documenting something that did not exist yet (feature + its docs)
- `cosmetic` — wording, formatting or a link -- nothing factual changed
- `unrelated` — the doc change and the code change are not about the same thing
- `unclear` — cannot tell from these diffs alone

The question is always: **at the parent commit, was this documentation false about the code?** Not whether the commit improved the docs — whether what it replaced was wrong.

---

## Case 1 — `a52ab20794d78164`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** update project metadata new readme readme as setup.py long_description links in changes git in authors add travis osx env break out docs build in travis remove python_requires for now
- **commit** https://github.com/pallets/flask/commit/9bf5c3b3a3bdc3f2f2dcca2b5747378470d0d354
- **doc** `CONTRIBUTING.rst`
- **code** `setup.py`
- **shared identifiers** `building`, `open`

**VERDICT: `unrelated`**

<details><summary>doc diff</summary>

```diff
diff --git a/CONTRIBUTING.rst b/CONTRIBUTING.rst
index ef02b732..a9bcace6 100644
--- a/CONTRIBUTING.rst
+++ b/CONTRIBUTING.rst
@@ -131,8 +131,22 @@ Read more about `coverage <https://coverage.readthedocs.io>`_.
 Running the full test suite with ``tox`` will combine the coverage reports
 from all runs.
 
-``make`` targets
-~~~~~~~~~~~~~~~~
+
+Building the docs
+~~~~~~~~~~~~~~~~~
+
+Build the docs in the ``docs`` directory using Sphinx::
+
+    cd docs
+    make html
+
+Open ``_build/html/index.html`` in your browser to view the docs.
+
+Read more about `Sphinx <http://www.sphinx-doc.org>`_.
+
+
+make targets
+~~~~~~~~~~~~
 
 Flask provides a ``Makefile`` with various shortcuts. They will ensure that
 all dependencies are installed.

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/setup.py b/setup.py
old mode 100644
new mode 100755
index 2ece939a..22a39b64
--- a/setup.py
+++ b/setup.py
@@ -1,74 +1,27 @@
-"""
-Flask
------
-
-Flask is a microframework for Python based on Werkzeug, Jinja 2 and good
-intentions. And before you ask: It's BSD licensed!
-
-Flask is Fun
-````````````
-
-Save in a hello.py:
-
-.. code:: python
-
-    from flask import Flask
-    app = Flask(__name__)
-
-    @app.route("/")
-    def hello():
-        return "Hello World!"
-
-    if __name__ == "__main__":
-        app.run()
-
-And Easy to Setup
-`````````````````
-
-And run it:
-
-.. code:: bash
-
-    $ pip install Flask
-    $ python hello.py
-    * Running on http://localhost:5000/
-
-Ready for production? `Read this first <http://flask.pocoo.org/docs/deploying/>`.
-
-Links
-`````
-
-* `website <http://flask.pocoo.org/>`_
-* `documentation <http://flask.pocoo.org/docs/>`_
-* `development version
-  <https://github.com/pallets/flask/zipball/master#egg=Flask-dev>`_
-
-"""
+#!/usr/bin/env python
+import io
 import re
-import ast
 from setuptools import setup
 
-_version_re = re.compile(r'__version__\s+=\s+(.*)')
+with io.open('README.rst', 'rt', encoding='utf8') as f:
+    readme = f.read()
 
-with open('flask/__init__.py', 'rb') as f:
-    version = str(ast.literal_eval(_version_re.search(
-        f.read().decode('utf-8')).group(1)))
+with io.open('flask/__init__.py', 'rt', encoding='utf8') as f:
+    version = re.search(r'__version__ = \'(.*?)\'', f.read()).group(1)
 
 setup(
     name='Flask',
     version=version,
-    url='https://github.com/pallets/flask/',
+    url='https://www.palletsprojects.com/p/flask/',
     license='BSD',
     author='Armin Ronacher',
     author_email='armin.ronacher@active-4.com',
-    description='A microframework based on Werkzeug, Jinja2 '
-                'and good intentions',
-    long_description=__doc__,
+    description='A simple framework for building complex web applications.',
+    long_description=readme,
     packages=['flask', 'flask.json'],
     include_package_data=True,
     zip_safe=False,
     platforms='any',
-    python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*',
     install_requires=[
         'Werkzeug>=0.14',
         'Jinja2>=2.10',

```

</details>

---

## Case 2 — `37fbf5ed3140a847`

- **repo** `psf/requests` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Disable requests[security] and remove 3.5 support references
- **commit** https://github.com/psf/requests/commit/f6c0619d892a41dcf84933810ffda89e9f6b10d4
- **doc** `docs/index.rst`
- **code** `setup.py`
- **shared identifiers** `ver:2.7`, `ver:3.5`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/index.rst b/docs/index.rst
index 4f8a9e4d..49bda6dc 100644
--- a/docs/index.rst
+++ b/docs/index.rst
@@ -68,7 +68,7 @@ Requests is ready for today's web.
 - Chunked Requests
 - ``.netrc`` Support
 
-Requests officially supports Python 2.7 & 3.5+, and runs great on PyPy.
+Requests officially supports Python 2.7 & 3.6+, and runs great on PyPy.
 
 
 The User Guide

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/setup.py b/setup.py
index 1e5ffaa2..ce5e5c80 100755
--- a/setup.py
+++ b/setup.py
@@ -78,7 +78,7 @@ setup(
     package_data={'': ['LICENSE', 'NOTICE']},
     package_dir={'requests': 'requests'},
     include_package_data=True,
-    python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*",
+    python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*, !=3.5.*",
     install_requires=requires,
     license=about['__license__'],
     zip_safe=False,
@@ -91,7 +91,6 @@ setup(
         'Programming Language :: Python :: 2',
         'Programming Language :: Python :: 2.7',
         'Programming Language :: Python :: 3',
-        'Programming Language :: Python :: 3.5',
         'Programming Language :: Python :: 3.6',
         'Programming Language :: Python :: 3.7',
         'Programming Language :: Python :: 3.8',
@@ -102,7 +101,7 @@ setup(
     cmdclass={'test': PyTest},
     tests_require=test_requirements,
     extras_require={
-        'security': ['pyOpenSSL >= 0.14', 'cryptography>=1.3.4'],
+        'security': [],
         'socks': ['PySocks>=1.5.6, !=1.5.7'],
         'socks:sys_platform == "win32" and python_version == "2.7"': ['win_inet_pton'],
         'use_chardet_on_py3': ['chardet>=3.0.2,<5']

```

</details>

---

## Case 3 — `0161d7b8f7fa0cfb`

- **repo** `pydantic/pydantic` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Improve the rendering of the conversion table (#6275)
- **commit** https://github.com/pydantic/pydantic/commit/0bde99751e23239ab7ccd9159d26be87c2b341e1
- **doc** `docs/usage/conversion_table.md`
- **code** `docs/plugins/main.py`
- **shared identifiers** `conversion_table`, `conversion`, `strict`, `table`, `json`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/usage/conversion_table.md b/docs/usage/conversion_table.md
index fed7ed035..3f941500d 100644
--- a/docs/usage/conversion_table.md
+++ b/docs/usage/conversion_table.md
@@ -4,4 +4,17 @@ The following table provides details on how Pydantic converts data during valida
 
 See [Strict Mode](models.md#strict-mode) for more details.
 
-{{ conversion_table }}
+=== "All"
+{{ conversion_table_all }}
+
+=== "JSON"
+{{ conversion_table_json }}
+
+=== "JSON - Strict"
+{{ conversion_table_json_strict }}
+
+=== "Python"
+{{ conversion_table_python }}
+
+=== "Python - Strict"
+{{ conversion_table_python_strict }}

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/docs/plugins/main.py b/docs/plugins/main.py
index 1424f203b..ce7192098 100644
--- a/docs/plugins/main.py
+++ b/docs/plugins/main.py
@@ -4,6 +4,7 @@ import json
 import logging
 import os
 import re
+import textwrap
 from pathlib import Path
 from textwrap import dedent, indent
 
@@ -14,7 +15,7 @@ from mkdocs.config import Config
 from mkdocs.structure.files import Files
 from mkdocs.structure.pages import Page
 
-from .conversion_table import table
+from .conversion_table import conversion_table
 
 logger = logging.getLogger('mkdocs.plugin')
 THIS_DIR = Path(__file__).parent
@@ -222,26 +223,20 @@ def build_conversion_table(markdown: str, page: Page) -> str | None:
     if page.file.src_uri != 'usage/conversion_table.md':
         return None
 
-    col_names = [
-        'Field Type',
-        'Input',
-        'Mode',
-        'Input Source',
-        'Conditions',
-    ]
-    table_text = _generate_table_heading(col_names)
+    filtered_table_predicates = {
+        'all': lambda r: True,
+        'json': lambda r: r.json_input,
+        'json_strict': lambda r: r.json_input and r.strict,
+        'python': lambda r: r.python_input,
+        'python_strict': lambda r: r.python_input and r.strict,
+    }
 
-    for row in table:
-        cols = [
-            f'`{row.field_type.__name__}`' if hasattr(row.field_type, '__name__') else f'`{row.field_type}`',
-            f'`{row.input_type.__name__}`' if hasattr(row.input_type, '__name__') else f'`{row.input_type}`',
-            row.mode,
-            row.input_format,
-            row.condition if row.condition else '',
-        ]
-        table_text += _generate_table_row(cols)
+    for table_id, predicate in filtered_table_predicates.items():
+        table_markdown = conversion_table.filtered(predicate).as_markdown()
+        table_markdown = textwrap.indent(table_markdown, '    ')
+        markdown = re.sub(rf'{{{{ *conversion_table_{table_id} *}}}}', table_markdown, markdown)
 
-    return re.sub(r'{{ *conversion_table *}}', table_text, markdown)
+    return markdown
 
 
 def devtools_example(markdown: str, page: Page) -> str | None:

```

</details>

---

## Case 4 — `4d4c63eed06a8e97`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Added support for signals
- **commit** https://github.com/pallets/flask/commit/e0712b47c6e5bc98f2afd8b0a82cc5005dc58722
- **doc** `docs/api.rst`
- **code** `flask/__init__.py`
- **shared identifiers** `got_request_exception`, `signals_available`, `template_rendered`, `request_finished`, `request_started`, `exception`, `finished`, `rendered`, `signals`

**VERDICT: `new`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/api.rst b/docs/api.rst
index f31563b4..afcb4c20 100644
--- a/docs/api.rst
+++ b/docs/api.rst
@@ -351,3 +351,54 @@ Useful Internals
    information from the context local around for a little longer.  Make
    sure to properly :meth:`~werkzeug.LocalStack.pop` the stack yourself in
    that situation, otherwise your unittests will leak memory.
+
+Signals
+-------
+
+.. versionadded:: 0.6
+
+.. data:: signals_available
+
+   `True` if the signalling system is available.  This is the case
+   when `blinker`_ is installed.
+
+.. data:: template_rendered
+
+   This signal is sent when a template was successfully rendered.  The
+   signal is invoked with the instance of the template as `template`
+   and the context as dictionary (named `context`).
+
+.. data:: request_started
+
+   This signal is sent before any request processing started but when the
+   request context was set up.  Because the request context is already
+   bound, the subscriber can access the request with the standard global
+   proxies such as :class:`~flask.request`.
+
+.. data:: request_finished
+
+   This signal is sent right before the response is sent to the client.
+   It is passed the response to be sent named `response`.
+
+.. data:: got_request_exception
+
+   This signal is sent when an exception happens during request processing.
+   It is sent *before* the standard exception handling kicks in and even
+   in debug mode, where no exception handling happens.  The exception
+   itself is passed to the subscriber as `exception`.
+
+.. class:: flask.signals.Namespace
+
+   An alias for :class:`blinker.base.Namespace` if blinker is available,
+   otherwise a dummy class that creates fake signals.  This class is
+   available for Flask extensions that want to provide the same fallback
+   system as Flask itself.
+
+   .. method:: signal(name, doc=None)
+
+      Creates a new signal for this namespace if blinker is available,
+      otherwise returns a fake signal that has a send method that will
+      do nothing but will fail with a :exc:`RuntimeError` for all other
+      operations, including connecting.
+
+.. _blinker: http://pypi.python.org/pypi/blinker

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/flask/__init__.py b/flask/__init__.py
index 93ada5f7..95497069 100644
--- a/flask/__init__.py
+++ b/flask/__init__.py
@@ -24,6 +24,10 @@ from .globals import current_app, g, request, session, _request_ctx_stack
 from .module import Module
 from .templating import render_template, render_template_string
 
+# the signals
+from .signals import signals_available, template_rendered, request_started, \
+     request_finished, got_request_exception
+
 # only import json if it's available
 if json_available:
     from .helpers import json

```

</details>

---

## Case 5 — `5c3d82fb9439ea71`

- **repo** `pydantic/pydantic` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Fix wasm preview (pydantic/pydantic-core#835)
- **commit** https://github.com/pydantic/pydantic/commit/d208635ebc79c2510c511d99bdc1512e6770889b
- **doc** `wasm-preview/README.md`
- **code** `wasm-preview/worker.js`
- **shared identifiers** `pydantic_core_version`, `pydantic`, `pyodide`, `core`

**VERDICT: `unrelated`**

<details><summary>doc diff</summary>

```diff
diff --git a/wasm-preview/README.md b/wasm-preview/README.md
index 8d2140e8f..8579ce5b1 100644
--- a/wasm-preview/README.md
+++ b/wasm-preview/README.md
@@ -2,10 +2,10 @@
 
 To run tests in your browser, go [here](https://githubproxy.samuelcolvin.workers.dev/pydantic/pydantic-core/blob/main/wasm-preview/index.html).
 
-To test with a specific version of pydantic-core, add a query parameter `?pydantic_core_version=...` to the URL, e.g. `?pydantic_core_version=v0.25.0`, defaults to latest release.
+To test with a specific version of pydantic-core, add a query parameter `?pydantic_core_version=...` to the URL, e.g. `?pydantic_core_version=v2.4.0`, defaults to latest release.
 
 This doesn't work for version of pydantic-core before v0.23.0 as before that we built 3.10 binaries, and pyodide now rust 3.11.
 
 If the output appears to stop prematurely, try looking in the developer console for more details.
 
-Tests are currently failing 10-15% of the wait through on Chrome due to a suspected V8 bug, see [pyodide/pyodide#3792](https://github.com/pyodide/pyodide/issues/3792) for more information.
+For pydantic-core versions prior to `2.2.0`, tests will freeze at  at 10-15% of the way through on Chrome due to a suspected V8 bug, see [pyodide/pyodide#3792](https://github.com/pyodide/pyodide/issues/3792) for more information. 

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/wasm-preview/worker.js b/wasm-preview/worker.js
index 4d05bde95..6b5130115 100644
--- a/wasm-preview/worker.js
+++ b/wasm-preview/worker.js
@@ -97,7 +97,8 @@ async function main() {
     setupStreams(FS, pyodide._module.TTY);
     FS.mkdir('/test_dir');
     FS.chdir('/test_dir');
-    await pyodide.loadPackage(['micropip', 'pytest', 'pytz', 'typing-extensions']);
+    await pyodide.loadPackage(['micropip', 'pytest', 'pytz']);
+    if (pydantic_core_version < '2.0.0') await pyodide.loadPackage(['typing-extensions']);
     await pyodide.runPythonAsync(python_code, {globals: pyodide.toPy({pydantic_core_version, tests_zip})});
     post();
   } catch (err) {

```

</details>

---

## Case 6 — `8c221707d13b6e4a`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Added support for deferred context cleanup. test_client users can now access the context locals after the actual request if the client is used with a with-block. This fixes #59.
- **commit** https://github.com/pallets/flask/commit/bc00fd1e83f23f57dd6a765b6a4bab2394584ae6
- **doc** `docs/testing.rst`
- **code** `flask.py`
- **shared identifiers** `test_client`, `context`, `ver:0.4`, `client`, `block`, `flask`, `down`

**VERDICT: `new`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/testing.rst b/docs/testing.rst
index db2b4188..de14413d 100644
--- a/docs/testing.rst
+++ b/docs/testing.rst
@@ -218,3 +218,27 @@ All the other objects that are context bound can be used the same.
 If you want to test your application with different configurations and
 there does not seem to be a good way to do that, consider switching to
 application factories (see :ref:`app-factories`).
+
+
+Keeping the Context Around
+--------------------------
+
+.. versionadded:: 0.4
+
+Sometimes it can be helpful to trigger a regular request but keep the
+context around for a little longer so that additional introspection can
+happen.  With Flask 0.4 this is possible by using the
+:meth:`~flask.Flask.test_client` with a `with` block::
+
+    app = flask.Flask(__name__)
+
+    with app.test_client() as c:
+        rv = c.get('/?foo=42')
+        assert request.args['foo'] == '42'
+
+If you would just be using the :meth:`~flask.Flask.test_client` without
+the `with` block, the `assert` would fail with an error because `request`
+is no longer available (because used outside of an actual request).
+Keep in mind however that :meth:`~flask.Flask.after_request` functions
+are already called at that point so your database connection and
+everything involved is probably already closed down.

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/flask.py b/flask.py
index 00d23287..f5d94fbe 100644
--- a/flask.py
+++ b/flask.py
@@ -163,8 +163,10 @@ class _RequestContext(object):
     def __exit__(self, exc_type, exc_value, tb):
         # do not pop the request stack if we are in debug mode and an
         # exception happened.  This will allow the debugger to still
-        # access the request object in the interactive shell.
-        if tb is None or not self.app.debug:
+        # access the request object in the interactive shell.  Furthermore
+        # the context can be force kept alive for the test client.
+        if not self.request.environ.get('flask._preserve_context') and \
+           (tb is None or not self.app.debug):
             self.pop()
 
 
@@ -1021,9 +1023,40 @@ class Flask(_PackageBoundObject):
     def test_client(self):
         """Creates a test client for this application.  For information
         about unit testing head over to :ref:`testing`.
+
+        The test client can be used in a `with` block to defer the closing down
+        of the context until the end of the `with` block.  This is useful if
+        you want to access the context locals for testing::
+
+            with app.test_client() as c:
+                rv = c.get('/?foo=42')
+                assert request.args['foo'] == '42'
+
+        .. versionchanged:: 0.4
+           added support for `with` block usage for the client.
         """
         from werkzeug import Client
-        return Client(self, self.response_class, use_cookies=True)
+        class FlaskClient(Client):
+            preserve_context = context_preserved = False
+            def open(self, *args, **kwargs):
+                if self.context_preserved:
+                    _request_ctx_stack.pop()
+                    self.context_preserved = False
+                kwargs.setdefault('environ_overrides', {}) \
+                    ['flask._preserve_context'] = self.preserve_context
+                old = _request_ctx_stack.top
+                try:
+                    return Client.open(self, *args, **kwargs)
+                finally:
+                    self.context_preserved = _request_ctx_stack.top is not old
+            def __enter__(self):
+                self.preserve_context = True
+                return self
+            def __exit__(self, exc_type, exc_value, tb):
+                self.preserve_context = False
+                if self.context_preserved:
+                    _request_ctx_stack.pop()
+        return FlaskClient(self, self.response_class, use_cookies=True)
 
     def open_session(self, request):
         """Creates or opens a new session.  Default implementation stores all

```

</details>

---

## Case 7 — `884f8d4776cb8b02`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Started work on new request dispatching.  Unittests not yet updated
- **commit** https://github.com/pallets/flask/commit/e71a5ff8de93801c30ed6daecac4b8502aa86813
- **doc** `docs/api.rst`
- **code** `flask/ctx.py`
- **shared identifiers** `preserve_context`, `requestcontext`, `automatically`, `functionality`, `application`, `environment`, `interactive`, `test_client`, `exceptions`, `introspect`, `localstack`, `debuggers`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/api.rst b/docs/api.rst
index 88d026ed..b3953537 100644
--- a/docs/api.rst
+++ b/docs/api.rst
@@ -310,6 +310,9 @@ Configuration
 Useful Internals
 ----------------
 
+.. autoclass:: flask.ctx.RequestContext
+   :members:
+
 .. data:: _request_ctx_stack
 
    The internal :class:`~werkzeug.local.LocalStack` that is used to implement
@@ -347,23 +350,6 @@ Useful Internals
           if ctx is not None:
               return ctx.session
 
-   .. versionchanged:: 0.4
-
-   The request context is automatically popped at the end of the request
-   for you.  In debug mode the request context is kept around if
-   exceptions happen so that interactive debuggers have a chance to
-   introspect the data.  With 0.4 this can also be forced for requests
-   that did not fail and outside of `DEBUG` mode.  By setting
-   ``'flask._preserve_context'`` to `True` on the WSGI environment the
-   context will not pop itself at the end of the request.  This is used by
-   the :meth:`~flask.Flask.test_client` for example to implement the
-   deferred cleanup functionality.
-
-   You might find this helpful for unittests where you need the
-   information from the context local around for a little longer.  Make
-   sure to properly :meth:`~werkzeug.LocalStack.pop` the stack yourself in
-   that situation, otherwise your unittests will leak memory.
-
 Signals
 -------
 
@@ -401,6 +387,12 @@ Signals
    in debug mode, where no exception handling happens.  The exception
    itself is passed to the subscriber as `exception`.
 
+.. data:: request_tearing_down
+
+   This signal is sent when the application is tearing down the request.
+   This is always called, even if an error happened.  No arguments are
+   provided.
+
 .. currentmodule:: None
 
 .. class:: flask.signals.Namespace
@@ -418,28 +410,3 @@ Signals
       operations, including connecting.
 
 .. _blinker: http://pypi.python.org/pypi/blinker
-
-.. _notes-on-proxies:
-
-Notes On Proxies
-----------------
-
-Some of the objects provided by Flask are proxies to other objects.  The
-reason behind this is that these proxies are shared between threads and
-they have to dispatch to the actual object bound to a thread behind the
-scenes as necessary.
-
-Most of the time you don't have to care about that, but there are some
-exceptions where it is good to know that this object is an actual proxy:
-
--   The proxy objects do not fake their inherited types, so if you want to
-    perform actual instance checks, you have to do that on the instance
-    that is being proxied (see `_get_current_object` below).
--   if the object reference is important (so for example for sending
-    :ref:`signals`)
-
-If you need to get access to the underlying object that is proxied, you
-can use the :meth:`~werkzeug.local.LocalProxy._get_current_object` method::
-
-    app = current_app._get_current_object()
-    my_signal.send(app)

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/flask/ctx.py b/flask/ctx.py
index b63f09f1..bc4877cd 100644
--- a/flask/ctx.py
+++ b/flask/ctx.py
@@ -51,11 +51,34 @@ def has_request_context():
     return _request_ctx_stack.top is not None
 
 
-class _RequestContext(object):
+class RequestContext(object):
     """The request context contains all request relevant information.  It is
     created at the beginning of the request and pushed to the
     `_request_ctx_stack` and removed at the end of it.  It will create the
     URL adapter and request object for the WSGI environment provided.
+
+    Do not attempt to use this class directly, instead use
+    :meth:`~flask.Flask.test_request_context` and
+    :meth:`~flask.Flask.request_context` to create this object.
+
+    When the request context is popped, it will evaluate all the
+    functions registered on the application for teardown execution
+    (:meth:`~flask.Flask.teardown_request`).
+
+    The request context is automatically popped at the end of the request
+    for you.  In debug mode the request context is kept around if
+    exceptions happen so that interactive debuggers have a chance to
+    introspect the data.  With 0.4 this can also be forced for requests
+    that did not fail and outside of `DEBUG` mode.  By setting
+    ``'flask._preserve_context'`` to `True` on the WSGI environment the
+    context will not pop itself at the end of the request.  This is used by
+    the :meth:`~flask.Flask.test_client` for example to implement the
+    deferred cleanup functionality.
+
+    You might find this helpful for unittests where you need the
+    information from the context local around for a little longer.  Make
+    sure to properly :meth:`~werkzeug.LocalStack.pop` the stack yourself in
+    that situation, otherwise your unittests will leak memory.
     """
 
     def __init__(self, app, environ):
@@ -74,7 +97,7 @@ class _RequestContext(object):
             self.request.routing_exception = e
 
     def push(self):
-        """Binds the request context."""
+        """Binds the request context to the current context."""
         _request_ctx_stack.push(self)
 
         # Open the session at the moment that the request context is
@@ -85,7 +108,11 @@ class _RequestContext(object):
             self.session = _NullSession()
 
     def pop(self):
-        """Pops the request context."""
+        """Pops the request context and unbinds it by doing that.  This will
+        also trigger the execution of functions registered by the
+        :meth:`~flask.Flask.teardown_request` decorator.
+        """
+        self.app.do_teardown_request()
         _request_ctx_stack.pop()
 
     def __enter__(self):
@@ -99,5 +126,5 @@ class _RequestContext(object):
         # the context can be force kept alive for the test client.
         # See flask.testing for how this works.
         if not self.request.environ.get('flask._preserve_context') and \
-           (tb is None or not self.app.debug):
+           (tb is None or not self.app.preserve_context_on_exception):
             self.pop()

```

</details>

---

## Case 8 — `d3f7419115663da9`

- **repo** `pydantic/pydantic` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Rewrite serialization documentation (#12018)
- **commit** https://github.com/pydantic/pydantic/commit/ffc084053b1ed87927c4c10e6dc2d17f6a4f2cac
- **doc** `docs/concepts/serialization.md`
- **code** `pydantic/functional_serializers.py`
- **shared identifiers** `serializeasany`, `serialization`, `serializers`, `serializing`, `particular`, `serialized`, `subclasses`, `serialize`, `concepts`, `original`, `subclass`, `present`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/concepts/serialization.md b/docs/concepts/serialization.md
index e1cd10491..757f083a3 100644
--- a/docs/concepts/serialization.md
+++ b/docs/concepts/serialization.md
@@ -1,7 +1,8 @@
 Beyond accessing model attributes directly via their field names (e.g. `model.foobar`), models can be converted, dumped,
-serialized, and exported in a number of ways.
+serialized, and exported in a number of ways. Serialization can be customized for the whole model, or on a per-field
+or per-type basis.
 
-!!! tip "Serialize versus dump"
+??? abstract "Serialize versus dump"
     Pydantic uses the terms "serialize" and "dump" interchangeably. Both refer to the process of converting a model to a
     dictionary or JSON-encoded string.
 
@@ -14,36 +15,52 @@ serialized, and exported in a number of ways.
     primitives and "serialize" when converting to string, for practical purposes, we frequently use the word "serialize"
     to refer to both of these situations, even though it does not always imply conversion to a string or bytes.
 
-## `model.model_dump(...)` <a name="model_dump"></a>
+!!! tip
+    Want to quickly jump to the relevant serializer section?
 
-??? api "API Documentation"
-    [`pydantic.main.BaseModel.model_dump`][pydantic.main.BaseModel.model_dump]<br>
+    <div class="grid cards" markdown>
 
-This is the primary way of converting a model to a dictionary. Sub-models will be recursively converted to dictionaries.
+    *   Field serializer
 
-By default, the output may contain non-JSON-serializable Python objects. The `mode` argument can be specified as `'json'` to ensure that the output only contains JSON serializable types. Other parameters exist to include or exclude fields, [including nested fields](#advanced-include-and-exclude), or to further customize the serialization behaviour.
+        ---
 
-See the available [parameters][pydantic.main.BaseModel.model_dump] for more information.
+        * [field *plain* serializer](#field-plain-serializer)
+        * [field *wrap* serializer](#field-wrap-serializer)
 
-!!! note
-    The one exception to sub-models being converted to dictionaries is that [`RootModel`](models.md#rootmodel-and-custom-root-types)
-    and its subclasses will have the `root` field value dumped directly, without a wrapping dictionary. This is also
-    done recursively.
+    *   Model serializer
 
-!!! note
-    You can use [computed fields](../api/fields.md#pydantic.fields.computed_field) to include `property` and
-    `cached_property` data in the `model.model_dump(...)` output.
+        ---
 
-Example:
+        * [model *plain* serializer](#model-plain-serializer)
+        * [model *wrap* serializer](#model-wrap-serializer)
 
-```python
-from typing import Any, Optional
+    </div>
+
+## Serializing data
+
+Pydantic allows models (and any other type using [type adapters](./type_adapter.md)) to be serialized in *two* modes:
+[Python](#python-mode) and [JSON](#json-mode). The Python output may contain non-JSON serializable data (although this
+can be emulated).
 
-from pydantic import BaseModel, Field, Json
+<!-- old anchor added for backwards compatibility -->
+<!-- markdownlint-disable-next-line no-empty-links -->
+[](){#modelmodel_dump}
+
+### Python mode
+
+When using the Python mode, Pydantic models (and model-like types such as [dataclasses][]) (1) will be (recursively) converted to dictionaries. This is achievable by using the [`model_dump()`][pydantic.BaseModel.model_dump] method:
+{ .annotate }
+
+1. With the exception of [root models](./models.md#rootmodel-and-custom-root-types), where the root value is dumped directly.
+
+```python {group="python-dump"}
+from typing import Optional
+
+from pydantic import BaseModel, Field
 
 
 class BarModel(BaseModel):
-    whatever: int
+    whatever: tuple[int, ...]
 
 
 class FooBarModel(BaseModel):
@@ -52,66 +69,35 @@ class FooBarModel(BaseModel):
     bar: BarModel
 
 
-m = FooBarModel(banana=3.14, foo='hello', bar={'whatever': 123})
+m = F
```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/pydantic/functional_serializers.py b/pydantic/functional_serializers.py
index ba2f342b8..d67773cbd 100644
--- a/pydantic/functional_serializers.py
+++ b/pydantic/functional_serializers.py
@@ -231,6 +231,7 @@ def field_serializer(
 def field_serializer(
     *fields: str,
     mode: Literal['plain', 'wrap'] = 'plain',
+    # TODO PEP 747 (grep for 'return_type' on the whole code base):
     return_type: Any = PydanticUndefined,
     when_used: WhenUsed = 'always',
     check_fields: bool | None = None,
@@ -260,7 +261,7 @@ def field_serializer(
     #> {"name":"Jane","courses":["Chemistry","English","Math"]}
     ```
 
-    See [Custom serializers](../concepts/serialization.md#custom-serializers) for more information.
+    See [the usage documentation](../concepts/serialization.md#serializers) for more information.
 
     Four signatures are supported:
 
@@ -391,7 +392,7 @@ def model_serializer(
     - `(self, nxt: SerializerFunctionWrapHandler)`
     - `(self, nxt: SerializerFunctionWrapHandler, info: SerializationInfo)`
 
-        See [Custom serializers](../concepts/serialization.md#custom-serializers) for more information.
+        See [the usage documentation](../concepts/serialization.md#serializers) for more information.
 
     Args:
         f: The function to be decorated.
@@ -422,15 +423,19 @@ AnyType = TypeVar('AnyType')
 
 if TYPE_CHECKING:
     SerializeAsAny = Annotated[AnyType, ...]  # SerializeAsAny[list[str]] will be treated by type checkers as list[str]
-    """Force serialization to ignore whatever is defined in the schema and instead ask the object
-    itself how it should be serialized.
-    In particular, this means that when model subclasses are serialized, fields present in the subclass
-    but not in the original schema will be included.
+    """Annotation used to mark a type as having duck-typing serialization behavior.
+
+    See [usage documentation](../concepts/serialization.md#serializing-with-duck-typing) for more details.
     """
 else:
 
     @dataclasses.dataclass(**_internal_dataclass.slots_true)
-    class SerializeAsAny:  # noqa: D101
+    class SerializeAsAny:
+        """Annotation used to mark a type as having duck-typing serialization behavior.
+
+        See [usage documentation](../concepts/serialization.md#serializing-with-duck-typing) for more details.
+        """
+
         def __class_getitem__(cls, item: Any) -> Any:
             return Annotated[item, SerializeAsAny()]
 

```

</details>

---

## Case 9 — `04184beb66a30564`

- **repo** `pydantic/pydantic` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Add PastDatetime and FutureDatetime types (#5720)
- **commit** https://github.com/pydantic/pydantic/commit/af9f579f946d6b9b92483f7c5aad102c48bbf38e
- **doc** `docs/usage/types/datetime.md`
- **code** `pydantic/types.py`
- **shared identifiers** `futuredatetime`, `pastdatetime`, `datetime`, `future`, `past`

**VERDICT: `new`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/usage/types/datetime.md b/docs/usage/types/datetime.md
index 4e0f17f37..7b1b8a7bc 100644
--- a/docs/usage/types/datetime.md
+++ b/docs/usage/types/datetime.md
@@ -74,6 +74,12 @@ types:
 `NaiveDatetime`
 : like `datetime`, but requires the value to lack timezone info
 
+`PastDatetime`
+: like `datetime`, but the datetime should be in the past
+
+`FutureDatetime`
+: like `datetime`, but the datetime should be in the future
+
 
 ```py
 from datetime import date, datetime, time, timedelta

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/pydantic/types.py b/pydantic/types.py
index f0e91ce41..168f214da 100644
--- a/pydantic/types.py
+++ b/pydantic/types.py
@@ -73,6 +73,8 @@ __all__ = [
     'ByteSize',
     'PastDate',
     'FutureDate',
+    'PastDatetime',
+    'FutureDatetime',
     'condate',
     'AwareDatetime',
     'NaiveDatetime',
@@ -762,6 +764,12 @@ class ByteSize(int):
 
 # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ DATE TYPES ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 
+
+def _check_annotated_type(annotated_type: str, expected_type: str, annotation: str) -> None:
+    if annotated_type != expected_type:
+        raise PydanticUserError(f"'{annotation}' cannot annotate '{annotated_type}'.", code='invalid_annotated_type')
+
+
 if TYPE_CHECKING:
     PastDate = Annotated[date, ...]
     FutureDate = Annotated[date, ...]
@@ -777,7 +785,7 @@ else:
                 return core_schema.date_schema(now_op='past')
             else:
                 schema = handler(source)
-                assert schema['type'] == 'date'
+                _check_annotated_type(schema['type'], 'date', cls.__name__)
                 schema['now_op'] = 'past'
                 return schema
 
@@ -794,7 +802,7 @@ else:
                 return core_schema.date_schema(now_op='future')
             else:
                 schema = handler(source)
-                assert schema['type'] == 'date'
+                _check_annotated_type(schema['type'], 'date', cls.__name__)
                 schema['now_op'] = 'future'
                 return schema
 
@@ -822,6 +830,9 @@ def condate(
 if TYPE_CHECKING:
     AwareDatetime = Annotated[datetime, ...]
     NaiveDatetime = Annotated[datetime, ...]
+    PastDatetime = Annotated[datetime, ...]
+    FutureDatetime = Annotated[datetime, ...]
+
 else:
 
     class AwareDatetime:
@@ -834,7 +845,7 @@ else:
                 return core_schema.datetime_schema(tz_constraint='aware')
             else:
                 schema = handler(source)
-                assert schema['type'] == 'datetime'
+                _check_annotated_type(schema['type'], 'datetime', cls.__name__)
                 schema['tz_constraint'] = 'aware'
                 return schema
 
@@ -851,13 +862,47 @@ else:
                 return core_schema.datetime_schema(tz_constraint='naive')
             else:
                 schema = handler(source)
-                assert schema['type'] == 'datetime'
+                _check_annotated_type(schema['type'], 'datetime', cls.__name__)
                 schema['tz_constraint'] = 'naive'
                 return schema
 
         def __repr__(self) -> str:
             return 'NaiveDatetime'
 
+    class PastDatetime:
+        @classmethod
+        def __get_pydantic_core_schema__(
+            cls, source: type[Any], handler: GetCoreSchemaHandler
+        ) -> core_schema.CoreSchema:
+            if cls is source:
+                # used directly as a type
+                return core_schema.datetime_schema(now_op='past')
+            else:
+                schema = handler(source)
+                _check_annotated_type(schema['type'], 'datetime', cls.__name__)
+                schema['now_op'] = 'past'
+                return schema
+
+        def __repr__(self) -> str:
+            return 'PastDatetime'
+
+    class FutureDatetime:
+        @classmethod
+        def __get_pydantic_core_schema__(
+            cls, source: type[Any], handler: GetCoreSchemaHandler
+        ) -> core_schema.CoreSchema:
+            if cls is source:
+                # used directly as a type
+                return core_schema.datetime_schema(now_op='future')
+            else:
+                schema = handler(source)
+                _check_annotated_type(schema['type'], 'datetime', cls.__name__)
+                schema['now_op'] = 'future'
+                return schema
+
+        def __repr__(self) -> str:
+            return 'FutureDatetime'
+
 
 # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Encoded TYPES ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
 

```

</details>

---

## Case 10 — `cae8831ef783741d`

- **repo** `pydantic/pydantic` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** 🐛 Fix RootModel json schema meta info (#6104)
- **commit** https://github.com/pydantic/pydantic/commit/c8a6d8be1806f8265c8e420490b0f81981cb485e
- **doc** `docs/usage/models.md`
- **code** `pydantic/_internal/_generate_schema.py`
- **shared identifiers** `root`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/usage/models.md b/docs/usage/models.md
index ae75ec7c1..4e5def1cb 100644
--- a/docs/usage/models.md
+++ b/docs/usage/models.md
@@ -884,7 +884,7 @@ print(Pets(['dog', 'cat']).model_dump_json())
 print(Pets.model_validate(['dog', 'cat']))
 #> root=['dog', 'cat']
 print(Pets.model_json_schema())
-#> {'items': {'type': 'string'}, 'type': 'array'}
+#> {'items': {'type': 'string'}, 'title': 'RootModel[List[str]]', 'type': 'array'}
 
 print(PetsByName({'Otis': 'dog', 'Milo': 'cat'}))
 #> root={'Otis': 'dog', 'Milo': 'cat'}

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/pydantic/_internal/_generate_schema.py b/pydantic/_internal/_generate_schema.py
index c72280414..911df2d07 100644
--- a/pydantic/_internal/_generate_schema.py
+++ b/pydantic/_internal/_generate_schema.py
@@ -156,6 +156,11 @@ def modify_model_json_schema(
     """Add title and description for model-like classes' JSON schema."""
     json_schema = handler(schema_or_field)
     original_schema = handler.resolve_ref_schema(json_schema)
+    # Preserve the fact that definitions schemas should never have sibling keys:
+    if '$ref' in original_schema:
+        ref = original_schema['$ref']
+        original_schema.clear()
+        original_schema['allOf'] = [{'$ref': ref}]
     if 'title' not in original_schema:
         original_schema['title'] = cls.__name__
     docstring = cls.__doc__
@@ -271,7 +276,7 @@ class GenerateSchema:
                     post_init=getattr(cls, '__pydantic_post_init__', None),
                     config=core_config,
                     ref=model_ref,
-                    metadata={**metadata, **root_field['metadata']},
+                    metadata=metadata,
                 )
             else:
                 self._config_wrapper_stack.append(config_wrapper)

```

</details>

---

## Case 11 — `c58c91cf27aa1f80`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Use American English for "behavior" in docs.
- **commit** https://github.com/pallets/flask/commit/a3cb2a33829ee517530d30cd920e5d652b358086
- **doc** `docs/extensiondev.rst`
- **code** `flask/app.py`
- **shared identifiers** `behaviour`, `behavior`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/extensiondev.rst b/docs/extensiondev.rst
index 86c7c721..59ca76c5 100644
--- a/docs/extensiondev.rst
+++ b/docs/extensiondev.rst
@@ -40,7 +40,7 @@ that it works with multiple Flask application instances at once.  This is
 a requirement because many people will use patterns like the
 :ref:`app-factories` pattern to create their application as needed to aid
 unittests and to support multiple configurations.  Because of that it is
-crucial that your application supports that kind of behaviour.
+crucial that your application supports that kind of behavior.
 
 Most importantly the extension must be shipped with a `setup.py` file and
 registered on PyPI.  Also the development checkout link should work so
@@ -145,7 +145,7 @@ initialization functions:
 classes:
 
     Classes work mostly like initialization functions but can later be
-    used to further change the behaviour.  For an example look at how the
+    used to further change the behavior.  For an example look at how the
     `OAuth extension`_ works: there is an `OAuth` object that provides
     some helper functions like `OAuth.remote_app` to create a reference to
     a remote application that uses OAuth.

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

## Case 12 — `2954ab751b985422`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** document python 2.6 minimum requirement, remove all stuff that refers to 2.5
- **commit** https://github.com/pallets/flask/commit/40fad2ece80e8bf6784e137028645fa66a3cd9c2
- **doc** `docs/installation.rst`
- **code** `setup.py`
- **shared identifiers** `ver:2.5`

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
diff --git a/setup.py b/setup.py
index 2f9c95ca..ba5f4a67 100644
--- a/setup.py
+++ b/setup.py
@@ -101,7 +101,6 @@ setup(
         'License :: OSI Approved :: BSD License',
         'Operating System :: OS Independent',
         'Programming Language :: Python',
-        'Programming Language :: Python :: 2.5',
         'Programming Language :: Python :: 2.6',
         'Programming Language :: Python :: 2.7',
         'Topic :: Internet :: WWW/HTTP :: Dynamic Content',

```

</details>

---

## Case 13 — `c551eb37addf3050`

- **repo** `psf/requests` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Add support for connect timeouts
- **commit** https://github.com/psf/requests/commit/c2aeaa3959b5754f5b39a45bceff91b196b6c986
- **doc** `docs/user/advanced.rst`
- **code** `requests/adapters.py`
- **shared identifiers** `connection`, `timeouts`, `connect`, `timeout`

**VERDICT: `new`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/user/advanced.rst b/docs/user/advanced.rst
index 8eb888b1..65970daf 100644
--- a/docs/user/advanced.rst
+++ b/docs/user/advanced.rst
@@ -707,3 +707,41 @@ Two excellent examples are `grequests`_ and `requests-futures`_.
 
 .. _`grequests`: https://github.com/kennethreitz/grequests
 .. _`requests-futures`: https://github.com/ross/requests-futures
+
+Timeouts
+--------
+
+Most requests to external servers should have a timeout attached, in case the
+server is not responding in a timely manner. Without a timeout, your code may
+hang for minutes or more.
+
+The **connect** timeout is the number of seconds Requests will wait for your
+client to establish a connection to a remote machine (corresponding to the
+`connect()`_) call on the socket. It's a good practice to set connect timeouts
+to slightly larger than a multiple of 3, which is the default `TCP packet
+retransmission window <http://www.hjp.at/doc/rfc/rfc2988.txt>`_.
+
+Once your client has connected to the server and sent the HTTP request, the
+**read** timeout is the number of seconds the client will wait for the server
+to send a response. (Specifically, it's the number of seconds that the client
+will wait *between* bytes sent from the server. In 99.9% of cases, this is the
+time before the server sends the first byte).
+
+If you specify a single value for the timeout, like this::
+
+    r = requests.get('https://github.com', timeout=5)
+
+The timeout value will be applied to both the ``connect`` and the ``read``
+timeouts. Specify a tuple if you would like to set the values separately::
+
+    r = requests.get('https://github.com', timeout=(3.05, 27))
+
+If the remote server is very slow, you can tell Requests to wait forever for
+a response, by passing None as a timeout value and then retrieving a cup of
+coffee.
+
+.. code-block:: python
+
+    r = requests.get('https://github.com', timeout=None)
+
+.. _`connect()`: http://linux.die.net/man/2/connect

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/requests/adapters.py b/requests/adapters.py
index 1ce54470..3c1e979f 100644
--- a/requests/adapters.py
+++ b/requests/adapters.py
@@ -15,17 +15,19 @@ from .packages.urllib3 import Retry
 from .packages.urllib3.poolmanager import PoolManager, proxy_from_url
 from .packages.urllib3.response import HTTPResponse
 from .packages.urllib3.util import Timeout as TimeoutSauce
-from .compat import urlparse, basestring, urldefrag, unquote
+from .compat import urlparse, basestring, urldefrag
 from .utils import (DEFAULT_CA_BUNDLE_PATH, get_encoding_from_headers,
                     prepend_scheme_if_needed, get_auth_from_url)
 from .structures import CaseInsensitiveDict
-from .packages.urllib3.exceptions import MaxRetryError
-from .packages.urllib3.exceptions import TimeoutError
-from .packages.urllib3.exceptions import SSLError as _SSLError
+from .packages.urllib3.exceptions import ConnectTimeoutError
 from .packages.urllib3.exceptions import HTTPError as _HTTPError
+from .packages.urllib3.exceptions import MaxRetryError
 from .packages.urllib3.exceptions import ProxyError as _ProxyError
+from .packages.urllib3.exceptions import ReadTimeoutError
+from .packages.urllib3.exceptions import SSLError as _SSLError
 from .cookies import extract_cookies_to_jar
-from .exceptions import ConnectionError, Timeout, SSLError, ProxyError
+from .exceptions import (ConnectionError, ConnectTimeout, ReadTimeout, SSLError,
+                         ProxyError)
 from .auth import _basic_auth_str
 
 DEFAULT_POOLBLOCK = False
@@ -315,6 +317,7 @@ class HTTPAdapter(BaseAdapter):
         :param request: The :class:`PreparedRequest <PreparedRequest>` being sent.
         :param stream: (optional) Whether to stream the request content.
         :param timeout: (optional) The timeout on the request.
+        :type timeout: float or tuple (connect timeout, read timeout), eg (3.1, 20)
         :param verify: (optional) Whether to verify SSL certificates.
         :param cert: (optional) Any user-provided SSL certificate to be trusted.
         :param proxies: (optional) The proxies dictionary to apply to the request.
@@ -328,7 +331,18 @@ class HTTPAdapter(BaseAdapter):
 
         chunked = not (request.body is None or 'Content-Length' in request.headers)
 
-        timeout = TimeoutSauce(connect=timeout, read=timeout)
+        if isinstance(timeout, tuple):
+            try:
+                connect, read = timeout
+                timeout = TimeoutSauce(connect=connect, read=read)
+            except ValueError as e:
+                # this may raise a string formatting error.
+                err = ("Invalid timeout {0}. Pass a (connect, read) "
+                       "timeout tuple, or a single float to set "
+                       "both timeouts to the same value".format(timeout))
+                raise ValueError(err)
+        else:
+            timeout = TimeoutSauce(connect=timeout, read=timeout)
 
         try:
             if not chunked:
@@ -390,6 +404,9 @@ class HTTPAdapter(BaseAdapter):
             raise ConnectionError(sockerr, request=request)
 
         except MaxRetryError as e:
+            if isinstance(e.reason, ConnectTimeoutError):
+                raise ConnectTimeout(e, request=request)
+
             raise ConnectionError(e, request=request)
 
         except _ProxyError as e:
@@ -398,8 +415,8 @@ class HTTPAdapter(BaseAdapter):
         except (_SSLError, _HTTPError) as e:
             if isinstance(e, _SSLError):
                 raise SSLError(e, request=request)
-            elif isinstance(e, TimeoutError):
-                raise Timeout(e, request=request)
+            elif isinstance(e, ReadTimeoutError):
+                raise ReadTimeout(e, request=request)
             else:
                 raise
 

```

</details>

---

## Case 14 — `4bf946cb81b5517e`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Added interactive Python docs, fixed part style.
- **commit** https://github.com/pallets/flask/commit/ef0dc1800f7558abbefe070f361b97b9161b2452
- **doc** `docs/latexindex.rst`
- **code** `flask.py`
- **shared identifiers** `testing`

**VERDICT: `unrelated`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/latexindex.rst b/docs/latexindex.rst
index a4aa0b4a..288197c3 100644
--- a/docs/latexindex.rst
+++ b/docs/latexindex.rst
@@ -3,36 +3,4 @@
 Flask Documentation
 ===================
 
-User's Guide
-------------
-
-.. toctree::
-   :maxdepth: 3
-
-   foreword
-   installation
-   quickstart
-   tutorial/index
-   testing
-   errorhandling
-   patterns/index
-   deploying/index
-   becomingbig
-
-API Reference
--------------
-
-.. toctree::
-   :maxdepth: 3
-
-   api
-
-Additional Notes
-----------------
-
-.. toctree::
-   :maxdepth: 3
-
-   design
-   license
-   changelog
+.. include:: contents.rst.inc

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/flask.py b/flask.py
index ea3fcaa0..d3391a43 100644
--- a/flask.py
+++ b/flask.py
@@ -147,15 +147,24 @@ class _RequestContext(object):
         except HTTPException, e:
             self.request.routing_exception = e
 
-    def __enter__(self):
+    def push(self):
+        """Binds the request context."""
         _request_ctx_stack.push(self)
 
+    def pop(self):
+        """Pops the request context."""
+        _request_ctx_stack.pop()
+
+    def __enter__(self):
+        self.push()
+        return self
+
     def __exit__(self, exc_type, exc_value, tb):
         # do not pop the request stack if we are in debug mode and an
         # exception happened.  This will allow the debugger to still
         # access the request object in the interactive shell.
         if tb is None or not self.app.debug:
-            _request_ctx_stack.pop()
+            self.pop()
 
 
 def url_for(endpoint, **values):
@@ -1202,6 +1211,30 @@ class Flask(_PackageBoundObject):
             with app.request_context(environ):
                 do_something_with(request)
 
+        The object returned can also be used without the `with` statement
+        which is useful for working in the shell.  The example above is
+        doing exactly the same as this code::
+
+            ctx = app.request_context(environ)
+            ctx.push()
+            try:
+                do_something_with(request)
+            finally:
+                ctx.pop()
+
+        The big advantage of this approach is that you can use it without
+        the try/finally statement in a shell for interactive testing:
+
+        >>> ctx = app.test_request_context()
+        >>> ctx.bind()
+        >>> request.path
+        u'/'
+        >>> ctx.unbind()
+
+        .. versionchanged:: 0.5
+           Added support for non-with statement usage and `with` statement
+           is now passed the ctx object.
+
         :param environ: a WSGI environment
         """
         return _RequestContext(self, environ)

```

</details>

---

## Case 15 — `756ac020b878f26e`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** with_appcontext lasts for the lifetime of the click context
- **commit** https://github.com/pallets/flask/commit/c9e000b9cea2e117218d460874d86301fbb43c43
- **doc** `docs/tutorial/database.rst`
- **code** `src/flask/cli.py`
- **shared identifiers** `with_appcontext`, `appcontext`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/tutorial/database.rst b/docs/tutorial/database.rst
index b2852197..934f6008 100644
--- a/docs/tutorial/database.rst
+++ b/docs/tutorial/database.rst
@@ -40,7 +40,6 @@ response is sent.
 
     import click
     from flask import current_app, g
-    from flask.cli import with_appcontext
 
 
     def get_db():
@@ -128,7 +127,6 @@ Add the Python functions that will run these SQL commands to the
 
 
     @click.command('init-db')
-    @with_appcontext
     def init_db_command():
         """Clear the existing data and create new tables."""
         init_db()

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/src/flask/cli.py b/src/flask/cli.py
index 40f1de54..321794b6 100644
--- a/src/flask/cli.py
+++ b/src/flask/cli.py
@@ -410,15 +410,25 @@ pass_script_info = click.make_pass_decorator(ScriptInfo, ensure=True)
 
 def with_appcontext(f):
     """Wraps a callback so that it's guaranteed to be executed with the
-    script's application context.  If callbacks are registered directly
-    to the ``app.cli`` object then they are wrapped with this function
-    by default unless it's disabled.
+    script's application context.
+
+    Custom commands (and their options) registered under ``app.cli`` or
+    ``blueprint.cli`` will always have an app context available, this
+    decorator is not required in that case.
+
+    .. versionchanged:: 2.2
+        The app context is active for subcommands as well as the
+        decorated callback. The app context is always available to
+        ``app.cli`` command and parameter callbacks.
     """
 
     @click.pass_context
     def decorator(__ctx, *args, **kwargs):
-        with __ctx.ensure_object(ScriptInfo).load_app().app_context():
-            return __ctx.invoke(f, *args, **kwargs)
+        if not current_app:
+            app = __ctx.ensure_object(ScriptInfo).load_app()
+            __ctx.with_resource(app.app_context())
+
+        return __ctx.invoke(f, *args, **kwargs)
 
     return update_wrapper(decorator, f)
 
@@ -587,6 +597,10 @@ class FlaskGroup(AppGroup):
         Added the ``-A/--app``, ``-E/--env``, ``--debug/--no-debug``,
         and ``-e/--env-file`` options.
 
+    .. versionchanged:: 2.2
+        An app context is pushed when running ``app.cli`` commands, so
+        ``@with_appcontext`` is no longer required for those commands.
+
     .. versionchanged:: 1.0
         If installed, python-dotenv will be used to load environment variables
         from :file:`.env` and :file:`.flaskenv` files.
@@ -660,9 +674,18 @@ class FlaskGroup(AppGroup):
         # Look up commands provided by the app, showing an error and
         # continuing if the app couldn't be loaded.
         try:
-            return info.load_app().cli.get_command(ctx, name)
+            app = info.load_app()
         except NoAppException as e:
             click.secho(f"Error: {e.format_message()}\n", err=True, fg="red")
+            return None
+
+        # Push an app context for the loaded app unless it is already
+        # active somehow. This makes the context available to parameter
+        # and command callbacks without needing @with_appcontext.
+        if not current_app or current_app._get_current_object() is not app:
+            ctx.with_resource(app.app_context())
+
+        return app.cli.get_command(ctx, name)
 
     def list_commands(self, ctx):
         self._load_plugin_commands()

```

</details>

---

## Case 16 — `a188f67ccd242c40`

- **repo** `encode/httpx` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Event hooks (#1246)
- **commit** https://github.com/encode/httpx/commit/54f7708e2b8bc9bbd5f4ea9f1e4386b8acbf3811
- **doc** `docs/advanced.md`
- **code** `httpx/_client.py`
- **shared identifiers** `event_hooks`, `property`, `event`, `hooks`, `hook`

**VERDICT: `new`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/advanced.md b/docs/advanced.md
index b0ed25f..f374d0c 100644
--- a/docs/advanced.md
+++ b/docs/advanced.md
@@ -221,6 +221,58 @@ with httpx.Client(headers=headers) as client:
     ...
 ```
 
+## Event Hooks
+
+HTTPX allows you to register "event hooks" with the client, that are called
+every time a particular type of event takes place.
+
+There are currently two event hooks:
+
+* `request` - Called once a request is about to be sent. Passed the `request` instance.
+* `response` - Called once the response has been returned. Passed the `response` instance.
+
+These allow you to install client-wide functionality such as logging and monitoring.
+
+```python
+def log_request(request):
+    print(f"Request event hook: {request.method} {request.url} - Waiting for response")
+
+def log_response(response):
+    request = response.request
+    print(f"Response event hook: {request.method} {request.url} - Status {response.status_code}")
+
+client = httpx.Client(event_hooks={'request': [log_request], 'response': [log_response]})
+```
+
+You can also use these hooks to install response processing code, such as this
+example, which creates a client instance that always raises `httpx.HTTPStatusError`
+on 4xx and 5xx responses.
+
+```python
+def raise_on_4xx_5xx(response):
+    response.raise_for_status()
+
+client = httpx.Client(event_hooks={'response': [raise_on_4xx_5xx]})
+```
+
+Event hooks must always be set as a **list of callables**, and you may register
+multiple event hooks for each type of event.
+
+As well as being able to set event hooks on instantiating the client, there
+is also an `.event_hooks` property, that allows you to inspect and modify
+the installed hooks.
+
+```python
+client = httpx.Client()
+client.event_hooks['request'] = [log_request]
+client.event_hooks['response'] = [log_response, raise_for_status]
+```
+
+!!! note
+    If you are using HTTPX's async support, then you need to be aware that
+    hooks registered with `httpx.AsyncClient` MUST be async functions,
+    rather than plain functions.
+
 ## Monitoring download progress
 
 If you need to monitor download progress of large responses, you can use response streaming and inspect the `response.num_bytes_downloaded` property.

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/httpx/_client.py b/httpx/_client.py
index 7a26431..7599233 100644
--- a/httpx/_client.py
+++ b/httpx/_client.py
@@ -74,9 +74,12 @@ class BaseClient:
         cookies: CookieTypes = None,
         timeout: TimeoutTypes = DEFAULT_TIMEOUT_CONFIG,
         max_redirects: int = DEFAULT_MAX_REDIRECTS,
+        event_hooks: typing.Dict[str, typing.List[typing.Callable]] = None,
         base_url: URLTypes = "",
         trust_env: bool = True,
     ):
+        event_hooks = {} if event_hooks is None else event_hooks
+
         self._base_url = self._enforce_trailing_slash(URL(base_url))
 
         self._auth = self._build_auth(auth)
@@ -85,6 +88,10 @@ class BaseClient:
         self._cookies = Cookies(cookies)
         self._timeout = Timeout(timeout)
         self.max_redirects = max_redirects
+        self._event_hooks = {
+            "request": list(event_hooks.get("request", [])),
+            "response": list(event_hooks.get("response", [])),
+        }
         self._trust_env = trust_env
         self._netrc = NetRCInfo()
         self._is_closed = True
@@ -133,6 +140,19 @@ class BaseClient:
     def timeout(self, timeout: TimeoutTypes) -> None:
         self._timeout = Timeout(timeout)
 
+    @property
+    def event_hooks(self) -> typing.Dict[str, typing.List[typing.Callable]]:
+        return self._event_hooks
+
+    @event_hooks.setter
+    def event_hooks(
+        self, event_hooks: typing.Dict[str, typing.List[typing.Callable]]
+    ) -> None:
+        self._event_hooks = {
+            "request": list(event_hooks.get("request", [])),
+            "response": list(event_hooks.get("response", [])),
+        }
+
     @property
     def auth(self) -> typing.Optional[Auth]:
         """
@@ -532,6 +552,7 @@ class Client(BaseClient):
         limits: Limits = DEFAULT_LIMITS,
         pool_limits: Limits = None,
         max_redirects: int = DEFAULT_MAX_REDIRECTS,
+        event_hooks: typing.Dict[str, typing.List[typing.Callable]] = None,
         base_url: URLTypes = "",
         transport: httpcore.SyncHTTPTransport = None,
         app: typing.Callable = None,
@@ -544,6 +565,7 @@ class Client(BaseClient):
             cookies=cookies,
             timeout=timeout,
             max_redirects=max_redirects,
+            event_hooks=event_hooks,
             base_url=base_url,
             trust_env=trust_env,
         )
@@ -739,6 +761,13 @@ class Client(BaseClient):
             finally:
                 response.close()
 
+        try:
+            for hook in self._event_hooks["response"]:
+                hook(response)
+        except Exception:
+            response.close()
+            raise
+
         return response
 
     def _send_handling_auth(
@@ -752,6 +781,9 @@ class Client(BaseClient):
         auth_flow = auth.sync_auth_flow(request)
         request = next(auth_flow)
 
+        for hook in self._event_hooks["request"]:
+            hook(request)
+
         while True:
             response = self._send_handling_redirects(
                 request,
@@ -1153,6 +1185,7 @@ class AsyncClient(BaseClient):
         limits: Limits = DEFAULT_LIMITS,
         pool_limits: Limits = None,
         max_redirects: int = DEFAULT_MAX_REDIRECTS,
+        event_hooks: typing.Dict[str, typing.List[typing.Callable]] = None,
         base_url: URLTypes = "",
         transport: httpcore.AsyncHTTPTransport = None,
         app: typing.Callable = None,
@@ -1165,6 +1198,7 @@ class AsyncClient(BaseClient):
             cookies=cookies,
             timeout=timeout,
             max_redirects=max_redirects,
+            event_hooks=event_hooks,
             base_url=base_url,
             trust_env=trust_env,
         )
@@ -1362,6 +1396,13 @@ class AsyncClient(BaseClient):
             finally:
                 await response.aclose()
 
+        try:
+            for hook in self._event_hooks["response"]:
+                await hook(response)
+        except Exception:
+            await response.aclose()
+            r
```

</details>

---

## Case 17 — `14ead10bcd3ffba9`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** update docs about contexts
- **commit** https://github.com/pallets/flask/commit/e0dad454810dd081947d3ca2ff376c5096185698
- **doc** `docs/extensiondev.rst`
- **code** `src/flask/testing.py`
- **shared identifiers** `context`, `flask`, `stack`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/extensiondev.rst b/docs/extensiondev.rst
index 25ced187..95745119 100644
--- a/docs/extensiondev.rst
+++ b/docs/extensiondev.rst
@@ -187,12 +187,6 @@ when the application context ends. If it should only be valid during a
 request, or would not be used in the CLI outside a reqeust, use
 :meth:`~flask.Flask.teardown_request`.
 
-An older technique for storing context data was to store it on
-``_app_ctx_stack.top`` or ``_request_ctx_stack.top``. However, this just
-moves the same namespace collision problem elsewhere (although less
-likely) and modifies objects that are very internal to Flask's
-operations. Prefer storing data under a unique name in ``g``.
-
 
 Views and Models
 ----------------

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/src/flask/testing.py b/src/flask/testing.py
index e188439b..bf84f848 100644
--- a/src/flask/testing.py
+++ b/src/flask/testing.py
@@ -94,11 +94,10 @@ class EnvironBuilder(werkzeug.test.EnvironBuilder):
 
 
 class FlaskClient(Client):
-    """Works like a regular Werkzeug test client but has some knowledge about
-    how Flask works to defer the cleanup of the request context stack to the
-    end of a ``with`` body when used in a ``with`` statement.  For general
-    information about how to use this class refer to
-    :class:`werkzeug.test.Client`.
+    """Works like a regular Werkzeug test client but has knowledge about
+    Flask's contexts to defer the cleanup of the request context until
+    the end of a ``with`` block. For general information about how to
+    use this class refer to :class:`werkzeug.test.Client`.
 
     .. versionchanged:: 0.12
        `app.test_client()` includes preset default environment, which can be

```

</details>

---

## Case 18 — `2a0317397257b004`

- **repo** `pydantic/pydantic` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Add PastDatetime and FutureDatetime types (#5720)
- **commit** https://github.com/pydantic/pydantic/commit/af9f579f946d6b9b92483f7c5aad102c48bbf38e
- **doc** `docs/usage/types/datetime.md`
- **code** `pydantic/__init__.py`
- **shared identifiers** `futuredatetime`, `pastdatetime`, `datetime`, `future`, `past`

**VERDICT: `new`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/usage/types/datetime.md b/docs/usage/types/datetime.md
index 4e0f17f37..7b1b8a7bc 100644
--- a/docs/usage/types/datetime.md
+++ b/docs/usage/types/datetime.md
@@ -74,6 +74,12 @@ types:
 `NaiveDatetime`
 : like `datetime`, but requires the value to lack timezone info
 
+`PastDatetime`
+: like `datetime`, but the datetime should be in the past
+
+`FutureDatetime`
+: like `datetime`, but the datetime should be in the future
+
 
 ```py
 from datetime import date, datetime, time, timedelta

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/pydantic/__init__.py b/pydantic/__init__.py
index e40565342..ab7e5be85 100644
--- a/pydantic/__init__.py
+++ b/pydantic/__init__.py
@@ -133,6 +133,8 @@ __all__ = [
     'ByteSize',
     'PastDate',
     'FutureDate',
+    'PastDatetime',
+    'FutureDatetime',
     'AwareDatetime',
     'NaiveDatetime',
     'AllowInfNan',

```

</details>

---

## Case 19 — `e16c84eec5c9fc3b`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** add generate_template and generate_template_string functions
- **commit** https://github.com/pallets/flask/commit/46433e9807a1c960d6b2bb0e125cf16a90167d97
- **doc** `docs/api.rst`
- **code** `src/flask/templating.py`
- **shared identifiers** `stream_template_string`, `stream_template`, `stream`

**VERDICT: `new`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/api.rst b/docs/api.rst
index b3cffde2..217473bc 100644
--- a/docs/api.rst
+++ b/docs/api.rst
@@ -287,6 +287,10 @@ Template Rendering
 
 .. autofunction:: render_template_string
 
+.. autofunction:: stream_template
+
+.. autofunction:: stream_template_string
+
 .. autofunction:: get_template_attribute
 
 Configuration

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/src/flask/templating.py b/src/flask/templating.py
index 36a8645c..7d92cf1e 100644
--- a/src/flask/templating.py
+++ b/src/flask/templating.py
@@ -7,6 +7,9 @@ from jinja2 import TemplateNotFound
 
 from .globals import _app_ctx_stack
 from .globals import _request_ctx_stack
+from .globals import current_app
+from .globals import request
+from .helpers import stream_with_context
 from .signals import before_render_template
 from .signals import template_rendered
 
@@ -122,8 +125,6 @@ class DispatchingJinjaLoader(BaseLoader):
 
 
 def _render(template: Template, context: dict, app: "Flask") -> str:
-    """Renders the template and fires the signal"""
-
     before_render_template.send(app, template=template, context=context)
     rv = template.render(context)
     template_rendered.send(app, template=template, context=context)
@@ -164,3 +165,56 @@ def render_template_string(source: str, **context: t.Any) -> str:
     ctx = _app_ctx_stack.top
     ctx.app.update_template_context(context)
     return _render(ctx.app.jinja_env.from_string(source), context, ctx.app)
+
+
+def _stream(
+    app: "Flask", template: Template, context: t.Dict[str, t.Any]
+) -> t.Iterator[str]:
+    app.update_template_context(context)
+    before_render_template.send(app, template=template, context=context)
+
+    def generate() -> t.Iterator[str]:
+        yield from template.generate(context)
+        template_rendered.send(app, template=template, context=context)
+
+    rv = generate()
+
+    # If a request context is active, keep it while generating.
+    if request:
+        rv = stream_with_context(rv)
+
+    return rv
+
+
+def stream_template(
+    template_name_or_list: t.Union[str, Template, t.List[t.Union[str, Template]]],
+    **context: t.Any
+) -> t.Iterator[str]:
+    """Render a template by name with the given context as a stream.
+    This returns an iterator of strings, which can be used as a
+    streaming response from a view.
+
+    :param template_name_or_list: The name of the template to render. If
+        a list is given, the first name to exist will be rendered.
+    :param context: The variables to make available in the template.
+
+    .. versionadded:: 2.2
+    """
+    app = current_app._get_current_object()  # type: ignore[attr-defined]
+    template = app.jinja_env.get_or_select_template(template_name_or_list)
+    return _stream(app, template, context)
+
+
+def stream_template_string(source: str, **context: t.Any) -> t.Iterator[str]:
+    """Render a template from the given source string with the given
+    context as a stream. This returns an iterator of strings, which can
+    be used as a streaming response from a view.
+
+    :param source: The source code of the template to render.
+    :param context: The variables to make available in the template.
+
+    .. versionadded:: 2.2
+    """
+    app = current_app._get_current_object()  # type: ignore[attr-defined]
+    template = app.jinja_env.from_string(source)
+    return _stream(app, template, context)

```

</details>

---

## Case 20 — `591a4116b7311caa`

- **repo** `fastapi/fastapi` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** 🐛 Fix support for `StreamingResponse`s with dependencies with `yield` or `UploadFile`s, close after the response is done (#14099)
- **commit** https://github.com/fastapi/fastapi/commit/e329d78f866a12893699f786f1209a666e1688e3
- **doc** `docs/en/docs/advanced/advanced-dependencies.md`
- **code** `fastapi/applications.py`
- **shared identifiers** `exceptions`, `exception`, `handlers`, `fastapi`, `handler`, `errors`, `exit`

**VERDICT: `new`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/en/docs/advanced/advanced-dependencies.md b/docs/en/docs/advanced/advanced-dependencies.md
index c71c11404..e0404b389 100644
--- a/docs/en/docs/advanced/advanced-dependencies.md
+++ b/docs/en/docs/advanced/advanced-dependencies.md
@@ -63,3 +63,91 @@ In the chapters about security, there are utility functions that are implemented
 If you understood all this, you already know how those utility tools for security work underneath.
 
 ///
+
+## Dependencies with `yield`, `HTTPException`, `except` and Background Tasks { #dependencies-with-yield-httpexception-except-and-background-tasks }
+
+/// warning
+
+You most probably don't need these technical details.
+
+These details are useful mainly if you had a FastAPI application older than 0.118.0 and you are facing issues with dependencies with `yield`.
+
+///
+
+Dependencies with `yield` have evolved over time to account for the different use cases and to fix some issues, here's a summary of what has changed.
+
+### Dependencies with `yield` and `StreamingResponse`, Technical Details { #dependencies-with-yield-and-streamingresponse-technical-details }
+
+Before FastAPI 0.118.0, if you used a dependency with `yield`, it would run the exit code after the *path operation function* returned but right before sending the response.
+
+The intention was to avoid holding resources for longer than necessary, waiting for the response to travel through the network.
+
+This change also meant that if you returned a `StreamingResponse`, the exit code of the dependency with `yield` would have been already run.
+
+For example, if you had a database session in a dependency with `yield`, the `StreamingResponse` would not be able to use that session while streaming data because the session would have already been closed in the exit code after `yield`.
+
+This behavior was reverted in 0.118.0, to make the exit code after `yield` be executed after the response is sent.
+
+/// info
+
+As you will see below, this is very similar to the behavior before version 0.106.0, but with several improvements and bug fixes for corner cases.
+
+///
+
+#### Use Cases with Early Exit Code { #use-cases-with-early-exit-code }
+
+There are some use cases with specific conditions that could benefit from the old behavior of running the exit code of dependencies with `yield` before sending the response.
+
+For example, imagine you have code that uses a database session in a dependency with `yield` only to verify a user, but the database session is never used again in the *path operation function*, only in the dependency, **and** the response takes a long time to be sent, like a `StreamingResponse` that sends data slowly, but for some reason doesn't use the database.
+
+In this case, the database session would be held until the response is finished being sent, but if you don't use it, then it wouldn't be necessary to hold it.
+
+Here's how it could look like:
+
+{* ../../docs_src/dependencies/tutorial013_an_py310.py *}
+
+The exit code, the automatic closing of the `Session` in:
+
+{* ../../docs_src/dependencies/tutorial013_an_py310.py ln[19:21] *}
+
+...would be run after the the response finishes sending the slow data:
+
+{* ../../docs_src/dependencies/tutorial013_an_py310.py ln[30:38] hl[31:33] *}
+
+But as `generate_stream()` doesn't use the database session, it is not really necessary to keep the session open while sending the response.
+
+If you have this specific use case using SQLModel (or SQLAlchemy), you could explicitly close the session after you don't need it anymore:
+
+{* ../../docs_src/dependencies/tutorial014_an_py310.py ln[24:28] hl[28] *}
+
+That way the session would release the database connection, so other requests could use it.
+
+If you have a different use case that needs to exit early from a dependency with `yield`, please create a <a href="https://github.com/fastapi/fastapi/discussions/new?category=questions" class="external-link" target="_blank">GitHub Discussion Question</a> with you
```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/fastapi/applications.py b/fastapi/applications.py
index b3424efcc..915f5f70a 100644
--- a/fastapi/applications.py
+++ b/fastapi/applications.py
@@ -22,6 +22,7 @@ from fastapi.exception_handlers import (
 )
 from fastapi.exceptions import RequestValidationError, WebSocketRequestValidationError
 from fastapi.logger import logger
+from fastapi.middleware.asyncexitstack import AsyncExitStackMiddleware
 from fastapi.openapi.docs import (
     get_redoc_html,
     get_swagger_ui_html,
@@ -36,10 +37,12 @@ from starlette.datastructures import State
 from starlette.exceptions import HTTPException
 from starlette.middleware import Middleware
 from starlette.middleware.base import BaseHTTPMiddleware
+from starlette.middleware.errors import ServerErrorMiddleware
+from starlette.middleware.exceptions import ExceptionMiddleware
 from starlette.requests import Request
 from starlette.responses import HTMLResponse, JSONResponse, Response
 from starlette.routing import BaseRoute
-from starlette.types import ASGIApp, Lifespan, Receive, Scope, Send
+from starlette.types import ASGIApp, ExceptionHandler, Lifespan, Receive, Scope, Send
 from typing_extensions import Annotated, Doc, deprecated
 
 AppType = TypeVar("AppType", bound="FastAPI")
@@ -990,6 +993,54 @@ class FastAPI(Starlette):
         self.middleware_stack: Union[ASGIApp, None] = None
         self.setup()
 
+    def build_middleware_stack(self) -> ASGIApp:
+        # Duplicate/override from Starlette to add AsyncExitStackMiddleware
+        # inside of ExceptionMiddleware, inside of custom user middlewares
+        debug = self.debug
+        error_handler = None
+        exception_handlers: dict[Any, ExceptionHandler] = {}
+
+        for key, value in self.exception_handlers.items():
+            if key in (500, Exception):
+                error_handler = value
+            else:
+                exception_handlers[key] = value
+
+        middleware = (
+            [Middleware(ServerErrorMiddleware, handler=error_handler, debug=debug)]
+            + self.user_middleware
+            + [
+                Middleware(
+                    ExceptionMiddleware, handlers=exception_handlers, debug=debug
+                ),
+                # Add FastAPI-specific AsyncExitStackMiddleware for closing files.
+                # Before this was also used for closing dependencies with yield but
+                # those now have their own AsyncExitStack, to properly support
+                # streaming responses while keeping compatibility with the previous
+                # versions (as of writing 0.117.1) that allowed doing
+                # except HTTPException inside a dependency with yield.
+                # This needs to happen after user middlewares because those create a
+                # new contextvars context copy by using a new AnyIO task group.
+                # This AsyncExitStack preserves the context for contextvars, not
+                # strictly necessary for closing files but it was one of the original
+                # intentions.
+                # If the AsyncExitStack lived outside of the custom middlewares and
+                # contextvars were set, for example in a dependency with 'yield'
+                # in that internal contextvars context, the values would not be
+                # available in the outer context of the AsyncExitStack.
+                # By placing the middleware and the AsyncExitStack here, inside all
+                # user middlewares, the same context is used.
+                # This is currently not needed, only for closing files, but used to be
+                # important when dependencies with yield were closed here.
+                Middleware(AsyncExitStackMiddleware),
+            ]
+        )
+
+        app = self.router
+        for cls, args, kwargs in reversed(middleware):
+            app = cls(app, *args, **kwargs)
+        return app
+
     def openapi(self) -> Dict[str, Any]:
         """
         Generate the 
```

</details>

---

## Case 21 — `04a332fe0dc498cc`

- **repo** `encode/httpx` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Stream interface (#1550)
- **commit** https://github.com/encode/httpx/commit/110ce8565259a3c6927352554eccd94ca5804463
- **doc** `docs/advanced.md`
- **code** `httpx/_models.py`
- **shared identifiers** `bytestream`, `content`, `stream`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/advanced.md b/docs/advanced.md
index 1902b0e..4438cb2 100644
--- a/docs/advanced.md
+++ b/docs/advanced.md
@@ -1070,7 +1070,7 @@ class HelloWorldTransport(httpx.BaseTransport):
     def handle_request(self, method, url, headers, stream, extensions):
         message = {"text": "Hello, world!"}
         content = json.dumps(message).encode("utf-8")
-        stream = [content]
+        stream = httpx.ByteStream(content)
         headers = [(b"content-type", b"application/json")]
         extensions = {}
         return 200, headers, stream, extensions
@@ -1131,7 +1131,7 @@ class HTTPSRedirectTransport(httpx.BaseTransport):
             location = b"https://%s%s" % (host, path)
         else:
             location = b"https://%s:%d%s" % (host, port, path)
-        stream = [b""]
+        stream = httpx.ByteStream(b"")
         headers = [(b"location", location)]
         extensions = {}
         return 303, headers, stream, extensions

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/httpx/_models.py b/httpx/_models.py
index ade5a31..a3b6ff1 100644
--- a/httpx/_models.py
+++ b/httpx/_models.py
@@ -11,7 +11,7 @@ from urllib.parse import parse_qsl, quote, unquote, urlencode
 import rfc3986
 import rfc3986.exceptions
 
-from ._content import PlainByteStream, encode_request, encode_response
+from ._content import ByteStream, encode_request, encode_response
 from ._decoders import (
     SUPPORTED_DECODERS,
     ByteChunker,
@@ -33,8 +33,8 @@ from ._exceptions import (
     request_context,
 )
 from ._status_codes import codes
+from ._transports.base import AsyncByteStream, SyncByteStream
 from ._types import (
-    ByteStream,
     CookieTypes,
     HeaderTypes,
     PrimitiveData,
@@ -798,7 +798,7 @@ class Request:
         data: RequestData = None,
         files: RequestFiles = None,
         json: typing.Any = None,
-        stream: ByteStream = None,
+        stream: typing.Union[SyncByteStream, AsyncByteStream] = None,
     ):
         if isinstance(method, bytes):
             self.method = method.decode("ascii").upper()
@@ -872,7 +872,7 @@ class Request:
             # If a streaming request has been read entirely into memory, then
             # we can replace the stream with a raw bytes implementation,
             # to ensure that any non-replayable streams can still be used.
-            self.stream = PlainByteStream(self._content)
+            self.stream = ByteStream(self._content)
         return self._content
 
     async def aread(self) -> bytes:
@@ -885,7 +885,7 @@ class Request:
             # If a streaming request has been read entirely into memory, then
             # we can replace the stream with a raw bytes implementation,
             # to ensure that any non-replayable streams can still be used.
-            self.stream = PlainByteStream(self._content)
+            self.stream = ByteStream(self._content)
         return self._content
 
     def __repr__(self) -> str:
@@ -904,7 +904,7 @@ class Response:
         text: str = None,
         html: str = None,
         json: typing.Any = None,
-        stream: ByteStream = None,
+        stream: typing.Union[SyncByteStream, AsyncByteStream] = None,
         request: Request = None,
         extensions: dict = None,
         history: typing.List["Response"] = None,
@@ -1222,7 +1222,7 @@ class Response:
             raise StreamConsumed()
         if self.is_closed:
             raise ResponseClosed()
-        if not isinstance(self.stream, typing.Iterable):
+        if not isinstance(self.stream, SyncByteStream):
             raise RuntimeError("Attempted to call a sync iterator on an async stream.")
 
         self.is_stream_consumed = True
@@ -1318,8 +1318,8 @@ class Response:
             raise StreamConsumed()
         if self.is_closed:
             raise ResponseClosed()
-        if not isinstance(self.stream, typing.AsyncIterable):
-            raise RuntimeError("Attempted to call a async iterator on a sync stream.")
+        if not isinstance(self.stream, AsyncByteStream):
+            raise RuntimeError("Attempted to call an async iterator on an sync stream.")
 
         self.is_stream_consumed = True
         self._num_bytes_downloaded = 0

```

</details>

---

## Case 22 — `0eea9dc58ea4a754`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** blinker is required, signals are always available
- **commit** https://github.com/pallets/flask/commit/9cb1a7a52d7927071e2b737d52f902f006969e82
- **doc** `docs/signals.rst`
- **code** `src/flask/__init__.py`
- **shared identifiers** `signals`, `flask`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/signals.rst b/docs/signals.rst
index 27630de6..3ba12a5a 100644
--- a/docs/signals.rst
+++ b/docs/signals.rst
@@ -1,33 +1,28 @@
 Signals
 =======
 
-.. versionadded:: 0.6
-
-Starting with Flask 0.6, there is integrated support for signalling in
-Flask.  This support is provided by the excellent `blinker`_ library and
-will gracefully fall back if it is not available.
-
-What are signals?  Signals help you decouple applications by sending
-notifications when actions occur elsewhere in the core framework or
-another Flask extensions.  In short, signals allow certain senders to
-notify subscribers that something happened.
-
-Flask comes with a couple of signals and other extensions might provide
-more.  Also keep in mind that signals are intended to notify subscribers
-and should not encourage subscribers to modify data.  You will notice that
-there are signals that appear to do the same thing like some of the
-builtin decorators do (eg: :data:`~flask.request_started` is very similar
-to :meth:`~flask.Flask.before_request`).  However, there are differences in
-how they work.  The core :meth:`~flask.Flask.before_request` handler, for
-example, is executed in a specific order and is able to abort the request
-early by returning a response.  In contrast all signal handlers are
-executed in undefined order and do not modify any data.
-
-The big advantage of signals over handlers is that you can safely
-subscribe to them for just a split second.  These temporary
-subscriptions are helpful for unit testing for example.  Say you want to
-know what templates were rendered as part of a request: signals allow you
-to do exactly that.
+Signals are a lightweight way to notify subscribers of certain events during the
+lifecycle of the application and each request. When an event occurs, it emits the
+signal, which calls each subscriber.
+
+Signals are implemented by the `Blinker`_ library. See its documentation for detailed
+information. Flask provides some built-in signals. Extensions may provide their own.
+
+Many signals mirror Flask's decorator-based callbacks with similar names. For example,
+the :data:`.request_started` signal is similar to the :meth:`~.Flask.before_request`
+decorator. The advantage of signals over handlers is that they can be subscribed to
+temporarily, and can't directly affect the application. This is useful for testing,
+metrics, auditing, and more. For example, if you want to know what templates were
+rendered at what parts of what requests, there is a signal that will notify you of that
+information.
+
+
+Core Signals
+------------
+
+See :ref:`core-signals-list` for a list of all built-in signals. The :doc:`lifecycle`
+page also describes the order that signals and decorators execute.
+
 
 Subscribing to Signals
 ----------------------
@@ -99,11 +94,6 @@ The example above would then look like this::
         ...
         template, context = templates[0]
 
-.. admonition:: Blinker API Changes
-
-   The :meth:`~blinker.base.Signal.connected_to` method arrived in Blinker
-   with version 1.1.
-
 Creating Signals
 ----------------
 
@@ -123,12 +113,6 @@ The name for the signal here makes it unique and also simplifies
 debugging.  You can access the name of the signal with the
 :attr:`~blinker.base.NamedSignal.name` attribute.
 
-.. admonition:: For Extension Developers
-
-   If you are writing a Flask extension and you want to gracefully degrade for
-   missing blinker installations, you can do so by using the
-   :class:`flask.signals.Namespace` class.
-
 .. _signals-sending:
 
 Sending Signals
@@ -170,7 +154,7 @@ in :ref:`signals-sending` and the :data:`~flask.request_tearing_down` signal.
 Decorator Based Signal Subscriptions
 ------------------------------------
 
-With Blinker 1.1 you can also easily subscribe to signals by using the new
+You can also easily subscribe to signals by using the
 :meth:`~blinker.base.NamedSignal.connect_via` decorator::
 
     from flask import template_rendered
@@ 
```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/src/flask/__init__.py b/src/flask/__init__.py
index 2361bdb4..4441b95a 100644
--- a/src/flask/__init__.py
+++ b/src/flask/__init__.py
@@ -32,7 +32,6 @@ from .signals import message_flashed as message_flashed
 from .signals import request_finished as request_finished
 from .signals import request_started as request_started
 from .signals import request_tearing_down as request_tearing_down
-from .signals import signals_available as signals_available
 from .signals import template_rendered as template_rendered
 from .templating import render_template as render_template
 from .templating import render_template_string as render_template_string
@@ -89,4 +88,15 @@ def __getattr__(name):
         )
         return Markup
 
+    if name == "signals_available":
+        import warnings
+
+        warnings.warn(
+            "'signals_available' is deprecated and will be removed in Flask 2.4."
+            " Signals are always available",
+            DeprecationWarning,
+            stacklevel=2,
+        )
+        return True
+
     raise AttributeError(name)

```

</details>

---

## Case 23 — `4f67609c6526c970`

- **repo** `pydantic/pydantic` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Update internal links to be compatible with versions (#6271)
- **commit** https://github.com/pydantic/pydantic/commit/e0c0fe8cd6b6a1a5fdd43ab92d9814b278e324ad
- **doc** `docs/usage/fields.md`
- **code** `pydantic/config.py`
- **shared identifiers** `model_config`, `config`, `alias`, `model`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/usage/fields.md b/docs/usage/fields.md
index a06e54311..26e6b94cb 100644
--- a/docs/usage/fields.md
+++ b/docs/usage/fields.md
@@ -1,7 +1,7 @@
 
 The `Field` function is used to customize and add metadata to fields of models.
 
-See the [`Field`](/api/fields/#pydantic.fields.Field) API reference for additional details.
+See the [`Field`][pydantic.fields.Field] API reference for additional details.
 
 ## Default values
 
@@ -72,7 +72,7 @@ print(user.model_dump(by_alias=True))  # (2)!
 1. The alias `'username'` is used for instance creation and validation.
 2. We are using `model_dump` to convert the model into a serializable format.
 
-    You can see more details about [`model_dump`](/api/main/#pydantic.main.BaseModel.model_dump) in the API reference.
+    You can see more details about [`model_dump`][pydantic.main.BaseModel.model_dump] in the API reference.
 
     Note that the `by_alias` keyword argument defaults to `False`, and must be specified explicitly to dump
     models using the field (serialization) aliases.
@@ -123,8 +123,8 @@ In case you use `alias` together with `validation_alias` or `serialization_alias
 the `validation_alias` will have priority over `alias` for validation, and `serialization_alias` will have priority
 over `alias` for serialization.
 
-You can read more about [Alias Precedence](/usage/model_config/#alias-precedence) in the
-[Model Config](/usage/model_config/) documentation.
+You can read more about [Alias Precedence](model_config.md#alias-precedence) in the
+[Model Config](model_config.md) documentation.
 
 
 ??? tip "VSCode and Pyright users"
@@ -145,7 +145,7 @@ You can read more about [Alias Precedence](/usage/model_config/#alias-precedence
     1. VSCode will NOT show a warning here.
 
     When the `'alias'` keyword argument is specified, even if you set `populate_by_name` to `True` in the
-    [Model Config](/usage/model_config/#populate-by-name), VSCode will show a warning when instantiating
+    [Model Config](model_config.md#populate-by-name), VSCode will show a warning when instantiating
     a model using the field name (though it will work at runtime) — in this case, `'name'`:
 
     ```py
@@ -232,7 +232,7 @@ print(user)
 
 1. We are using `model_validate` to validate a dictionary using the field aliases.
 
-    You can see more details about [`model_validate`](/api/main/#pydantic.main.BaseModel.model_validate) in the API reference.
+    You can see more details about [`model_validate`][pydantic.main.BaseModel.model_validate] in the API reference.
 
 In the `'first_name'` field, we are using the alias `'names'` and the index `0` to specify the path to the first name.
 In the `'last_name'` field, we are using the alias `'names'` and the index `1` to specify the path to the last name.
@@ -728,10 +728,10 @@ print(User.model_json_schema())
 TODO: Add `final`, and `alias_priority` parameters.
 
 [JSON Schema Draft 2020-12]: https://json-schema.org/understanding-json-schema/reference/numeric.html#numeric-types
-[Discriminated Unions]: /usage/types/unions/#discriminated-unions-aka-tagged-unions
-[Helper Functions]: /usage/models/#helper-functions
-[Models]: /usage/models/
+[Discriminated Unions]: types/unions.md#discriminated-unions-aka-tagged-unions
+[Helper Functions]: models.md#helper-functions
+[Models]: models.md
 [init-only field]: https://docs.python.org/3/library/dataclasses.html#init-only-variables
 [frozen dataclass documentation]: https://docs.python.org/3/library/dataclasses.html#frozen-instances
-[Validate Assignment]: /usage/models/#validate-assignment
-[Exporting Models]: /usage/exporting_models/#model-and-field-level-include-and-exclude
+[Validate Assignment]: models.md#validate-assignment
+[Exporting Models]: exporting_models.md#model-and-field-level-include-and-exclude

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/pydantic/config.py b/pydantic/config.py
index 30bfa74db..7ace91c98 100644
--- a/pydantic/config.py
+++ b/pydantic/config.py
@@ -59,7 +59,7 @@ class ConfigDict(TypedDict, total=False):
             - `'ignore'` will silently ignore any extra attributes.
             - `'allow'` will assign the attributes to the model.
 
-            See [the dedicated section](/usage/model_config#extra-attributes).
+            See [Extra Attributes](../usage/model_config.md#extra-attributes) for details.
         frozen: Whether or not models are faux-immutable, i.e. whether `__setattr__` is allowed, and also generates
             a `__hash__()` method for the model. This makes instances of the model potentially hashable if all the
             attributes are hashable. Defaults to `False`.
@@ -79,7 +79,7 @@ class ConfigDict(TypedDict, total=False):
             checking if the value is an instance of the type). If `False`, `RuntimeError` will be raised on model
             declaration. Defaults to `False`.
 
-            See [the dedicated section](/usage/model_config/#arbitrary-types-allowed).
+            See [Arbitrary Types Allowed](../usage/model_config.md#arbitrary-types-allowed) for details.
         from_attributes: Whether to allow model creation from object attributes. Defaults to `False`.
 
             !!! note
@@ -87,7 +87,7 @@ class ConfigDict(TypedDict, total=False):
         loc_by_alias: Whether to use the alias for error `loc`s. Defaults to `True`.
         alias_generator: a callable that takes a field name and returns an alias for it.
 
-            See [the dedicated section](/usage/model_config#alias-generator).
+            See [Alias Generator](../usage/model_config.md#alias-generator) for details.
         ignored_types: A tuple of types that may occur as values of class attributes without annotations. This is
             typically used for custom descriptors (classes that behave like `property`). If an attribute is set on a
             class without an annotation and has a type that is not in this tuple (or otherwise recognized by
@@ -104,7 +104,7 @@ class ConfigDict(TypedDict, total=False):
             - `'subclass-instances'` will revalidate models and dataclasses during validation if the instance is a
                 subclass of the model or dataclass
 
-            See [the dedicated section](/usage/model_config#revalidate-instances).
+            See [Revalidate Instances](../usage/model_config.md#revalidate-instances) for details.
         ser_json_timedelta: The format of JSON serialized timedeltas. Accepts the string values of `'iso8601'` and
             `'float'`. Defaults to `'iso8601'`.
 
@@ -119,10 +119,10 @@ class ConfigDict(TypedDict, total=False):
         protected_namespaces: A `tuple` of strings that prevent model to have field which conflict with them.
             Defaults to `('model_', )`).
 
-            See [the dedicated section](/usage/model_config#protected-namespaces).
+            See [Protected Namespaces](../usage/model_config.md#protected-namespaces) for details.
         hide_input_in_errors: Whether to hide inputs when printing errors. Defaults to `False`.
 
-            See [the dedicated section](/usage/model_config#hide-input-in-errors).
+            See [Hide Input in Errors](../usage/model_config.md#hide-input-in-errors).
     """
 
     title: str | None

```

</details>

---

## Case 24 — `8c5f05476eef28d9`

- **repo** `pydantic/pydantic` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Rework `__get_pydantic_core_schema__` APIs (#5490)
- **commit** https://github.com/pydantic/pydantic/commit/86e442525bc7faec6cebd9a50933b14ee6578197
- **doc** `docs/usage/schema.md`
- **code** `pydantic/networks.py`
- **shared identifiers** `get_pydantic_core_schema`, `core_schema`, `coreschema`, `validator`, `callable`, `pydantic`, `validate`, `handler`, `fields`, `schema`, `source`, `typing`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/usage/schema.md b/docs/usage/schema.md
index 6a3ebf17e..93255742b 100644
--- a/docs/usage/schema.md
+++ b/docs/usage/schema.md
@@ -355,15 +355,22 @@ Defaults can be set outside `Annotated` as the assigned value or with `Field.def
 
 For versions of Python prior to 3.9, `typing_extensions.Annotated` can be used.
 
-## Modifying schema in custom types and custom fields
+## Modifying the schema
 
-Custom types (used as `field_name: TheType` or `field_name: Annotated[TheType, ...]`) can *override* schema generation by implementing a `__get_pydantic_core_schema__` method.
-This method receives a single positional argument with the type annotation that corresponds to this type (so in the case of `TheType[T][int]` it would be `TheType[int]`).
-All implementation of `__get_pydantic_core_schema__` *must* accept `**_kwargs` and ignore them; they are used for private implementations.
+Custom types (used as `field_name: TheType` or `field_name: Annotated[TheType, ...]`) as well as Annotated metadata (used as `field_name: Annotated[int, SomeMetadata]`)
+can modify or override the generated schema by implementing `__get_pydantic_core_schema__`.
+This method receives two positional arguments:
+
+1. The type annotation that corresponds to this type (so in the case of `TheType[T][int]` it would be `TheType[int]`).
+2. A handler / callback to call the next implementer of `__get_pydantic_core_schema__`.
+
+The handler system works just like `mode='wrap'` validators. In this case the input is the type and the output is a `CoreSchema`.
+
+Here is an example of a custom type that *overrides* the generated core schema:
 
 ```py
 from dataclasses import dataclass
-from typing import Any, Dict, List
+from typing import Any, Callable, Dict, List, Type
 
 from pydantic_core import core_schema
 
@@ -380,7 +387,7 @@ class CompressedString:
 
     @classmethod
     def __get_pydantic_core_schema__(
-        cls, source: Any, **_kwargs: Any
+        cls, source: Type[Any], handler: Callable[[Type[Any]], core_schema.CoreSchema]
     ) -> core_schema.CoreSchema:
         assert source is CompressedString
         return core_schema.no_info_after_validator_function(
@@ -426,12 +433,13 @@ print(MyModel(value='fox fox fox dog fox').model_dump(mode='json'))
 #> {'value': 'fox fox fox dog fox'}
 ```
 
-Annotations / constraints can implement `__modify_pydantic_core_schema__` to *modify or override* the core schema that is being generated.
-This method receives a single positional argument `schema: pydantic_core.core_schema.CoreSchema` which you can wrap or ignore and return a completely new schema.
+Since Pydantic would not know how to generate a schema for `CompressedString` if you call `handler(source)` in it's `__get_pydantic_core_schema__` method you would get a `pydantic.errors.PydanticSchemaGenerationError` error. This will be the case for most custom types so you almost never want to call into `handler` for custom types.
+
+The process for Annotated metadata is much the same except that you can generally call into `handler` to have Pydantic handle generating the schema.
 
 ```py
 from dataclasses import dataclass
-from typing import Sequence
+from typing import Any, Callable, Sequence, Type
 
 from pydantic_core import core_schema
 from typing_extensions import Annotated
@@ -443,10 +451,12 @@ from pydantic import BaseModel, ValidationError
 class RestrictCharacters:
     alphabet: Sequence[str]
 
-    def __modify_pydantic_core_schema__(
-        self,
-        schema: core_schema.CoreSchema,
+    def __get_pydantic_core_schema__(
+        self, source: Type[Any], handler: Callable[[Any], core_schema.CoreSchema]
     ) -> core_schema.CoreSchema:
+        if not self.alphabet:
+            raise ValueError('Alphabet may not be empty')
+        schema = handler(source)  # get the CoreSchema from the type / inner constraints
         if schema['type'] != 'str':
             raise TypeError('RestrictCharacters can only be applied to strings')

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/pydantic/networks.py b/pydantic/networks.py
index 3530bd429..16938467a 100644
--- a/pydantic/networks.py
+++ b/pydantic/networks.py
@@ -3,7 +3,7 @@ from __future__ import annotations as _annotations
 import dataclasses as _dataclasses
 import re
 from ipaddress import IPv4Address, IPv4Interface, IPv4Network, IPv6Address, IPv6Interface, IPv6Network
-from typing import TYPE_CHECKING, Any
+from typing import TYPE_CHECKING, Any, Callable
 
 from pydantic_core import MultiHostUrl, PydanticCustomError, Url, core_schema
 from typing_extensions import Annotated, TypeAlias
@@ -133,14 +133,10 @@ else:
     class EmailStr:
         @classmethod
         def __get_pydantic_core_schema__(
-            cls, schema: core_schema.CoreSchema | None = None, **_kwargs: Any
+            cls, source: type[Any], handler: Callable[[Any], core_schema.CoreSchema]
         ) -> core_schema.CoreSchema:
             import_email_validator()
-            if schema is None:
-                return core_schema.general_after_validator_function(cls.validate, core_schema.str_schema())
-            else:
-                assert schema['type'] == 'str', 'EmailStr must be used with string fields'
-                return core_schema.general_after_validator_function(cls.validate, schema)
+            return core_schema.general_after_validator_function(cls.validate, core_schema.str_schema())
 
         @classmethod
         def __pydantic_modify_json_schema__(cls, field_schema: dict[str, Any]) -> dict[str, Any]:
@@ -168,7 +164,9 @@ class NameEmail(_repr.Representation):
         return field_schema
 
     @classmethod
-    def __get_pydantic_core_schema__(cls, **_kwargs: Any) -> core_schema.AfterValidatorFunctionSchema:
+    def __get_pydantic_core_schema__(
+        cls, source: type[Any], handler: Callable[[Any], core_schema.CoreSchema]
+    ) -> core_schema.CoreSchema:
         import_email_validator()
         return core_schema.general_after_validator_function(
             cls._validate,
@@ -208,7 +206,9 @@ class IPvAnyAddress:
         return field_schema
 
     @classmethod
-    def __get_pydantic_core_schema__(cls, **_kwargs: Any) -> core_schema.PlainValidatorFunctionSchema:
+    def __get_pydantic_core_schema__(
+        cls, source: type[Any], handler: Callable[[Any], core_schema.CoreSchema]
+    ) -> core_schema.CoreSchema:
         return core_schema.general_plain_validator_function(cls._validate)
 
     @classmethod
@@ -236,7 +236,9 @@ class IPvAnyInterface:
         return field_schema
 
     @classmethod
-    def __get_pydantic_core_schema__(cls, **_kwargs: Any) -> core_schema.PlainValidatorFunctionSchema:
+    def __get_pydantic_core_schema__(
+        cls, source: type[Any], handler: Callable[[Any], core_schema.CoreSchema]
+    ) -> core_schema.CoreSchema:
         return core_schema.general_plain_validator_function(cls._validate)
 
     @classmethod
@@ -266,7 +268,9 @@ class IPvAnyNetwork:
         return field_schema
 
     @classmethod
-    def __get_pydantic_core_schema__(cls, **_kwargs: Any) -> core_schema.PlainValidatorFunctionSchema:
+    def __get_pydantic_core_schema__(
+        cls, source: type[Any], handler: Callable[[Any], core_schema.CoreSchema]
+    ) -> core_schema.CoreSchema:
         return core_schema.general_plain_validator_function(cls._validate)
 
     @classmethod

```

</details>

---

## Case 25 — `57a43fc36bff3dc6`

- **repo** `pallets/flask` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** use app.name as app.logger name
- **commit** https://github.com/pallets/flask/commit/df470aecb96efbcb17ca76e73196c25c38ce6d17
- **doc** `docs/errorhandling.rst`
- **code** `src/flask/app.py`
- **shared identifiers** `logging`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/errorhandling.rst b/docs/errorhandling.rst
index 9359acf8..2f4b7335 100644
--- a/docs/errorhandling.rst
+++ b/docs/errorhandling.rst
@@ -231,7 +231,7 @@ errors, use ``getattr`` to get access it for compatibility.
 Logging
 -------
 
-See :ref:`logging` for information on how to log exceptions, such as by
+See :doc:`/logging` for information on how to log exceptions, such as by
 emailing them to admins.
 
 

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/src/flask/app.py b/src/flask/app.py
index cead46d7..e596fe57 100644
--- a/src/flask/app.py
+++ b/src/flask/app.py
@@ -653,22 +653,26 @@ class Flask(_PackageBoundObject):
 
     @locked_cached_property
     def logger(self):
-        """The ``'flask.app'`` logger, a standard Python
-        :class:`~logging.Logger`.
+        """A standard Python :class:`~logging.Logger` for the app, with
+        the same name as :attr:`name`.
 
-        In debug mode, the logger's :attr:`~logging.Logger.level` will be set
-        to :data:`~logging.DEBUG`.
+        In debug mode, the logger's :attr:`~logging.Logger.level` will
+        be set to :data:`~logging.DEBUG`.
 
-        If there are no handlers configured, a default handler will be added.
-        See :ref:`logging` for more information.
+        If there are no handlers configured, a default handler will be
+        added. See :doc:`/logging` for more information.
 
-        .. versionchanged:: 1.0
+        .. versionchanged:: 1.1.0
+            The logger takes the same name as :attr:`name` rather than
+            hard-coding ``"flask.app"``.
+
+        .. versionchanged:: 1.0.0
             Behavior was simplified. The logger is always named
-            ``flask.app``. The level is only set during configuration, it
-            doesn't check ``app.debug`` each time. Only one format is used,
-            not different ones depending on ``app.debug``. No handlers are
-            removed, and a handler is only added if no handlers are already
-            configured.
+            ``"flask.app"``. The level is only set during configuration,
+            it doesn't check ``app.debug`` each time. Only one format is
+            used, not different ones depending on ``app.debug``. No
+            handlers are removed, and a handler is only added if no
+            handlers are already configured.
 
         .. versionadded:: 0.3
         """

```

</details>

---

