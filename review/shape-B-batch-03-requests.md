# Drift label review — 20 cases (seed 31)

For each case, replace `VERDICT: ?` with one of:

- `drift` — the doc said something untrue about the code, and this commit corrected it
- `new` — the doc was documenting something that did not exist yet (feature + its docs)
- `cosmetic` — wording, formatting or a link -- nothing factual changed
- `unrelated` — the doc change and the code change are not about the same thing
- `unclear` — cannot tell from these diffs alone

The question is always: **at the parent commit, was this documentation false about the code?** Not whether the commit improved the docs — whether what it replaced was wrong.

---

## Case 1 — `3c528312a79f240d`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Rewrite quickstart docs.
- **commit** https://github.com/psf/requests/commit/45506d1f39be8cc055814227952e53d94d3cb10d
- **doc** `docs/user/quickstart.rst`
- **no longer asserted after this commit** `ver:127.0.0.1.502.21746.1321131593.786.1`, `ver:127.0.0.1.502.41433.1335385481.788.1`, `ver:179.13.100.4`, `ver:127.0.0.1`, `ver:0.11.0`, `ver:0.11.1`, `ver:0.8.0`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/user/quickstart.rst b/docs/user/quickstart.rst
index bdb6635c..36275362 100644
--- a/docs/user/quickstart.rst
+++ b/docs/user/quickstart.rst
@@ -15,53 +15,71 @@ First, make sure that:
 * Requests is :ref:`up-to-date <updates>`
 
 
-Lets gets started with some simple use cases and examples.
+Let's get started with some simple examples.
 
 
-Make a GET Request
+Make a Request
 ------------------
 
-Making a standard request with Requests is very simple.
+Making a request with Requests is very simple.
 
-Let's get GitHub's public timeline ::
+Begin by importing the Requests module::
+    
+    >>> import requests
 
-    r = requests.get('https://github.com/timeline.json')
+Now, let's try to get a webpage. For this example, let's get GitHub's public
+timeline ::
+
+    >>> r = requests.get('https://github.com/timeline.json')
 
 Now, we have a :class:`Response` object called ``r``. We can get all the
-information we need from this.
+information we need from this object.
+
+Requests' simple API means that all forms of HTTP request are as obvious. For
+example, this is how you make an HTTP POST request::
+    
+    >>> r = requests.post("http://httpbin.org/post")
+
+Nice, right? What about the other HTTP request types: PUT, DELETE, HEAD and
+OPTIONS? These are all just as simple::
+    
+    >>> r = requests.put("http://httpbin.org/put")
+    >>> r = requests.delete("http://httpbin.org/delete")
+    >>> r = requests.head("http://httpbin.org/get")
+    >>> r = requests.options("http://httpbin.org/get")
+
+That's all well and good, but it's also only the start of what Requests can
+do.
+
 
-Typically, you want to send some sort of data in the urls query string.
-To do this, simply pass a dictionary to the `params` argument. Your
-dictionary of data will automatically be encoded when the request is made::
+Passing Parameters In URLs
+--------------------------
+
+You often want to send some sort of data in the URL's query string. If
+you were constructing the URL by hand, this data would be given as key/value
+pairs in the URL after a question mark, e.g. ``httpbin.org/get?key=val``.
+Requests allows you to provide these arguments as a dictionary, using the
+``params`` keyword argument. As an example, if you wanted to pass
+``key1=value1`` and ``key2=value2`` to ``httpbin.org/get``, you would use the
+following code::
 
     >>> payload = {'key1': 'value1', 'key2': 'value2'}
     >>> r = requests.get("http://httpbin.org/get", params=payload)
-    >>> print r.text
-    {
-      "origin": "179.13.100.4",
-      "args": {
-        "key2": "value2",
-        "key1": "value1"
-      },
-      "url": "http://httpbin.org/get",
-      "headers": {
-        "Connections": "keep-alive",
-        "Content-Length": "",
-        "Accept-Encoding": "identity, deflate, compress, gzip",
-        "Accept": "*/*",
-        "User-Agent": "python-requests/0.11.0",
-        "Host": httpbin.org",
-        "Content-Type": ""
-      },
-    }
 
