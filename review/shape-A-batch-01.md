# Drift label review — 20 cases (seed 7)

For each case, replace `VERDICT: ?` with one of:

- `drift` — the doc said something untrue about the code, and this commit corrected it
- `new` — the doc was documenting something that did not exist yet (feature + its docs)
- `cosmetic` — wording, formatting or a link -- nothing factual changed
- `unrelated` — the doc change and the code change are not about the same thing
- `unclear` — cannot tell from these diffs alone

The question is always: **at the parent commit, was this documentation false about the code?** Not whether the commit improved the docs — whether what it replaced was wrong.

---

## Case 1 — `a90fb09268690fe3`

- **repo** `psf/requests` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** new requests namespace
- **commit** https://github.com/psf/requests/commit/7f14db17c8612aed71a181b084455b71e130ffc8
- **doc** `docs/user/install.rst`
- **code** `requests/sessions.py`
- **shared identifiers** `kennethreitz`, `github`, `https`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/user/install.rst b/docs/user/install.rst
index 922c489b..96884558 100644
--- a/docs/user/install.rst
+++ b/docs/user/install.rst
@@ -22,7 +22,7 @@ Get the Source Code
 -------------------
 
 Requests is actively developed on GitHub, where the code is
-`always available <https://github.com/kennethreitz/requests>`_.
+`always available <https://github.com/requests/requests>`_.
 
 You can either clone the public repository::
 

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/requests/sessions.py b/requests/sessions.py
index 9b74f5dd..82a978c2 100755
--- a/requests/sessions.py
+++ b/requests/sessions.py
@@ -164,9 +164,9 @@ class SessionRedirectMixin(object):
 
             self.rebuild_method(prepared_request, resp)
 
-            # https://github.com/kennethreitz/requests/issues/1084
+            # https://github.com/requests/requests/issues/1084
             if resp.status_code not in (codes.temporary_redirect, codes.permanent_redirect):
-                # https://github.com/kennethreitz/requests/issues/3490
+                # https://github.com/requests/requests/issues/3490
                 purged_headers = ('Content-Length', 'Content-Type', 'Transfer-Encoding')
                 for header in purged_headers:
                     prepared_request.headers.pop(header, None)

```

</details>

---

## Case 2 — `b976f3726c5ca7d4`

- **repo** `psf/requests` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Prefer https:// for URLs throughout project
- **commit** https://github.com/psf/requests/commit/b0ad2499c8641d29affc90f565e6628d333d2a96
- **doc** `docs/user/advanced.rst`
- **code** `requests/utils.py`
- **shared identifiers** `python`, `https`, `http`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/user/advanced.rst b/docs/user/advanced.rst
index 2076fc00..9a615aae 100644
--- a/docs/user/advanced.rst
+++ b/docs/user/advanced.rst
@@ -25,8 +25,8 @@ Let's persist some cookies across requests::
 
     s = requests.Session()
 
-    s.get('http://httpbin.org/cookies/set/sessioncookie/123456789')
-    r = s.get('http://httpbin.org/cookies')
+    s.get('https://httpbin.org/cookies/set/sessioncookie/123456789')
+    r = s.get('https://httpbin.org/cookies')
 
     print(r.text)
     # '{"cookies": {"sessioncookie": "123456789"}}'
@@ -40,7 +40,7 @@ is done by providing data to the properties on a Session object::
     s.headers.update({'x-test': 'true'})
 
     # both 'x-test' and 'x-test2' are sent
-    s.get('http://httpbin.org/headers', headers={'x-test2': 'true'})
+    s.get('https://httpbin.org/headers', headers={'x-test2': 'true'})
 
 
 Any dictionaries that you pass to a request method will be merged with the
@@ -53,11 +53,11 @@ with the first request, but not the second::
 
     s = requests.Session()
 
-    r = s.get('http://httpbin.org/cookies', cookies={'from-my': 'browser'})
+    r = s.get('https://httpbin.org/cookies', cookies={'from-my': 'browser'})
     print(r.text)
     # '{"cookies": {"from-my": "browser"}}'
 
-    r = s.get('http://httpbin.org/cookies')
+    r = s.get('https://httpbin.org/cookies')
     print(r.text)
     # '{"cookies": {}}'
 
@@ -69,7 +69,7 @@ If you want to manually add cookies to your session, use the
 Sessions can also be used as context managers::
 
     with requests.Session() as s:
-        s.get('http://httpbin.org/cookies/set/sessioncookie/123456789')
+        s.get('https://httpbin.org/cookies/set/sessioncookie/123456789')
 
 This will make sure the session is closed as soon as the ``with`` block is
 exited, even if unhandled exceptions occurred.
@@ -97,7 +97,7 @@ The ``Response`` object contains all of the information returned by the server a
 also contains the ``Request`` object you created originally. Here is a simple
 request to get some very important information from Wikipedia's servers::
 
-    >>> r = requests.get('http://en.wikipedia.org/wiki/Monty_Python')
+    >>> r = requests.get('https://en.wikipedia.org/wiki/Monty_Python')
 
 If we want to access the headers the server sent back to us, we do this::
 
@@ -323,7 +323,7 @@ inefficiency with connections. If you find yourself partially reading request
 bodies (or not reading them at all) while using ``stream=True``, you should
 make the request within a ``with`` statement to ensure it's always closed::
 
-    with requests.get('http://httpbin.org/get', stream=True) as r:
+    with requests.get('https://httpbin.org/get', stream=True) as r:
         # Do things with the response here.
 
 .. _keep-alive:
@@ -393,7 +393,7 @@ upload image files to an HTML form with a multiple file field 'images'::
 
 To do that, just set files to a list of tuples of ``(form_field_name, file_info)``::
 
-    >>> url = 'http://httpbin.org/post'
+    >>> url = 'https://httpbin.org/post'
     >>> multiple_files = [
             ('images', ('foo.png', open('foo.png', 'rb'), 'image/png')),
             ('images', ('bar.png', open('bar.png', 'rb'), 'image/png'))]
@@ -455,13 +455,13 @@ anything, nothing else is affected.
 
 Let's print some request method arguments at runtime::
 
-    >>> requests.get('http://httpbin.org', hooks={'response': print_url})
-    http://httpbin.org
+    >>> requests.get('https://httpbin.org/', hooks={'response': print_url})
+    https://httpbin.org/
     <Response [200]>
 
 You can add multiple hooks to a single request.  Let's call two hooks at once::
 
-    >>> r = requests.get('http://httpbin.org', hooks={'response': [print_url, record_hook]})
+    >>> r = requests.get('https://httpbin.org/', hooks={'response': [print_url, record_hook]})
     >>> r.hook_called
     True
 
@@ -470,8 +470,8 @@ be called on every request made to the session.  For example::
 
    >>> s = requests.Session()
    >>> s.hooks['respo
```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/requests/utils.py b/requests/utils.py
index 6892713a..67197312 100644
--- a/requests/utils.py
+++ b/requests/utils.py
@@ -176,7 +176,7 @@ def get_netrc_auth(url, raise_errors=False):
                 loc = os.path.expanduser('~/{0}'.format(f))
             except KeyError:
                 # os.path.expanduser can fail when $HOME is undefined and
