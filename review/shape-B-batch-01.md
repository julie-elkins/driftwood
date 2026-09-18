# Drift label review — 20 cases (seed 7)

For each case, replace `VERDICT: ?` with one of:

- `drift` — the doc said something untrue about the code, and this commit corrected it
- `new` — the doc was documenting something that did not exist yet (feature + its docs)
- `cosmetic` — wording, formatting or a link -- nothing factual changed
- `unrelated` — the doc change and the code change are not about the same thing
- `unclear` — cannot tell from these diffs alone

The question is always: **at the parent commit, was this documentation false about the code?** Not whether the commit improved the docs — whether what it replaced was wrong.

---

## Case 1 — `d66019e9f9f6a687`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** docs
- **commit** https://github.com/psf/requests/commit/c2c523ba9e327adf5810165d115136397f8190f7
- **doc** `docs/index.rst`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/index.rst b/docs/index.rst
index 7a5568e3..c1d78c87 100644
--- a/docs/index.rst
+++ b/docs/index.rst
@@ -73,7 +73,7 @@ Institutions that prefer to be unnamed claim to use Requests internally.
     right level of abstraction.
 
 **Matt DeBoard**
-    I'm going to get @kennethreitz's Python requests module tattooed
+    I'm going to get `@kennethreitz <https://twitter.com/kennethreitz>`_'s Python requests module tattooed
     on my body, somehow. The whole thing.
 
 **Daniel Greenfeld**

```

</details>

---

## Case 2 — `ef41b178cdff4618`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** fix
- **commit** https://github.com/psf/requests/commit/5d0635473446121afeea34d109504a44be14d4e0
- **doc** `docs/index.rst`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/index.rst b/docs/index.rst
index b1696497..35f8c617 100644
--- a/docs/index.rst
+++ b/docs/index.rst
@@ -28,7 +28,7 @@ Release v\ |version|. (:ref:`Installation <install>`)
 **Requests** is the only *Non-GMO* HTTP library for Python, safe for human
 consumption.
 
-.. note:: **Requests 2.x** is officially in *maintinence-mode only*. This means we only respond to CVE-level tickets. All of our limited available attention / energy is being allocated towards the development of `Requests III <https://3.python-requests.org/>`_. Your involvement / support is appreciated! Please see `this page <https://kennethreitz.org/requests3>`_ for more details.`.
+.. note:: **Requests 2.x** is officially in *maintinence-mode only*. This means we only respond to CVE-level tickets. All of our limited available attention / energy is being allocated towards the development of `Requests III <https://3.python-requests.org/>`_. Your involvement / support is appreciated! Please see `this page <https://kennethreitz.org/requests3>`_ for more details.
 
 If you're on the job market, consider taking `this programming quiz <https://triplebyte.com/a/b1i2FB8/requests-docs-home>`_. A substantial donation will be made to this project, if you find a job through this platform.
 

```

</details>

---

## Case 3 — `318d9107e8339dbf`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Reverting redirect examples back to intended URLs
- **commit** https://github.com/psf/requests/commit/5fdc25b029b582464e90c0374ce3b3297a3ccd60
- **doc** `docs/user/quickstart.rst`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/user/quickstart.rst b/docs/user/quickstart.rst
index 1a75b5ce..f47903cf 100644
--- a/docs/user/quickstart.rst
+++ b/docs/user/quickstart.rst
@@ -481,7 +481,7 @@ response.
 
 For example, GitHub redirects all HTTP requests to HTTPS::
 
-    >>> r = requests.get('https://github.com/')
+    >>> r = requests.get('http://github.com/')
 
     >>> r.url
     'https://github.com/'
@@ -496,7 +496,7 @@ For example, GitHub redirects all HTTP requests to HTTPS::
 If you're using GET, OPTIONS, POST, PUT, PATCH or DELETE, you can disable
 redirection handling with the ``allow_redirects`` parameter::
 
-    >>> r = requests.get('https://github.com/', allow_redirects=False)
+    >>> r = requests.get('http://github.com/', allow_redirects=False)
 
     >>> r.status_code
     301
@@ -506,7 +506,7 @@ redirection handling with the ``allow_redirects`` parameter::
 
 If you're using HEAD, you can enable redirection as well::
 
-    >>> r = requests.head('https://github.com/', allow_redirects=True)
+    >>> r = requests.head('http://github.com/', allow_redirects=True)
 
     >>> r.url
     'https://github.com/'

```

</details>

---

## Case 4 — `93a5ef9d51835b52`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Update supported Python versions
- **commit** https://github.com/psf/requests/commit/f462eecf4817ad886efd21f417129c4fd820c7ce
- **doc** `docs/community/faq.rst`