+You can see that the URL has been correctly encoded by printing the URL::
 
+    >>> print r.url
+    u'http://httpbin.org/get?key2=value2&key1=value1'
+    
 
 Response Content
 ----------------
 
-We can read the content of the server's response::
+We can read the content of the server's response. Consider the GitHub timeline
+again::
 
+    >>> import requests
+    >>> r = requests.get('https://github.com/timeline.json')
     >>> r.text
     '[{"repository":{"open_issues":0,"url":"https://github.com/...
 
@@ -85,7 +103,7 @@ You can also access the response body as bytes, for non-text requests::
 
 The ``gzip`` and ``deflate`` transfer-encodings are automatically decoded for you.
 
-For example to create an image from binary data returned by a request, you can
+For example, to create an image from binary data returned by a request, you can
 use the following code:
 
     >>> from PIL import Image
@@ -106,14 +124,24 @@ you can access ``r.raw``::
     '\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x03'
 
 
+Cus
```

</details>

---

## Case 2 — `77863feda874ae98`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Add PreparedRequest recipe to the docs
- **commit** https://github.com/psf/requests/commit/b9e5cce2d2ab85e073c04cab03ac81210d25f2ee
- **doc** `docs/user/advanced.rst`
- **no longer asserted after this commit** `ver:0.13.1`

**VERDICT: `new`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/user/advanced.rst b/docs/user/advanced.rst
index d8c142c9..a987dff4 100644
--- a/docs/user/advanced.rst
+++ b/docs/user/advanced.rst
@@ -75,8 +75,42 @@ request, and then the request's headers::
 
     >>> r.request.headers
     {'Accept-Encoding': 'identity, deflate, compress, gzip',
-    'Accept': '*/*', 'User-Agent': 'python-requests/0.13.1'}
+    'Accept': '*/*', 'User-Agent': 'python-requests/1.2.0'}
 
+Prepared Requests
+-----------------
+
+Whenever you receive a :class:`Response <requests.models.Response>` object 
+from an API call or a Session call, the ``request`` attribute is actually the 
+``PreparedRequest`` that was used. In some cases you may wish to do some extra 
+work to the body or headers (or anything else really) before sending a 
+request. The simple recipe for this is the following::
+
+    from requests import Request, Session
+
+    s = Session()
+    prepped = Request('GET',  # or any other method, 'POST', 'PUT', etc.
+                      url,
+                      data=data
+                      headers=headers
+                      # ...
+                      ).prepare()
+    # do something with prepped.body
+    # do something with prepped.headers
+    resp = s.send(prepped,
+                  stream=stream,
+                  verify=verify,
+                  proxies=proxies,
+                  cert=cert,
+                  timeout=timeout,
+                  # etc.
+                  )
+    print(resp.status_code)
+
+Since you are not doing anything special with the ``Request`` object, you 
+prepare it immediately and modified the ``PreparedRequest`` object. You then 
+send that with the other parameters you would have sent to ``requests.*`` or 
+``Sesssion.*``. 
 
 SSL Cert Verification
 ---------------------

```

</details>

---

## Case 3 — `ccb346a319a3d698`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Correct redirection introduction
- **commit** https://github.com/psf/requests/commit/671ba85d410febab91ac580eab8282a485c89108
- **doc** `docs/user/quickstart.rst`
- **no longer asserted after this commit** `request`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/user/quickstart.rst b/docs/user/quickstart.rst
index 1a4b2714..1e852c99 100644
--- a/docs/user/quickstart.rst
+++ b/docs/user/quickstart.rst
@@ -369,9 +369,9 @@ HEAD.
 We can use the ``history`` property of the Response object to track redirection.
 
 The :meth:`Response.history <requests.Response.history>` list contains the
-:class:`Request <requests.Request>` objects that were created in order to
+:class:`Response <requests.Response>` objects that were created in order to
 complete the request. The list is sorted from the oldest to the most recent