-                # getpwuid fails. See http://bugs.python.org/issue20164 &
+                # getpwuid fails. See https://bugs.python.org/issue20164 &
                 # https://github.com/requests/requests/issues/1846
                 return
 

```

</details>

---

## Case 3 — `fc67d8f92be44150`

- **repo** `psf/requests` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Prefer https:// for URLs throughout project
- **commit** https://github.com/psf/requests/commit/b0ad2499c8641d29affc90f565e6628d333d2a96
- **doc** `docs/user/quickstart.rst`
- **code** `requests/sessions.py`
- **shared identifiers** `httpbin`, `https`, `tools`, `html`, `http`, `ietf`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/user/quickstart.rst b/docs/user/quickstart.rst
index 699c0ffd..1a75b5ce 100644
--- a/docs/user/quickstart.rst
+++ b/docs/user/quickstart.rst
@@ -39,15 +39,15 @@ get all the information we need from this object.
 Requests' simple API means that all forms of HTTP request are as obvious. For
 example, this is how you make an HTTP POST request::
 
-    >>> r = requests.post('http://httpbin.org/post', data = {'key':'value'})
+    >>> r = requests.post('https://httpbin.org/post', data = {'key':'value'})
 
 Nice, right? What about the other HTTP request types: PUT, DELETE, HEAD and
 OPTIONS? These are all just as simple::
 
-    >>> r = requests.put('http://httpbin.org/put', data = {'key':'value'})
-    >>> r = requests.delete('http://httpbin.org/delete')
-    >>> r = requests.head('http://httpbin.org/get')
-    >>> r = requests.options('http://httpbin.org/get')
+    >>> r = requests.put('https://httpbin.org/put', data = {'key':'value'})
+    >>> r = requests.delete('https://httpbin.org/delete')
+    >>> r = requests.head('https://httpbin.org/get')
+    >>> r = requests.options('https://httpbin.org/get')
 
 That's all well and good, but it's also only the start of what Requests can
 do.
@@ -65,12 +65,12 @@ using the ``params`` keyword argument. As an example, if you wanted to pass
 following code::
 
     >>> payload = {'key1': 'value1', 'key2': 'value2'}
-    >>> r = requests.get('http://httpbin.org/get', params=payload)
+    >>> r = requests.get('https://httpbin.org/get', params=payload)
 
 You can see that the URL has been correctly encoded by printing the URL::
 
     >>> print(r.url)
-    http://httpbin.org/get?key2=value2&key1=value1
+    https://httpbin.org/get?key2=value2&key1=value1
 
 Note that any dictionary key whose value is ``None`` will not be added to the
 URL's query string.
@@ -79,9 +79,9 @@ You can also pass a list of items as a value::
 
     >>> payload = {'key1': 'value1', 'key2': ['value2', 'value3']}
 
-    >>> r = requests.get('http://httpbin.org/get', params=payload)
+    >>> r = requests.get('https://httpbin.org/get', params=payload)
     >>> print(r.url)
-    http://httpbin.org/get?key1=value1&key2=value2&key2=value3
+    https://httpbin.org/get?key1=value1&key2=value2&key2=value3
 
 Response Content
 ----------------
@@ -233,7 +233,7 @@ dictionary of data will automatically be form-encoded when the request is made::
 
     >>> payload = {'key1': 'value1', 'key2': 'value2'}
 
-    >>> r = requests.post("http://httpbin.org/post", data=payload)
+    >>> r = requests.post("https://httpbin.org/post", data=payload)
     >>> print(r.text)
     {
       ...
@@ -250,9 +250,9 @@ as values. This is particularly useful when the form has multiple elements that
 use the same key::
 
     >>> payload_tuples = [('key1', 'value1'), ('key1', 'value2')]
-    >>> r1 = requests.post('http://httpbin.org/post', data=payload_tuples)
+    >>> r1 = requests.post('https://httpbin.org/post', data=payload_tuples)
     >>> payload_dict = {'key1': ['value1', 'value2']}
-    >>> r2 = requests.post('http://httpbin.org/post', data=payload_dict)
+    >>> r2 = requests.post('https://httpbin.org/post', data=payload_dict)
     >>> print(r1.text)
     {
       ...
@@ -296,7 +296,7 @@ POST a Multipart-Encoded File
 
 Requests makes it simple to upload Multipart-encoded files::
 
-    >>> url = 'http://httpbin.org/post'
+    >>> url = 'https://httpbin.org/post'
     >>> files = {'file': open('report.xls', 'rb')}
 
     >>> r = requests.post(url, files=files)
@@ -311,7 +311,7 @@ Requests makes it simple to upload Multipart-encoded files::
 
 You can set the filename, content_type and headers explicitly::
 
-    >>> url = 'http://httpbin.org/post'
+    >>> url = 'https://httpbin.org/post'
     >>> files = {'file': ('report.xls', open('report.xls', 'rb'), 'application/vnd.ms-excel', {'Expires': '0'})}
 
     >>> r = requests.post(url, files=files)
@@ -326,7 +326,7 @@ You can set the filename, content_type and headers explicitly::

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/requests/sessions.py b/requests/sessions.py
index 27d0e971..b124d793 100644
--- a/requests/sessions.py
+++ b/requests/sessions.py
@@ -311,7 +311,7 @@ class SessionRedirectMixin(object):
         """
         method = prepared_request.method
 
-        # http://tools.ietf.org/html/rfc7231#section-6.4.4
+        # https://tools.ietf.org/html/rfc7231#section-6.4.4
         if response.status_code == codes.see_other and method != 'HEAD':
             method = 'GET'
 
@@ -337,13 +337,13 @@ class Session(SessionRedirectMixin):
 
       >>> import requests
       >>> s = requests.Session()
-      >>> s.get('http://httpbin.org/get')
+      >>> s.get('https://httpbin.org/get')
       <Response [200]>
 
     Or as a context manager::
 
       >>> with requests.Session() as s:
-      >>>     s.get('http://httpbin.org/get')
+      >>>     s.get('https://httpbin.org/get')
       <Response [200]>
     """
 

```

</details>

---

## Case 4 — `402787a4fdcdb269`