**VERDICT: `unclear`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/community/faq.rst b/docs/community/faq.rst
index 9fdce417..ebc6bb7e 100644
--- a/docs/community/faq.rst
+++ b/docs/community/faq.rst
@@ -54,15 +54,7 @@ Chris Adams gave an excellent summary on
 Python 3 Support?
 -----------------
 
-Yes! Here's a list of Python platforms that are officially
-supported:
-
-* Python 2.7
-* Python 3.4
-* Python 3.5
-* Python 3.6
-* Python 3.7
-* PyPy
+Yes! Requests officially supports Python 2.7 & 3.5+ and PyPy.
 
 What are "hostname doesn't match" errors?
 -----------------------------------------

```

</details>

---

## Case 5 — `64fb8850330e5ff9`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Update README.rst
- **commit** https://github.com/psf/requests/commit/44c9b7e93b47333f910177773f3edcafa51ece59
- **doc** `README.rst`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/README.rst b/README.rst
index 0e165b5f..1dbee794 100644
--- a/README.rst
+++ b/README.rst
@@ -10,9 +10,6 @@ Requests: HTTP for Humans
 .. image:: https://img.shields.io/pypi/pyversions/requests.svg
     :target: https://pypi.python.org/pypi/requests
 
-.. image:: https://travis-ci.org/requests/requests.svg?branch=master
-    :target: https://travis-ci.org/requests/requests
-
 .. image:: https://codecov.io/github/requests/requests/coverage.svg?branch=master
     :target: https://codecov.io/github/requests/requests
     :alt: codecov.io

```

</details>

---

## Case 6 — `221715d0242ad252`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Update README.md
- **commit** https://github.com/psf/requests/commit/c4c60864f8868ec33f3d33dc635f60a5453a3d71
- **doc** `README.md`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/README.md b/README.md
index 83fc8ba5..61e2ec97 100644
--- a/README.md
+++ b/README.md
@@ -3,7 +3,7 @@
 <span align="center">
 
 <pre>
-    <a href="https://2.python-requests.org/"><img src="https://raw.githubusercontent.com/psf/requests/master/ext/deepmind-kr.jpg" align="center" /></a>
+    <a href="https://2.python-requests.org/"><img src="https://raw.githubusercontent.com/psf/requests/master/ext/kr.jpg" align="center" /></a>
     <div align="left">
     <p></p>
     <code> Python 3.7.4 (default, Sep  7 2019, 18:27:02)</code>

```

</details>

---

## Case 7 — `d3ee01cb6e880fcd`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** fix codecov logo in readme
- **commit** https://github.com/psf/requests/commit/7d57e8ec55a95fdd818fb089533fbab8cc207989
- **doc** `README.md`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/README.md b/README.md
index 41e92667..ba63a552 100644
--- a/README.md
+++ b/README.md
@@ -4,7 +4,7 @@ Requests: HTTP for Humans™
 [![image](https://img.shields.io/pypi/v/requests.svg)](https://pypi.org/project/requests/)
 [![image](https://img.shields.io/pypi/l/requests.svg)](https://pypi.org/project/requests/)
 [![image](https://img.shields.io/pypi/pyversions/requests.svg)](https://pypi.org/project/requests/)
-[![codecov.io](https://codecov.io/github/requests/requests/coverage.svg?branch=master)](https://codecov.io/github/requests/requests)
+[![codecov.io](https://codecov.io/github/psf/requests/coverage.svg?branch=master)](https://codecov.io/github/psf/requests)
 [![image](https://img.shields.io/github/contributors/requests/requests.svg)](https://github.com/requests/requests/graphs/contributors)
 [![image](https://img.shields.io/badge/Say%20Thanks-!-1EAEDB.svg)](https://saythanks.io/to/kennethreitz)
 

```

</details>

---

## Case 8 — `c5df13f57266984a`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Update README.md
- **commit** https://github.com/psf/requests/commit/e35ace77bfe246d083c5ff247357a5e5e6196c45
- **doc** `README.md`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/README.md b/README.md
index 761614c4..2022ecec 100644
--- a/README.md
+++ b/README.md
@@ -62,8 +62,7 @@ Besides, all the cool kids are doing it. Requests is one of the most
 downloaded Python packages of all time, pulling about 60,000,000
 downloads every month. You don't want to be left out!
 
-Feature Support
----------------
+<h2 align="center>Supported Features</h2>
 
 Requests is ready for the demands of building robust and reliable HTTP–speaking applications, on today's web (or your own infrastructure).
 