-request.
+response.
 
 For example, GitHub redirects all HTTP requests to HTTPS::
 

```

</details>

---

## Case 4 — `e4bba43ffbd5dbca`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Clarify that SSL verification is on by default
- **commit** https://github.com/psf/requests/commit/e94c812c2d02427e924b72adfa3572e911eba2ca
- **doc** `docs/user/advanced.rst`
- **no longer asserted after this commit** `verify`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/user/advanced.rst b/docs/user/advanced.rst
index ddd6edf6..a7812882 100644
--- a/docs/user/advanced.rst
+++ b/docs/user/advanced.rst
@@ -192,15 +192,16 @@ applied, replace the call to :meth:`Request.prepare()
 SSL Cert Verification
 ---------------------
 
-Requests can verify SSL certificates for HTTPS requests, just like a web browser.
-To check a host's SSL certificate, you can use the ``verify`` argument::
+Requests verifies SSL certificates for HTTPS requests, just like a web browser.
+By default, SSL verification is enabled, and requests will throw a SSLError if
+it's unable to verify the certificate::
 
-    >>> requests.get('https://kennethreitz.com', verify=True)
-    requests.exceptions.SSLError: hostname 'kennethreitz.com' doesn't match either of '*.herokuapp.com', 'herokuapp.com'
+    >>> requests.get('https://requestb.in')
+    requests.exceptions.SSLError: hostname 'requestb.in' doesn't match either of '*.herokuapp.com', 'herokuapp.com'
 
-I don't have SSL setup on this domain, so it fails. Excellent. GitHub does though::
+I don't have SSL setup on this domain, so it throws an exception. Excellent. GitHub does though::
 
-    >>> requests.get('https://github.com', verify=True)
+    >>> requests.get('https://github.com')
     <Response [200]>
 
 You can pass ``verify`` the path to a CA_BUNDLE file or directory with certificates of trusted CAs::
@@ -225,7 +226,7 @@ file's path::
     >>> requests.get('https://kennethreitz.com', cert=('/path/client.cert', '/path/client.key'))
     <Response [200]>
 
-If you specify a wrong path or an invalid cert::
+If you specify a wrong path or an invalid cert, you'll get a SSLError::
 
     >>> requests.get('https://kennethreitz.com', cert='/wrong_path/client.pem')
     SSLError: [Errno 336265225] _ssl.c:347: error:140B0009:SSL routines:SSL_CTX_use_PrivateKey_file:PEM lib

```

</details>

---

## Case 5 — `f2d90d27b33cea19`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** support
- **commit** https://github.com/psf/requests/commit/a23f22e5dc81b359229d68a10352c4ad8ed71c46
- **doc** `docs/community/faq.rst`
- **no longer asserted after this commit** `ver:1.4`, `ver:1.5`, `ver:1.6`, `ver:1.7`

**VERDICT: `unclear`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/community/faq.rst b/docs/community/faq.rst
index fa9b0687..edbf9b70 100644
--- a/docs/community/faq.rst
+++ b/docs/community/faq.rst
@@ -54,30 +54,9 @@ Python 3 Support?
 Yes! Here's a list of Python platforms that are officially
 supported:
 
-* cPython 2.6
-* cPython 2.7
-* cPython 3.1
-* cPython 3.2
-* PyPy-c 1.4
-* PyPy-c 1.5
-* PyPy-c 1.6
-* PyPy-c 1.7
-
-
-Keep-alive Support?
--------------------
-
-Yep!
-
-
-Proxy Support?
---------------
-
-You bet!
-
-
-SSL Verification?
------------------
-
-Absolutely.
-
+* Python 2.6
+* Python 2.7
+* Python 3.1
+* Python 3.2
+* Python 3.3
+* PyPy 1.9

```

</details>

---