- **repo** `psf/requests` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Remove remaining references to removed, vendored packages (#4499)
- **commit** https://github.com/psf/requests/commit/265ef609d5903151374fba480aa81aafe68126ff
- **doc** `docs/api.rst`
- **code** `requests/help.py`
- **shared identifiers** `packages`, `urllib3`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/api.rst b/docs/api.rst
index c3e00e54..ef84bf60 100644
--- a/docs/api.rst
+++ b/docs/api.rst
@@ -181,7 +181,7 @@ API Changes
 
       logging.basicConfig() # you need to initialize logging, otherwise you will not see anything from requests
       logging.getLogger().setLevel(logging.DEBUG)
-      requests_log = logging.getLogger("requests.packages.urllib3")
+      requests_log = logging.getLogger("urllib3")
       requests_log.setLevel(logging.DEBUG)
       requests_log.propagate = True
 

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/requests/help.py b/requests/help.py
index 5440ee61..06e06b2a 100644
--- a/requests/help.py
+++ b/requests/help.py
@@ -13,7 +13,7 @@ import chardet
 from . import __version__ as requests_version
 
 try:
-    from .packages.urllib3.contrib import pyopenssl
+    from urllib3.contrib import pyopenssl
 except ImportError:
     pyopenssl = None
     OpenSSL = None

```

</details>

---

## Case 5 — `3b7710af3aaa1c49`

- **repo** `psf/requests` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Switch LGPL'd chardet for MIT licensed charset_normalizer (#5797)
- **commit** https://github.com/psf/requests/commit/2ed84f55b22f19a1e1e8eea2e50963dce62052d3
- **doc** `docs/user/advanced.rst`
- **code** `requests/models.py`
- **shared identifiers** `charset_normalizer`, `normalizer`, `encoding`, `chardet`, `charset`, `library`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/user/advanced.rst b/docs/user/advanced.rst
index aa4b1ddb..34d400d5 100644
--- a/docs/user/advanced.rst
+++ b/docs/user/advanced.rst
@@ -697,10 +697,22 @@ Encodings
 When you receive a response, Requests makes a guess at the encoding to
 use for decoding the response when you access the :attr:`Response.text
 <requests.Response.text>` attribute. Requests will first check for an
-encoding in the HTTP header, and if none is present, will use `chardet
-<https://pypi.org/project/chardet/>`_ to attempt to guess the encoding.
-
-The only time Requests will not do this is if no explicit charset
+encoding in the HTTP header, and if none is present, will use
+`charset_normalizer <https://pypi.org/project/charset_normalizer/>`_
+or `chardet <https://github.com/chardet/chardet>`_ to attempt to
+guess the encoding.
+
+If ``chardet`` is installed, ``requests`` uses it, however for python3
+``chardet`` is no longer a mandatory dependency. The ``chardet``
+library is an LGPL-licenced dependency and some users of requests
+cannot depend on mandatory LGPL-licensed dependencies.
+
+When you install ``request`` without specifying ``[use_chardet_on_py3]]`` extra,
+and ``chardet`` is not already installed, ``requests`` uses ``charset-normalizer``
+(MIT-licensed) to guess the encoding. For Python 2, ``requests`` uses only
+``chardet`` and is a mandatory dependency there.
+
+The only time Requests will not guess the encoding is if no explicit charset
 is present in the HTTP headers **and** the ``Content-Type``
 header contains ``text``. In this situation, `RFC 2616
 <https://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html#sec3.7.1>`_ specifies

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/requests/models.py b/requests/models.py
index 93b901b4..aa6fb86e 100644
--- a/requests/models.py
+++ b/requests/models.py
@@ -731,7 +731,7 @@ class Response(object):
 
     @property
     def apparent_encoding(self):
-        """The apparent encoding, provided by the chardet library."""
+        """The apparent encoding, provided by the charset_normalizer or chardet libraries."""
         return chardet.detect(self.content)['encoding']
 
     def iter_content(self, chunk_size=1, decode_unicode=False):