```

</details>

---

## Case 9 — `30b6d94502f02abf`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Update README.md
- **commit** https://github.com/psf/requests/commit/ac9f0d7c978528615183598377144186295025b1
- **doc** `README.md`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/README.md b/README.md
index 26a35083..6ab92e85 100644
--- a/README.md
+++ b/README.md
@@ -71,8 +71,9 @@ Requests is ready for the demands of building robust and reliable HTTP–speakin
                             &, of course, rock–solid stability!
 </pre>
 </div>
+
 <p align="center">
-        <img src="https://raw.githubusercontent.com/psf/requests/master/ext/license.png" align="center" />
+        ✨ 🍰 ✨
 </p>
 
 
@@ -103,10 +104,9 @@ PyPy.
 
 ------------------
 
+
 <p align="center">
-        ✨ 🍰 ✨
+        <img src="https://raw.githubusercontent.com/psf/requests/master/ext/license.png" align="center" />
 </p>
 
 
-
-

```

</details>

---

## Case 10 — `c27fe1ccf9a1df41`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** streaming doc clarification
- **commit** https://github.com/psf/requests/commit/4f9d0e04552e7cfcc5bcc2a37cf9e548ca09ffd8
- **doc** `docs/user/quickstart.rst`

**VERDICT: `unclear`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/user/quickstart.rst b/docs/user/quickstart.rst
index 4aa2bbf4..232760f4 100644
--- a/docs/user/quickstart.rst
+++ b/docs/user/quickstart.rst
@@ -178,13 +178,14 @@ In general, however, you should use a pattern like this to save what is being
 streamed to a file::
 
     with open(filename, 'wb') as fd:
-        for chunk in r.iter_content(chunk_size):
+        for chunk in r.iter_content(chunk_size=128):
             fd.write(chunk)
 
 Using ``Response.iter_content`` will handle a lot of what you would otherwise
 have to handle when using ``Response.raw`` directly. When streaming a
 download, the above is the preferred and recommended way to retrieve the
-content. Note that ``chunk_size`` is optional.
+content. Note that ``chunk_size`` can be freely adjusted to a number that
+may better fit your use cases.
 
 
 Custom Headers

```

</details>

---

## Case 11 — `3c9dcb3e22404af2`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Update index.rst to match README info (#7386)
- **commit** https://github.com/psf/requests/commit/93bf5331a70cd2c77ac3ba43f85c918cae67c69f
- **doc** `docs/index.rst`

**VERDICT: `unclear`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/index.rst b/docs/index.rst
index aef47a89..e8564c1b 100644
--- a/docs/index.rst
+++ b/docs/index.rst
@@ -9,21 +9,25 @@ Requests: HTTP for Humans™
 Release v\ |version|. (:ref:`Installation <install>`)
 
 
-.. image:: https://static.pepy.tech/badge/requests/month
-    :target: https://pepy.tech/project/requests
-    :alt: Requests Downloads Per Month Badge
-    
-.. image:: https://img.shields.io/pypi/l/requests.svg
+.. image:: https://img.shields.io/pypi/v/requests.svg?maxAge=86400
     :target: https://pypi.org/project/requests/
-    :alt: License Badge
-
-.. image:: https://img.shields.io/pypi/wheel/requests.svg
-    :target: https://pypi.org/project/requests/
-    :alt: Wheel Support Badge
+    :alt: PyPI Version Badge
 
 .. image:: https://img.shields.io/pypi/pyversions/requests.svg
     :target: https://pypi.org/project/requests/
-    :alt: Python Version Support Badge
+    :alt: Supported Versions Badge
+
+.. image:: https://static.pepy.tech/badge/requests/month
+    :target: https://pepy.tech/project/requests
+    :alt: Downloads Per Month Badge
+
+.. image:: https://img.shields.io/github/contributors/psf/requests.svg
+    :target: https://github.com/psf/requests/graphs/contributors
+    :alt: Contributors Badge
+
+.. image:: https://readthedocs.org/projects/requests/badge/?version=latest
+    :target: https://requests.readthedocs.io
+    :alt: Documentation Badge
 
 **Requests** is an elegant and simple HTTP library for Python, built for human beings.
 
@@ -72,7 +76,7 @@ Requests is ready for today's web.
 - Chunked Requests
 - ``.netrc`` Support
 
-Requests officially supports Python 3.9+, and runs great on PyPy.
+Requests officially supports Python 3.10+, and runs great on PyPy.
 
 
 The User Guide

```

</details>

---