## Case 6 — `f61e10c964444bfd`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** http://pep8.org
- **commit** https://github.com/psf/requests/commit/f8798a253adc21c63cac0c4df936f72f0a3b42ae
- **doc** `docs/dev/contributing.rst`
- **no longer asserted after this commit** `pep8`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/dev/contributing.rst b/docs/dev/contributing.rst
index 4b98a945..bdb733a0 100644
--- a/docs/dev/contributing.rst
+++ b/docs/dev/contributing.rst
@@ -111,7 +111,7 @@ Please also check the :ref:`early-feedback` section.
 Kenneth Reitz's Code Style™
 ~~~~~~~~~~~~~~~~~~~~~~~~~~~
 
-The Requests codebase uses the `PEP8`_ code style.
+The Requests codebase uses the `PEP 8`_ code style.
 
 In addition to the standards outlined in PEP8, we have a few guidelines:
 
@@ -155,7 +155,7 @@ model methods (e.g. ``__repr__``) are typically the exception to this rule.
 
 Thanks for helping to make the world a better place!
 
-.. _PEP8: https://www.python.org/dev/peps/pep-0008/
+.. _PEP8: http://pep8.org
 .. _line continuations: https://www.python.org/dev/peps/pep-0008/#indentation
 
 Documentation Contributions

```

</details>

---

## Case 7 — `96cd92abfdfd84eb`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** we support python 3.6
- **commit** https://github.com/psf/requests/commit/c3fb8e020b865a04afbc01e2c439fb3995feb702
- **doc** `docs/index.rst`
- **no longer asserted after this commit** `ver:3.5`

**VERDICT: `unclear`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/index.rst b/docs/index.rst
index d8279a9c..1f323631 100644
--- a/docs/index.rst
+++ b/docs/index.rst
@@ -87,7 +87,7 @@ Requests is ready for today's web.
 - Chunked Requests
 - Thread-safety
 
-Requests officially supports Python 2.6–2.7 & 3.3–3.5, and runs great on PyPy.
+Requests officially supports Python 2.6–2.7 & 3.3–3.6, and runs great on PyPy.
 
 
 The User Guide

```

</details>

---

## Case 8 — `0186067fe912d37e`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** documentation link fixed
- **commit** https://github.com/psf/requests/commit/74b72ce4265583db0430080ab67d3d5e0c4b44b2
- **doc** `README.md`
- **no longer asserted after this commit** `python`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/README.md b/README.md
index 89ec151f..80412cc8 100644
--- a/README.md
+++ b/README.md
@@ -103,7 +103,7 @@ Requests officially supports Python 2.7 & 3.4–3.8.
 
 -------------------------------------
 
-## P.S. — Documentation is Available at [`//2.python-requests.org`](https://2.python-requests.org/).
+## P.S. — Documentation is Available at [`//requests.readthedocs.io`](https://requests.readthedocs.io/en/master/).
 
 <p align="center">
         <a href="https://2.python-requests.org/"><img src="https://raw.githubusercontent.com/psf/requests/master/ext/ss.png" align="center" /></a>

```

</details>

---

## Case 9 — `87b176ff529b620c`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Fix a couple more malformed :meth: and :class: links
- **commit** https://github.com/psf/requests/commit/c6fa5bb1cd06ab6d8206ddb4c07572c77f26b9a3
- **doc** `docs/user/authentication.rst`
- **no longer asserted after this commit** `requests`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/user/authentication.rst b/docs/user/authentication.rst
index af43bd29..dd0bf2b8 100644
--- a/docs/user/authentication.rst
+++ b/docs/user/authentication.rst
@@ -99,7 +99,7 @@ If you can't find a good implementation of the form of authentication you
 want, you can implement it yourself. Requests makes it easy to add your own
 forms of authentication.
 
-To do so, subclass :class:`requests.auth.AuthBase` and implement the
+To do so, subclass :class:`AuthBase <requests.auth.AuthBase>` and implement the
 ``__call__()`` method::
 
     >>> import requests

```

</details>

---

## Case 10 — `6589e5065d2fa53a`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** remove debian packaging warning
- **commit** https://github.com/psf/requests/commit/e65f52aae4e347ecfbf1010745e899519ad5c6e6
- **doc** `docs/community/out-there.rst`
- **no longer asserted after this commit** `ver:5.0`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/community/out-there.rst b/docs/community/out-there.rst
index 553c7444..5ef090f3 100644
--- a/docs/community/out-there.rst
+++ b/docs/community/out-there.rst
@@ -50,9 +50,6 @@ Requests is available installed as a Debian package! Debian Etch Ubuntu, since O
 
     $ apt-get install python-requests
 