@@ -845,7 +845,7 @@ class Response(object):
         """Content of the response, in unicode.
 
         If Response.encoding is None, encoding will be guessed using
-        ``chardet``.
+        ``charset_normalizer`` or ``chardet``.
 
         The encoding of the response content is determined based solely on HTTP
         headers, following RFC 2616 to the letter. If you can take advantage of
@@ -893,7 +893,7 @@ class Response(object):
         if not self.encoding and self.content and len(self.content) > 3:
             # No encoding set. JSON RFC 4627 section 3 states we should expect
             # UTF-8, -16 or -32. Detect which one to use; If the detection or
-            # decoding fails, fall back to `self.text` (using chardet to make
+            # decoding fails, fall back to `self.text` (using charset_normalizer to make
             # a best guess).
             encoding = guess_json_utf(self.content)
             if encoding is not None:

```

</details>

---

## Case 6 — `d1e827075edc7b76`

- **repo** `psf/requests` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Updated references to previous requests/requests GitHub path
- **commit** https://github.com/psf/requests/commit/9cdf29410778f31b88c48385c4a0fdf96fa10bd1
- **doc** `docs/index.rst`
- **code** `requests/sessions.py`
- **shared identifiers** `github`, `https`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/index.rst b/docs/index.rst
index f44340b7..5085503a 100644
--- a/docs/index.rst
+++ b/docs/index.rst
@@ -17,8 +17,8 @@ Release v\ |version|. (:ref:`Installation <install>`)
 .. image:: https://img.shields.io/pypi/pyversions/requests.svg
     :target: https://pypi.org/project/requests/
 
-.. image:: https://codecov.io/github/requests/requests/coverage.svg?branch=master
-    :target: https://codecov.io/github/requests/requests
+.. image:: https://codecov.io/github/psf/requests/coverage.svg?branch=master
+    :target: https://codecov.io/github/psf/requests
     :alt: codecov.io
 
 .. image:: https://img.shields.io/badge/Say%20Thanks!-🦉-1EAEDB.svg

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/requests/sessions.py b/requests/sessions.py
index d73d700f..759ecbe0 100644
--- a/requests/sessions.py
+++ b/requests/sessions.py
@@ -192,9 +192,9 @@ class SessionRedirectMixin(object):
 
             self.rebuild_method(prepared_request, resp)
 
-            # https://github.com/requests/requests/issues/1084
+            # https://github.com/psf/requests/issues/1084
             if resp.status_code not in (codes.temporary_redirect, codes.permanent_redirect):
-                # https://github.com/requests/requests/issues/3490
+                # https://github.com/psf/requests/issues/3490
                 purged_headers = ('Content-Length', 'Content-Type', 'Transfer-Encoding')
                 for header in purged_headers:
                     prepared_request.headers.pop(header, None)

```

</details>

---

## Case 7 — `9a7d090a3de6c27e`

- **repo** `psf/requests` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** new requests namespace
- **commit** https://github.com/psf/requests/commit/7f14db17c8612aed71a181b084455b71e130ffc8
- **doc** `docs/dev/contributing.rst`
- **code** `requests/utils.py`
- **shared identifiers** `kennethreitz`, `github`, `issues`, `https`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/dev/contributing.rst b/docs/dev/contributing.rst
index 93181dad..265994b3 100644
--- a/docs/dev/contributing.rst
+++ b/docs/dev/contributing.rst
@@ -187,7 +187,7 @@ through the `GitHub issues`_, **both open and closed**, to confirm that the bug
 hasn't been reported before. Duplicate bug reports are a huge drain on the time
 of other contributors, and should be avoided as much as possible.
 
-.. _GitHub issues: https://github.com/kennethreitz/requests/issues
+.. _GitHub issues: https://github.com/requests/requests/issues
 
 
 Feature Requests

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/requests/utils.py b/requests/utils.py
index 5976192f..056f6fb3 100644
--- a/requests/utils.py
+++ b/requests/utils.py
@@ -171,7 +171,7 @@ def get_netrc_auth(url, raise_errors=False):
             except KeyError:
                 # os.path.expanduser can fail when $HOME is undefined and
                 # getpwuid fails. See http://bugs.python.org/issue20164 &
-                # https://github.com/kennethreitz/requests/issues/1846
+                # https://github.com/requests/requests/issues/1846
                 return
 
             if os.path.exists(loc):

```

</details>

---

## Case 8 — `9a94070904496f5c`

- **repo** `psf/requests` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** General cleanup for 2.27.0
- **commit** https://github.com/psf/requests/commit/17e6e27a93131b7295165408e69b4cadb098b0d7
- **doc** `docs/community/faq.rst`
- **code** `setup.py`
- **shared identifiers** `python`

**VERDICT: `unrelated`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/community/faq.rst b/docs/community/faq.rst
index fbdd9dad..c0a2f2e9 100644
--- a/docs/community/faq.rst
+++ b/docs/community/faq.rst
@@ -60,11 +60,11 @@ Yes! Requests officially supports Python 2.7 & 3.6+ and PyPy.
 Python 2 Support?
 -----------------
 
-Yes! We do not have immediate plans to `sunset
-<https://www.python.org/doc/sunset-python-2/>`_ our support for Python
-2.7. We understand that we have a large user base with varying needs.
+Yes! We understand that we have a large user base with varying needs. Through
+**at least** Requests 2.27.x, we will be providing continued support for Python
+2.7. However, this support is likely to end some time in 2022.
 
-That said, it is *highly* recommended users migrate to Python 3.6+ since Python
+It is *highly* recommended users migrate to Python 3.7+ now since Python
 2.7 is no longer receiving bug fixes or security updates as of January 1, 2020.
 
 What are "hostname doesn't match" errors?

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/setup.py b/setup.py
index 008565a6..c279c81b 100755
--- a/setup.py
+++ b/setup.py
@@ -84,9 +84,11 @@ setup(
     zip_safe=False,
     classifiers=[
         'Development Status :: 5 - Production/Stable',
+        'Environment :: Web Environment',
         'Intended Audience :: Developers',
-        'Natural Language :: English',
         'License :: OSI Approved :: Apache Software License',
+        'Natural Language :: English',
+        'Operating System :: OS Independent',
         'Programming Language :: Python',
         'Programming Language :: Python :: 2',
         'Programming Language :: Python :: 2.7',
@@ -97,7 +99,9 @@ setup(
         'Programming Language :: Python :: 3.9',
         'Programming Language :: Python :: 3.10',
         'Programming Language :: Python :: Implementation :: CPython',
-        'Programming Language :: Python :: Implementation :: PyPy'
+        'Programming Language :: Python :: Implementation :: PyPy',
+        'Topic :: Internet :: WWW/HTTP',
+        'Topic :: Software Development :: Libraries',
     ],
     cmdclass={'test': PyTest},
     tests_require=test_requirements,

```

</details>

---

## Case 9 — `e7df72235ade950f`

- **repo** `psf/requests` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Remove remaining references to removed, vendored packages (#4499)
- **commit** https://github.com/psf/requests/commit/265ef609d5903151374fba480aa81aafe68126ff
- **doc** `docs/user/quickstart.rst`
- **code** `requests/help.py`
- **shared identifiers** `packages`, `urllib3`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/user/quickstart.rst b/docs/user/quickstart.rst
index 1a2c6fbf..b0ff231b 100644
--- a/docs/user/quickstart.rst
+++ b/docs/user/quickstart.rst
@@ -171,7 +171,7 @@ server, you can access ``r.raw``. If you want to do this, make sure you set
     >>> r = requests.get('https://api.github.com/events', stream=True)
 
     >>> r.raw
-    <requests.packages.urllib3.response.HTTPResponse object at 0x101194810>
+    <urllib3.response.HTTPResponse object at 0x101194810>
 
     >>> r.raw.read(10)
     '\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x03'

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/requests/help.py b/requests/help.py
index 5440ee61..06e06b2a 100644
--- a/requests/help.py
+++ b/requests/help.py
@@ -13,7 +13,7 @@ import chardet
 from . import __version__ as requests_version
 
 try:
-    from .packages.urllib3.contrib import pyopenssl
+    from urllib3.contrib import pyopenssl
 except ImportError:
     pyopenssl = None
     OpenSSL = None

```

</details>

---

## Case 10 — `d0f54d7f2b930191`

- **repo** `psf/requests` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Drop support for CPython 3.7
- **commit** https://github.com/psf/requests/commit/58cea7a7282999adafdc19a4e82e2d09207ab568
- **doc** `docs/index.rst`
- **code** `setup.py`
- **shared identifiers** `python`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/index.rst b/docs/index.rst
index 50b0adc3..289250c2 100644
--- a/docs/index.rst
+++ b/docs/index.rst
@@ -72,7 +72,7 @@ Requests is ready for today's web.
 - Chunked Requests
 - ``.netrc`` Support
 
-Requests officially supports Python 3.7+, and runs great on PyPy.
+Requests officially supports Python 3.8+, and runs great on PyPy.
 
 
 The User Guide

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/setup.py b/setup.py
index dc8043a6..1b0eb377 100755
--- a/setup.py
+++ b/setup.py
@@ -7,7 +7,7 @@ from setuptools import setup
 from setuptools.command.test import test as TestCommand
 
 CURRENT_PYTHON = sys.version_info[:2]
-REQUIRED_PYTHON = (3, 7)
+REQUIRED_PYTHON = (3, 8)
 
 if CURRENT_PYTHON < REQUIRED_PYTHON:
     sys.stderr.write(
@@ -20,7 +20,7 @@ you're trying to install it on Python {}.{}. To resolve this,
 consider upgrading to a supported Python version.
 
 If you can't upgrade your Python version, you'll need to
-pin to an older version of Requests (<2.28).
+pin to an older version of Requests (<2.32.0).
 """.format(
             *(REQUIRED_PYTHON + CURRENT_PYTHON)
         )
