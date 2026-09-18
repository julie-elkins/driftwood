# Drift label review — 20 cases (seed 43)

For each case, replace `VERDICT: ?` with one of:

- `drift` — the doc said something untrue about the code, and this commit corrected it
- `new` — the doc was documenting something that did not exist yet (feature + its docs)
- `cosmetic` — wording, formatting or a link -- nothing factual changed
- `unrelated` — the doc change and the code change are not about the same thing
- `unclear` — cannot tell from these diffs alone

The question is always: **at the parent commit, was this documentation false about the code?** Not whether the commit improved the docs — whether what it replaced was wrong.

---

## Case 1 — `222912096e5bad9a`

- **repo** `pallets/flask` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Clean up tutorial docs for installable app pattern with flaskr (#2002)
- **commit** https://github.com/pallets/flask/commit/e6f9d2b41417b442946acfede9200d361ac401cc
- **doc** `docs/tutorial/setup.rst`
- **no longer asserted after this commit** `setuptools`

**VERDICT: ?**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/tutorial/setup.rst b/docs/tutorial/setup.rst
index 78b6390a..4bedb54c 100644
--- a/docs/tutorial/setup.rst
+++ b/docs/tutorial/setup.rst
@@ -94,4 +94,4 @@ tuples.
 
 In the next section you will see how to run the application.
 
-Continue with :ref:`tutorial-setuptools`.
+Continue with :ref:`tutorial-packaging`.

```

</details>

---

## Case 2 — `dfea2b0068c42323`

- **repo** `encode/httpx` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Update README.md
- **commit** https://github.com/encode/httpx/commit/01a3c090646f219f22c930c5f9ddf372454ebc06
- **doc** `README.md`
- **no longer asserted after this commit** `requests3`, `httpcore`, `response`, `headers`, `encode`, `core`, `text`

**VERDICT: ?**

<details><summary>doc diff</summary>

```diff
diff --git a/README.md b/README.md
index 94d2e72..4aa8778 100644
--- a/README.md
+++ b/README.md
@@ -1,64 +1,29 @@
 # HTTPCore
 
-I started to dive into implementation and API design here.
-
-I know this isn't what you were suggesting with `requests-core`, but it'd be
-worth you taking a slow look at this and seeing if there's anything that you
-think is a no-go.
-
-`httpcore` provides the same proposed *functionality* as requests-core, but at a slightly
-lower abstraction level.
-
-Rather than returning `Response` models, it returns the minimal possible
-interface. There's no `response.text` or any other cleverness, `response.headers`
-are plain byte-pair lists, rather than a headers datastructure etc...
-
-**The proposal here is that `httpcore` would be a silent-partner dependency of `requests3`,
-taking the place of the existing `urllib3` dependency.**
-
----
-
-The benefits to my mind of this level of abstraction are that it is as
-agnostic as possible to whatever request/response models are built on top
-of it, and exposes only plain datastructures that reflect the network response.
-
-* An `encode/httpcore` package would be something I'd gladly maintain. The naming
-  makes sense to me, as there's no strictly implied relationship to `requests`,
-  although it would fulfil all the requirements for `requests3` to build on,
-  and would have a strict semver policy.
-* An `encode/httpcore` package is something that would play in well to the
-  collaboratively sponsored OSS story that Encode is pitching. It'd provide what
-  you need for `requests3` without encroaching on the `requests` brand.
-  We'd position it similarly to how `urllib3` is positioned to `requests` now.
-  A focused, low-level networking library, that `requests` then builds the
-  developer-focused API on top of.
-* A big chunk of this is implemented now. Streaming requests and responses are
-  supported. Connection pooling is stubbed-out at the moment, but all in place.
-  GZip decoding is stubbed-out at the moment, but easy to do, and all in place.
-  Theres various stuff around connection closing and error handling still to finesse.
-* Take a quick look over the test cases or the package itself to get a feel
-  for it. It's all type annotated, and should be easy to find your way around.
-* I've not yet added corresponding sync API points to the implementation, but
-  they will come.
-* We would absolutely want to implement HTTP/2 support.
-* Trio support is something that could *potentially* come later, but it needs to
-  be a secondary consideration.
-* I think all the functionality required is stubbed out in the API, with two exceptions.
-  (1) I've not yet added any proxy configuration API. Haven't looked into that enough
-  yet. (2) I've not yet added any retry configuration API, since I havn't really
-  looked enough into which side of requests vs. urllib3 that sits on, or exactly how
-  urllib3 tackles retries, etc.
-* I'd be planning to prioritize working on this from Mon 15th April. I don't think
-  it'd take too long to get it to a feature complete and API stable state.
-  (With the exception of the later HTTP/2 work, which I can't really assess yet.)
-  I probably don't have any time left before then - need to focus on what I'm
-  delivering to DjangoCon Europe over the rest of this week.
-* To my mind the killer app for `requests3`/`httpcore` is a high-performance
-  proxy server / gateway service in Python. Pitching the growing ASGI ecosystem
-  is an important part of that story.
-* I think there's enough headroom before PyCon to have something ready to pitch by then.
-  I could be involved in sprints remotely if there's areas we still need to fill in,
-  anyplace.
+A low-level async HTTP library.
+
+## Proposed functionality
+
+* Support for streaming requests and responses. (Done)
+* Support for connection pooling. (Not done, but structure in place)
+* gzip, deflate, and brotli decoding. (Not done, but structure in place)
+* SSL verificati
```

</details>

---

## Case 3 — `3e7924f77b518e35`

- **repo** `pallets/flask` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** clean up py3 info more
- **commit** https://github.com/pallets/flask/commit/baa2689658e340fc5a2a093bb061f3b9af6d85b6
- **doc** `docs/python3.rst`
- **no longer asserted after this commit** `itsdangerous`, `werkzeug`, `jinja2`

**VERDICT: ?**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/python3.rst b/docs/python3.rst
index 4d488f16..61ef3eaa 100644
--- a/docs/python3.rst
+++ b/docs/python3.rst
@@ -3,32 +3,22 @@
 Python 3 Support
 ================
 
-Flask and all of its dependencies support Python 3 so you can in theory
-start working on it already.  There are however a few things you should be
-aware of before you start using Python 3 for your next project.
+Flask, its dependencies, and most Flask extensions support Python 3.
+You should start using Python 3 for your next project,
+but there are a few things to be aware of.
 
-If you want to use Flask with Python 3 you will need to use Python 3.3 or
-higher.  3.2 and older are *not* supported.
+You need to use Python 3.3 or higher.  3.2 and older are *not* supported.
 
-In addition to that you need to use the latest and greatest versions of
-`itsdangerous`, `Jinja2` and `Werkzeug`. Flask 0.10 and Werkzeug 0.9 were
-the first versions to introduce Python 3 support.
+You should use the latest versions of all Flask-related packages.
+Flask 0.10 and Werkzeug 0.9 were the first versions to introduce Python 3 support.
 
-Some of the decisions made in regards to unicode and byte utilization on
-Python 3 make it hard to write low level code.  This mainly affects WSGI
-middlewares and interacting with the WSGI provided information.  Werkzeug
-wraps all that information in high-level helpers but some of those were
-specifically added for the Python 3 support and are quite new.
+Python 3 changed how unicode and bytes are handled,
+which complicated how low level code handles HTTP data.
+This mainly affects WSGI middleware interacting with the WSGI ``environ`` data.
+Werkzeug wraps that information in high-level helpers,
+so encoding issues should not effect you.
 
-Unless you require absolute compatibility, you should be fine with Python 3
-nowadays. Most libraries and Flask extensions have been ported by now and
-using Flask with Python 3 is generally a smooth ride. However, keep in mind
-that most libraries (including Werkzeug and Flask) might not quite as stable
-on Python 3 yet. You might therefore sometimes run into bugs that are
-usually encoding-related.
-
-The majority of the upgrade pain is in the lower-level libraries like
-Flask and Werkzeug and not in the actual high-level application code.  For
-instance all of the Flask examples that are in the Flask repository work
-out of the box on both 2.x and 3.x and did not require a single line of
-code changed.
+The majority of the upgrade work is in the lower-level libraries like
+Flask and Werkzeug, not the high-level application code.
+For example, all of the examples in the Flask repository work on both Python 2 and 3
+and did not require a single line of code changed.

```

</details>

---

## Case 4 — `7cc49dee2c4eec25`

- **repo** `fastapi/fastapi` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** 📝 Update docs (#11603)
- **commit** https://github.com/fastapi/fastapi/commit/651dd00a9e3bc75fd872737cb0fbc3a0f44b9e38
- **doc** `docs/en/docs/tutorial/first-steps.md`
- **no longer asserted after this commit** `uvicorn`, `reload`, `main`

**VERDICT: ?**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/en/docs/tutorial/first-steps.md b/docs/en/docs/tutorial/first-steps.md
index 35b2feb41..d18b25d97 100644
--- a/docs/en/docs/tutorial/first-steps.md
+++ b/docs/en/docs/tutorial/first-steps.md
@@ -325,6 +325,6 @@ There are many other objects and models that will be automatically converted to
 
 * Import `FastAPI`.
 * Create an `app` instance.
-* Write a **path operation decorator** (like `@app.get("/")`).
-* Write a **path operation function** (like `def root(): ...` above).
-* Run the development server (like `uvicorn main:app --reload`).
+* Write a **path operation decorator** using decorators like `@app.get("/")`.
+* Define a **path operation function**; for example, `def root(): ...`.
+* Run the development server using the command `fastapi dev`.

```

</details>

---

## Case 5 — `561bdb6a3a84a71c`

- **repo** `pallets/flask` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Updated mod_wsgi.rst to point to new mod_wsgi repo (#2038)
- **commit** https://github.com/pallets/flask/commit/a6a36ec72a1f65514e137b0f21708e8c61dbe4ba
- **doc** `docs/deploying/mod_wsgi.rst`
- **no longer asserted after this commit** `wiki`

**VERDICT: ?**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/deploying/mod_wsgi.rst b/docs/deploying/mod_wsgi.rst
index b06a1904..0f4af6c3 100644
--- a/docs/deploying/mod_wsgi.rst
+++ b/docs/deploying/mod_wsgi.rst
@@ -130,12 +130,12 @@ to httpd 2.4 syntax
     Require all granted
 
 
-For more information consult the `mod_wsgi wiki`_.
+For more information consult the `mod_wsgi documentation`_.
 
-.. _mod_wsgi: http://code.google.com/p/modwsgi/
-.. _installation instructions: http://code.google.com/p/modwsgi/wiki/QuickInstallationGuide
+.. _mod_wsgi: https://github.com/GrahamDumpleton/mod_wsgi
+.. _installation instructions: http://modwsgi.readthedocs.io/en/develop/installation.html
 .. _virtual python: https://pypi.python.org/pypi/virtualenv
-.. _mod_wsgi wiki: http://code.google.com/p/modwsgi/w/list
+.. _mod_wsgi documentation: http://modwsgi.readthedocs.io/en/develop/index.html
 
 Troubleshooting
 ---------------

```

</details>

---

## Case 6 — `e6ae0443a94e19cf`

- **repo** `pallets/flask` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** docs: `HTTP` -> HTTP
- **commit** https://github.com/pallets/flask/commit/6dbb015b43cbf0e1670c168b2746a3c16b6fc5a9
- **doc** `docs/tutorial/folders.rst`
- **no longer asserted after this commit** `http`

**VERDICT: ?**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/tutorial/folders.rst b/docs/tutorial/folders.rst
index e1ff229d..550d5a9b 100644
--- a/docs/tutorial/folders.rst
+++ b/docs/tutorial/folders.rst
@@ -13,7 +13,7 @@ application::
 The `flaskr` folder is not a python package, but just something where we
 drop our files. We will then put our database schema as well as main module
 into this folder. It is done in the following way. The files inside
-the `static` folder are available to users of the application via `HTTP`.
+the `static` folder are available to users of the application via HTTP.
 This is the place where css and javascript files go.  Inside the
 `templates` folder Flask will look for `Jinja2`_ templates.  The
 templates you create later in the tutorial will go in this directory.

```

</details>

---

## Case 7 — `8610444374655980`

- **repo** `pallets/flask` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** simplify mongoengine doc, redirect from mongokit
- **commit** https://github.com/pallets/flask/commit/edef8cb38b968228b0721d3cf93ac246e81e6c82
- **doc** `docs/patterns/mongoengine.rst`
- **no longer asserted after this commit** `get_connection`, `age__not__mod`, `istartswith`, `stringfield`, `collection`, `connection`, `startswith`, `icontains`, `iendswith`, `objectids`, `contains`, `endswith`

**VERDICT: ?**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/patterns/mongoengine.rst b/docs/patterns/mongoengine.rst
index d635128e..015e7b61 100644
--- a/docs/patterns/mongoengine.rst
+++ b/docs/patterns/mongoengine.rst
@@ -1,32 +1,30 @@
-.. mongoengine-pattern:
+MongoDB with MongoEngine
+========================
 
-MongoEngine in Flask
-====================
+Using a document database like MongoDB is a common alternative to
+relational SQL databases. This pattern shows how to use
+`MongoEngine`_, a document mapper library, to integrate with MongoDB.
 
-Using a document database rather than a full DBMS gets more common these days.
-This pattern shows how to use MongoEngine, a document mapper library, to
-integrate with MongoDB.
-
-This pattern requires a running MongoDB server, MongoEngine_ and Flask-MongoEngine_
-libraries installed::
+A running MongoDB server and `Flask-MongoEngine`_ are required. ::
 
     pip install flask-mongoengine
 
 .. _MongoEngine: http://mongoengine.org
-.. _Flask-MongoEngine: http://docs.mongoengine.org/projects/flask-mongoengine/en/latest/>`_
+.. _Flask-MongoEngine: https://flask-mongoengine.readthedocs.io
+
 
 Configuration
 -------------
 
-Basic setup can be done by defining ``MONGODB_SETTINGS`` on App config and then
-creating a ``MongoEngine`` instance::
+Basic setup can be done by defining ``MONGODB_SETTINGS`` on
+``app.config`` and creating a ``MongoEngine`` instance. ::
 
     from flask import Flask
     from flask_mongoengine import MongoEngine
 
     app = Flask(__name__)
     app.config['MONGODB_SETTINGS'] = {
-        'host': "mongodb://localhost:27017/mydb"
+        "db": "myapp",
     }
     db = MongoEngine(app)
 
@@ -34,40 +32,38 @@ creating a ``MongoEngine`` instance::
 Mapping Documents
 -----------------
 
-To declare models that will represent your Mongo documents, just create a class that
-inherits from ``Document`` and declare each of the fields::
-
-    from mongoengine import *
-
-
-    class Movie(Document):
+To declare a model that represents a Mongo document, create a class that
+inherits from ``Document`` and declare each of the fields. ::
 
-        title = StringField(required=True)
-        year = IntField()
-        rated = StringField()
-        director = StringField()
-        actors = ListField()
+    import mongoengine as me
 
-If the model has embedded documents, use ``EmbeddedDocument`` to defined the fields of
-the embedded document and ``EmbeddedDocumentField`` to declare it on the parent document::
+    class Movie(me.Document):
+        title = me.StringField(required=True)
+        year = me.IntField()
+        rated = me.StringField()
+        director = me.StringField()
+        actors = me.ListField()
 
-    class Imdb(EmbeddedDocument):
+If the document has nested fields, use ``EmbeddedDocument`` to
+defined the fields of the embedded document and
+``EmbeddedDocumentField`` to declare it on the parent document. ::
 
-        imdb_id = StringField()
-        rating = DecimalField()
-        votes = IntField()
-
-
-    class Movie(Document):
+    class Imdb(me.EmbeddedDocument):
+        imdb_id = me.StringField()
+        rating = me.DecimalField()
+        votes = me.IntField()
 
+    class Movie(me.Document):
         ...
-        imdb = EmbeddedDocumentField(Imdb)
+        imdb = me.EmbeddedDocumentField(Imdb)
 
 
 Creating Data
 -------------
 
-Just create the objects and call ``save()``::
+Instantiate your document class with keyword arguments for the fields.
+You can also assign values to the field attributes after instantiation.
+Then call ``doc.save()``. ::
 
     bttf = Movie(title="Back To The Future", year=1985)
     bttf.actors = [
@@ -81,73 +77,27 @@ Just create the objects and call ``save()``::
 Queries
 -------
 
-Use the class ``objects`` attribute to make queries::
+Use the class ``objects`` attribute to make queries. A keyword argument
+looks for an equal value on the field. ::
 
-    bttf = Movies.objects(title="Back To The Future").get()  # Throw error if not unique
+   
```

</details>

---

## Case 8 — `085c18d5ae3cab59`

- **repo** `pallets/flask` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** use dashes for command names
- **commit** https://github.com/pallets/flask/commit/146df0f9e8ea8a55bb66b7cc52d186e288580b92
- **doc** `docs/cli.rst`
- **no longer asserted after this commit** `create_user`

**VERDICT: ?**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/cli.rst b/docs/cli.rst
index a8dd8f24..85b99fcb 100644
--- a/docs/cli.rst
+++ b/docs/cli.rst
@@ -191,10 +191,10 @@ environment variables. The variables use the pattern
 ``FLASK_COMMAND_OPTION``. For example, to set the port for the run
 command, instead of ``flask run --port 8000``:
 
-.. code-block:: none
+.. code-block:: bash
 
-    export FLASK_RUN_PORT=8000
-    flask run
+    $ export FLASK_RUN_PORT=8000
+    $ flask run
      * Running on http://127.0.0.1:8000/
 
 These can be added to the ``.flaskenv`` file just like ``FLASK_APP`` to
@@ -207,9 +207,9 @@ Disable dotenv
 The ``flask`` command will show a message if it detects dotenv files but
 python-dotenv is not installed.
 
-.. code-block:: none
+.. code-block:: bash
 
-    flask run
+    $ flask run
      * Tip: There are .env files present. Do "pip install python-dotenv" to use them.
 
 You can tell Flask not to load dotenv files even when python-dotenv is
@@ -219,10 +219,10 @@ a project runner that loads them already. Keep in mind that the
 environment variables must be set before the app loads or it won't
 configure as expected.
 
-.. code-block:: none
+.. code-block:: bash
 
-    export FLASK_SKIP_DOTENV=1
-    flask run
+    $ export FLASK_SKIP_DOTENV=1
+    $ flask run
 
 
 Environment Variables From virtualenv
@@ -234,11 +234,11 @@ script. Activating the virtualenv will set the variables.
 
 Unix Bash, :file:`venv/bin/activate`::
 
-    export FLASK_APP=hello
+    $ export FLASK_APP=hello
 
 Windows CMD, :file:`venv\\Scripts\\activate.bat`::
 
-    set FLASK_APP=hello
+    > set FLASK_APP=hello
 
 It is preferred to use dotenv support over this, since :file:`.flaskenv` can be
 committed to the repository so that it works automatically wherever the project
@@ -251,7 +251,7 @@ Custom Commands
 The ``flask`` command is implemented using `Click`_. See that project's
 documentation for full information about writing commands.
 
-This example adds the command ``create_user`` that takes the argument
+This example adds the command ``create-user`` that takes the argument
 ``name``. ::
 
     import click
@@ -259,14 +259,14 @@ This example adds the command ``create_user`` that takes the argument
 
     app = Flask(__name__)
 
-    @app.cli.command()
-    @click.argument('name')
+    @app.cli.command("create-user")
+    @click.argument("name")
     def create_user(name):
         ...
 
 ::
 
-    flask create_user admin
+    $ flask create-user admin
 
 This example adds the same command, but as ``user create``, a command in a
 group. This is useful if you want to organize multiple related commands. ::
@@ -287,7 +287,7 @@ group. This is useful if you want to organize multiple related commands. ::
 
 ::
 
-    flask user create demo
+    $ flask user create demo
 
 See :ref:`testing-cli` for an overview of how to test your custom
 commands.

```

</details>

---

## Case 9 — `240c6ef7ddad3f16`

- **repo** `psf/requests` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Cleanup defunct links from community docs page
- **commit** https://github.com/psf/requests/commit/6106a63eb6c0fa490efa73d44388ac25b1b08af4
- **doc** `docs/community/out-there.rst`
- **no longer asserted after this commit** `humans`, `python`, `talk`

**VERDICT: ?**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/community/out-there.rst b/docs/community/out-there.rst
index c33ab3c9..c75c71f6 100644
--- a/docs/community/out-there.rst
+++ b/docs/community/out-there.rst
@@ -1,22 +1,10 @@
 Integrations
 ============
 
-Python for iOS
---------------
-
-Requests is built into the wonderful `Python for iOS <https://itunes.apple.com/us/app/python-2.7-for-ios/id485729872?mt=Python8>`_ runtime!
-
-To give it a try, simply::
-
-    import requests
-
-
 Articles & Talks
 ================
-- `Python for the Web <https://www.gun.io/blog/python-for-the-web>`_ teaches how to use Python to interact with the web, using Requests.
 - `Daniel Greenfeld's Review of Requests <https://pydanny.blogspot.com/2011/05/python-http-requests-for-humans.html>`_
-- `My 'Python for Humans' talk <http://python-for-humans.heroku.com>`_ ( `audio <https://codeconf.s3.amazonaws.com/2011/pycodeconf/talks/PyCodeConf2011%20-%20Kenneth%20Reitz.m4a>`_ )
-- `Issac Kelly's 'Consuming Web APIs' talk <https://issackelly.github.com/Consuming-Web-APIs-with-Python-Talk/slides/slides.html>`_
+- `Issac Kelly's 'Consuming Web APIs' talk <https://issackelly.github.io/Consuming-Web-APIs-with-Python-Talk/slides/slides.html>`_
 - `Blog post about Requests via Yum <https://arunsag.wordpress.com/2011/08/17/new-package-python-requests-http-for-humans/>`_
 - `Russian blog post introducing Requests <https://habr.com/post/126262/>`_
 - `Sending JSON in Requests <http://www.coglib.com/~icordasc/blog/2014/11/sending-json-in-requests.html>`_

```

</details>

---

## Case 10 — `78eb6cde3be96b82`

- **repo** `fastapi/fastapi` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** 📝 Update docs about serving FastAPI: ASGI servers, Docker containers, etc. (#12069)
- **commit** https://github.com/fastapi/fastapi/commit/bd1b77548f0f1788c5ae0fbd8144f5139bdb959e
- **doc** `docs/en/docs/deployment/docker.md`
- **no longer asserted after this commit** `dockerfile`, `pyproject`, `gunicorn`, `tiangolo`, `headers`, `python3`, `uvicorn`, `without`, `export`, `hashes`, `num:10`, `num:11`

**VERDICT: ?**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/en/docs/deployment/docker.md b/docs/en/docs/deployment/docker.md
index ab1c2201f..2d832a238 100644
--- a/docs/en/docs/deployment/docker.md
+++ b/docs/en/docs/deployment/docker.md
@@ -167,22 +167,22 @@ def read_item(item_id: int, q: Union[str, None] = None):
 Now in the same project directory create a file `Dockerfile` with:
 
 ```{ .dockerfile .annotate }
-# (1)
+# (1)!
 FROM python:3.9
 
-# (2)
+# (2)!
 WORKDIR /code
 
-# (3)
+# (3)!
 COPY ./requirements.txt /code/requirements.txt
 
-# (4)
+# (4)!
 RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
 
-# (5)
+# (5)!
 COPY ./app /code/app
 
-# (6)
+# (6)!
 CMD ["fastapi", "run", "app/main.py", "--port", "80"]
 ```
 
@@ -400,10 +400,10 @@ COPY ./requirements.txt /code/requirements.txt
 
 RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
 
-# (1)
+# (1)!
 COPY ./main.py /code/
 
-# (2)
+# (2)!
 CMD ["fastapi", "run", "main.py", "--port", "80"]
 ```
 
@@ -456,11 +456,11 @@ Without using containers, making applications run on startup and with restarts c
 
 ## Replication - Number of Processes
 
-If you have a <abbr title="A group of machines that are configured to be connected and work together in some way.">cluster</abbr> of machines with **Kubernetes**, Docker Swarm Mode, Nomad, or another similar complex system to manage distributed containers on multiple machines, then you will probably want to **handle replication** at the **cluster level** instead of using a **process manager** (like Gunicorn with workers) in each container.
+If you have a <abbr title="A group of machines that are configured to be connected and work together in some way.">cluster</abbr> of machines with **Kubernetes**, Docker Swarm Mode, Nomad, or another similar complex system to manage distributed containers on multiple machines, then you will probably want to **handle replication** at the **cluster level** instead of using a **process manager** (like Uvicorn with workers) in each container.
 
 One of those distributed container management systems like Kubernetes normally has some integrated way of handling **replication of containers** while still supporting **load balancing** for the incoming requests. All at the **cluster level**.
 
-In those cases, you would probably want to build a **Docker image from scratch** as [explained above](#dockerfile), installing your dependencies, and running **a single Uvicorn process** instead of running something like Gunicorn with Uvicorn workers.
+In those cases, you would probably want to build a **Docker image from scratch** as [explained above](#dockerfile), installing your dependencies, and running **a single Uvicorn process** instead of using multiple Uvicorn workers.
 
 ### Load Balancer
 
@@ -490,37 +490,44 @@ And normally this **load balancer** would be able to handle requests that go to
 
 In this type of scenario, you probably would want to have **a single (Uvicorn) process per container**, as you would already be handling replication at the cluster level.
 
-So, in this case, you **would not** want to have a process manager like Gunicorn with Uvicorn workers, or Uvicorn using its own Uvicorn workers. You would want to have just a **single Uvicorn process** per container (but probably multiple containers).
+So, in this case, you **would not** want to have a multiple workers in the container, for example with the `--workers` command line option.You would want to have just a **single Uvicorn process** per container (but probably multiple containers).
 
-Having another process manager inside the container (as would be with Gunicorn or Uvicorn managing Uvicorn workers) would only add **unnecessary complexity** that you are most probably already taking care of with your cluster system.
+Having another process manager inside the container (as would be with multiple workers) would only add **unnecessary complexity** that you are most probably already taking care of with your cluster system.
 
 ### Containers with Mul
```

</details>

---

## Case 11 — `75f61a6ce4149482`

- **repo** `fastapi/fastapi` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** 📝 Add docs for `pyproject.toml` with `entrypoint` (#15075)
- **commit** https://github.com/fastapi/fastapi/commit/edaf23943c2959d1b59eec4f8322f534ddc21033
- **doc** `docs/en/docs/fastapi-cli.md`
- **no longer asserted after this commit** `fast`

**VERDICT: ?**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/en/docs/fastapi-cli.md b/docs/en/docs/fastapi-cli.md
index e0b40b500..17898888f 100644
--- a/docs/en/docs/fastapi-cli.md
+++ b/docs/en/docs/fastapi-cli.md
@@ -1,15 +1,15 @@
 # FastAPI CLI { #fastapi-cli }
 
-**FastAPI CLI** is a command line program that you can use to serve your FastAPI app, manage your FastAPI project, and more.
+**FastAPI <abbr title="command line interface">CLI</abbr>** is a command line program that you can use to serve your FastAPI app, manage your FastAPI project, and more.
 
-When you install FastAPI (e.g. with `pip install "fastapi[standard]"`), it includes a package called `fastapi-cli`, this package provides the `fastapi` command in the terminal.
+When you install FastAPI (e.g. with `pip install "fastapi[standard]"`), it comes with a command line program you can run in the terminal.
 
 To run your FastAPI app for development, you can use the `fastapi dev` command:
 
 <div class="termy">
 
 ```console
-$ <font color="#4E9A06">fastapi</font> dev <u style="text-decoration-style:solid">main.py</u>
+$ <font color="#4E9A06">fastapi</font> dev
 
   <span style="background-color:#009485"><font color="#D3D7CF"> FastAPI </font></span>  Starting development server 🚀
 
@@ -46,14 +46,67 @@ $ <font color="#4E9A06">fastapi</font> dev <u style="text-decoration-style:solid
 
 </div>
 
-The command line program called `fastapi` is **FastAPI CLI**.
+/// tip
 
-FastAPI CLI takes the path to your Python program (e.g. `main.py`) and automatically detects the `FastAPI` instance (commonly named `app`), determines the correct import process, and then serves it.
+For production you would use `fastapi run` instead of `fastapi dev`. 🚀
 
-For production you would use `fastapi run` instead. 🚀
+///
 
 Internally, **FastAPI CLI** uses [Uvicorn](https://www.uvicorn.dev), a high-performance, production-ready, ASGI server. 😎
 
+The `fastapi` CLI will try to detect automatically the FastAPI app to run, assuming it's an object called `app` in a file `main.py` (or a couple other variants).
+
+But you can configure explicitly the app to use.
+
+## Configure the app `entrypoint` in `pyproject.toml` { #configure-the-app-entrypoint-in-pyproject-toml }
+
+You can configure where your app is located in a `pyproject.toml` file like:
+
+```toml
+[tool.fastapi]
+entrypoint = "main:app"
+```
+
+That `entrypoint` will tell the `fastapi` command that it should import the app like:
+
+```python
+from main import app
+```
+
+If your code was structured like:
+
+```
+.
+├── backend
+│   ├── main.py
+│   ├── __init__.py
+```
+
+Then you would set the `entrypoint` as:
+
+```toml
+[tool.fastapi]
+entrypoint = "backend.main:app"
+```
+
+which would be equivalent to:
+
+```python
+from backend.main import app
+```
+
+### `fastapi dev` with path { #fastapi-dev-with-path }
+
+You can also pass the file path to the `fastapi dev` command, and it will guess the FastAPI app object to use:
+
+```console
+$ fastapi dev main.py
+```
+
+But you would have to remember to pass the correct path every time you call the `fastapi` command.
+
+Additionally, other tools might not be able to find it, for example the [VS Code Extension](editor-support.md) or [FastAPI Cloud](https://fastapicloud.com), so it is recommended to use the `entrypoint` in `pyproject.toml`.
+
 ## `fastapi dev` { #fastapi-dev }
 
 Running `fastapi dev` initiates development mode.
@@ -62,7 +115,7 @@ By default, **auto-reload** is enabled, automatically reloading the server when
 
 ## `fastapi run` { #fastapi-run }
 
-Executing `fastapi run` starts FastAPI in production mode by default.
+Executing `fastapi run` starts FastAPI in production mode.
 
 By default, **auto-reload** is disabled. It also listens on the IP address `0.0.0.0`, which means all the available IP addresses, this way it will be publicly accessible to anyone that can communicate with the machine. This is how you would normally run it in production, for example, in a container.
 

```

</details>

---

## Case 12 — `10371c50241da25b`

- **repo** `pallets/flask` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Reordered deployment docs
- **commit** https://github.com/pallets/flask/commit/b9cae3564ad31876d977c24a09d760e77ca992f3
- **doc** `docs/deploying.rst`
- **no longer asserted after this commit** `browsers`

**VERDICT: ?**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/deploying.rst b/docs/deploying.rst
index e04112f0..0d0ed19e 100644
--- a/docs/deploying.rst
+++ b/docs/deploying.rst
@@ -11,6 +11,133 @@ how to use a WSGI app with it.  Just remember that your application object
 is the actual WSGI application.
 
 
+mod_wsgi (Apache)
+-----------------
+
+If you are using the `Apache`_ webserver you should consider using `mod_wsgi`_.
+
+.. _Apache: http://httpd.apache.org/
+
+Installing `mod_wsgi`
+`````````````````````
+
+If you don't have `mod_wsgi` installed yet you have to either install it using
+a package manager or compile it yourself.
+
+The mod_wsgi `installation instructions`_ cover installation instructions for
+source installations on UNIX systems.
+
+If you are using ubuntu / debian you can apt-get it and activate it as follows::
+
+    # apt-get install libapache2-mod-wsgi
+
+On FreeBSD install `mod_wsgi` by compiling the `www/mod_wsgi` port or by using
+pkg_add::
+
+    # pkg_add -r mod_wsgi
+
+If you are using pkgsrc you can install `mod_wsgi` by compiling the
+`www/ap2-wsgi` package.
+
+If you encounter segfaulting child processes after the first apache reload you
+can safely ignore them.  Just restart the server.
+
+Creating a `.wsgi` file
+```````````````````````
+
+To run your application you need a `yourapplication.wsgi` file.  This file
+contains the code `mod_wsgi` is executing on startup to get the application
+object.  The object called `application` in that file is then used as
+application.
+
+For most applications the following file should be sufficient::
+
+    from yourapplication import app as application
+
+If you don't have a factory function for application creation but a singleton
+instance you can directly import that one as `application`.
+
+Store that file somewhere where you will find it again (eg:
+`/var/www/yourapplication`) and make sure that `yourapplication` and all
+the libraries that are in use are on the python load path.  If you don't
+want to install it system wide consider using a `virtual python`_ instance.
+
+Configuring Apache
+``````````````````
+
+The last thing you have to do is to create an Apache configuration file for
+your application.  In this example we are telling `mod_wsgi` to execute the
+application under a different user for security reasons:
+
+.. sourcecode:: apache
+
+    <VirtualHost *>
+        ServerName example.com
+
+        WSGIDaemonProcess yourapplication user=user1 group=group1 threads=5
+        WSGIScriptAlias / /var/www/yourapplication/yourapplication.wsgi
+
+        <Directory /var/www/yourapplication>
+            WSGIProcessGroup yourapplication
+            WSGIApplicationGroup %{GLOBAL}
+            Order deny,allow
+            Allow from all
+        </Directory>
+    </VirtualHost>
+
+For more information consult the `mod_wsgi wiki`_.
+
+.. _mod_wsgi: http://code.google.com/p/modwsgi/
+.. _installation instructions: http://code.google.com/p/modwsgi/wiki/QuickInstallationGuide
+.. _virtual python: http://pypi.python.org/pypi/virtualenv
+.. _mod_wsgi wiki: http://code.google.com/p/modwsgi/wiki/
+
+
+CGI
+---
+
+If all other deployment methods do not work, CGI will work for sure.  CGI
+is supported by all major servers but usually has a less-than-optimal
+performance.
+
+This is also the way you can use a Flask application on Google's
+`AppEngine`_, there however the execution does happen in a CGI-like
+environment.  The application's performance is unaffected because of that.
+
+.. _AppEngine: http://code.google.com/appengine/
+
+Creating a `.cgi` file
+``````````````````````
+
+First you need to create the CGI application file.  Let's call it
+`yourapplication.cgi`::
+
+    #!/usr/bin/python
+    from wsgiref.handlers import CGIHandler
+    from yourapplication import app
+
+    CGIHandler().run(app)
+
+If you're running Python 2.4 you will need the :mod:`wsgiref` package.  Python
+2.5 and higher ship this as part of the standard library.
+
+Server Setup
+````````````
+
+Usually there are
```

</details>

---

## Case 13 — `2a019e6f76764ccf`

- **repo** `pallets/flask` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Updated documentation to use teardown request where appropriate
- **commit** https://github.com/pallets/flask/commit/a9fc040c39109f86f3ea98440215b4a54f291f53
- **doc** `docs/patterns/sqlite3.rst`
- **no longer asserted after this commit** `after_request`, `after`

**VERDICT: ?**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/patterns/sqlite3.rst b/docs/patterns/sqlite3.rst
index 68833234..d0ec5a27 100644
--- a/docs/patterns/sqlite3.rst
+++ b/docs/patterns/sqlite3.rst
@@ -5,7 +5,7 @@ Using SQLite 3 with Flask
 
 In Flask you can implement the opening of database connections at the
 beginning of the request and closing at the end with the
-:meth:`~flask.Flask.before_request` and :meth:`~flask.Flask.after_request`
+:meth:`~flask.Flask.before_request` and :meth:`~flask.Flask.teardown_request`
 decorators in combination with the special :class:`~flask.g` object.
 
 So here is a simple example of how you can use SQLite 3 with Flask::
@@ -22,10 +22,34 @@ So here is a simple example of how you can use SQLite 3 with Flask::
     def before_request():
         g.db = connect_db()
 
-    @app.after_request
-    def after_request(response):
+    @app.teardown_request
+    def teardown_request(exception):
         g.db.close()
-        return response
+
+Connect on Demand
+-----------------
+
+The downside of this approach is that this will only work if Flask
+executed the before-request handlers for you.  If you are attempting to
+use the database from a script or the interactive Python shell you would
+have to do something like this::
+
+    with app.test_request_context()
+        app.preprocess_request()
+        # now you can use the g.db object
+
+In order to trigger the execution of the connection code.  You won't be
+able to drop the dependency on the request context this way, but you could
+make it so that the application connects when necessary::
+
+    def get_connection():
+        db = getattr(g, '_db', None)
+        if db is None:
+            db = g._db = connect_db()
+        return db
+
+Downside here is that you have to use ``db = get_connection()`` instead of
+just being able to use ``g.db`` directly.
 
 .. _easy-querying:
 

```

</details>

---

## Case 14 — `b450b28af586605c`

- **repo** `pallets/flask` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Stop recommending Tornado as a WSGI server
- **commit** https://github.com/pallets/flask/commit/e401a83fc5e57c6ac12175edcf3ef9157f094d7e
- **doc** `docs/deploying/wsgi-standalone.rst`
- **no longer asserted after this commit** `friendfeed`, `tornado`, `friend`, `feed`

**VERDICT: ?**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/deploying/wsgi-standalone.rst b/docs/deploying/wsgi-standalone.rst
index 11d07831..77a564a2 100644
--- a/docs/deploying/wsgi-standalone.rst
+++ b/docs/deploying/wsgi-standalone.rst
@@ -27,28 +27,6 @@ For example, to run a Flask application with 4 worker processes (``-w
 .. _eventlet: http://eventlet.net/
 .. _greenlet: http://greenlet.readthedocs.org/en/latest/
 
-Tornado
---------
-
-`Tornado`_ is an open source version of the scalable, non-blocking web
-server and tools that power `FriendFeed`_.  Because it is non-blocking and
-uses epoll, it can handle thousands of simultaneous standing connections,
-which means it is ideal for real-time web services.  Integrating this
-service with Flask is straightforward::
-
-    from tornado.wsgi import WSGIContainer
-    from tornado.httpserver import HTTPServer
-    from tornado.ioloop import IOLoop
-    from yourapplication import app
-
-    http_server = HTTPServer(WSGIContainer(app))
-    http_server.listen(5000)
-    IOLoop.instance().start()
-
-
-.. _Tornado: http://www.tornadoweb.org/
-.. _FriendFeed: http://friendfeed.com/
-
 Gevent
 -------
 

```

</details>

---

## Case 15 — `990feb02f5700f79`

- **repo** `encode/httpx` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Tweak
- **commit** https://github.com/encode/httpx/commit/f6a2aef13a63d405141ff97123f08efaf65c7d80
- **doc** `README.md`
- **no longer asserted after this commit** `content`, `headers`, `params`, `init`

**VERDICT: ?**

<details><summary>doc diff</summary>

```diff
diff --git a/README.md b/README.md
index 69bda6e..6f4e7cf 100644
--- a/README.md
+++ b/README.md
@@ -145,12 +145,8 @@ what gets sent over the wire.*
 >>> response = client.send(request)
 ```
 
-<<<<<<< HEAD
 * `def __init__(method, url, params, [content], [headers], [cookies])`
-=======
-* `def __init__(method, url, params, content, headers)`
->>>>>>> cookies
-* `.method` - **str** (Uppercased)
+* `.method` - **str**
 * `.url` - **URL**
 * `.content` - **byte** or **byte async iterator**
 * `.headers` - **Headers**

```

</details>

---

## Case 16 — `7aa792000dc8986d`

- **repo** `encode/httpx` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Update docs for 0.15 (#1306)
- **commit** https://github.com/encode/httpx/commit/c923f1af912eae78fa977aa740e4e750ab04c650
- **doc** `docs/index.md`
- **no longer asserted after this commit** `ver:0.14`, `chardet`

**VERDICT: ?**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/index.md b/docs/index.md
index c0d5e1a..16194de 100644
--- a/docs/index.md
+++ b/docs/index.md
@@ -27,7 +27,7 @@ HTTPX is a fully featured HTTP client for Python 3, which provides sync and asyn
 !!! note
     HTTPX should currently be considered in beta.
 
-    We believe we've got the public API to a stable point now, but would strongly recommend pinning your dependencies to the `0.14.*` release, so that you're able to properly review [API changes between package updates](https://github.com/encode/httpx/blob/master/CHANGELOG.md).
+    We believe we've got the public API to a stable point now, but would strongly recommend pinning your dependencies to the `0.15.*` release, so that you're able to properly review [API changes between package updates](https://github.com/encode/httpx/blob/master/CHANGELOG.md).
 
     A 1.0 release is expected to be issued sometime in late 2020.
 
@@ -110,7 +110,6 @@ The HTTPX project relies on these excellent libraries:
   * `h11` - HTTP/1.1 support.
   * `h2` - HTTP/2 support. *(Optional)*
 * `certifi` - SSL certificates.
-* `chardet` - Fallback auto-detection for response encoding.
 * `rfc3986` - URL parsing & normalization.
   * `idna` - Internationalized domain name support.
 * `sniffio` - Async library autodetection.

```

</details>

---

## Case 17 — `f38aaf95ae33af92`

- **repo** `pallets/flask` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Update installation documentation for using 'pip' command (#1920)
- **commit** https://github.com/pallets/flask/commit/b7a0cc61c54dbfebf8c3b21634ec9e37596b1e9a
- **doc** `docs/installation.rst`
- **no longer asserted after this commit** `ez_setup`, `setup`

**VERDICT: ?**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/installation.rst b/docs/installation.rst
index 638d07ce..91d95270 100644
--- a/docs/installation.rst
+++ b/docs/installation.rst
@@ -40,24 +40,20 @@ installations of Python, one for each project.  It doesn't actually install
 separate copies of Python, but it does provide a clever way to keep different
 project environments isolated.  Let's see how virtualenv works.
 
-If you are on Mac OS X or Linux, chances are that one of the following two
-commands will work for you::
-
-    $ sudo easy_install virtualenv
-
-or even better::
+If you are on Mac OS X or Linux, chances are that the following
+command will work for you::
 
     $ sudo pip install virtualenv
 
-One of these will probably install virtualenv on your system.  Maybe it's even
+It will probably install virtualenv on your system.  Maybe it's even
 in your package manager.  If you use Ubuntu, try::
 
     $ sudo apt-get install python-virtualenv
 
-If you are on Windows and don't have the :command:`easy_install` command, you must
+If you are on Windows and don't have the ``easy_install`` command, you must
 install it first.  Check the :ref:`windows-easy-install` section for more
 information about how to do that.  Once you have it installed, run the same
-commands as above, but without the :command:`sudo` prefix.
+commands as above, but without the ``sudo`` prefix.
 
 Once you have virtualenv installed, just fire up a shell and create
 your own environment.  I usually create a project folder and a :file:`venv`
@@ -99,19 +95,19 @@ System-Wide Installation
 ------------------------
 
 This is possible as well, though I do not recommend it.  Just run
-:command:`pip` with root privileges::
+``pip`` with root privileges::
 
     $ sudo pip install Flask
 
 (On Windows systems, run it in a command-prompt window with administrator
-privileges, and leave out :command:`sudo`.)
+privileges, and leave out ``sudo``.)
 
 
 Living on the Edge
 ------------------
 
 If you want to work with the latest version of Flask, there are two ways: you
-can either let :command:`pip` pull in the development version, or you can tell
+can either let ``pip`` pull in the development version, or you can tell
 it to operate on a git checkout.  Either way, virtualenv is recommended.
 
 Get the git checkout in a new virtualenv and run in development mode::
@@ -131,40 +127,34 @@ This will pull in the dependencies and activate the git head as the current
 version inside the virtualenv.  Then all you have to do is run ``git pull
 origin`` to update to the latest version.
 
-
 .. _windows-easy-install:
 
 `pip` and `setuptools` on Windows
 ---------------------------------
 
-Sometimes getting the standard "Python packaging tools" like *pip*, *setuptools*
-and *virtualenv* can be a little trickier, but nothing very hard. The two crucial
-packages you will need are setuptools and pip - these will let you install
-anything else (like virtualenv). Fortunately there are two "bootstrap scripts"
-you can run to install either.
+Sometimes getting the standard "Python packaging tools" like ``pip``, ``setuptools``
+and ``virtualenv`` can be a little trickier, but nothing very hard. The crucial
+package you will need is pip - this will let you install
+anything else (like virtualenv). Fortunately there is a "bootstrap script"
+you can run to install.
 
-If you don't currently have either, then :file:`get-pip.py` will install both for you
-(you won't need to run :file:`ez_setup.py`).
+If you don't currently have ``pip``, then `get-pip.py` will install it for you.
 
 `get-pip.py`_
 
-To install the latest setuptools, you can use its bootstrap file:
-
-`ez_setup.py`_
-
-Either should be double-clickable once you download them. If you already have pip,
+It should be double-clickable once you download it. If you already have ``pip``,
 you can upgrade them by running::
 
     > pip install --upgrade pip setuptools
 
-Most often, once you pull up a command prompt you want to be able to type :command:`pip
```

</details>

---

## Case 18 — `f68e747201410b1c`

- **repo** `pallets/flask` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** update patterns, snippets, extensions docs
- **commit** https://github.com/pallets/flask/commit/e01b68e7ee66f7c5ec221bcb9e0cd3526153664d
- **doc** `docs/extensions.rst`
- **no longer asserted after this commit** `extension`

**VERDICT: ?**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/extensions.rst b/docs/extensions.rst
index ea9980e3..836552d7 100644
--- a/docs/extensions.rst
+++ b/docs/extensions.rst
@@ -43,7 +43,7 @@ Building Extensions
 
 While the `PyPI <pypi_>`_ contains many Flask extensions, you may
 not find an extension that fits your need. If this is the case, you can
-create your own. Read :ref:`extension-dev` to develop your own Flask
+create your own. Read :doc:`/extensiondev` to develop your own Flask
 extension.
 
 

```

</details>

---

## Case 19 — `1d222d6fd431c7ae`

- **repo** `pallets/flask` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** rewrite testing docs
- **commit** https://github.com/pallets/flask/commit/761d7e165244709221888827cec764d8f3a3d21a
- **doc** `docs/api.rst`
- **no longer asserted after this commit** `resources`, `faking`

**VERDICT: ?**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/api.rst b/docs/api.rst
index 09fc71a9..1a87f8d4 100644
--- a/docs/api.rst
+++ b/docs/api.rst
@@ -168,9 +168,9 @@ thing, like it does for :class:`request` and :class:`session`.
     :attr:`Flask.app_ctx_globals_class`, which defaults to
     :class:`ctx._AppCtxGlobals`.
 
-    This is a good place to store resources during a request. During
-    testing, you can use the :ref:`faking-resources` pattern to
-    pre-configure such resources.
+    This is a good place to store resources during a request. For
+    example, a ``before_request`` function could load a user object from
+    a session id, then set ``g.user`` to be used in the view function.
 
     This is a proxy. See :ref:`notes-on-proxies` for more information.
 

```

</details>

---

## Case 20 — `fa9f663f389d127d`

- **repo** `pydantic/pydantic` · **shape** B
- **basis** `doc_only_commit_modified_existing_prose`
- **subject** Update Mypy docs with correct output from Mypy (#8395)
- **commit** https://github.com/pydantic/pydantic/commit/ed0fd9b13c8d40260744b62de948566c5be153bd
- **doc** `docs/contributing.md`
- **no longer asserted after this commit** `docs`, `make`

**VERDICT: ?**

<details><summary>doc diff</summary>

```diff
diff --git a/docs/contributing.md b/docs/contributing.md
index a2d1b39d8..a3ec77ae9 100644
--- a/docs/contributing.md
+++ b/docs/contributing.md
@@ -108,7 +108,7 @@ If you've made any changes to the documentation (including changes to function s
 # Build documentation
 make docs
 # If you have changed the documentation, make sure it builds successfully.
-# You can also use `make docs-serve` to serve the documentation at localhost:8000
+# You can also use `pdm run mkdocs serve` to serve the documentation at localhost:8000
 ```
 
 ### Commit and push your changes

```

</details>

---