-Unfortunately, the most recent version available is  v0.5.0. If you're on the
-Debian Python Package team, I'd love an update of that :)
-
 
 Fedora and RedHat
 -----------------

```

</details>

---

## Case 11 — `86b9742f0a4936e6`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** docs updates
- **commit** https://github.com/psf/requests/commit/1435cf5affcc3822f8cb4e424bef0260083bfce5
- **doc** `docs/dev/todo.rst`
- **no longer asserted after this commit** `ver:1.9`

**VERDICT: `unclear`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/dev/todo.rst b/docs/dev/todo.rst
index 5f1700a9..79b95a21 100644
--- a/docs/dev/todo.rst
+++ b/docs/dev/todo.rst
@@ -41,7 +41,7 @@ Requests currently supports the following versions of Python:
 - Python 3.3
 - Python 3.4
 - Python 3.5
-- PyPy 1.9
+- PyPy
 
 Google AppEngine is not officially supported although support is available
 with the `Requests-Toolbelt`_.

```

</details>

---

## Case 12 — `a3a289930505cf10`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Fixed gevent reference
- **commit** https://github.com/psf/requests/commit/6833b326f801272afc50d2a816147021c4c62057
- **doc** `docs/user/advanced.rst`
- **no longer asserted after this commit** `gevent`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/user/advanced.rst b/docs/user/advanced.rst
index df274994..d4a416cf 100644
--- a/docs/user/advanced.rst
+++ b/docs/user/advanced.rst
@@ -72,7 +72,7 @@ Requests has first-class support for concurrent requests, powered
 by gevent. This allows you to send a bunch of HTTP requests at the same
 
 First, let's import the async module. Heads up — if you don't have
-`gevent <gevent>`_ this will fail::
+`gevent <http://pypi.python.org/pypi/gevent>`_ this will fail::
 
     from requests import async
 

```

</details>

---

## Case 13 — `c72d069fab230211`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Split authentication out into a separate file.
- **commit** https://github.com/psf/requests/commit/a7c5d5e8ac7b4fac71352ef359a5af6b812a9a4c
- **doc** `docs/user/quickstart.rst`
- **no longer asserted after this commit** `httpbasicauth`, `organization`, `httpbasic`, `github`, `auth`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/user/quickstart.rst b/docs/user/quickstart.rst
index 5f6e6a23..1731b295 100644
--- a/docs/user/quickstart.rst
+++ b/docs/user/quickstart.rst
@@ -337,62 +337,6 @@ parameter::
     '{"cookies": {"cookies_are": "working"}}'
 
 
-Basic Authentication
---------------------
-
-Many web services require authentication. There are many different types of
-authentication, but the most common is HTTP Basic Auth.
-
-Making requests with Basic Auth is extremely simple::
-
-    >>> from requests.auth import HTTPBasicAuth
-    >>> requests.get('https://api.github.com/user', auth=HTTPBasicAuth('user', 'pass'))
-    <Response [200]>
-
-Due to the prevalence of HTTP Basic Auth, requests provides a shorthand for
-this authentication method::
-
-    >>> requests.get('https://api.github.com/user', auth=('user', 'pass'))
-    <Response [200]>
-
-Providing the credentials as a tuple in this fashion is functionally equivalent
-to the ``HTTPBasicAuth`` example above.
-
-
-Digest Authentication
----------------------
-
-Another popular form of web service protection is Digest Authentication::
-
-    >>> from requests.auth import HTTPDigestAuth
-    >>> url = 'http://httpbin.org/digest-auth/auth/user/pass'
-    >>> requests.get(url, auth=HTTPDigestAuth('user', 'pass'))
-    <Response [200]>
-
-
-Other Authentication
---------------------
-
-Requests is designed to allow other forms of authentication to be easily and
-quickly plugged in. Members of the open-source community frequently write
-authentication handlers for more complicated or less commonly-used forms of
-authentication. Some of the best have been brought together under a single
-`organization on Github`_, including:
-
-- OAuth_
-- Kerberos_
-- NTLM_
-
-If you want to use any of these forms of authentication, go straight to their
-Github page and follow the instructions. If you can't find the one you want,
-why not write one and submit it?
-
-.. _OAuth: https://github.com/requests/requests-oauthlib
-.. _Kerberos: https://github.com/requests/requests-kerberos
-.. _NTLM: https://github.com/requests/requests-ntlm
-.. _organization on Github: https://github.com/requests
-
-
 Redirection and History
 -----------------------
 

```