@@ -94,7 +94,7 @@ setup(
     package_data={"": ["LICENSE", "NOTICE"]},
     package_dir={"": "src"},
     include_package_data=True,
-    python_requires=">=3.7",
+    python_requires=">=3.8",
     install_requires=requires,
     license=about["__license__"],
     zip_safe=False,
@@ -107,7 +107,6 @@ setup(
         "Operating System :: OS Independent",
         "Programming Language :: Python",
         "Programming Language :: Python :: 3",
-        "Programming Language :: Python :: 3.7",
         "Programming Language :: Python :: 3.8",
         "Programming Language :: Python :: 3.9",
         "Programming Language :: Python :: 3.10",

```

</details>

---

## Case 11 — `f6ff7af97ac3c31c`

- **repo** `psf/requests` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Switch LGPL'd chardet for MIT licensed charset_normalizer (#5797)
- **commit** https://github.com/psf/requests/commit/2ed84f55b22f19a1e1e8eea2e50963dce62052d3
- **doc** `docs/user/advanced.rst`
- **code** `requests/__init__.py`
- **shared identifiers** `charset_normalizer`, `normalizer`, `installed`, `chardet`, `charset`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/user/advanced.rst b/docs/user/advanced.rst
index aa4b1ddb..34d400d5 100644
--- a/docs/user/advanced.rst
+++ b/docs/user/advanced.rst
@@ -697,10 +697,22 @@ Encodings
 When you receive a response, Requests makes a guess at the encoding to
 use for decoding the response when you access the :attr:`Response.text
 <requests.Response.text>` attribute. Requests will first check for an
-encoding in the HTTP header, and if none is present, will use `chardet
-<https://pypi.org/project/chardet/>`_ to attempt to guess the encoding.
-
-The only time Requests will not do this is if no explicit charset
+encoding in the HTTP header, and if none is present, will use
+`charset_normalizer <https://pypi.org/project/charset_normalizer/>`_
+or `chardet <https://github.com/chardet/chardet>`_ to attempt to
+guess the encoding.
+
+If ``chardet`` is installed, ``requests`` uses it, however for python3
+``chardet`` is no longer a mandatory dependency. The ``chardet``
+library is an LGPL-licenced dependency and some users of requests
+cannot depend on mandatory LGPL-licensed dependencies.
+
+When you install ``request`` without specifying ``[use_chardet_on_py3]]`` extra,
+and ``chardet`` is not already installed, ``requests`` uses ``charset-normalizer``
+(MIT-licensed) to guess the encoding. For Python 2, ``requests`` uses only
+``chardet`` and is a mandatory dependency there.
+
+The only time Requests will not guess the encoding is if no explicit charset
 is present in the HTTP headers **and** the ``Content-Type``
 header contains ``text``. In this situation, `RFC 2616
 <https://www.w3.org/Protocols/rfc2616/rfc2616-sec3.html#sec3.7.1>`_ specifies

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/requests/__init__.py b/requests/__init__.py
index f8f94295..0ac7713b 100644
--- a/requests/__init__.py
+++ b/requests/__init__.py
@@ -41,12 +41,20 @@ is at <https://requests.readthedocs.io>.
 """
 
 import urllib3
-import chardet
 import warnings
 from .exceptions import RequestsDependencyWarning
 
+try:
+    from charset_normalizer import __version__ as charset_normalizer_version
+except ImportError:
+    charset_normalizer_version = None
 
-def check_compatibility(urllib3_version, chardet_version):
+try:
+    from chardet import __version__ as chardet_version
+except ImportError:
+    chardet_version = None
+
+def check_compatibility(urllib3_version, chardet_version, charset_normalizer_version):
     urllib3_version = urllib3_version.split('.')
     assert urllib3_version != ['dev']  # Verify urllib3 isn't installed from git.
 
@@ -62,12 +70,19 @@ def check_compatibility(urllib3_version, chardet_version):
     assert minor >= 21
     assert minor <= 26
 
-    # Check chardet for compatibility.
-    major, minor, patch = chardet_version.split('.')[:3]
-    major, minor, patch = int(major), int(minor), int(patch)
-    # chardet >= 3.0.2, < 5.0.0
-    assert (3, 0, 2) <= (major, minor, patch) < (5, 0, 0)
-
+    # Check charset_normalizer for compatibility.
+    if chardet_version:
+        major, minor, patch = chardet_version.split('.')[:3]
+        major, minor, patch = int(major), int(minor), int(patch)
+        # chardet_version >= 3.0.2, < 5.0.0
+        assert (3, 0, 2) <= (major, minor, patch) < (5, 0, 0)
+    elif charset_normalizer_version:
+        major, minor, patch = charset_normalizer_version.split('.')[:3]
+        major, minor, patch = int(major), int(minor), int(patch)
+        # charset_normalizer >= 2.0.0 < 3.0.0
+        assert (2, 0, 0) <= (major, minor, patch) < (3, 0, 0)
+    else:
+        raise Exception("You need either charset_normalizer or chardet installed")
 
 def _check_cryptography(cryptography_version):
     # cryptography < 1.3.4
@@ -82,10 +97,10 @@ def _check_cryptography(cryptography_version):
 
 # Check imported dependencies for compatibility.
 try:
-    check_compatibility(urllib3.__version__, chardet.__version__)
+    check_compatibility(urllib3.__version__, chardet_version, charset_normalizer_version)
 except (AssertionError, ValueError):
-    warnings.warn("urllib3 ({}) or chardet ({}) doesn't match a supported "
-                  "version!".format(urllib3.__version__, chardet.__version__),
+    warnings.warn("urllib3 ({}) or chardet ({})/charset_normalizer ({}) doesn't match a supported "
+                  "version!".format(urllib3.__version__, chardet_version, charset_normalizer_version),
                   RequestsDependencyWarning)
 
 # Attempt to enable urllib3's fallback for SNI support

```

</details>

---

## Case 12 — `75204eac25cd1307`

- **repo** `psf/requests` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Updated references to previous requests/requests GitHub path
- **commit** https://github.com/psf/requests/commit/9cdf29410778f31b88c48385c4a0fdf96fa10bd1
- **doc** `docs/dev/contributing.rst`
- **code** `requests/sessions.py`
- **shared identifiers** `github`, `issues`, `https`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/dev/contributing.rst b/docs/dev/contributing.rst
index 434dc565..308fdd25 100644
--- a/docs/dev/contributing.rst
+++ b/docs/dev/contributing.rst
@@ -197,7 +197,7 @@ through the `GitHub issues`_, **both open and closed**, to confirm that the bug
 hasn't been reported before. Duplicate bug reports are a huge drain on the time
 of other contributors, and should be avoided as much as possible.
 
-.. _GitHub issues: https://github.com/requests/requests/issues
+.. _GitHub issues: https://github.com/psf/requests/issues
 
 
 Feature Requests

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/requests/sessions.py b/requests/sessions.py
index d73d700f..759ecbe0 100644
--- a/requests/sessions.py
+++ b/requests/sessions.py
@@ -192,9 +192,9 @@ class SessionRedirectMixin(object):
 
             self.rebuild_method(prepared_request, resp)
 
-            # https://github.com/requests/requests/issues/1084
+            # https://github.com/psf/requests/issues/1084
             if resp.status_code not in (codes.temporary_redirect, codes.permanent_redirect):
-                # https://github.com/requests/requests/issues/3490
+                # https://github.com/psf/requests/issues/3490
                 purged_headers = ('Content-Length', 'Content-Type', 'Transfer-Encoding')
                 for header in purged_headers:
                     prepared_request.headers.pop(header, None)

```

</details>

---

## Case 13 — `43323744ae0c02a0`

- **repo** `psf/requests` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** new requests namespace
- **commit** https://github.com/psf/requests/commit/7f14db17c8612aed71a181b084455b71e130ffc8
- **doc** `docs/user/advanced.rst`
- **code** `requests/auth.py`
- **shared identifiers** `kennethreitz`, `github`, `issues`, `https`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/user/advanced.rst b/docs/user/advanced.rst
index b7775f24..2aac434c 100644
--- a/docs/user/advanced.rst
+++ b/docs/user/advanced.rst
@@ -280,7 +280,7 @@ immediately. You can override this behaviour and defer downloading the response
 body until you access the :attr:`Response.content <requests.Response.content>`
 attribute with the ``stream`` parameter::
 
-    tarball_url = 'https://github.com/kennethreitz/requests/tarball/master'
+    tarball_url = 'https://github.com/requests/requests/tarball/master'
     r = requests.get(tarball_url, stream=True)
 
 At this point only the response headers have been downloaded and the connection
@@ -642,7 +642,7 @@ from GitHub. Suppose we wanted commit ``a050faf`` on Requests. We would get it
 like so::
 
     >>> import requests
-    >>> r = requests.get('https://api.github.com/repos/kennethreitz/requests/git/commits/a050faf084662f3a352dd1a941f2c7c9f886d4ad')
+    >>> r = requests.get('https://api.github.com/repos/requests/requests/git/commits/a050faf084662f3a352dd1a941f2c7c9f886d4ad')
 
 We should confirm that GitHub responded correctly. If it has, we want to work
 out what type of content it is. Do this like so::
@@ -697,12 +697,12 @@ we should probably avoid making ham-handed POSTS to it. Instead, let's play
 with the Issues feature of GitHub.
 
 This documentation was added in response to
-`Issue #482 <https://github.com/kennethreitz/requests/issues/482>`_. Given that
+`Issue #482 <https://github.com/requests/requests/issues/482>`_. Given that
 this issue already exists, we will use it as an example. Let's start by getting it.
 
 ::
 
-    >>> r = requests.get('https://api.github.com/repos/kennethreitz/requests/issues/482')
+    >>> r = requests.get('https://api.github.com/repos/requests/requests/issues/482')
     >>> r.status_code
     200
 
@@ -745,7 +745,7 @@ is to POST to the thread. Let's do it.
 ::
 
     >>> body = json.dumps({u"body": u"Sounds great! I'll get right on it!"})
-    >>> url = u"https://api.github.com/repos/kennethreitz/requests/issues/482/comments"
+    >>> url = u"https://api.github.com/repos/requests/requests/issues/482/comments"
 
     >>> r = requests.post(url=url, data=body)
     >>> r.status_code
@@ -779,7 +779,7 @@ that.
     5804413
 
     >>> body = json.dumps({u"body": u"Sounds great! I'll get right on it once I feed my cat."})
-    >>> url = u"https://api.github.com/repos/kennethreitz/requests/issues/comments/5804413"
+    >>> url = u"https://api.github.com/repos/requests/requests/issues/comments/5804413"
 
     >>> r = requests.patch(url=url, data=body, auth=auth)
     >>> r.status_code

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/requests/auth.py b/requests/auth.py
index cd9be911..a44b4d15 100644
--- a/requests/auth.py
+++ b/requests/auth.py
@@ -227,7 +227,7 @@ class HTTPDigestAuth(AuthBase):
         """
 
         # If response is not 4xx, do not auth
-        # See https://github.com/kennethreitz/requests/issues/3772
+        # See https://github.com/requests/requests/issues/3772
         if not 400 <= r.status_code < 500:
             self._thread_local.num_401_calls = 1
             return r

```

</details>

---

## Case 14 — `13897a4cbd14195b`

- **repo** `psf/requests` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Prefer https:// for URLs throughout project
- **commit** https://github.com/psf/requests/commit/b0ad2499c8641d29affc90f565e6628d333d2a96
- **doc** `docs/user/install.rst`
- **code** `requests/__init__.py`
- **shared identifiers** `https`, `http`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/user/install.rst b/docs/user/install.rst
index 1dd9de8e..3888876a 100644
--- a/docs/user/install.rst
+++ b/docs/user/install.rst
@@ -18,7 +18,7 @@ To install Requests, simply run this simple command in your terminal of choice::
     $ pipenv install requests
 
 If you don't have `pipenv <http://pipenv.org/>`_ installed (tisk tisk!), head over to the Pipenv website for installation instructions. Or, if you prefer to just use pip and don't have it installed,
-`this Python installation guide <http://docs.python-guide.org/en/latest/starting/installation/>`_
+`this Python installation guide <https://docs.python-guide.org/starting/installation/>`_
 can guide you through the process.
 
 Get the Source Code

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/requests/__init__.py b/requests/__init__.py
index a5b3c9c3..098c21f0 100644
--- a/requests/__init__.py
+++ b/requests/__init__.py
@@ -22,7 +22,7 @@ usage:
 ... or POST:
 
    >>> payload = dict(key1='value1', key2='value2')
-   >>> r = requests.post('http://httpbin.org/post', data=payload)
+   >>> r = requests.post('https://httpbin.org/post', data=payload)
    >>> print(r.text)
    {
      ...

```

</details>

---

## Case 15 — `c2b171dae83904d2`

- **repo** `psf/requests` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Prefer https:// for URLs throughout project
- **commit** https://github.com/psf/requests/commit/b0ad2499c8641d29affc90f565e6628d333d2a96
- **doc** `docs/api.rst`
- **code** `requests/utils.py`
- **shared identifiers** `https`, `http`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/api.rst b/docs/api.rst
index ef84bf60..93cc4f0d 100644
--- a/docs/api.rst
+++ b/docs/api.rst
@@ -139,7 +139,7 @@ API Changes
       s = requests.Session()    # formerly, session took parameters
       s.auth = auth
       s.headers.update(headers)
-      r = s.get('http://httpbin.org/headers')
+      r = s.get('https://httpbin.org/headers')
 
 * All request hooks have been removed except 'response'.
 
@@ -185,7 +185,7 @@ API Changes
       requests_log.setLevel(logging.DEBUG)
       requests_log.propagate = True
 
-      requests.get('http://httpbin.org/headers')
+      requests.get('https://httpbin.org/headers')
 
 
 
@@ -197,8 +197,8 @@ license from the ISC_ license to the `Apache 2.0`_ license. The Apache 2.0
 license ensures that contributions to Requests are also covered by the Apache
 2.0 license.
 
-.. _ISC: http://opensource.org/licenses/ISC
-.. _Apache 2.0: http://opensource.org/licenses/Apache-2.0
+.. _ISC: https://opensource.org/licenses/ISC
+.. _Apache 2.0: https://opensource.org/licenses/Apache-2.0
 
 
 Migrating to 2.x
@@ -213,7 +213,7 @@ For more details on the changes in this release including new APIs, links
 to the relevant GitHub issues and some of the bug fixes, read Cory's blog_
 on the subject.
 
-.. _blog: http://lukasa.co.uk/2013/09/Requests_20/
+.. _blog: https://lukasa.co.uk/2013/09/Requests_20/
 
 
 API Changes

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/requests/utils.py b/requests/utils.py
index 6892713a..67197312 100644
--- a/requests/utils.py
+++ b/requests/utils.py
@@ -176,7 +176,7 @@ def get_netrc_auth(url, raise_errors=False):
                 loc = os.path.expanduser('~/{0}'.format(f))
             except KeyError:
                 # os.path.expanduser can fail when $HOME is undefined and
-                # getpwuid fails. See http://bugs.python.org/issue20164 &
+                # getpwuid fails. See https://bugs.python.org/issue20164 &
                 # https://github.com/requests/requests/issues/1846
                 return
 

```

</details>

---

## Case 16 — `65463185f227a96c`

- **repo** `psf/requests` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Add support for Python 3.14 and drop support for Python 3.8 (#6993)
- **commit** https://github.com/psf/requests/commit/2edca11103c1c27dd8b572dab544b7f48cf3b446
- **doc** `README.md`
- **code** `setup.py`
- **shared identifiers** `python`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/README.md b/README.md
index 18d9723c..74adab80 100644
--- a/README.md
+++ b/README.md
@@ -33,7 +33,7 @@ Requests is available on PyPI:
 $ python -m pip install requests
 ```
 
-Requests officially supports Python 3.8+.
+Requests officially supports Python 3.9+.
 
 ## Supported Features & Best–Practices
 

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

## Case 17 — `24d95c54234488b2`

- **repo** `psf/requests` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Prefer https:// for URLs throughout project
- **commit** https://github.com/psf/requests/commit/b0ad2499c8641d29affc90f565e6628d333d2a96
- **doc** `docs/user/install.rst`
- **code** `requests/api.py`
- **shared identifiers** `https`, `http`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/user/install.rst b/docs/user/install.rst
index 1dd9de8e..3888876a 100644
--- a/docs/user/install.rst
+++ b/docs/user/install.rst
@@ -18,7 +18,7 @@ To install Requests, simply run this simple command in your terminal of choice::
     $ pipenv install requests
 
 If you don't have `pipenv <http://pipenv.org/>`_ installed (tisk tisk!), head over to the Pipenv website for installation instructions. Or, if you prefer to just use pip and don't have it installed,
-`this Python installation guide <http://docs.python-guide.org/en/latest/starting/installation/>`_
+`this Python installation guide <https://docs.python-guide.org/starting/installation/>`_
 can guide you through the process.
 
 Get the Source Code

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/requests/api.py b/requests/api.py
index 5f07a19f..abada96d 100644
--- a/requests/api.py
+++ b/requests/api.py
@@ -49,7 +49,7 @@ def request(method, url, **kwargs):
     Usage::
 
       >>> import requests
-      >>> req = requests.request('GET', 'http://httpbin.org/get')
+      >>> req = requests.request('GET', 'https://httpbin.org/get')
       <Response [200]>
     """
 

```

</details>

---

## Case 18 — `914faec414ddd58a`

- **repo** `psf/requests` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Change documentation website to requests.readthedocs.io (#5236)
- **commit** https://github.com/psf/requests/commit/d2590ee46c0641958b6d4792a206bd5171cb247d
- **doc** `docs/user/install.rst`
- **code** `docs/conf.py`
- **shared identifiers** `readthedocs`, `master`, `python`, `https`, `docs`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/user/install.rst b/docs/user/install.rst
index 73e69f29..bc32244f 100644
--- a/docs/user/install.rst
+++ b/docs/user/install.rst
@@ -18,7 +18,7 @@ To install Requests, simply run this simple command in your terminal of choice::
     $ pipenv install requests
 
 If you don't have `pipenv <http://pipenv.org/>`_ installed (tisk tisk!), head over to the Pipenv website for installation instructions. Or, if you prefer to just use pip and don't have it installed,
-`this Python installation guide <https://docs.python-guide.org/starting/installation/>`_
+`this Python installation guide <https://requests.readthedocs.io/en/master/user/install/>`_
 can guide you through the process.
 
 Get the Source Code

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/docs/conf.py b/docs/conf.py
index eb556a81..c13b05e7 100644
--- a/docs/conf.py
+++ b/docs/conf.py
@@ -381,6 +381,6 @@ epub_exclude_files = ["search.html"]
 # epub_use_index = True
 
 intersphinx_mapping = {
-    "python": ("https://docs.python.org/3/", None),
+    "python": ("https://requests.readthedocs.io/en/master/", None),
     "urllib3": ("https://urllib3.readthedocs.io/en/latest", None),
 }

```

</details>

---

## Case 19 — `bf4fc2f7999408a9`

- **repo** `psf/requests` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Updated references to previous requests/requests GitHub path
- **commit** https://github.com/psf/requests/commit/9cdf29410778f31b88c48385c4a0fdf96fa10bd1
- **doc** `docs/dev/todo.rst`
- **code** `requests/auth.py`
- **shared identifiers** `github`, `https`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/dev/todo.rst b/docs/dev/todo.rst
index 26cd9b71..d09fce39 100644
--- a/docs/dev/todo.rst
+++ b/docs/dev/todo.rst
@@ -8,11 +8,11 @@ Requests is under active development, and contributions are more than welcome!
 #. Check for open issues or open a fresh issue to start a discussion around a bug.
    There is a Contributor Friendly tag for issues that should be ideal for people who are not very
    familiar with the codebase yet.
-#. Fork `the repository <https://github.com/requests/requests>`_ on GitHub and start making your
+#. Fork `the repository <https://github.com/psf/requests>`_ on GitHub and start making your
    changes to a new branch.
 #. Write a test which shows that the bug was fixed.
 #. Send a pull request and bug the maintainer until it gets merged and published. :)
-   Make sure to add yourself to `AUTHORS <https://github.com/requests/requests/blob/master/AUTHORS.rst>`_.
+   Make sure to add yourself to `AUTHORS <https://github.com/psf/requests/blob/master/AUTHORS.rst>`_.
 
 Feature Freeze
 --------------

```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/requests/auth.py b/requests/auth.py
index 34e7c8b8..eeface39 100644
--- a/requests/auth.py
+++ b/requests/auth.py
@@ -239,7 +239,7 @@ class HTTPDigestAuth(AuthBase):
         """
 
         # If response is not 4xx, do not auth
-        # See https://github.com/requests/requests/issues/3772
+        # See https://github.com/psf/requests/issues/3772
         if not 400 <= r.status_code < 500:
             self._thread_local.num_401_calls = 1
             return r

```

</details>

---

## Case 20 — `ddfbbda777efcafd`

- **repo** `psf/requests` · **shape** A
- **basis** `doc_and_code_both_modified_sharing_identifier`
- **subject** Prefer https:// for URLs throughout project
- **commit** https://github.com/psf/requests/commit/b0ad2499c8641d29affc90f565e6628d333d2a96
- **doc** `docs/user/advanced.rst`
- **code** `requests/api.py`
- **shared identifiers** `httpbin`, `https`, `http`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/user/advanced.rst b/docs/user/advanced.rst
index 2076fc00..9a615aae 100644
--- a/docs/user/advanced.rst
+++ b/docs/user/advanced.rst
@@ -25,8 +25,8 @@ Let's persist some cookies across requests::
 
     s = requests.Session()
 
-    s.get('http://httpbin.org/cookies/set/sessioncookie/123456789')
-    r = s.get('http://httpbin.org/cookies')
+    s.get('https://httpbin.org/cookies/set/sessioncookie/123456789')
+    r = s.get('https://httpbin.org/cookies')
 
     print(r.text)
     # '{"cookies": {"sessioncookie": "123456789"}}'
@@ -40,7 +40,7 @@ is done by providing data to the properties on a Session object::
     s.headers.update({'x-test': 'true'})
 
     # both 'x-test' and 'x-test2' are sent
-    s.get('http://httpbin.org/headers', headers={'x-test2': 'true'})
+    s.get('https://httpbin.org/headers', headers={'x-test2': 'true'})
 
 
 Any dictionaries that you pass to a request method will be merged with the
@@ -53,11 +53,11 @@ with the first request, but not the second::
 
     s = requests.Session()
 
-    r = s.get('http://httpbin.org/cookies', cookies={'from-my': 'browser'})
+    r = s.get('https://httpbin.org/cookies', cookies={'from-my': 'browser'})
     print(r.text)
     # '{"cookies": {"from-my": "browser"}}'
 
-    r = s.get('http://httpbin.org/cookies')
+    r = s.get('https://httpbin.org/cookies')
     print(r.text)
     # '{"cookies": {}}'
 
@@ -69,7 +69,7 @@ If you want to manually add cookies to your session, use the
 Sessions can also be used as context managers::
 
     with requests.Session() as s:
-        s.get('http://httpbin.org/cookies/set/sessioncookie/123456789')
+        s.get('https://httpbin.org/cookies/set/sessioncookie/123456789')
 
 This will make sure the session is closed as soon as the ``with`` block is
 exited, even if unhandled exceptions occurred.
@@ -97,7 +97,7 @@ The ``Response`` object contains all of the information returned by the server a
 also contains the ``Request`` object you created originally. Here is a simple
 request to get some very important information from Wikipedia's servers::
 
-    >>> r = requests.get('http://en.wikipedia.org/wiki/Monty_Python')
+    >>> r = requests.get('https://en.wikipedia.org/wiki/Monty_Python')
 
 If we want to access the headers the server sent back to us, we do this::
 
@@ -323,7 +323,7 @@ inefficiency with connections. If you find yourself partially reading request
 bodies (or not reading them at all) while using ``stream=True``, you should
 make the request within a ``with`` statement to ensure it's always closed::
 
-    with requests.get('http://httpbin.org/get', stream=True) as r:
+    with requests.get('https://httpbin.org/get', stream=True) as r:
         # Do things with the response here.
 
 .. _keep-alive:
@@ -393,7 +393,7 @@ upload image files to an HTML form with a multiple file field 'images'::
 
 To do that, just set files to a list of tuples of ``(form_field_name, file_info)``::
 
-    >>> url = 'http://httpbin.org/post'
+    >>> url = 'https://httpbin.org/post'
     >>> multiple_files = [
             ('images', ('foo.png', open('foo.png', 'rb'), 'image/png')),
             ('images', ('bar.png', open('bar.png', 'rb'), 'image/png'))]
@@ -455,13 +455,13 @@ anything, nothing else is affected.
 
 Let's print some request method arguments at runtime::
 
-    >>> requests.get('http://httpbin.org', hooks={'response': print_url})
-    http://httpbin.org
+    >>> requests.get('https://httpbin.org/', hooks={'response': print_url})
+    https://httpbin.org/
     <Response [200]>
 
 You can add multiple hooks to a single request.  Let's call two hooks at once::
 
-    >>> r = requests.get('http://httpbin.org', hooks={'response': [print_url, record_hook]})
+    >>> r = requests.get('https://httpbin.org/', hooks={'response': [print_url, record_hook]})
     >>> r.hook_called
     True
 
@@ -470,8 +470,8 @@ be called on every request made to the session.  For example::
 
    >>> s = requests.Session()
    >>> s.hooks['respo
```

</details>

<details><summary>code diff</summary>

```diff
diff --git a/requests/api.py b/requests/api.py
index 5f07a19f..abada96d 100644
--- a/requests/api.py
+++ b/requests/api.py
@@ -49,7 +49,7 @@ def request(method, url, **kwargs):
     Usage::
 
       >>> import requests
-      >>> req = requests.request('GET', 'http://httpbin.org/get')
+      >>> req = requests.request('GET', 'https://httpbin.org/get')
       <Response [200]>
     """
 

```

</details>

---