## Case 12 — `d5e552a80f62ed8a`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Add netrc file search information to authentication documentation (#6876)
- **commit** https://github.com/psf/requests/commit/59f8aa2adf1d3d06bcbf7ce6b13743a1639a5401
- **doc** `docs/user/authentication.rst`

**VERDICT: `unclear`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/user/authentication.rst b/docs/user/authentication.rst
index 0737bd31..76be9ccc 100644
--- a/docs/user/authentication.rst
+++ b/docs/user/authentication.rst
@@ -44,6 +44,16 @@ set with `headers=`.
 If credentials for the hostname are found, the request is sent with HTTP Basic
 Auth.
 
+Requests will search for the netrc file at `~/.netrc`, `~/_netrc`, or at the path
+specified by the `NETRC` environment variable. `~` denotes the user's home
+directory, which is `$HOME` on Unix based systems and `%USERPROFILE%` on Windows.
+
+Usage of netrc file can be disabled by setting `trust_env` to `False` in the
+Requests session::
+
+    >>> s = requests.Session()
+    >>> s.trust_env = False
+    >>> s.get('https://httpbin.org/basic-auth/user/pass')
 
 Digest Authentication
 ---------------------

```

</details>

---

## Case 13 — `d7f78f065a6aef77`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Clarify that a Session can have multiple hooks
- **commit** https://github.com/psf/requests/commit/40c5a8b0c28e2756e83ecfab0160ca3be37391e1
- **doc** `docs/user/advanced.rst`

**VERDICT: `unclear`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/user/advanced.rst b/docs/user/advanced.rst
index 93f86baa..c24f6e5b 100644
--- a/docs/user/advanced.rst
+++ b/docs/user/advanced.rst
@@ -458,8 +458,8 @@ Let's print some request method arguments at runtime::
     http://httpbin.org
     <Response [200]>
 
-You can also assign hooks to a ``Session`` instance.  The hook will then be
-called on every request made to the session.  For example::
+You can also add hooks to a ``Session`` instance.  Any hooks you add will then
+be called on every request made to the session.  For example::
 
    >>> s = requests.Session()
    >>> s.hooks['response'].append(print_url)
@@ -467,6 +467,9 @@ called on every request made to the session.  For example::
     http://httpbin.org
     <Response [200]>
 
+A ``Session`` can have multiple hooks, which will be called in the order
+they are added.
+
 .. _custom-auth:
 
 Custom Authentication

```

</details>

---

## Case 14 — `cc0e8c8fb6f478c7`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Update README.md
- **commit** https://github.com/psf/requests/commit/687ff0eb360c054e11d4e9de78c129f6501511f4
- **doc** `README.md`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/README.md b/README.md
index 9dce3e7b..cd7b5f34 100644
--- a/README.md
+++ b/README.md
@@ -7,6 +7,7 @@
     <code> >>> r.json()["description"]</code>
     <code> 'An elegant & simple HTTP library. Handcrafted, with ♥, for the Python community.'</code>
     </div>
+    <img src="https://raw.githubusercontent.com/psf/requests/master/docs/_static/requests-logo-small.png" align="right" />
 </pre>  
    
 </span>