</details>

---

## Case 14 — `5d2857d9a83d5e71`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Update README.md
- **commit** https://github.com/psf/requests/commit/e63d846b15753ca1f51d6afe3405eb2c8c7d655e
- **doc** `README.md`
- **no longer asserted after this commit** `netrc`, `dict`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/README.md b/README.md
index 3fb3c149..e020fb55 100644
--- a/README.md
+++ b/README.md
@@ -66,15 +66,26 @@ downloads every month. You don't want to be left out!
 
 Requests is ready for the demands of building robust and reliable HTTP–speaking applications, on today's web (or your own infrastructure).
 
-|----------------------------------|---------------------------------|
-| International Domains and URLs   | Keep-Alive & Connection Pooling |
-| Sessions with Cookie Persistence | Browser-style SSL Verification  |
-| Basic & Digest Authentication    | Familiar `dict`–like Cookies    |
-| Automatic Decompression          | Automatic Content Decoding      |
-| Automatic Connection Pooling     | Unicode Response Bodies (smart) |
-| Multi-part File Uploads          | SOCKS Proxy Support             |
-| Connection Timeouts              | Streaming Downloads             |
-| Automatic honoring of `.netrc`   | Chunked HTTP Requests           |
+<style type="text/css">
+.tg  {border-collapse:collapse;border-spacing:0;}
+.tg td{font-family:Arial, sans-serif;font-size:14px;padding:10px 5px;border-style:solid;border-width:1px;overflow:hidden;word-break:normal;border-color:black;}
+.tg th{font-family:Arial, sans-serif;font-size:14px;font-weight:normal;padding:10px 5px;border-style:solid;border-width:1px;overflow:hidden;word-break:normal;border-color:black;}
+.tg .tg-0pky{border-color:inherit;text-align:left;vertical-align:top}
+</style>
+<table class="tg">
+  <tr>
+    <th class="tg-0pky">International Domains and URLs</th>
+    <th class="tg-0pky">Keep-Alive &amp; Connection Pooling</th>
+  </tr>
+  <tr>
+    <td class="tg-0pky"></td>
+    <td class="tg-0pky"></td>
+  </tr>
+  <tr>
+    <td class="tg-0pky"></td>
+    <td class="tg-0pky"></td>
+  </tr>
+</table>
 
 
 Requests officially supports Python 2.7 & 3.4–3.8, and runs great on

```

</details>

---

## Case 15 — `ad42584ef15e8b0b`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Update the advanced doc to use the r.json method
- **commit** https://github.com/psf/requests/commit/7687746c7c1691946f24e414c065025f895104e6
- **doc** `docs/user/advanced.rst`
- **no longer asserted after this commit** `content`, `text`

**VERDICT: `unclear`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/user/advanced.rst b/docs/user/advanced.rst
index 0e0405ce..92108339 100644
--- a/docs/user/advanced.rst
+++ b/docs/user/advanced.rst
@@ -313,17 +313,12 @@ out what type of content it is. Do this like so::
     ...
     application/json; charset=utf-8
 
-So, GitHub returns JSON. That's great, we can use the JSON module to turn it
-into Python objects. Because GitHub returned UTF-8, we should use the
-``r.text`` method, not the ``r.content`` method. ``r.content`` returns a
-bytestring, while ``r.text`` returns a Unicode-encoded string. I have no plans
-to perform byte-manipulation on this response, so I want any Unicode code
-points encoded.
+So, GitHub returns JSON. That's great, we can use the ``r.json`` method to
+parse it into Python objects.
 
 ::
 
-    >>> import json
-    >>> commit_data = json.loads(r.text)
+    >>> commit_data = r.json()
     >>> print commit_data.keys()
     [u'committer', u'author', u'url', u'tree', u'sha', u'parents', u'message']
     >>> print commit_data[u'committer']
@@ -380,7 +375,7 @@ Cool, we have three comments. Let's take a look at the last of them.
     >>> r = requests.get(r.url + u'/comments')
     >>> r.status_code
     200
-    >>> comments = json.loads(r.text)
+    >>> comments = r.json()
     >>> print comments[0].keys()
     [u'body', u'url', u'created_at', u'updated_at', u'user', u'id']
     >>> print comments[2][u'body']
@@ -417,7 +412,7 @@ the very common Basic Auth.
     >>> r = requests.post(url=url, data=body, auth=auth)
     >>> r.status_code
     201
-    >>> content = json.loads(r.text)
+    >>> content = r.json()
     >>> print content[u'body']
     Sounds great! I'll get right on it.
 

```

</details>

---

## Case 16 — `06c74ca6b2fc7674`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** If this comment is true (https://github.com/kennethreitz/requests/issues/239#issuecomment-6180706), then it would be good to point people in the right direction. Otherwise disregard this message.
- **commit** https://github.com/psf/requests/commit/c589d8a251868d983ecf97b2fbffff0e9f29e56c
- **doc** `docs/user/advanced.rst`
- **no longer asserted after this commit** `response`, `request`, `send`, `size`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/user/advanced.rst b/docs/user/advanced.rst
index fe5e19ea..ac8ab984 100644
--- a/docs/user/advanced.rst
+++ b/docs/user/advanced.rst
@@ -107,43 +107,8 @@ If you'd like to disable keep-alive, you can simply set the ``keep_alive`` confi
 Asynchronous Requests
 ----------------------
 
-Requests has first-class support for concurrent requests, powered by gevent.
-This allows you to send a bunch of HTTP requests at the same time.
 
-First, let's import the async module. Heads up — if you don't have
-`gevent <http://pypi.python.org/pypi/gevent>`_ this will fail::
-
-    from requests import async
-
-The ``async`` module has the exact same api as ``requests``, except it
-doesn't send the request immediately. Instead, it returns the ``Request``
-object.
-
-We can build a list of ``Request`` objects easily::
-
-    urls = [
-        'http://python-requests.org',
-        'http://httpbin.org',
-        'http://python-guide.org',
-        'http://kennethreitz.com'
-    ]
-
-    rs = [async.get(u) for u in urls]
-
-Now we have a list of ``Request`` objects, ready to be sent. We could send them
-one at a time with ``Request.send()``, but that would take a while.  Instead,
-we'll send them all at the same time with ``async.map()``.  Using ``async.map()``
-will also guarantee execution of the ``response`` hook, described below. ::
-
-    >>> responses = async.map(rs)
-    >>> responses
-    [<Response [200]>, <Response [200]>, <Response [200]>, <Response [200]>]
-
-.. admonition:: Throttling
-
-    The ``map`` function also takes a ``size`` parameter, that specifies the number of connections to make at a time::
-
-        async.map(rs, size=5)
+``requests.async`` has been removed from requests and is now its own repository named `GRequests <https://github.com/kennethreitz/grequests>`_.
 
 
 Event Hooks