@@ -40,7 +41,7 @@ u'{"type":"User"...'
 
 See [the similar code, sans Requests](https://gist.github.com/973705).
 
-[![image](https://raw.githubusercontent.com/psf/requests/master/docs/_static/requests-logo-small.png)](http://docs.python-requests.org/)
+[![image]()](http://docs.python-requests.org/)
 
 Requests allows you to send *organic, grass-fed* HTTP/1.1 requests,
 without the need for manual labor. There's no need to manually add query

```

</details>

---

## Case 15 — `314b338cd797736c`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Update all documentation to show Python 3.7 is supported
- **commit** https://github.com/psf/requests/commit/c8f3add5ed31bbb82cb337435295200a3525920a
- **doc** `README.rst`

**VERDICT: `unclear`**

<details><summary>doc diff</summary>

```diff
diff --git a/README.rst b/README.rst
index 7846e068..af4ce7e7 100644
--- a/README.rst
+++ b/README.rst
@@ -77,7 +77,7 @@ Requests is ready for today's web.
 - ``.netrc`` Support
 - Chunked Requests
 
-Requests officially supports Python 2.7 & 3.4–3.6, and runs great on PyPy.
+Requests officially supports Python 2.7 & 3.4–3.7, and runs great on PyPy.
 
 Installation
 ------------

```

</details>

---

## Case 16 — `f97654b605cff329`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Update README.md
- **commit** https://github.com/psf/requests/commit/dc1526f85d7b55d7f2005c0a8cd8eacf47d77a5c
- **doc** `README.md`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/README.md b/README.md
index cdf6efb0..93c69244 100644
--- a/README.md
+++ b/README.md
@@ -29,6 +29,8 @@ by <a href="https://kennethreitz.org/">Kenneth Reitz</a> & is secured by The <a
 
 <p align="center"><strong>Requests</strong> is an elegant and simple HTTP library for Python, built with ♥.</p>
 
+<p>&nbsp;</p>
+
 ```pycon
 >>> import requests
 >>> r = requests.get('https://api.github.com/user', auth=('user', 'pass'))

```

</details>

---

## Case 17 — `a96e6f1dfacf8eac`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Update advanced.rst
- **commit** https://github.com/psf/requests/commit/3cb75399812ad3b2ef6dd12d19cc814b9e48ab13
- **doc** `docs/user/advanced.rst`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/user/advanced.rst b/docs/user/advanced.rst
index 0806ff6d..cd6c4d7d 100644
--- a/docs/user/advanced.rst
+++ b/docs/user/advanced.rst
@@ -225,6 +225,9 @@ Requests can also ignore verifying the SSL certificate if you set ``verify`` to
 
 By default, ``verify`` is set to True. Option ``verify`` only applies to host certs.
 
+Client side certificates
+------------------------
+
 You can also specify a local cert to use as client side certificate, as a single
 file (containing the private key and the certificate) or as a tuple of both
 files' paths::

```

</details>

---

## Case 18 — `4e30e1db13992a26`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** we support python 3.6
- **commit** https://github.com/psf/requests/commit/c3fb8e020b865a04afbc01e2c439fb3995feb702
- **doc** `README.rst`

**VERDICT: `unclear`**

<details><summary>doc diff</summary>

```diff
diff --git a/README.rst b/README.rst
index a5916437..e1783b70 100644
--- a/README.rst
+++ b/README.rst
@@ -73,7 +73,7 @@ Requests is ready for today's web.
 - Chunked Requests
 - Thread-safety
 
-Requests officially supports Python 2.6–2.7 & 3.3–3.5, and runs great on PyPy.
+Requests officially supports Python 2.6–2.7 & 3.3–3.6, and runs great on PyPy.
 
 Installation
 ------------

```

</details>

---

## Case 19 — `c81f449bfd33366d`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Update README.md
- **commit** https://github.com/psf/requests/commit/92b88fcffb312630dd3e8b94b44be8a746fd585b
- **doc** `README.md`

**VERDICT: `cosmetic`**

<details><summary>doc diff</summary>

```diff
diff --git a/README.md b/README.md
index f2c5152b..6bdc1472 100644
--- a/README.md
+++ b/README.md
@@ -20,7 +20,7 @@ This software has been designed for you, with much joy,
 by <a href="https://kennethreitz.org/">Kenneth Reitz</a> & is secured by The <a href="https://www.python.org/psf/">Python Software Foundation</a>.  
    </p>
 <p>&nbsp;</p>
-<img src="https://github.com/psf/requests/blob/master/ext/flourish.png?raw=true" />
+<img src="https://github.com/psf/requests/blob/master/ext/flourish.jpg?raw=true" />
 </pre>
 
 </span>

```

</details>

---

## Case 20 — `06314df7cd0de29c`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** mention all_proxy env variable in Proxies section
- **commit** https://github.com/psf/requests/commit/e2fa8d3654b48a3ef3d268624d365bb2dfbf0927
- **doc** `docs/user/advanced.rst`

**VERDICT: `unclear`**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/user/advanced.rst b/docs/user/advanced.rst
index 24e07528..215a2ede 100644
--- a/docs/user/advanced.rst
+++ b/docs/user/advanced.rst
@@ -605,13 +605,13 @@ Alternatively you can configure it once for an entire
 
 When the proxies configuration is not overridden in python as shown above,
 by default Requests relies on the proxy configuration defined by standard
-environment variables ``http_proxy``, ``https_proxy``, ``no_proxy`` and
-``curl_ca_bundle``. Uppercase variants of these variables are also supported.
-You can therefore set them to configure Requests (only set the ones relevant
-to your needs)::
+environment variables ``http_proxy``, ``https_proxy``, ``no_proxy``, 
+``curl_ca_bundle``, and ``all_proxy``. Uppercase variants of these variables are also supported.
+You can therefore set them to configure Requests (you only need to export one)::
 
     $ export HTTP_PROXY="http://10.10.1.10:3128"
     $ export HTTPS_PROXY="http://10.10.1.10:1080"
+    $ export ALL_PROXY="socks5://10.10.1.10:3434"
 
     $ python
     >>> import requests

```

</details>

---

g 