```

</details>

---

## Case 17 — `ce92c8fc35b59cf8`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** python for ios
- **commit** https://github.com/psf/requests/commit/afd64822198206aef3b4b6fc7140fe351dfafd43
- **doc** `docs/community/out-there.rst`
- **no longer asserted after this commit** `ver:1.0`, `ver:2.0`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/community/out-there.rst b/docs/community/out-there.rst
index 9b90771b..c3cf0f5e 100644
--- a/docs/community/out-there.rst
+++ b/docs/community/out-there.rst
@@ -1,8 +1,6 @@
 Modules
 =======
-
-- `requests-oauth <https://github.com/maraujop/requests-oauth>`_, adds OAuth support to Requests.
-- `rauth <https://github.com/litl/rauth>`_, an alternative to requests-oauth, supports OAuth versions 1.0 and 2.0.
+- `HTTPie <https://github.com/jkbr/httpie>`_, a CLI, cURL-like tool for humans.
 - `FacePy <https://github.com/jgorset/facepy>`_, a Python wrapper to the Facebook API.
 - `robotframework-requests <https://github.com/bulkan/robotframework-requests>`_, a Robot Framework API wrapper.
 - `fullerene <https://github.com/bitprophet/fullerene>`_, a Graphite Dashboard.
@@ -32,6 +30,15 @@ ScraperWiki
 you to run Python, Ruby, and PHP scraper scripts on the web. Now, Requests
 v0.6.1 is available to use in your scrapers!
 
+To give it a try, simply::
+
+    import requests
+
+Python for iOS
+--------------
+
+Requests is built into the wonderful `Python for iOS <https://itunes.apple.com/us/app/python-2.7-for-ios/id485729872?mt=Python8>`_ runtime!
+
 To give it a try, simply::
 
     import requests

```

</details>

---

## Case 18 — `48d81fed0ad3c89c`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Request->Response.
- **commit** https://github.com/psf/requests/commit/bf8f791a936dbaadb6be33546f41bca50a652ac0
- **doc** `docs/user/quickstart.rst`
- **no longer asserted after this commit** `request`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/user/quickstart.rst b/docs/user/quickstart.rst
index ff008347..1a4b2714 100644
--- a/docs/user/quickstart.rst
+++ b/docs/user/quickstart.rst
@@ -31,7 +31,7 @@ timeline ::
 
     >>> r = requests.get('https://api.github.com/events')
 
-Now, we have a :class:`Request <requests.Request>` object called ``r``. We can
+Now, we have a :class:`Response <requests.Response>` object called ``r``. We can
 get all the information we need from this object.
 
 Requests' simple API means that all forms of HTTP request are as obvious. For

```

</details>

---

## Case 19 — `168ab0f8982d4215`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** remove note about cacerts.pem
- **commit** https://github.com/psf/requests/commit/e41c2c2d965f6afb908c5acb595234d2bc5d2fe1
- **doc** `docs/dev/todo.rst`
- **no longer asserted after this commit** `cacerts`

**VERDICT: `drift`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/dev/todo.rst b/docs/dev/todo.rst
index 7a7f4edb..88f0073c 100644
--- a/docs/dev/todo.rst
+++ b/docs/dev/todo.rst
@@ -62,8 +62,3 @@ with the `Requests-Toolbelt`_.
 
 .. _Requests-Toolbelt: http://toolbelt.readthedocs.io/
 
-
-Downstream Repackaging
-----------------------
-
-If you are repackaging Requests, please note that you must also redistribute the ``cacerts.pem`` file in order to get correct SSL functionality.

```

</details>

---

## Case 20 — `ec2ba53db848cd72`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Remove stale sentence in philosophy.rst
- **commit** https://github.com/psf/requests/commit/d801d7797e509add1245acc85cd006b6fec21beb
- **doc** `docs/dev/philosophy.rst`
- **no longer asserted after this commit** `ver:0.0`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/dev/philosophy.rst b/docs/dev/philosophy.rst
index 8c9490ab..ab9f37ae 100644
--- a/docs/dev/philosophy.rst
+++ b/docs/dev/philosophy.rst
@@ -33,8 +33,6 @@ Requests has no *active* plans to be included in the standard library. This deci
 
 Essentially, the standard library is where a library goes to die. It is appropriate for a module to be included when active development is no longer necessary.
 
-Requests just reached v1.0.0. This huge milestone marks a major step in the right direction.
-
 Linux Distro Packages
 ~~~~~~~~~~~~~~~~~~~~~
 

```

</details>

---

